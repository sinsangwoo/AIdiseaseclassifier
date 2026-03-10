"""
Grad-CAM 히트맵 생성 엔진 (Phase B)

Grad-CAM(Gradient-weighted Class Activation Mapping) 알고리즘을 구현합니다.

원리:
  1. 이미지를 CNN에 통과시키며 마지막 conv layer의 출력(activation)을 저장
  2. 타겟 클래스에 대해 역전파(backprop)를 실행하여 gradient 계산
  3. gradient를 공간 평균 → 각 채널의 '중요도 가중치' α_k 획득
  4. Σ α_k * A^k 로 raw CAM 생성, ReLU 적용
  5. 원본 이미지 크기로 업샘플링 → 최종 히트맵

참고 논문:
  Selvaraju et al., "Grad-CAM: Visual Explanations from Deep Networks
  via Gradient-based Localization", ICCV 2017
"""

from __future__ import annotations
from typing import Tuple, Optional

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class GradCAM:
    """
    Grad-CAM 히트맵 생성기

    사용 예시:
        gradcam = GradCAM(model, "backbone.features.denseblock4")
        heatmap, cls_idx, probs = gradcam.generate(input_tensor)
    """

    def __init__(self, model, target_layer_name: str):
        """
        Args:
            model            : PneumoniaClassifier (PyTorch nn.Module)
            target_layer_name: 훅을 걸 레이어의 이름 문자열
                               (model.named_modules()에서 확인)
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError(
                "PyTorch가 설치되어 있지 않습니다. "
                "`pip install torch torchvision` 으로 설치하세요."
            )

        self.model = model
        self._activations: Optional["torch.Tensor"] = None
        self._gradients:   Optional["torch.Tensor"] = None

        target_layer = self._find_layer(target_layer_name)
        self._register_hooks(target_layer)

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _find_layer(self, name: str):
        """이름으로 레이어 객체를 탐색하여 반환"""
        for module_name, module in self.model.named_modules():
            if module_name == name:
                return module
        raise ValueError(
            f"레이어 '{name}'를 찾을 수 없습니다. "
            f"model.named_modules()를 확인하세요."
        )

    def _register_hooks(self, layer):
        """
        Forward hook  : layer의 출력(activation)을 저장
        Backward hook : layer로 흘러드는 gradient를 저장
        """
        def _forward_hook(module, inp, out):
            # detach(): gradient graph 에서 분리해 메모리 절약
            self._activations = out.detach()

        def _backward_hook(module, grad_in, grad_out):
            self._gradients = grad_out[0].detach()

        layer.register_forward_hook(_forward_hook)
        layer.register_full_backward_hook(_backward_hook)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def generate(
        self,
        input_tensor: "torch.Tensor",
        target_class: Optional[int] = None,
        output_size: Tuple[int, int] = (224, 224),
    ) -> Tuple[np.ndarray, int, np.ndarray]:
        """
        Grad-CAM 히트맵 생성

        Args:
            input_tensor : 전처리된 이미지 텐서 shape [1, C, H, W]
            target_class : 설명할 클래스 인덱스
                           None 이면 가장 높은 확률의 클래스를 자동 선택
            output_size  : 히트맵 출력 크기 (width, height)

        Returns:
            heatmap      : np.ndarray [H, W], 값 범위 0.0 ~ 1.0 (보장)
                           1.0에 가까울수록 AI가 그 위치를 강하게 주목
            target_class : 사용된 클래스 인덱스
            probabilities: 모든 클래스의 소프트맥스 확률 np.ndarray
        """
        self.model.eval()
        # requires_grad=True : input 자체의 gradient 도 계산 (GuidedGradCAM 확장용)
        input_tensor = input_tensor.clone().requires_grad_(True)

        # ── 1. Forward pass ─────────────────────────────────────────────
        output = self.model(input_tensor)          # [1, num_classes]
        probabilities = F.softmax(output, dim=1).squeeze().detach().numpy()

        if target_class is None:
            target_class = int(output.argmax(dim=1).item())

        # ── 2. Backward pass (타겟 클래스에 대해서만) ────────────────────
        self.model.zero_grad()
        score = output[0, target_class]            # 스칼라 값
        score.backward()                           # gradient 역전파!

        # ── 3. 채널별 가중치 α_k 계산 (공간 평균) ───────────────────────
        # gradients shape: [1, C, H', W']
        # keepdim=True 로 shape 유지해 브로드캐스팅 지원
        weights = self._gradients.mean(dim=[2, 3], keepdim=True)  # [1, C, 1, 1]

        # ── 4. 가중 합산 ────────────────────────────────────────────────
        cam = (weights * self._activations).sum(dim=1, keepdim=True)  # [1, 1, H', W']

        # ── 5. ReLU: 음수 → 0  (클래스와 무관한 영역 제거) ─────────────
        cam = F.relu(cam)

        # ── 6. 정규화 (0 ~ 1) ───────────────────────────────────────────
        cam_np = cam.squeeze().detach().numpy()    # [H', W']
        cam_min, cam_max = cam_np.min(), cam_np.max()
        # 분모가 0 이 되는 것을 방지 (모든 값이 동일한 경우)
        cam_np = (cam_np - cam_min) / (cam_max - cam_min + 1e-8)

        # ── 7. 원본 이미지 크기로 업샘플링 ─────────────────────────────
        heatmap = self._resize(cam_np, output_size)

        return heatmap, target_class, probabilities

    @staticmethod
    def _resize(cam: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
        """
        히트맵을 목표 크기로 보간 (업샘플링)

        INTER_CUBIC 보간 시 주의사항:
          Bicubic(3차 스플라인)은 monotone 보간이 아니므로
          업샘플링 경계에서 링잉(ringing/overshoot) 아티팩트가 발생하여
          입력 범위 [0, 1] 을 벗어나는 음수 또는 1 초과 값이 나올 수 있음.
          → resize 직후 np.clip(0.0, 1.0) 으로 반드시 후처리.
        """
        if CV2_AVAILABLE:
            resized = cv2.resize(
                cam.astype(np.float32),
                size,  # (width, height)
                interpolation=cv2.INTER_CUBIC,
            )
        else:
            # opencv 미설치 시 numpy 기반 단순 반복 확대 (품질 낮음)
            h, w = size[1], size[0]
            zoom_h = h / cam.shape[0]
            zoom_w = w / cam.shape[1]
            from numpy import repeat
            resized = repeat(repeat(cam, int(zoom_h) or 1, axis=0), int(zoom_w) or 1, axis=1)
            resized = resized[:h, :w].astype(np.float32)

        # Bicubic 링잉 아티팩트 제거: 보간 후 [0, 1] 범위 보장
        return np.clip(resized, 0.0, 1.0)


def get_reliability_level(probability: float) -> str:
    """
    예측 확률로 신뢰도 등급 반환

    Returns:
        'HIGH'   : probability >= 0.70  (정상 표시)
        'MEDIUM' : probability >= 0.50  (주의 경고 표시)
        'LOW'    : probability <  0.50  (히트맵 비표시 권장)
    """
    if probability >= 0.70:
        return "HIGH"
    elif probability >= 0.50:
        return "MEDIUM"
    return "LOW"
