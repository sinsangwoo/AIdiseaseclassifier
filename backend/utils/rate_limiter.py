"""
Rate Limiting 미들웨어 모듈

API 요청 속도를 제한하여 서비스 남용과 DDoS 공격을 방지합니다.
"""

import time
import functools
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple
from flask import request, g

from .exceptions import AIClassifierException
from .responses import error_response


class RateLimitExceeded(AIClassifierException):
    """속도 제한 초과 예외"""
    def __init__(self, message: str = "요청 속도 제한을 초과했습니다", retry_after: int = None):
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED")
        self.retry_after = retry_after


class RateLimiter:
    """
    토큰 버킷 알고리즘 기반 Rate Limiter
    
    각 클라이언트(IP)별로 독립적인 토큰 버킷을 관리합니다.
    """
    
    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
        burst_size: int = None
    ):
        """
        Rate Limiter 초기화
        
        Args:
            max_requests (int): 시간 윈도우당 최대 요청 수
            window_seconds (int): 시간 윈도우 (초)
            burst_size (int, optional): 버스트 허용 크기 (기본값: max_requests)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_size = burst_size or max_requests
        
        # {client_id: (tokens, last_update_time)}
        self.clients: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (self.burst_size, time.time())
        )
        self.lock = Lock()
    
    def _get_client_id(self) -> str:
        """
        클라이언트 식별자 생성
        
        Returns:
            str: 클라이언트 ID (IP 주소 또는 사용자 ID)
        """
        # X-Forwarded-For 헤더 확인 (프록시 뒤에 있는 경우)
        if request.headers.get('X-Forwarded-For'):
            return request.headers['X-Forwarded-For'].split(',')[0].strip()
        
        # X-Real-IP 헤더 확인
        if request.headers.get('X-Real-IP'):
            return request.headers['X-Real-IP']
        
        # 직접 연결된 IP
        return request.remote_addr or 'unknown'
    
    def _refill_tokens(self, client_id: str, current_time: float) -> float:
        """
        토큰 버킷 리필
        
        Args:
            client_id (str): 클라이언트 ID
            current_time (float): 현재 시간
        
        Returns:
            float: 현재 토큰 수
        """
        tokens, last_update = self.clients[client_id]
        
        # 경과 시간 계산
        elapsed = current_time - last_update
        
        # 토큰 리필 속도 계산 (초당)
        refill_rate = self.max_requests / self.window_seconds
        
        # 새로운 토큰 추가
        new_tokens = min(
            self.burst_size,
            tokens + (elapsed * refill_rate)
        )
        
        self.clients[client_id] = (new_tokens, current_time)
        return new_tokens
    
    def check_rate_limit(self) -> Tuple[bool, Dict]:
        """
        현재 요청이 속도 제한을 초과하는지 확인
        
        Returns:
            Tuple[bool, Dict]: (허용 여부, 메타데이터)
        """
        client_id = self._get_client_id()
        current_time = time.time()
        
        with self.lock:
            # 토큰 리필
            tokens = self._refill_tokens(client_id, current_time)
            
            # 토큰이 있으면 소비
            if tokens >= 1.0:
                self.clients[client_id] = (tokens - 1.0, current_time)
                
                metadata = {
                    'allowed': True,
                    'remaining': int(tokens - 1.0),
                    'limit': self.max_requests,
                    'reset': int(current_time + self.window_seconds)
                }
                return True, metadata
            
            # 토큰 부족 - 재시도 시간 계산
            retry_after = int((1.0 - tokens) / (self.max_requests / self.window_seconds))
            
            metadata = {
                'allowed': False,
                'remaining': 0,
                'limit': self.max_requests,
                'reset': int(current_time + retry_after),
                'retry_after': retry_after
            }
            return False, metadata
    
    def cleanup_old_clients(self, max_age_seconds: int = 3600):
        """
        오래된 클라이언트 데이터 정리
        
        Args:
            max_age_seconds (int): 최대 유지 시간 (초)
        """
        current_time = time.time()
        
        with self.lock:
            # 오래된 엔트리 제거
            to_remove = [
                client_id 
                for client_id, (_, last_update) in self.clients.items()
                if current_time - last_update > max_age_seconds
            ]
            
            for client_id in to_remove:
                del self.clients[client_id]


# 전역 Rate Limiter 인스턴스들
_rate_limiters = {}


def get_rate_limiter(name: str = 'default') -> RateLimiter:
    """
    Rate Limiter 인스턴스 가져오기
    
    Args:
        name (str): Rate Limiter 이름
    
    Returns:
        RateLimiter: Rate Limiter 인스턴스
    """
    return _rate_limiters.get(name)


def init_rate_limiters(app):
    """
    Flask 앱에 Rate Limiter 등록
    
    Args:
        app: Flask 애플리케이션 인스턴스
    """
    # API 엔드포인트용 (예측 API)
    _rate_limiters['api'] = RateLimiter(
        max_requests=app.config.get('API_RATE_LIMIT', 30),  # 분당 30회
        window_seconds=60,
        burst_size=app.config.get('API_BURST_SIZE', 10)  # 버스트 10회
    )
    
    # 일반 엔드포인트용
    _rate_limiters['default'] = RateLimiter(
        max_requests=app.config.get('DEFAULT_RATE_LIMIT', 100),  # 분당 100회
        window_seconds=60,
        burst_size=app.config.get('DEFAULT_BURST_SIZE', 20)
    )


def rate_limit(limiter_name: str = 'default'):
    """
    Rate Limiting 데코레이터
    
    Args:
        limiter_name (str): 사용할 Rate Limiter 이름
    
    Example:
        @app.route('/predict')
        @rate_limit('api')
        def predict():
            ...
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter(limiter_name)
            
            if limiter is None:
                # Rate Limiter가 초기화되지 않은 경우 통과
                return f(*args, **kwargs)
            
            # 속도 제한 확인
            allowed, metadata = limiter.check_rate_limit()
            
            # 응답 헤더에 Rate Limit 정보 추가
            g.rate_limit_metadata = metadata
            
            if not allowed:
                return error_response(
                    "요청 속도 제한을 초과했습니다. 잠시 후 다시 시도해주세요.",
                    status_code=429,
                    error_type="RATE_LIMIT_EXCEEDED",
                    details={
                        'retry_after': metadata['retry_after'],
                        'limit': metadata['limit']
                    }
                )
            
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


def add_rate_limit_headers(response):
    """
    응답에 Rate Limit 헤더 추가 (After Request Hook용)
    
    Args:
        response: Flask Response 객체
    
    Returns:
        Response: 헤더가 추가된 Response
    """
    if hasattr(g, 'rate_limit_metadata'):
        metadata = g.rate_limit_metadata
        
        response.headers['X-RateLimit-Limit'] = str(metadata['limit'])
        response.headers['X-RateLimit-Remaining'] = str(metadata['remaining'])
        response.headers['X-RateLimit-Reset'] = str(metadata['reset'])
        
        if not metadata['allowed']:
            response.headers['Retry-After'] = str(metadata['retry_after'])
    
    return response
