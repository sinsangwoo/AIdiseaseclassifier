"""
히트맵 렌더러 모듈 (Phase B)

Grad-CAM 히트맵(0~1 numpy array)을 실제 화면에 표시 가능한
이미지(컬러맵 적용, 원본 오버레이, base64 인코딩)로 변환합니다.
"""

from __future__ import annotations

import base64
import io
from typing import Optional

import numpy as np
from PIL import Image

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class HeatmapRenderer:
    """
    Grad-CAM 히트맵 시각화 유틸리티 클래스

    모든 메서드는 @staticmethod 로 인스턴스 없이 직접 호출 가능합니다.
    """

    # 의료 영상 권장 알파값 (너무 강하면 원본 폐 구조가 가려짐)
    DEFAULT_ALPHA: float = 0.40

    @staticmethod
    def apply_colormap(heatmap: np.ndarray) -> np.ndarray:
        """
        0~1 범위의 히트맵에 JET 컬러맵을 적용합니다.

        색상 매핑:
          0.0 → 파란색  (AI 주목도 낮음)
          0.5 → 초록/노란색
          1.0 → 빨간색  (AI 주목도 높음)

        Args:
            heatmap: np.ndarray [H, W], 값 범위 0.0 ~ 1.0

        Returns:
            colored: np.ndarray [H, W, 3], RGB, uint8
        """
        heatmap_uint8 = np.clip(heatmap * 255, 0, 255).astype(np.uint8)

        if CV2_AVAILABLE:
            # OpenCV의 JET 컬러맵 적용 (BGR 반환 → RGB로 변환)
            colored_bgr = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
            colored_rgb = cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)
            return colored_rgb

        # ── opencv 미설치 fallback: 단순 그레이스케일 RGB ────────────────
        gray = np.stack([heatmap_uint8] * 3, axis=-1)  # [H, W, 3]
        return gray

    @staticmethod
    def overlay(
        original_img: np.ndarray,
        heatmap: np.ndarray,
        alpha: float = DEFAULT_ALPHA,
    ) -> np.ndarray:
        """
        원본 이미지 위에 히트맵을 반투명하게 합성합니다.

        알파 블렌딩 공식:
          output = original * (1 - alpha) + heatmap_colored * alpha

        Args:
            original_img: np.ndarray [H, W, 3], RGB, uint8
            heatmap     : np.ndarray [H, W], 0.0 ~ 1.0
            alpha       : 히트맵 불투명도 (0=완전 투명, 1=완전 불투명)
                          의료용 권장값 0.3 ~ 0.4

        Returns:
            blended: np.ndarray [H, W, 3], RGB, uint8
        """
        colored = HeatmapRenderer.apply_colormap(heatmap)  # [H, W, 3]

        # 원본 이미지와 크기가 다를 경우 리사이즈
        h, w = original_img.shape[:2]
        if colored.shape[:2] != (h, w):
            if CV2_AVAILABLE:
                colored = cv2.resize(colored, (w, h), interpolation=cv2.INTER_LINEAR)
            else:
                pil_colored = Image.fromarray(colored).resize((w, h), Image.BILINEAR)
                colored = np.array(pil_colored)

        # 알파 블렌딩
        original_f = original_img.astype(np.float32)
        colored_f  = colored.astype(np.float32)
        blended = (original_f * (1.0 - alpha) + colored_f * alpha).clip(0, 255)
        return blended.astype(np.uint8)

    @staticmethod
    def to_base64(image: np.ndarray, fmt: str = "PNG") -> str:
        """
        numpy 이미지 배열을 base64 문자열로 변환합니다.
        API 응답의 JSON 필드에 직접 포함할 때 사용합니다.

        Args:
            image: np.ndarray [H, W, 3], uint8
            fmt  : 인코딩 포맷 ('PNG' 또는 'JPEG')

        Returns:
            base64 인코딩된 문자열 (data URI 접두어 없음)
        """
        pil_img = Image.fromarray(image.astype(np.uint8))
        buf = io.BytesIO()
        pil_img.save(buf, format=fmt)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @staticmethod
    def bytes_to_rgb_array(image_bytes: bytes) -> np.ndarray:
        """
        원본 이미지 바이트 → RGB numpy 배열 변환 (오버레이 합성용)

        Args:
            image_bytes: 원본 이미지의 raw bytes

        Returns:
            np.ndarray [H, W, 3], RGB, uint8
        """
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return np.array(pil_img, dtype=np.uint8)
