"""
모델 관리 서비스 (Phase 3 — 캐시 수술 완료)

PyTorch 모델의 로딩, 캐싱, 예측을 담당하는 서비스 레이어입니다.

캐시 아키텍처 (수술 전후)
─────────────────────────────────────────
  수술 전:
    predict() → _cached_predict(hash)  ← lru_cache 데코레이터
                  └─ 항상 None 반환 (설계 오류)
                _save_to_cache(hash, result) → self._cache[hash] = result
                  └─ 저장은 되지만 조회 경로에 연결되지 않음
                결과: cache_hit 발생 불가 (100% miss)

  수술 후:
    predict() → _get_from_cache(hash)  ← self._cache dict 직접 조회
                  └─ hit이면 즉시 반환
                _save_to_cache(hash, result) → self._cache[hash] = result
                  └─ OrderedDict 기반 LRU 정책 적용
    반환값: (predictions, from_cache: bool)  ← app.py에서 사용 가능
─────────────────────────────────────────
"""

import time
import hashlib
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

import numpy as np
import numpy as np

from backend.models import ModelPredictor
from backend.utils import get_logger, ModelLoadError, PredictionError


class ModelService:
    """
    모델 관리 및 예측 서비스

    역할:
    - 모델 로딩 및 라이프사이클 관리
    - 예측 결과 캐싱 (OrderedDict 기반 LRU)
    - 모델 워밍업 및 성능 최적화
    - 통계 및 메트릭 수집
    """

    def __init__(
        self,
        model_path: str,
        labels_path: str,
        enable_cache: bool = True,
        cache_size: int = 128
    ):
        """
        Args:
            model_path: 모델 파일 경로 (.pt 지원, 없으면 pretrained 사용)
            labels_path: 레이블 파일 경로
            enable_cache: 예측 캐싱 활성화 여부
            cache_size: LRU 캐시 최대 크기
        """
        self.model_path = model_path
        self.labels_path = labels_path
        self.enable_cache = enable_cache
        self.cache_size = cache_size

        self.logger = get_logger('aiclassifier.model_service')

        # 내부 ModelPredictor 인스턴스
        self._predictor: Optional[ModelPredictor] = None

        # OrderedDict 기반 LRU 캐시
        # - 조회·저장 시 해당 키를 end로 이동
        # - 크기 초과 시 가장 앞(오래된 항목)을 제거
        self._cache: OrderedDict = OrderedDict()

        # 통계
        self.stats = {
            'total_predictions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_inference_time_ms': 0.0,
            'warmup_completed': False
        }

        self.logger.info(
            f"✓ ModelService 초기화 (캐싱: {enable_cache}, 캐시 크기: {cache_size})"
        )

    # ─── 모델 로딩 ────────────────────────────────────────────────

    def load_model(self) -> None:
        """모델 로딩 및 초기화"""
        if self._predictor is None:
            self._predictor = ModelPredictor(
                model_path=self.model_path,
                labels_path=self.labels_path
            )
            self._predictor.load_model()
            self.logger.info("✓ 모델 로딩 완료")

            # 워밍업 수행
            if not self.stats['warmup_completed']:
                self._warmup_model()

    def _warmup_model(self) -> None:
        """
        모델 워밍업

        첫 예측은 모델 초기화로 인해 느릴 수 있으므로,
        더미 입력으로 사전 예측을 수행하여 성능 최적화
        """
        try:
            self.logger.info("🔥 모델 워밍업 시작...")

            # 더미 입력 생성 (1, 224, 224, 3) — ONNX Runtime NHWC 포맷
            dummy_input = np.random.rand(1, 224, 224, 3).astype(np.float32)

            start_time = time.time()
            _ = self._predictor.predict(dummy_input)
            warmup_time = (time.time() - start_time) * 1000

            self.stats['warmup_completed'] = True
            self.logger.info(f"✓ 모델 워밍업 완료 ({warmup_time:.0f}ms)")

        except Exception as e:
            self.logger.warning(f"모델 워밍업 실패 (무시됨): {e}")

    def is_ready(self) -> bool:
        """모델 준비 상태 확인"""
        return self._predictor is not None and self._predictor.is_ready()

    # ─── 예측 (캐시 조회 → 미스시 추론 → 저장) ───────────────────

    def predict(
        self,
        processed_image,
        use_cache: Optional[bool] = None
    ) -> Tuple[List[Dict[str, any]], bool]:
        """
        이미지 예측 (캐싱 지원)

        Args:
            processed_image: 전처리된 이미지 (torch.Tensor 또는 numpy array)
            use_cache: 캐시 사용 여부 (None이면 기본 설정 따름)

        Returns:
            (predictions, from_cache)
              - predictions : 예측 결과 리스트
              - from_cache   : True이면 캐시에서 반환된 결과
        """
        if not self.is_ready():
            raise PredictionError("모델이 로드되지 않았습니다")

        self.stats['total_predictions'] += 1
        should_use_cache = use_cache if use_cache is not None else self.enable_cache

        # ── 캐시 조회 ──────────────────────────────────────────
        if should_use_cache:
            image_hash = self._compute_image_hash(processed_image)
            cached = self._get_from_cache(image_hash)

            if cached is not None:
                self.stats['cache_hits'] += 1
                self.logger.debug(f"✓ 캐시 히트 (해시: {image_hash[:8]}...)")
                return cached, True          # ← from_cache = True

            self.stats['cache_misses'] += 1

        # ── 실제 추론 ──────────────────────────────────────────
        start_time = time.time()
        predictions = self._predictor.predict(processed_image)
        inference_time = (time.time() - start_time) * 1000
        self.stats['total_inference_time_ms'] += inference_time

        # ── 캐시 저장 ──────────────────────────────────────────
        if should_use_cache:
            self._save_to_cache(image_hash, predictions)

        return predictions, False            # ← from_cache = False

    # ─── 캐시 내부 구현 (OrderedDict LRU) ─────────────────────────

    def _compute_image_hash(self, image_array) -> str:
        """
        이미지 배열의 해시값 계산 (SHA-256)

        numpy 배열의 바이트 표현이 동일하면 해시도 동일하므로,
        동일한 이미지에 대한 캐시 조회가 정확히 동작합니다.
        """
        try:
            if isinstance(image_array, np.ndarray):
                buf = image_array.tobytes()
            else:
                # 알 수 없는 타입은 문자열 표현으로 해시
                buf = str(image_array).encode('utf-8')
            return hashlib.sha256(buf).hexdigest()
        except Exception:
            # 해시 실패 시 랜덤 값으로 충돌 최소화
            return hashlib.sha256(np.random.rand(32).tobytes()).hexdigest()

    def _get_from_cache(self, image_hash: str) -> Optional[List[Dict]]:
        """
        캐시 조회 + LRU 순서 갱신

        조회된 키를 OrderedDict의 end로 이동하여
        최근 사용된 항목이 제거되지 않도록 합니다.
        """
        if image_hash not in self._cache:
            return None

        # move_to_end → 최근 사용 시간 갱신
        self._cache.move_to_end(image_hash)
        return self._cache[image_hash]

    def _save_to_cache(self, image_hash: str, predictions: List[Dict]) -> None:
        """
        캐시 저장 + LRU 정책 적용

        크기 초과 시 가장 오래된 항목(begin)을 제거합니다.
        """
        # 이미 존재하면 값 갱신 + end로 이동
        if image_hash in self._cache:
            self._cache.move_to_end(image_hash)
            self._cache[image_hash] = predictions
            return

        # 새 항목 추가
        self._cache[image_hash] = predictions

        # LRU 퇴장: 크기 초과 시 begin(oldest) 제거
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    # ─── 모델 정보 / 통계 ─────────────────────────────────────────

    def get_model_info(self) -> Dict[str, any]:
        """모델 정보 조회"""
        if self._predictor:
            return self._predictor.get_model_info()
        return {
            'status': 'not_loaded',
            'model_path': self.model_path,
            'labels_path': self.labels_path
        }

    def get_statistics(self) -> Dict[str, any]:
        """
        서비스 통계 조회

        Returns:
            캐시 히트율, 평균 추론 시간 등 통계 딕셔너리
        """
        total = self.stats['total_predictions']
        hits = self.stats['cache_hits']
        misses = self.stats['cache_misses']

        cache_hit_rate = (hits / total * 100) if total > 0 else 0.0
        avg_inference_time = (
            self.stats['total_inference_time_ms'] / misses
        ) if misses > 0 else 0.0

        return {
            'total_predictions': total,
            'cache_enabled': self.enable_cache,
            'cache_size': self.cache_size,
            'cache_hits': hits,
            'cache_misses': misses,
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'avg_inference_time_ms': round(avg_inference_time, 2),
            'total_inference_time_ms': round(self.stats['total_inference_time_ms'], 2),
            'warmup_completed': self.stats['warmup_completed']
        }

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._cache.clear()
        self.stats['cache_hits'] = 0
        self.stats['cache_misses'] = 0
        self.logger.info("✓ 캐시 초기화 완료")

    def get_cache_info(self) -> Dict[str, int]:
        """캐시 정보 조회"""
        return {
            'hits': self.stats['cache_hits'],
            'misses': self.stats['cache_misses'],
            'maxsize': self.cache_size,
            'currsize': len(self._cache)
        }
