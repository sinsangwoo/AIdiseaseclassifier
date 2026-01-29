"""
성능 모니터링 미들웨어 모듈

API 요청의 성능을 측정하고 로깅합니다.
"""

import time
import functools
from typing import Dict, List
from collections import deque
from threading import Lock
from flask import request, g

from .logger import get_logger


logger = get_logger('aiclassifier.performance')


class PerformanceMetrics:
    """
    성능 메트릭 수집 및 관리 클래스
    """
    
    def __init__(self, max_samples: int = 1000):
        """
        성능 메트릭 초기화
        
        Args:
            max_samples (int): 저장할 최대 샘플 수
        """
        self.max_samples = max_samples
        # {endpoint: deque of response_times}
        self.metrics: Dict[str, deque] = {}
        self.lock = Lock()
    
    def record(self, endpoint: str, response_time: float):
        """
        응답 시간 기록
        
        Args:
            endpoint (str): API 엔드포인트
            response_time (float): 응답 시간 (초)
        """
        with self.lock:
            if endpoint not in self.metrics:
                self.metrics[endpoint] = deque(maxlen=self.max_samples)
            
            self.metrics[endpoint].append(response_time)
    
    def get_stats(self, endpoint: str = None) -> Dict:
        """
        통계 정보 가져오기
        
        Args:
            endpoint (str, optional): 특정 엔드포인트 (None이면 전체)
        
        Returns:
            Dict: 통계 정보
        """
        with self.lock:
            if endpoint:
                return self._calculate_stats(endpoint, self.metrics.get(endpoint, []))
            
            # 전체 통계
            all_stats = {}
            for ep, times in self.metrics.items():
                all_stats[ep] = self._calculate_stats(ep, times)
            
            return all_stats
    
    def _calculate_stats(self, endpoint: str, times: List[float]) -> Dict:
        """
        통계 계산
        
        Args:
            endpoint (str): 엔드포인트
            times (List[float]): 응답 시간 리스트
        
        Returns:
            Dict: 계산된 통계
        """
        if not times:
            return {
                'endpoint': endpoint,
                'count': 0,
                'avg': 0,
                'min': 0,
                'max': 0,
                'p50': 0,
                'p95': 0,
                'p99': 0
            }
        
        sorted_times = sorted(times)
        count = len(sorted_times)
        
        return {
            'endpoint': endpoint,
            'count': count,
            'avg': sum(sorted_times) / count,
            'min': sorted_times[0],
            'max': sorted_times[-1],
            'p50': sorted_times[int(count * 0.5)],
            'p95': sorted_times[int(count * 0.95)] if count > 20 else sorted_times[-1],
            'p99': sorted_times[int(count * 0.99)] if count > 100 else sorted_times[-1]
        }


# 전역 메트릭 인스턴스
_performance_metrics = PerformanceMetrics()


def get_performance_metrics() -> PerformanceMetrics:
    """전역 성능 메트릭 인스턴스 가져오기"""
    return _performance_metrics


def measure_performance(f):
    """
    함수 실행 시간 측정 데코레이터
    
    Example:
        @app.route('/predict')
        @measure_performance
        def predict():
            ...
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = f(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            response_time = end_time - start_time
            
            # 메트릭 기록
            endpoint = request.endpoint or 'unknown'
            _performance_metrics.record(endpoint, response_time)
            
            # g 객체에 저장 (after_request에서 사용)
            g.response_time = response_time
            
            # 느린 요청 경고 (2초 이상)
            if response_time > 2.0:
                logger.warning(
                    f"느린 요청 감지: {request.method} {request.path} - "
                    f"{response_time:.3f}초"
                )
    
    return wrapper


def init_performance_monitoring(app):
    """
    Flask 앱에 성능 모니터링 등록
    
    Args:
        app: Flask 애플리케이션 인스턴스
    """
    
    @app.before_request
    def before_request_handler():
        """요청 시작 시간 기록"""
        g.start_time = time.time()
    
    @app.after_request
    def after_request_handler(response):
        """요청 종료 후 성능 로깅"""
        if hasattr(g, 'start_time'):
            response_time = time.time() - g.start_time
            
            # 메트릭 기록
            endpoint = request.endpoint or 'unknown'
            _performance_metrics.record(endpoint, response_time)
            
            # 응답 헤더에 처리 시간 추가
            response.headers['X-Response-Time'] = f"{response_time:.3f}s"
            
            # 상세 로그 (DEBUG 레벨)
            logger.debug(
                f"{request.method} {request.path} - "
                f"Status: {response.status_code} - "
                f"Time: {response_time:.3f}s - "
                f"Size: {response.content_length or 0} bytes"
            )
            
            # 느린 요청 경고
            if response_time > 2.0:
                logger.warning(
                    f"느린 요청 감지: {request.method} {request.path} - "
                    f"{response_time:.3f}초 - Status: {response.status_code}"
                )
        
        return response
    
    # 성능 통계 엔드포인트
    @app.route('/metrics/performance')
    def performance_stats():
        """성능 통계 조회 엔드포인트 (관리자용)"""
        # TODO: 실제로는 인증 필요
        stats = _performance_metrics.get_stats()
        
        # 가독성을 위해 소수점 포맷팅
        for endpoint_stats in stats.values():
            for key in ['avg', 'min', 'max', 'p50', 'p95', 'p99']:
                if key in endpoint_stats:
                    endpoint_stats[key] = round(endpoint_stats[key], 3)
        
        return {
            'success': True,
            'data': stats
        }


def log_slow_operations(operation_name: str, threshold_seconds: float = 1.0):
    """
    느린 작업 로깅 데코레이터
    
    Args:
        operation_name (str): 작업 이름
        threshold_seconds (float): 경고 임계값 (초)
    
    Example:
        @log_slow_operations('model_prediction', threshold_seconds=0.5)
        def predict_image(image):
            ...
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = f(*args, **kwargs)
            elapsed = time.time() - start
            
            if elapsed > threshold_seconds:
                logger.warning(
                    f"느린 작업: {operation_name} - {elapsed:.3f}초 "
                    f"(임계값: {threshold_seconds}초)"
                )
            else:
                logger.debug(f"{operation_name} 완료: {elapsed:.3f}초")
            
            return result
        return wrapper
    return decorator


class PerformanceTimer:
    """
    컨텍스트 매니저 방식 성능 측정
    
    Example:
        with PerformanceTimer('image_preprocessing') as timer:
            preprocess_image(img)
        
        print(f"소요 시간: {timer.elapsed}초")
    """
    
    def __init__(self, operation_name: str, log_slow: float = None):
        """
        Args:
            operation_name (str): 작업 이름
            log_slow (float, optional): 느린 작업 로그 임계값
        """
        self.operation_name = operation_name
        self.log_slow = log_slow
        self.start_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        
        if self.log_slow and self.elapsed > self.log_slow:
            logger.warning(
                f"느린 작업: {self.operation_name} - {self.elapsed:.3f}초"
            )
        else:
            logger.debug(f"{self.operation_name} 완료: {self.elapsed:.3f}초")
