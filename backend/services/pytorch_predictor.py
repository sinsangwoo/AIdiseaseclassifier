"""
PyTorch 기반 예측기 + Grad-CAM 통합 서비스 (Phase E 개선)

Phase E 변경사항:
  E-2: LOW 신뢰도(< 0.50) 시 히트맵 이미지 미생성, low_confidence 플래그 반환
  E-4: gradcam_time_ms 필드로 성능 측정값 응답에 포함
  기타: 원본 이미지 크기 검증 (최소 32×32)
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
from PIL import Image

try:
    import torch
    import torchvision.transforms as T
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from backend.models.model_definition import (
    build_model,
    GRADCAM_TARGET_LAYER,
    MODEL_INPUT_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    TORCH_AVAILABLE as MODEL_TORCH_AVAILABLE,
)
from backend.services.gradcam import GradCAM, get_reliability_level
from backend.services.heatmap_renderer import HeatmapRenderer
from backend.utils import get_logger

# Phase E-2: LOW 신뢰도 시 히트맵 생성 억제 임계값
LOW_CONFIDENCE_THRESHOLD = 0.50
# Phase E: 이미지 최소 크기
MIN_IMAGE_DIMENSION = 32


class PyTorchPredictor:
    """
    PyTorch 모델로 예측 + Grad-CAM 히트맵을 한 번에 생성하는 서비스 클래스

    Phase E 추가:
      - LOW 신뢰도 이미지에 대한 히트맵 생성 억제
      - gradcam_time_ms 성능 측정
      - 이미지 크기 사전 검증
    """

    def __init__(
        self,
        weights_path: Optional[str] = None,
        labels_path: Optional[str] = None,
        num_classes: int = 2,
    ):
        self.logger = get_logger("aiclassifier.gradcam")
        self._ready = False
        self.model = None
        self.gradcam = None
        self.class_names: List[str] = []
        self.num_classes = num_classes

        if labels_path and Path(labels_path).exists():
            with open(labels_path, "r", encoding="utf-8") as f:
                self.class_names = [
                    line.strip().split(" ", 1)[1]
                    for line in f
                    if line.strip()
                ]
            self.num_classes = len(self.class_names)
            self.logger.info(f"레이블 로드: {self.class_names}")

        if not TORCH_AVAILABLE:
            self.logger.warning(
                "PyTorch 미설치 → Grad-CAM 비활성화. "
                "`pip install torch torchvision` 으로 설치하세요."
            )
            return

        try:
            self.model = build_model(
                num_classes=self.num_classes,
                weights_path=weights_path,
            )
            self.gradcam = GradCAM(self.model, GRADCAM_TARGET_LAYER)
            self._ready = True
            weight_info = weights_path if weights_path else "(랜덤 초기화)"
            self.logger.info(f"PyTorch 모델 로드 완료: {weight_info}")
        except Exception as exc:
            self.logger.warning(f"PyTorch 모델 로드 실패 → Grad-CAM 비활성화: {exc}")

    @property
    def is_ready(self) -> bool:
        return self._ready

    def predict_with_gradcam(
        self,
        image_bytes: bytes,
        existing_predictions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        이미지 바이트를 받아 Grad-CAM 히트맵 딕셔너리를 반환합니다.

        Phase E 추가 반환 필드:
          gradcam_time_ms : float  - Grad-CAM 생성 소요 시간 (ms)
          low_confidence  : bool   - True 면 신뢰도 낮아 히트맵 미생성
        """
        if not self._ready:
            return {"available": False, "error": "PyTorch 모델 미준비",
                    "gradcam_time_ms": 0.0, "low_confidence": False}

        t_start = time.time()

        try:
            # ── E: 이미지 크기 사전 검증 ──────────────────────────────
            self._validate_image_size(image_bytes)

            # ── 원본 이미지 RGB 보존 (오버레이용) ─────────────────────
            original_rgb = HeatmapRenderer.bytes_to_rgb_array(image_bytes)

            # ── PyTorch 텐서로 전처리 ──────────────────────────────────
            input_tensor = self._preprocess(image_bytes)

            # ── Grad-CAM 생성 ──────────────────────────────────────────
            heatmap, target_idx, probs = self.gradcam.generate(
                input_tensor,
                target_class=None,
                output_size=MODEL_INPUT_SIZE,
            )

            # ── 신뢰도 계산 ───────────────────────────────────────────
            top_prob = float(probs[target_idx])
            reliability = get_reliability_level(top_prob)

            # ── E-2: LOW 신뢰도 → 히트맵 이미지 생성 억제 ─────────────
            # 확률 50% 미만이면 히트맵 자체가 신뢰할 수 없으므로
            # 이미지 생성을 건너뛰고 low_confidence 플래그를 반환
            if top_prob < LOW_CONFIDENCE_THRESHOLD:
                elapsed_ms = (time.time() - t_start) * 1000
                self.logger.warning(
                    f"낮은 신뢰도({top_prob:.3f}) → 히트맵 생성 억제 "
                    f"(임계값: {LOW_CONFIDENCE_THRESHOLD})"
                )
                if self.class_names and target_idx < len(self.class_names):
                    target_class_name = self.class_names[target_idx]
                else:
                    target_class_name = str(target_idx)
                return {
                    "available"              : True,
                    "heatmap_overlay_base64" : None,
                    "heatmap_only_base64"    : None,
                    "target_class"           : target_class_name,
                    "target_class_index"     : int(target_idx),
                    "attention_score"        : float(heatmap.max()),
                    "reliability"            : reliability,
                    "low_confidence"         : True,
                    "gradcam_time_ms"        : round(elapsed_ms, 2),
                    "error"                  : None,
                }

            # ── 히트맵 이미지 생성 ────────────────────────────────────
            original_resized = np.array(
                Image.fromarray(original_rgb).resize(MODEL_INPUT_SIZE, Image.BILINEAR),
                dtype=np.uint8,
            )
            overlay_img = HeatmapRenderer.overlay(original_resized, heatmap)
            heatmap_img = HeatmapRenderer.apply_colormap(heatmap)

            # ── 클래스명 결정 ─────────────────────────────────────────
            if self.class_names and target_idx < len(self.class_names):
                target_class_name = self.class_names[target_idx]
            else:
                target_class_name = str(target_idx)

            elapsed_ms = (time.time() - t_start) * 1000
            self.logger.info(
                f"Grad-CAM 생성 완료: class={target_class_name} "
                f"prob={top_prob:.3f} reliability={reliability} "
                f"time={elapsed_ms:.1f}ms"  # E-4
            )

            return {
                "available"              : True,
                "heatmap_overlay_base64" : HeatmapRenderer.to_base64(overlay_img),
                "heatmap_only_base64"    : HeatmapRenderer.to_base64(heatmap_img),
                "target_class"           : target_class_name,
                "target_class_index"     : int(target_idx),
                "attention_score"        : float(heatmap.max()),
                "reliability"            : reliability,
                "low_confidence"         : False,
                "gradcam_time_ms"        : round(elapsed_ms, 2),  # E-4
                "error"                  : None,
            }

        except Exception as exc:
            elapsed_ms = (time.time() - t_start) * 1000
            self.logger.warning(f"Grad-CAM 생성 실패 (예측은 정상 반환): {exc}")
            return {
                "available"      : False,
                "error"          : str(exc),
                "gradcam_time_ms": round(elapsed_ms, 2),
                "low_confidence" : False,
            }

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _validate_image_size(self, image_bytes: bytes) -> None:
        """
        Phase E: 이미지 최소 크기 검증
        최소 32×32 이하는 Grad-CAM 품질이 너무 낮아 의미 없으므로 거부
        """
        pil_img = Image.open(io.BytesIO(image_bytes))
        w, h = pil_img.size
        if w < MIN_IMAGE_DIMENSION or h < MIN_IMAGE_DIMENSION:
            raise ValueError(
                f"이미지가 너무 작습니다 ({w}×{h}px). "
                f"최소 {MIN_IMAGE_DIMENSION}×{MIN_IMAGE_DIMENSION}px 이상이어야 합니다."
            )

    def _preprocess(self, image_bytes: bytes) -> "torch.Tensor":
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        transform = T.Compose([
            T.Resize(MODEL_INPUT_SIZE),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])
        return transform(pil_img).unsqueeze(0)
