"""
Grad-CAM 단위 테스트 (Phase A)

테스트 전략:
  - PyTorch 미설치 환경에서도 스킵하며 통과 (skipif 사용)
  - 실제 모델 가중치 없이 랜덤 초기화 모델로 구조 검증
  - HeatmapRenderer는 PyTorch 불필요 → 항상 실행
"""

import io
import base64
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

# PyTorch 설치 여부 확인
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

requires_torch = pytest.mark.skipif(
    not TORCH_AVAILABLE,
    reason="PyTorch 미설치 환경에서는 건너뜁니다"
)


# ──────────────────────────────────────────────────────────────────────── #
#  Fixtures                                                                #
# ──────────────────────────────────────────────────────────────────────── #

@pytest.fixture
def sample_image_bytes():
    """테스트용 224×224 흑백 이미지 (실제 X-ray 대체)"""
    img = Image.new("RGB", (224, 224), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_heatmap():
    """테스트용 히트맵 (0~1 범위 랜덤 numpy 배열)"""
    rng = np.random.default_rng(42)
    return rng.random((224, 224)).astype(np.float32)


@pytest.fixture
def sample_rgb_image():
    """테스트용 원본 RGB numpy 배열"""
    return np.full((224, 224, 3), 128, dtype=np.uint8)


# ──────────────────────────────────────────────────────────────────────── #
#  HeatmapRenderer 테스트 (PyTorch 불필요)                                 #
# ──────────────────────────────────────────────────────────────────────── #

class TestHeatmapRenderer:

    def test_apply_colormap_shape(self, sample_heatmap):
        """컬러맵 적용 후 shape이 [H, W, 3] 인지 확인"""
        from backend.services.heatmap_renderer import HeatmapRenderer
        colored = HeatmapRenderer.apply_colormap(sample_heatmap)
        assert colored.shape == (224, 224, 3), f"예상 (224,224,3), 실제 {colored.shape}"

    def test_apply_colormap_dtype(self, sample_heatmap):
        """출력 dtype 이 uint8 인지 확인"""
        from backend.services.heatmap_renderer import HeatmapRenderer
        colored = HeatmapRenderer.apply_colormap(sample_heatmap)
        assert colored.dtype == np.uint8

    def test_overlay_output_shape(self, sample_rgb_image, sample_heatmap):
        """오버레이 결과의 shape이 원본과 동일한지 확인"""
        from backend.services.heatmap_renderer import HeatmapRenderer
        result = HeatmapRenderer.overlay(sample_rgb_image, sample_heatmap)
        assert result.shape == sample_rgb_image.shape

    def test_overlay_alpha_bounds(self, sample_rgb_image, sample_heatmap):
        """오버레이 픽셀 값이 0~255 범위 안에 있는지 확인"""
        from backend.services.heatmap_renderer import HeatmapRenderer
        result = HeatmapRenderer.overlay(sample_rgb_image, sample_heatmap, alpha=0.4)
        assert result.min() >= 0 and result.max() <= 255

    def test_to_base64_is_valid_string(self, sample_rgb_image):
        """base64 인코딩 결과가 디코딩 가능한 문자열인지 확인"""
        from backend.services.heatmap_renderer import HeatmapRenderer
        b64 = HeatmapRenderer.to_base64(sample_rgb_image)
        assert isinstance(b64, str)
        decoded = base64.b64decode(b64)  # 예외 없이 디코딩되면 통과
        assert len(decoded) > 0

    def test_bytes_to_rgb_array(self, sample_image_bytes):
        """이미지 바이트 → RGB numpy 배열 변환 확인"""
        from backend.services.heatmap_renderer import HeatmapRenderer
        arr = HeatmapRenderer.bytes_to_rgb_array(sample_image_bytes)
        assert arr.ndim == 3
        assert arr.shape[2] == 3  # RGB 채널
        assert arr.dtype == np.uint8


# ──────────────────────────────────────────────────────────────────────── #
#  GradCAM 엔진 테스트 (PyTorch 필요)                                      #
# ──────────────────────────────────────────────────────────────────────── #

@requires_torch
class TestGradCAM:

    @pytest.fixture
    def model_and_gradcam(self):
        """랜덤 초기화 DenseNet-121 + GradCAM 인스턴스 생성"""
        from backend.models.model_definition import build_model, GRADCAM_TARGET_LAYER
        from backend.services.gradcam import GradCAM
        model = build_model(num_classes=2)
        gradcam = GradCAM(model, GRADCAM_TARGET_LAYER)
        return model, gradcam

    @pytest.fixture
    def sample_tensor(self):
        """랜덤 입력 텐서 [1, 3, 224, 224]"""
        return torch.randn(1, 3, 224, 224)

    def test_heatmap_shape(self, model_and_gradcam, sample_tensor):
        """히트맵 shape이 (224, 224) 인지 확인"""
        _, gradcam = model_and_gradcam
        heatmap, _, _ = gradcam.generate(sample_tensor)
        assert heatmap.shape == (224, 224), f"예상 (224,224), 실제 {heatmap.shape}"

    def test_heatmap_value_range(self, model_and_gradcam, sample_tensor):
        """히트맵 값이 0.0 ~ 1.0 범위인지 확인"""
        _, gradcam = model_and_gradcam
        heatmap, _, _ = gradcam.generate(sample_tensor)
        assert heatmap.min() >= 0.0, f"최솟값 {heatmap.min()} < 0"
        assert heatmap.max() <= 1.0, f"최댓값 {heatmap.max()} > 1"

    def test_probabilities_sum_to_one(self, model_and_gradcam, sample_tensor):
        """소프트맥스 확률의 합이 1.0 (±0.01) 인지 확인"""
        _, gradcam = model_and_gradcam
        _, _, probs = gradcam.generate(sample_tensor)
        assert abs(probs.sum() - 1.0) < 0.01, f"확률 합 = {probs.sum()}"

    def test_target_class_range(self, model_and_gradcam, sample_tensor):
        """반환된 target_class 가 유효한 인덱스 범위인지 확인"""
        model, gradcam = model_and_gradcam
        _, target_cls, _ = gradcam.generate(sample_tensor)
        num_classes = 2
        assert 0 <= target_cls < num_classes

    def test_different_classes_produce_different_heatmaps(self, model_and_gradcam, sample_tensor):
        """다른 클래스를 지정하면 다른 히트맵이 생성되어야 함"""
        _, gradcam = model_and_gradcam
        hmap_0, _, _ = gradcam.generate(sample_tensor.clone(), target_class=0)
        hmap_1, _, _ = gradcam.generate(sample_tensor.clone(), target_class=1)
        # 완전히 동일하지 않아야 함
        assert not np.allclose(hmap_0, hmap_1), "두 클래스 히트맵이 동일합니다"


# ──────────────────────────────────────────────────────────────────────── #
#  PyTorchPredictor 통합 테스트                                            #
# ──────────────────────────────────────────────────────────────────────── #

@requires_torch
class TestPyTorchPredictor:

    @pytest.fixture
    def predictor(self):
        """가중치 없는 폴백 모드 PyTorchPredictor"""
        from backend.services.pytorch_predictor import PyTorchPredictor
        # weights_path=None → 랜덤 초기화 모델 사용
        return PyTorchPredictor(weights_path=None, labels_path=None, num_classes=2)

    def test_predictor_is_ready(self, predictor):
        """PyTorch 설치 환경에서는 is_ready=True 여야 함"""
        assert predictor.is_ready is True

    def test_predict_with_gradcam_returns_dict(self, predictor, sample_image_bytes):
        """predict_with_gradcam 이 dict 를 반환하는지 확인"""
        result = predictor.predict_with_gradcam(sample_image_bytes)
        assert isinstance(result, dict)
        assert "available" in result

    def test_predict_with_gradcam_available_true(self, predictor, sample_image_bytes):
        """정상 이미지 입력 시 available=True 인지 확인"""
        result = predictor.predict_with_gradcam(sample_image_bytes)
        assert result["available"] is True

    def test_predict_with_gradcam_has_required_fields(self, predictor, sample_image_bytes):
        """응답에 필수 필드가 모두 포함되어 있는지 확인"""
        result = predictor.predict_with_gradcam(sample_image_bytes)
        required_fields = [
            "available", "heatmap_overlay_base64", "heatmap_only_base64",
            "target_class", "attention_score", "reliability"
        ]
        for field in required_fields:
            assert field in result, f"필드 '{field}' 누락"

    def test_predict_with_gradcam_base64_decodable(self, predictor, sample_image_bytes):
        """반환된 base64 이미지가 실제로 디코딩 가능한지 확인"""
        result = predictor.predict_with_gradcam(sample_image_bytes)
        if result["available"]:
            for key in ["heatmap_overlay_base64", "heatmap_only_base64"]:
                decoded = base64.b64decode(result[key])
                assert len(decoded) > 0, f"{key} 디코딩 결과가 빔"

    def test_predict_with_gradcam_reliability_values(self, predictor, sample_image_bytes):
        """reliability 필드가 유효한 값인지 확인"""
        result = predictor.predict_with_gradcam(sample_image_bytes)
        if result["available"]:
            assert result["reliability"] in ("HIGH", "MEDIUM", "LOW")


# ──────────────────────────────────────────────────────────────────────── #
#  get_reliability_level 유틸리티 테스트                                   #
# ──────────────────────────────────────────────────────────────────────── #

class TestGetReliabilityLevel:

    def test_high(self):
        from backend.services.gradcam import get_reliability_level
        assert get_reliability_level(0.90) == "HIGH"
        assert get_reliability_level(0.70) == "HIGH"

    def test_medium(self):
        from backend.services.gradcam import get_reliability_level
        assert get_reliability_level(0.69) == "MEDIUM"
        assert get_reliability_level(0.50) == "MEDIUM"

    def test_low(self):
        from backend.services.gradcam import get_reliability_level
        assert get_reliability_level(0.49) == "LOW"
        assert get_reliability_level(0.01) == "LOW"
