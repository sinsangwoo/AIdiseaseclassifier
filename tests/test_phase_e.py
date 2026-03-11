"""
Phase E 통합 테스트 — 품질 검증 및 안전장치

검증 항목:
  E-2: LOW 신뢰도 시 히트맵 이미지 차단
  E-2: 너무 작은 이미지 입력 거부
  E-3: xai_disclaimer 법적 고지 API 응답 포함
  E-4: gradcam_time_ms / onnx_time_ms 성능 필드 존재
  E-5: Grad-CAM 전체 파이프라인 통합 검증
"""

import io
import pytest
import numpy as np
from PIL import Image
from unittest.mock import MagicMock, patch

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

requires_torch = pytest.mark.skipif(
    not TORCH_AVAILABLE,
    reason="PyTorch 미설치 환경에서는 건너뜁니다"
)


# ─────────────────────────────────────────────────────────── #
#  Fixtures                                                   #
# ─────────────────────────────────────────────────────────── #

@pytest.fixture
def valid_image_bytes():
    """정상 크기 224×224 테스트 이미지"""
    img = Image.new("RGB", (224, 224), color=(100, 120, 140))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def tiny_image_bytes():
    """너무 작은 16×16 이미지 (E-2 크기 검증)"""
    img = Image.new("RGB", (16, 16), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def predictor_no_weights():
    """가중치 없는 PyTorchPredictor (랜덤 초기화)"""
    from backend.services.pytorch_predictor import PyTorchPredictor
    return PyTorchPredictor(weights_path=None, labels_path=None, num_classes=2)


# ─────────────────────────────────────────────────────────── #
#  E-2: LOW 신뢰도 히트맵 차단                               #
# ─────────────────────────────────────────────────────────── #

@requires_torch
class TestLowConfidenceBlock:

    def test_low_confidence_returns_no_images(self, predictor_no_weights, valid_image_bytes):
        """
        모델이 50% 미만의 확률을 반환하면
        heatmap_overlay_base64 / heatmap_only_base64 는 None 이어야 함.
        """
        from backend.services.pytorch_predictor import LOW_CONFIDENCE_THRESHOLD
        from backend.services.gradcam import GradCAM

        # GradCAM.generate 를 mock 해 낮은 확률 강제 반환
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch 없음")

        low_prob = LOW_CONFIDENCE_THRESHOLD - 0.1  # 0.40
        fake_probs = np.array([1.0 - low_prob, low_prob], dtype=np.float32)
        fake_heatmap = np.zeros((224, 224), dtype=np.float32)

        with patch.object(GradCAM, 'generate', return_value=(fake_heatmap, 1, fake_probs)):
            result = predictor_no_weights.predict_with_gradcam(valid_image_bytes)

        assert result['available'] is True
        assert result['low_confidence'] is True
        assert result['heatmap_overlay_base64'] is None, "낮은 신뢰도에서 오버레이 이미지가 None이어야 함"
        assert result['heatmap_only_base64'] is None,    "낮은 신뢰도에서 히트맵 이미지가 None이어야 함"

    def test_high_confidence_returns_images(self, predictor_no_weights, valid_image_bytes):
        """
        50% 이상 확률이면 히트맵 이미지가 생성되어야 함.
        """
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch 없음")

        from backend.services.gradcam import GradCAM

        high_prob = 0.85
        fake_probs = np.array([1.0 - high_prob, high_prob], dtype=np.float32)
        fake_heatmap = np.ones((224, 224), dtype=np.float32) * 0.7

        with patch.object(GradCAM, 'generate', return_value=(fake_heatmap, 1, fake_probs)):
            result = predictor_no_weights.predict_with_gradcam(valid_image_bytes)

        assert result['available'] is True
        assert result['low_confidence'] is False
        assert result['heatmap_overlay_base64'] is not None
        assert result['heatmap_only_base64'] is not None


# ─────────────────────────────────────────────────────────── #
#  E-2: 이미지 최소 크기 검증                                 #
# ─────────────────────────────────────────────────────────── #

@requires_torch
class TestImageSizeValidation:

    def test_tiny_image_returns_error(self, predictor_no_weights, tiny_image_bytes):
        """
        16×16 이미지는 크기 검증에서 걸려 available=False 반환.
        """
        result = predictor_no_weights.predict_with_gradcam(tiny_image_bytes)
        assert result['available'] is False
        assert result.get('error') is not None
        assert '작' in result['error'] or 'small' in result['error'].lower() or '32' in result['error']

    def test_valid_image_passes_size_check(self, predictor_no_weights, valid_image_bytes):
        """정상 크기 이미지는 크기 검증 통과."""
        result = predictor_no_weights.predict_with_gradcam(valid_image_bytes)
        # 크기 검증 오류가 아닌 다른 이유로 실패할 수 있으므로 error 내용만 체크
        if result.get('error'):
            assert '작' not in result['error']  # 크기 오류가 아님


# ─────────────────────────────────────────────────────────── #
#  E-3: 법적 고지 (xai_disclaimer) API 응답 포함 여부         #
# ─────────────────────────────────────────────────────────── #

class TestXaiDisclaimer:

    @pytest.mark.api
    def test_predict_response_contains_disclaimer(self, client, sample_image_valid):
        """
        /predict 응답의 metadata.xai_disclaimer 필드가 존재하고 비어있지 않아야 함.
        """
        data = {'file': (sample_image_valid, 'test.jpg', 'image/jpeg')}
        response = client.post('/predict', data=data, content_type='multipart/form-data')

        if response.status_code == 200:
            result = response.get_json()
            assert 'metadata' in result
            assert 'xai_disclaimer' in result['metadata'], "xai_disclaimer 필드 누락"
            disclaimer = result['metadata']['xai_disclaimer']
            assert len(disclaimer) > 20, "xai_disclaimer가 너무 짧음"


# ─────────────────────────────────────────────────────────── #
#  E-4: 성능 측정 필드 존재 확인                              #
# ─────────────────────────────────────────────────────────── #

class TestPerformanceFields:

    @pytest.mark.api
    def test_predict_response_has_timing_fields(self, client, sample_image_valid):
        """
        /predict 응답의 metadata에 성능 측정 필드가 포함되어야 함.
        """
        data = {'file': (sample_image_valid, 'test.jpg', 'image/jpeg')}
        response = client.post('/predict', data=data, content_type='multipart/form-data')

        if response.status_code == 200:
            result = response.get_json()
            metadata = result.get('metadata', {})
            assert 'processing_time_ms' in metadata, "processing_time_ms 누락"
            assert 'onnx_time_ms'        in metadata, "onnx_time_ms 누락"
            assert 'gradcam_time_ms'     in metadata, "gradcam_time_ms 누락"
            # 모든 timing 은 0 이상의 수치여야 함
            assert metadata['processing_time_ms'] >= 0
            assert metadata['onnx_time_ms']        >= 0
            assert metadata['gradcam_time_ms']     >= 0

    @requires_torch
    def test_gradcam_time_ms_is_populated(self, predictor_no_weights, valid_image_bytes):
        """PyTorchPredictor 반환값에 gradcam_time_ms가 포함되어야 함."""
        result = predictor_no_weights.predict_with_gradcam(valid_image_bytes)
        assert 'gradcam_time_ms' in result
        assert isinstance(result['gradcam_time_ms'], (int, float))
        assert result['gradcam_time_ms'] >= 0


# ─────────────────────────────────────────────────────────── #
#  E-5: 전체 통합 파이프라인 검증                             #
# ─────────────────────────────────────────────────────────── #

@requires_torch
class TestFullPipelineIntegration:

    def test_gradcam_result_schema(self, predictor_no_weights, valid_image_bytes):
        """
        predict_with_gradcam 반환 딕셔너리가 Phase E 스키마를 완전히 준수하는지 확인.
        """
        result = predictor_no_weights.predict_with_gradcam(valid_image_bytes)

        # 필수 필드 (Phase A ~ E)
        required = [
            'available', 'target_class', 'target_class_index',
            'attention_score', 'reliability', 'error',
            # Phase E 신규
            'low_confidence', 'gradcam_time_ms',
        ]
        for field in required:
            assert field in result, f"필수 필드 '{field}' 누락"

    def test_reliability_and_low_confidence_consistency(self, predictor_no_weights, valid_image_bytes):
        """
        reliability='LOW' 이면 low_confidence=True 여야 하고,
        그 반대도 항상 성립해야 함.
        """
        from backend.services.gradcam import GradCAM

        low_prob = 0.35
        fake_probs = np.array([1.0 - low_prob, low_prob], dtype=np.float32)
        fake_heatmap = np.zeros((224, 224), dtype=np.float32)

        with patch.object(GradCAM, 'generate', return_value=(fake_heatmap, 1, fake_probs)):
            result = predictor_no_weights.predict_with_gradcam(valid_image_bytes)

        assert result['reliability'] == 'LOW'
        assert result['low_confidence'] is True

    def test_attention_score_in_valid_range(self, predictor_no_weights, valid_image_bytes):
        """attention_score 는 0.0 ~ 1.0 사이여야 함 (히트맵 max값)."""
        result = predictor_no_weights.predict_with_gradcam(valid_image_bytes)
        if result['available'] and result.get('attention_score') is not None:
            assert 0.0 <= result['attention_score'] <= 1.0, (
                f"attention_score 범위 초과: {result['attention_score']}"
            )
