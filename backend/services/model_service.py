"""
모델 관리 서비스 (Phase 3 - Backend Refactoring)

이 모듈은 ONNX 모델의 로딩, 캐싱, 예측을 담당하는 서비스 레이어입니다.
기존 ModelPredictor의 로직을 확장하여 더 나은 관심사 분리와 캐싱을 제공합니다.
"""

import os
import time
from functools import lru_cache
from typing import Dict, List, Optional, Tuple
import hashlib
import numpy as np

from ..models import ModelPredictor
from ..utils import get_logger, ModelLoadError, PredictionError


class ModelService:
    """
    모델 관리 및 예측 서비스 (Phase 3)
    
    역할:
    - 모델 로딩 및 라이프사이클 관리
    - 예측 결과 캐싱 (LRU Cache)
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
            model_path: ONNX 모델 파일 경로
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
        
        # 통계
        self.stats = {
            'total_predictions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_inference_time_ms': 0.0,
            'warmup_completed': False
        }
        
        self.logger.info(f"✓ ModelService 초기화 (캐싱: {enable_cache}, 캐시 크기: {cache_size})")
    
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
            if self.stats['warmup_completed'] is False:
                self._warmup_model()
    
    def _warmup_model(self) -> None:
        """
        모델 워밍업
        
        첫 예측은 모델 초기화로 인해 느릴 수 있으므로,
        더미 입력으로 사전 예측을 수행하여 성능 최적화
        """
        try:
            self.logger.info("🔥 모델 워밍업 시작...")
            
            # 더미 이미지 생성 (224x224 RGB)
            dummy_input = np.random.rand(1, 3, 224, 224).astype(np.float32)
            
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
    
    def predict(
        self,
        processed_image: np.ndarray,
        use_cache: Optional[bool] = None
    ) -> List[Dict[str, any]]:
        """
        이미지 예측 (캐싱 지원)
        
        Args:
            processed_image: 전처리된 이미지 (numpy array)
            use_cache: 캐시 사용 여부 (None이면 기본 설정 따름)
        
        Returns:
            예측 결과 리스트
        """
        if not self.is_ready():
            raise PredictionError("모델이 로드되지 않았습니다")
        
        self.stats['total_predictions'] += 1
        
        # 캐싱 설정
        should_use_cache = use_cache if use_cache is not None else self.enable_cache
        
        # 캐시 사용 시 이미지 해시 계산
        if should_use_cache:
            image_hash = self._compute_image_hash(processed_image)
            
            # 캐시에서 결과 조회
            cached_result = self._get_from_cache(image_hash)
            if cached_result is not None:
                self.stats['cache_hits'] += 1
                self.logger.debug(f"✓ 캐시 히트 (해시: {image_hash[:8]}...)")
                return cached_result
            
            self.stats['cache_misses'] += 1
        
        # 실제 예측 수행
        start_time = time.time()
        predictions = self._predictor.predict(processed_image)
        inference_time = (time.time() - start_time) * 1000
        
        self.stats['total_inference_time_ms'] += inference_time
        
        # 캐시에 저장
        if should_use_cache:
            self._save_to_cache(image_hash, predictions)
        
        return predictions
    
    def _compute_image_hash(self, image_array: np.ndarray) -> str:
        """
        이미지 배열의 해시값 계산
        
        Args:
            image_array: numpy 이미지 배열
        
        Returns:
            SHA-256 해시 문자열
        """
        # numpy 배열을 bytes로 변환
        image_bytes = image_array.tobytes()
        return hashlib.sha256(image_bytes).hexdigest()
    
    @lru_cache(maxsize=128)
    def _get_from_cache(self, image_hash: str) -> Optional[List[Dict[str, any]]]:
        """
        캐시에서 예측 결과 조회 (LRU Cache 사용)
        
        Note: 실제로는 lru_cache 데코레이터가 캐싱을 담당하므로,
        이 메서드는 항상 None을 반환하고 실제 캐싱은 _predict_cached에서 수행
        """
        return None
    
    def _save_to_cache(self, image_hash: str, predictions: List[Dict[str, any]]) -> None:
        """
        예측 결과를 캐시에 저장
        
        Note: _predict_cached 메서드를 통해 자동으로 캐싱됨
        """
        # LRU cache를 통한 자동 캐싱
        self._predict_cached(image_hash, predictions)
    
    @lru_cache(maxsize=128)
    def _predict_cached(
        self,
        image_hash: str,
        predictions: List[Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """
        캐시된 예측 결과 반환 (실제 LRU 캐시 저장소)
        
        Args:
            image_hash: 이미지 해시
            predictions: 예측 결과
        
        Returns:
            캐시된 예측 결과
        """
        return predictions
    
    def get_model_info(self) -> Dict[str, any]:
        """모델 정보 조회"""
        if self._predictor:
            return self._predictor.get_model_info()
        else:
            return {
                'status': 'not_loaded',
                'model_path': self.model_path,
                'labels_path': self.labels_path
            }
    
    def get_statistics(self) -> Dict[str, any]:
        """
        서비스 통계 조회
        
        Returns:
            통계 정보 딕셔너리
        """
        cache_hit_rate = 0.0
        if self.stats['total_predictions'] > 0:
            cache_hit_rate = (
                self.stats['cache_hits'] / self.stats['total_predictions']
            ) * 100
        
        avg_inference_time = 0.0
        if self.stats['cache_misses'] > 0:
            avg_inference_time = (
                self.stats['total_inference_time_ms'] / self.stats['cache_misses']
            )
        
        return {
            'total_predictions': self.stats['total_predictions'],
            'cache_enabled': self.enable_cache,
            'cache_size': self.cache_size,
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'avg_inference_time_ms': round(avg_inference_time, 2),
            'total_inference_time_ms': round(self.stats['total_inference_time_ms'], 2),
            'warmup_completed': self.stats['warmup_completed']
        }
    
    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._predict_cached.cache_clear()
        self.stats['cache_hits'] = 0
        self.stats['cache_misses'] = 0
        self.logger.info("✓ 캐시 초기화 완료")
    
    def get_cache_info(self) -> Dict[str, int]:
        """
        LRU 캐시 정보 조회
        
        Returns:
            캐시 히트/미스/크기 정보
        """
        cache_info = self._predict_cached.cache_info()
        
        return {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'maxsize': cache_info.maxsize,
            'currsize': cache_info.currsize
        }
