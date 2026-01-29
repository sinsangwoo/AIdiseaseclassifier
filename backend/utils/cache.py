"""
예측 결과 캐싱 모듈

동일한 이미지에 대한 반복 예측 요청을 캐싱하여 성능을 최적화합니다.
"""

import hashlib
import time
from typing import Any, Optional, Tuple
from threading import Lock

from .logger import get_logger


logger = get_logger('aiclassifier.cache')


class PredictionCache:
    """
    LRU(Least Recently Used) 기반 예측 결과 캐시
    """
    
    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600
    ):
        """
        캐시 초기화
        
        Args:
            max_size (int): 최대 캐시 항목 수
            ttl_seconds (int): 캐시 유지 시간 (초)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # {hash: (result, timestamp, access_count)}
        self.cache = {}
        
        # LRU를 위한 액세스 순서 추적
        self.access_order = []
        
        self.lock = Lock()
        
        # 통계
        self.hits = 0
        self.misses = 0
    
    def _compute_hash(self, image_bytes: bytes) -> str:
        """
        이미지 바이트의 해시 계산
        
        Args:
            image_bytes (bytes): 이미지 데이터
        
        Returns:
            str: SHA-256 해시
        """
        return hashlib.sha256(image_bytes).hexdigest()
    
    def get(self, image_bytes: bytes) -> Optional[Any]:
        """
        캐시에서 예측 결과 가져오기
        
        Args:
            image_bytes (bytes): 이미지 데이터
        
        Returns:
            Optional[Any]: 캐시된 결과 (없으면 None)
        """
        cache_key = self._compute_hash(image_bytes)
        
        with self.lock:
            if cache_key in self.cache:
                result, timestamp, access_count = self.cache[cache_key]
                
                # TTL 확인
                if time.time() - timestamp > self.ttl_seconds:
                    # 만료된 항목 제거
                    del self.cache[cache_key]
                    self.access_order.remove(cache_key)
                    self.misses += 1
                    logger.debug(f"캐시 만료: {cache_key[:8]}...")
                    return None
                
                # 캐시 히트
                self.hits += 1
                
                # 액세스 카운트 증가 및 순서 업데이트
                self.cache[cache_key] = (result, timestamp, access_count + 1)
                self.access_order.remove(cache_key)
                self.access_order.append(cache_key)
                
                logger.info(
                    f"캐시 히트: {cache_key[:8]}... "
                    f"(히트율: {self.get_hit_rate():.1%})"
                )
                
                return result
            
            # 캐시 미스
            self.misses += 1
            return None
    
    def set(self, image_bytes: bytes, result: Any):
        """
        예측 결과를 캐시에 저장
        
        Args:
            image_bytes (bytes): 이미지 데이터
            result (Any): 예측 결과
        """
        cache_key = self._compute_hash(image_bytes)
        
        with self.lock:
            # 캐시가 가득 찬 경우 LRU 항목 제거
            if len(self.cache) >= self.max_size and cache_key not in self.cache:
                if self.access_order:
                    oldest_key = self.access_order.pop(0)
                    del self.cache[oldest_key]
                    logger.debug(f"LRU 제거: {oldest_key[:8]}...")
            
            # 캐시에 저장
            timestamp = time.time()
            self.cache[cache_key] = (result, timestamp, 1)
            
            if cache_key in self.access_order:
                self.access_order.remove(cache_key)
            self.access_order.append(cache_key)
            
            logger.debug(
                f"캐시 저장: {cache_key[:8]}... "
                f"(캐시 크기: {len(self.cache)}/{self.max_size})"
            )
    
    def clear(self):
        """캐시 전체 삭제"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.hits = 0
            self.misses = 0
            logger.info("캐시 전체 삭제 완료")
    
    def cleanup_expired(self):
        """만료된 캐시 항목 정리"""
        current_time = time.time()
        
        with self.lock:
            expired_keys = [
                key for key, (_, timestamp, _) in self.cache.items()
                if current_time - timestamp > self.ttl_seconds
            ]
            
            for key in expired_keys:
                del self.cache[key]
                self.access_order.remove(key)
            
            if expired_keys:
                logger.info(f"만료된 캐시 항목 {len(expired_keys)}개 제거")
    
    def get_stats(self) -> dict:
        """
        캐시 통계 반환
        
        Returns:
            dict: 캐시 통계 정보
        """
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'total_requests': total_requests,
                'hit_rate': round(hit_rate, 3),
                'ttl_seconds': self.ttl_seconds
            }
    
    def get_hit_rate(self) -> float:
        """캐시 히트율 반환"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0


# 전역 캐시 인스턴스
_prediction_cache = None


def get_prediction_cache() -> Optional[PredictionCache]:
    """전역 예측 캐시 인스턴스 가져오기"""
    return _prediction_cache


def init_prediction_cache(app, enabled: bool = True):
    """
    Flask 앱에 예측 캐시 초기화
    
    Args:
        app: Flask 애플리케이션 인스턴스
        enabled (bool): 캐시 활성화 여부
    """
    global _prediction_cache
    
    if not enabled:
        logger.info("예측 캐시 비활성화됨")
        return None
    
    cache_size = app.config.get('CACHE_MAX_SIZE', 100)
    cache_ttl = app.config.get('CACHE_TTL_SECONDS', 3600)
    
    _prediction_cache = PredictionCache(
        max_size=cache_size,
        ttl_seconds=cache_ttl
    )
    
    logger.info(
        f"예측 캐시 초기화 완료 "
        f"(최대 크기: {cache_size}, TTL: {cache_ttl}초)"
    )
    
    # 캐시 통계 엔드포인트
    @app.route('/metrics/cache')
    def cache_stats():
        """캐시 통계 조회 엔드포인트"""
        if _prediction_cache is None:
            return {'success': False, 'error': '캐시가 비활성화되어 있습니다'}
        
        return {
            'success': True,
            'data': _prediction_cache.get_stats()
        }
    
    return _prediction_cache


def cached_prediction(cache_enabled: bool = True):
    """
    예측 결과 캐싱 데코레이터
    
    Args:
        cache_enabled (bool): 캐싱 활성화 여부
    
    Example:
        @cached_prediction()
        def predict(image_bytes):
            ...
    """
    def decorator(f):
        def wrapper(image_bytes: bytes, *args, **kwargs):
            cache = get_prediction_cache()
            
            # 캐시가 비활성화되어 있거나 없으면 원본 함수 실행
            if not cache_enabled or cache is None:
                return f(image_bytes, *args, **kwargs)
            
            # 캐시에서 조회
            cached_result = cache.get(image_bytes)
            if cached_result is not None:
                return cached_result
            
            # 캐시 미스 - 실제 예측 수행
            result = f(image_bytes, *args, **kwargs)
            
            # 결과 캐싱
            cache.set(image_bytes, result)
            
            return result
        
        return wrapper
    return decorator
