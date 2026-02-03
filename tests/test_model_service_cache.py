"""
ModelService 캐시 단위 테스트

캐시 수술(Phase 3) 이후 조회·저장·퇴장·통계 경로를 검증합니다.

격리 전략:
  - ModelPredictor는 unittest.mock.MagicMock으로 대체
  - predict()의 실제 ONNX 추론은 발생하지 않음
  - 테스트 전후 캐시 상태 초기화 (fixture)
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from collections import OrderedDict

from backend.services.model_service import ModelService


# ─── 픽스처 ───────────────────────────────────────────────────────


@pytest.fixture
def mock_predictor():
    """ModelPredictor 모의 객체 — is_ready() True, predict()는 고정 결과 반환"""
    predictor = MagicMock()
    predictor.is_ready.return_value = True
    predictor.predict.return_value = [
        {'className': '정상', 'probability': 0.85},
        {'className': '폐렴', 'probability': 0.15}
    ]
    return predictor


@pytest.fixture
def service(mock_predictor) -> ModelService:
    """캐싱 활성화된 ModelService (cache_size=4)

    ModelPredictor 생성자와 load_model을 패치하여
    실제 모델 파일 없이 테스트합니다.
    """
    with patch('backend.services.model_service.ModelPredictor') as MockClass:
        MockClass.return_value = mock_predictor
        svc = ModelService(
            model_path='dummy.onnx',
            labels_path='dummy_labels.txt',
            enable_cache=True,
            cache_size=4
        )
        # 직접 _predictor를 주입하여 load_model() 호출 불필요
        svc._predictor = mock_predictor
        svc.stats['warmup_completed'] = True
    return svc


@pytest.fixture
def no_cache_service(mock_predictor) -> ModelService:
    """캐싱 비활성화된 ModelService"""
    with patch('backend.services.model_service.ModelPredictor'):
        svc = ModelService(
            model_path='dummy.onnx',
            labels_path='dummy_labels.txt',
            enable_cache=False
        )
        svc._predictor = mock_predictor
        svc.stats['warmup_completed'] = True
    return svc


def _make_image(seed: int) -> np.ndarray:
    """재현가능한 더미 이미지 생성 (seed가 다르면 해시도 다름)"""
    rng = np.random.default_rng(seed)
    return rng.random((1, 3, 224, 224)).astype(np.float32)


# ─── 기본 동작 테스트 ─────────────────────────────────────────────


class TestModelServiceBasic:
    """ModelService 기본 동작"""

    @pytest.mark.unit
    def test_is_ready(self, service):
        """모델이 주입되면 is_ready() → True"""
        assert service.is_ready() is True

    @pytest.mark.unit
    def test_predict_returns_tuple(self, service):
        """predict()는 (predictions, from_cache) 튜플을 반환"""
        img = _make_image(0)
        result = service.predict(img)

        assert isinstance(result, tuple)
        assert len(result) == 2

        predictions, from_cache = result
        assert isinstance(predictions, list)
        assert isinstance(from_cache, bool)

    @pytest.mark.unit
    def test_predict_first_call_is_miss(self, service, mock_predictor):
        """첫 호출은 캐시 미스 → 실제 추론 발생"""
        img = _make_image(1)
        predictions, from_cache = service.predict(img)

        assert from_cache is False
        mock_predictor.predict.assert_called_once()

    @pytest.mark.unit
    def test_predict_second_call_is_hit(self, service, mock_predictor):
        """동일 이미지의 두 번째 호출은 캐시 히트 → 추론 불발생"""
        img = _make_image(2)

        service.predict(img)                 # 1st — miss
        mock_predictor.predict.reset_mock()  # 카운터 초기화

        predictions, from_cache = service.predict(img)  # 2nd — hit

        assert from_cache is True
        mock_predictor.predict.assert_not_called()

    @pytest.mark.unit
    def test_predict_different_images_both_miss(self, service, mock_predictor):
        """서로 다른 이미지는 각각 미스"""
        img_a = _make_image(10)
        img_b = _make_image(11)

        _, from_a = service.predict(img_a)
        _, from_b = service.predict(img_b)

        assert from_a is False
        assert from_b is False
        assert mock_predictor.predict.call_count == 2


# ─── LRU 퇴장 정책 테스트 ─────────────────────────────────────────


class TestLRUEviction:
    """OrderedDict 기반 LRU 퇴장 정책 검증 (cache_size=4)"""

    @pytest.mark.unit
    def test_eviction_removes_oldest(self, service):
        """5번째 이미지 저장 시 가장 오래된(1번째) 항목이 퇴장"""
        images = [_make_image(i) for i in range(5)]

        # 0~3번 저장 → 캐시 가득침
        for img in images[:4]:
            service.predict(img)

        # 0번 해시를 미리 저장
        hash_0 = service._compute_image_hash(images[0])
        assert hash_0 in service._cache

        # 4번 저장 → 0번 퇴장
        service.predict(images[4])

        assert hash_0 not in service._cache
        assert len(service._cache) == 4

    @pytest.mark.unit
    def test_access_refreshes_lru_order(self, service):
        """조회된 항목은 퇴장 우선순위가 낮아짐

        저장 순서: A B C D
        A를 다시 조회 → 내부 순서: B C D A
        E 저장 → B가 퇴장 (A는 최근 사용이므로 유지)
        """
        images = {k: _make_image(k) for k in range(5)}  # A=0 B=1 C=2 D=3 E=4

        # A B C D 저장
        for k in range(4):
            service.predict(images[k])

        # A를 다시 조회 (hit → move_to_end)
        service.predict(images[0])

        hash_b = service._compute_image_hash(images[1])

        # E 저장 → B가 퇴장
        service.predict(images[4])

        assert hash_b not in service._cache
        # A는 최근 사용이므로 유지
        hash_a = service._compute_image_hash(images[0])
        assert hash_a in service._cache

    @pytest.mark.unit
    def test_cache_size_never_exceeds_limit(self, service):
        """100개 이미지를 순차 저장해도 캐시 크기는 4 이하"""
        for i in range(100):
            service.predict(_make_image(i + 200))
            assert len(service._cache) <= 4


# ─── 통계 테스트 ──────────────────────────────────────────────────


class TestCacheStatistics:
    """캐시 통계 정확성 검증"""

    @pytest.mark.unit
    def test_stats_hit_miss_count(self, service):
        """hit / miss 카운터가 정확히 증가"""
        img = _make_image(50)

        service.predict(img)   # miss
        service.predict(img)   # hit
        service.predict(img)   # hit

        assert service.stats['cache_hits'] == 2
        assert service.stats['cache_misses'] == 1
        assert service.stats['total_predictions'] == 3

    @pytest.mark.unit
    def test_get_statistics_hit_rate(self, service):
        """get_statistics()의 cache_hit_rate_percent 계산 정확성"""
        img = _make_image(51)

        service.predict(img)   # miss
        service.predict(img)   # hit

        stats = service.get_statistics()

        # 2회 중 1회 히트 = 50%
        assert stats['cache_hit_rate_percent'] == 50.0
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1

    @pytest.mark.unit
    def test_get_cache_info_currsize(self, service):
        """get_cache_info().currsize가 실제 캐시 항목 수와 일치"""
        for i in range(3):
            service.predict(_make_image(i + 100))

        info = service.get_cache_info()
        assert info['currsize'] == 3
        assert info['maxsize'] == 4


# ─── 캐시 초기화 테스트 ───────────────────────────────────────────


class TestCacheClear:
    """clear_cache() 동작 검증"""

    @pytest.mark.unit
    def test_clear_empties_cache(self, service):
        """clear_cache() 후 캐시가 비어있고 통계가 초기화"""
        img = _make_image(60)
        service.predict(img)
        service.predict(img)

        service.clear_cache()

        assert len(service._cache) == 0
        assert service.stats['cache_hits'] == 0
        assert service.stats['cache_misses'] == 0

    @pytest.mark.unit
    def test_predict_after_clear_is_miss(self, service, mock_predictor):
        """clear_cache() 후 동일 이미지 호출은 다시 미스"""
        img = _make_image(61)

        service.predict(img)           # miss
        service.predict(img)           # hit
        service.clear_cache()
        mock_predictor.predict.reset_mock()

        _, from_cache = service.predict(img)  # miss again

        assert from_cache is False
        mock_predictor.predict.assert_called_once()


# ─── 캐싱 비활성화 모드 테스트 ────────────────────────────────────


class TestCacheDisabled:
    """enable_cache=False 시 캐시가 완전히 우회됨을 검증"""

    @pytest.mark.unit
    def test_no_cache_always_infers(self, no_cache_service, mock_predictor):
        """캐싱 비활성화 시 동일 이미지도 매번 추론"""
        img = _make_image(70)

        no_cache_service.predict(img)
        no_cache_service.predict(img)

        assert mock_predictor.predict.call_count == 2

    @pytest.mark.unit
    def test_no_cache_from_cache_always_false(self, no_cache_service):
        """캐싱 비활성화 시 from_cache는 항상 False"""
        img = _make_image(71)

        _, fc1 = no_cache_service.predict(img)
        _, fc2 = no_cache_service.predict(img)

        assert fc1 is False
        assert fc2 is False

    @pytest.mark.unit
    def test_no_cache_stats_no_hits(self, no_cache_service):
        """캐싱 비활성화 시 cache_hits 카운터는 0"""
        img = _make_image(72)

        no_cache_service.predict(img)
        no_cache_service.predict(img)

        assert no_cache_service.stats['cache_hits'] == 0


# ─── 해시 결정성 테스트 ───────────────────────────────────────────


class TestImageHashing:
    """동일 이미지 → 동일 해시, 다른 이미지 → 다른 해시"""

    @pytest.mark.unit
    def test_same_array_same_hash(self, service):
        """동일한 numpy 배열은 동일한 해시를 생성"""
        img = _make_image(80)
        h1 = service._compute_image_hash(img)
        h2 = service._compute_image_hash(img)
        assert h1 == h2

    @pytest.mark.unit
    def test_different_array_different_hash(self, service):
        """다른 numpy 배열은 다른 해시를 생성"""
        h1 = service._compute_image_hash(_make_image(81))
        h2 = service._compute_image_hash(_make_image(82))
        assert h1 != h2

    @pytest.mark.unit
    def test_hash_is_sha256_hex(self, service):
        """해시는 64자리 SHA-256 hex 문자열"""
        h = service._compute_image_hash(_make_image(83))
        assert len(h) == 64
        assert all(c in '0123456789abcdef' for c in h)
