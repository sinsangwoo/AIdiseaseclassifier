"""
PyTorch 기반 예측기 + Grad-CAM 통합 서비스 (Phase A)

기존 ONNX 기반 ModelService를 대체하지 않고 병렬로 운영합니다.
Grad-CAM이 필요한 /predict 엔드포인트에서만 이 클래스를 사용합니다.

폴백(Fallback) 전략:
  PyTorch 또는 모델 가중치 미존재 시 → ONNX 예측 결과를 그대로 사용하되
  gradcam.available = false 를 응답에 포함합니다.
  이렇게 하면 기존 기능을 해치지 않으면서 점진적으로 Grad-CAM을 도입합니다.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from PIL import Image

# PyTorch 조건부 임포트 (미설치 환경에서도 서버가 기동되어야 함)
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


class PyTorchPredictor:
    """
    PyTorch 모델로 예측 + Grad-CAM 히트맵을 한 번에 생성하는 서비스 클래스

    주요 메서드:
        predict_with_gradcam(image_bytes) -> dict
            예측 결과 + gradcam 필드가 포함된 딕셔너리 반환
    """

    def __init__(
        self,
        weights_path: Optional[str] = None,
        labels_path: Optional[str] = None,
        num_classes: int = 2,
    ):
        """
        Args:
            weights_path : .pth 가중치 파일 경로
                           None 또는 파일 없음 → 폴백 모드로 동작
            labels_path  : labels.txt 경로
            num_classes  : 분류 클래스 수
        """
        self.logger = get_logger("aiclassifier.gradcam")
        self._ready = False
        self.model = None
        self.gradcam = None
        self.class_names: List[str] = []
        self.num_classes = num_classes

        # ── 레이블 로드 ───────────────────────────────────────────────────
        if labels_path and Path(labels_path).exists():
            with open(labels_path, "r", encoding="utf-8") as f:
                self.class_names = [
                    line.strip().split(" ", 1)[1]
                    for line in f
                    if line.strip()
                ]
            self.num_classes = len(self.class_names)
            self.logger.info(f"레이블 로드: {self.class_names}")

        # ── PyTorch 모델 로드 ─────────────────────────────────────────────
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

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    @property
    def is_ready(self) -> bool:
        """Grad-CAM 사용 가능 여부"""
        return self._ready

    def predict_with_gradcam(
        self,
        image_bytes: bytes,
        existing_predictions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        이미지 바이트를 받아 Grad-CAM 히트맵 딕셔너리를 반환합니다.

        Args:
            image_bytes          : 원본 이미지의 raw bytes
            existing_predictions : 이미 계산된 ONNX 예측 결과 (있으면 재사용)
                                   None 이면 PyTorch로 독립적으로 예측

        Returns:
            {
              "available"             : bool,
              "heatmap_overlay_base64": str | None,  # 원본 + 히트맵 합성
              "heatmap_only_base64"   : str | None,  # 히트맵만
              "target_class"          : str | None,  # 예측 클래스명
              "target_class_index"    : int | None,
              "attention_score"       : float | None,  # 히트맵 최대값
              "reliability"           : str | None,    # HIGH / MEDIUM / LOW
              "error"                 : str | None,
            }
        """
        if not self._ready:
            return {"available": False, "error": "PyTorch 모델 미준비"}

        try:
            # ── 1. 원본 이미지 → RGB numpy array 보존 (오버레이용) ────────
            original_rgb = HeatmapRenderer.bytes_to_rgb_array(image_bytes)

            # ── 2. PyTorch 텐서로 전처리 ─────────────────────────────────
            input_tensor = self._preprocess(image_bytes)  # [1, 3, 224, 224]

            # ── 3. Grad-CAM 생성 ─────────────────────────────────────────
            # target_class=None → 가장 높은 확률 클래스 자동 선택
            heatmap, target_idx, probs = self.gradcam.generate(
                input_tensor,
                target_class=None,
                output_size=MODEL_INPUT_SIZE,
            )

            # ── 4. 신뢰도 계산 ───────────────────────────────────────────
            top_prob = float(probs[target_idx])
            reliability = get_reliability_level(top_prob)

            # ── 5. 히트맵 이미지 생성 ────────────────────────────────────
            # 원본을 224×224 로 리사이즈해 히트맵과 크기 맞춤
            original_resized = np.array(
                Image.fromarray(original_rgb).resize(MODEL_INPUT_SIZE, Image.BILINEAR),
                dtype=np.uint8,
            )
            overlay_img  = HeatmapRenderer.overlay(original_resized, heatmap)
            heatmap_img  = HeatmapRenderer.apply_colormap(heatmap)

            # ── 6. 클래스명 결정 ─────────────────────────────────────────
            if self.class_names and target_idx < len(self.class_names):
                target_class_name = self.class_names[target_idx]
            else:
                target_class_name = str(target_idx)

            self.logger.info(
                f"Grad-CAM 생성 완료: class={target_class_name} "
                f"prob={top_prob:.3f} reliability={reliability}"
            )

            return {
                "available"              : True,
                "heatmap_overlay_base64" : HeatmapRenderer.to_base64(overlay_img),
                "heatmap_only_base64"    : HeatmapRenderer.to_base64(heatmap_img),
                "target_class"           : target_class_name,
                "target_class_index"     : int(target_idx),
                "attention_score"        : float(heatmap.max()),
                "reliability"            : reliability,
                "error"                  : None,
            }

        except Exception as exc:
            self.logger.warning(f"Grad-CAM 생성 실패 (예측은 정상 반환): {exc}")
            return {"available": False, "error": str(exc)}

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _preprocess(self, image_bytes: bytes) -> "torch.Tensor":
        """
        이미지 바이트 → PyTorch 텐서 전처리

        전처리 파이프라인:
          1. JPEG/PNG → PIL RGB
          2. 224×224 리사이즈
          3. numpy float32 → Tensor [C, H, W]
          4. ImageNet 정규화 (mean, std)
          5. 배치 차원 추가 → [1, C, H, W]
        """
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        transform = T.Compose([
            T.Resize(MODEL_INPUT_SIZE),
            T.ToTensor(),                       # [0,255] uint8 → [0,1] float32
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])
        tensor = transform(pil_img).unsqueeze(0)  # [1, 3, 224, 224]
        return tensor
