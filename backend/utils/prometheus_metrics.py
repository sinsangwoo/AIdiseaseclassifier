"""
Prometheus 메트릭 수집 모듈

Enterprise-grade observability를 위한 Prometheus 메트릭 시스템.
Grafana 대시보드와 네이티브 통합되며, production 환경의
성능 분석 및 장애 대응을 지원합니다.
"""

import time
import psutil
from typing import Optional, Callable
from functools import wraps

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)


# ─── 글로벌 레지스트리 ─────────────────────────────────────────────
# 
# 모든 메트릭을 단일 레지스트리에 등록하여 /metrics 엔드포인트에서
# 일관되게 export합니다. 테스트 환경에서는 별도 레지스트리 사용 가능.
#
REGISTRY = CollectorRegistry(auto_describe=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  메트릭 정의
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ─── 1. API 요청 메트릭 ────────────────────────────────────────

# 총 HTTP 요청 수 (endpoint, method, status 차원)
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['endpoint', 'method', 'status'],
    registry=REGISTRY
)

# 요청 처리 시간 히스토그램 (P50/P95/P99 분석용)
# 버킷: 10ms, 50ms, 100ms, 500ms, 1s, 5s, 10s, 30s, +Inf
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['endpoint', 'method'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, float('inf')),
    registry=REGISTRY
)

# 요청 크기 (바이트)
http_request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['endpoint', 'method'],
    registry=REGISTRY
)

# 응답 크기 (바이트)
http_response_size_bytes = Summary(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['endpoint', 'method'],
    registry=REGISTRY
)

# ─── 2. 모델 추론 메트릭 ───────────────────────────────────────

# 총 예측 요청 수 (성공/실패)
predictions_total = Counter(
    'predictions_total',
    'Total prediction requests',
    ['status'],  # success, cache_hit, error
    registry=REGISTRY
)

# 추론 시간 히스토그램 (모델 실행 시간만 측정)
# 버킷: 50ms, 100ms, 200ms, 500ms, 1s, 2s, 5s
inference_duration_seconds = Histogram(
    'inference_duration_seconds',
    'Model inference time in seconds',
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, float('inf')),
    registry=REGISTRY
)

# 전처리 시간
preprocessing_duration_seconds = Histogram(
    'preprocessing_duration_seconds',
    'Image preprocessing time in seconds',
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1.0, float('inf')),
    registry=REGISTRY
)

# ─── 3. 캐시 메트릭 ────────────────────────────────────────────

# 캐시 히트 수
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    registry=REGISTRY
)

# 캐시 미스 수
cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    registry=REGISTRY
)

# 캐시 히트율 (0.0~1.0)
cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate (0.0 to 1.0)',
    registry=REGISTRY
)

# 캐시 크기 (현재 항목 수)
cache_size_current = Gauge(
    'cache_size_current',
    'Current number of items in cache',
    registry=REGISTRY
)

# 캐시 메모리 사용량 추정 (바이트)
cache_memory_bytes = Gauge(
    'cache_memory_bytes',
    'Estimated cache memory usage in bytes',
    registry=REGISTRY
)

# ─── 4. 모델 상태 메트릭 ───────────────────────────────────────

# 모델 로드 상태 (0: 미준비, 1: 정상, 2: 에러)
model_state = Gauge(
    'model_state',
    'Model state (0=not_loaded, 1=loaded, 2=error)',
    registry=REGISTRY
)

# 모델 로드 시간
model_load_duration_seconds = Gauge(
    'model_load_duration_seconds',
    'Time taken to load model',
    registry=REGISTRY
)

# 모델 메모리 사용량 (바이트)
model_memory_bytes = Gauge(
    'model_memory_bytes',
    'Model memory usage in bytes',
    registry=REGISTRY
)

# ─── 5. 시스템 리소스 메트릭 ───────────────────────────────────

# CPU 사용률 (0.0~100.0)
system_cpu_percent = Gauge(
    'system_cpu_percent',
    'System CPU usage percentage',
    registry=REGISTRY
)

# 메모리 사용률 (0.0~100.0)
system_memory_percent = Gauge(
    'system_memory_percent',
    'System memory usage percentage',
    registry=REGISTRY
)

# 메모리 사용량 (바이트)
system_memory_bytes = Gauge(
    'system_memory_bytes',
    'System memory usage in bytes',
    ['type'],  # used, available, total
    registry=REGISTRY
)

# 프로세스 메모리 (바이트)
process_memory_bytes = Gauge(
    'process_memory_bytes',
    'Process memory usage in bytes',
    ['type'],  # rss, vms
    registry=REGISTRY
)

# ─── 6. 애플리케이션 정보 ──────────────────────────────────────

# 앱 메타데이터 (버전, 환경 등)
app_info = Info(
    'app',
    'Application information',
    registry=REGISTRY
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  헬퍼 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def update_system_metrics():
    """
    시스템 리소스 메트릭 업데이트
    
    주기적으로 호출하여 CPU/메모리 사용률을 갱신합니다.
    /metrics 엔드포인트 호출 시 자동 실행됩니다.
    """
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        system_cpu_percent.set(cpu_percent)
        
        # 시스템 메모리
        mem = psutil.virtual_memory()
        system_memory_percent.set(mem.percent)
        system_memory_bytes.labels(type='used').set(mem.used)
        system_memory_bytes.labels(type='available').set(mem.available)
        system_memory_bytes.labels(type='total').set(mem.total)
        
        # 프로세스 메모리
        process = psutil.Process()
        mem_info = process.memory_info()
        process_memory_bytes.labels(type='rss').set(mem_info.rss)
        process_memory_bytes.labels(type='vms').set(mem_info.vms)
        
    except Exception:
        # psutil 에러는 조용히 무시 (메트릭 수집 실패가 앱을 중단시키면 안 됨)
        pass


def track_request_time(endpoint: str, method: str) -> Callable:
    """
    HTTP 요청 시간 추적 데코레이터
    
    Args:
        endpoint: 엔드포인트 경로 (예: '/predict', '/health')
        method: HTTP 메서드 (예: 'POST', 'GET')
    
    Returns:
        데코레이터 함수
    
    Example:
        @track_request_time('/predict', 'POST')
        def predict():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                http_request_duration_seconds.labels(
                    endpoint=endpoint,
                    method=method
                ).observe(duration)
        return wrapper
    return decorator


def record_prediction(
    success: bool,
    cache_hit: bool,
    inference_time: Optional[float] = None,
    preprocessing_time: Optional[float] = None
):
    """
    예측 요청 메트릭 기록
    
    Args:
        success: 예측 성공 여부
        cache_hit: 캐시 히트 여부
        inference_time: 추론 시간 (초, 캐시 미스 시만 제공)
        preprocessing_time: 전처리 시간 (초, 선택)
    
    Example:
        # 캐시 히트
        record_prediction(success=True, cache_hit=True)
        
        # 실제 추론
        record_prediction(
            success=True,
            cache_hit=False,
            inference_time=0.342,
            preprocessing_time=0.015
        )
    """
    if cache_hit:
        predictions_total.labels(status='cache_hit').inc()
        cache_hits_total.inc()
    elif success:
        predictions_total.labels(status='success').inc()
        cache_misses_total.inc()
        
        if inference_time is not None:
            inference_duration_seconds.observe(inference_time)
        
        if preprocessing_time is not None:
            preprocessing_duration_seconds.observe(preprocessing_time)
    else:
        predictions_total.labels(status='error').inc()


def update_cache_metrics(
    current_size: int,
    total_hits: int,
    total_misses: int,
    memory_bytes: Optional[int] = None
):
    """
    캐시 메트릭 업데이트
    
    Args:
        current_size: 현재 캐시 항목 수
        total_hits: 총 캐시 히트 수
        total_misses: 총 캐시 미스 수
        memory_bytes: 캐시 메모리 사용량 (바이트, 선택)
    
    Example:
        update_cache_metrics(
            current_size=42,
            total_hits=127,
            total_misses=85,
            memory_bytes=5242880  # 5MB
        )
    """
    cache_size_current.set(current_size)
    
    # 히트율 계산 (0으로 나누기 방지)
    total_requests = total_hits + total_misses
    if total_requests > 0:
        hit_rate = total_hits / total_requests
        cache_hit_rate.set(hit_rate)
    else:
        cache_hit_rate.set(0.0)
    
    if memory_bytes is not None:
        cache_memory_bytes.set(memory_bytes)


def set_model_state(state: str, load_time: Optional[float] = None):
    """
    모델 상태 메트릭 설정
    
    Args:
        state: 모델 상태 ('not_loaded', 'loaded', 'error')
        load_time: 모델 로드 시간 (초, 선택)
    
    Example:
        set_model_state('loaded', load_time=2.341)
        set_model_state('error')
    """
    state_map = {
        'not_loaded': 0,
        'loaded': 1,
        'error': 2
    }
    model_state.set(state_map.get(state, 0))
    
    if load_time is not None:
        model_load_duration_seconds.set(load_time)


def set_app_info(version: str, environment: str, **kwargs):
    """
    애플리케이션 메타데이터 설정
    
    Args:
        version: 앱 버전
        environment: 환경 (development, production, testing)
        **kwargs: 추가 메타데이터
    
    Example:
        set_app_info(
            version='1.0.0',
            environment='production',
            python_version='3.10.12'
        )
    """
    info_dict = {
        'version': version,
        'environment': environment,
        **kwargs
    }
    app_info.info(info_dict)


def get_metrics() -> tuple[bytes, str]:
    """
    Prometheus 형식 메트릭 export
    
    /metrics 엔드포인트에서 호출됩니다.
    
    Returns:
        tuple: (메트릭 바이트, content-type)
    
    Example:
        metrics_output, content_type = get_metrics()
        return Response(metrics_output, mimetype=content_type)
    """
    # 시스템 메트릭 갱신
    update_system_metrics()
    
    # Prometheus 형식으로 export
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Middleware 통합
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PrometheusMiddleware:
    """
    Flask 미들웨어: 자동 메트릭 수집
    
    모든 HTTP 요청에 대해 자동으로 메트릭을 수집합니다.
    
    Usage:
        app = Flask(__name__)
        app.wsgi_app = PrometheusMiddleware(app.wsgi_app)
    """
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # 요청 시작 시간
        start_time = time.time()
        
        # 요청 정보 추출
        path = environ.get('PATH_INFO', '/')
        method = environ.get('REQUEST_METHOD', 'GET')
        
        # 응답 캡처용 래퍼
        status_code = [None]
        
        def custom_start_response(status, headers, exc_info=None):
            # 상태 코드 추출 (예: "200 OK" → "200")
            status_code[0] = status.split()[0]
            return start_response(status, headers, exc_info)
        
        try:
            # 실제 요청 처리
            response = self.app(environ, custom_start_response)
            return response
        finally:
            # 메트릭 기록
            duration = time.time() - start_time
            
            http_requests_total.labels(
                endpoint=path,
                method=method,
                status=status_code[0] or '500'
            ).inc()
            
            http_request_duration_seconds.labels(
                endpoint=path,
                method=method
            ).observe(duration)
