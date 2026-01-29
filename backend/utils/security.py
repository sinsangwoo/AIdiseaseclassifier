"""
보안 헤더 미들웨어 모듈

HTTP 보안 헤더를 자동으로 추가하여 다양한 웹 공격을 방지합니다.
"""

from flask import Response


class SecurityHeaders:
    """
    보안 헤더 관리 클래스
    
    OWASP 권장사항에 따른 보안 헤더를 자동으로 추가합니다.
    """
    
    def __init__(
        self,
        csp_enabled: bool = True,
        hsts_enabled: bool = True,
        content_type_nosniff: bool = True,
        frame_options: str = 'DENY',
        xss_protection: bool = True,
        referrer_policy: str = 'strict-origin-when-cross-origin'
    ):
        """
        보안 헤더 설정 초기화
        
        Args:
            csp_enabled (bool): Content Security Policy 활성화
            hsts_enabled (bool): HTTP Strict Transport Security 활성화
            content_type_nosniff (bool): X-Content-Type-Options 활성화
            frame_options (str): X-Frame-Options 설정 ('DENY', 'SAMEORIGIN')
            xss_protection (bool): X-XSS-Protection 활성화
            referrer_policy (str): Referrer-Policy 설정
        """
        self.csp_enabled = csp_enabled
        self.hsts_enabled = hsts_enabled
        self.content_type_nosniff = content_type_nosniff
        self.frame_options = frame_options
        self.xss_protection = xss_protection
        self.referrer_policy = referrer_policy
    
    def add_security_headers(self, response: Response) -> Response:
        """
        응답에 보안 헤더 추가
        
        Args:
            response (Response): Flask Response 객체
        
        Returns:
            Response: 보안 헤더가 추가된 Response
        """
        # Content Security Policy (XSS, 데이터 인젝션 공격 방지)
        if self.csp_enabled:
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        
        # HTTP Strict Transport Security (HTTPS 강제)
        # 프로덕션에서만 활성화 권장
        if self.hsts_enabled:
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains'
            )
        
        # X-Content-Type-Options (MIME 스니핑 방지)
        if self.content_type_nosniff:
            response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options (클릭재킹 공격 방지)
        if self.frame_options:
            response.headers['X-Frame-Options'] = self.frame_options
        
        # X-XSS-Protection (XSS 공격 방지 - 구형 브라우저용)
        if self.xss_protection:
            response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy (리퍼러 정보 노출 제어)
        if self.referrer_policy:
            response.headers['Referrer-Policy'] = self.referrer_policy
        
        # X-Permitted-Cross-Domain-Policies (Flash/PDF 교차 도메인 정책)
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
        
        # Permissions-Policy (브라우저 기능 접근 제어)
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=(), '
            'gyroscope=(), speaker=()'
        )
        
        return response


def init_security_headers(app, config: dict = None):
    """
    Flask 앱에 보안 헤더 미들웨어 등록
    
    Args:
        app: Flask 애플리케이션 인스턴스
        config (dict, optional): 보안 헤더 설정
    """
    config = config or {}
    
    # HSTS는 프로덕션에서만 활성화
    is_production = app.config.get('ENV') == 'production'
    
    security = SecurityHeaders(
        csp_enabled=config.get('csp_enabled', True),
        hsts_enabled=config.get('hsts_enabled', is_production),
        content_type_nosniff=config.get('content_type_nosniff', True),
        frame_options=config.get('frame_options', 'DENY'),
        xss_protection=config.get('xss_protection', True),
        referrer_policy=config.get('referrer_policy', 'strict-origin-when-cross-origin')
    )
    
    @app.after_request
    def add_security_headers_hook(response):
        """After Request Hook: 모든 응답에 보안 헤더 추가"""
        return security.add_security_headers(response)
    
    return security


def sanitize_filename(filename: str) -> str:
    """
    파일명 새니타이징 (경로 탐색 공격 방지)
    
    Args:
        filename (str): 원본 파일명
    
    Returns:
        str: 새니타이징된 파일명
    """
    import os
    import re
    
    # 경로 구분자 제거
    filename = os.path.basename(filename)
    
    # 위험한 문자 제거
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # 공백을 언더스코어로 변경
    filename = filename.replace(' ', '_')
    
    # 연속된 점 제거 (경로 탐색 방지)
    filename = re.sub(r'\.+', '.', filename)
    
    # 최대 길이 제한
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    return filename


def is_safe_redirect_url(target: str, allowed_hosts: list = None) -> bool:
    """
    리다이렉트 URL 안전성 검증 (오픈 리다이렉트 공격 방지)
    
    Args:
        target (str): 리다이렉트 대상 URL
        allowed_hosts (list, optional): 허용된 호스트 목록
    
    Returns:
        bool: 안전한 URL이면 True
    """
    from urllib.parse import urlparse, urljoin
    from flask import request
    
    # 상대 경로는 안전
    if not target:
        return False
    
    # URL 파싱
    parsed = urlparse(target)
    
    # 프로토콜이 없으면 상대 경로로 간주
    if not parsed.scheme:
        return True
    
    # 허용된 스킴만 허용
    if parsed.scheme not in ['http', 'https']:
        return False
    
    # 허용된 호스트 확인
    if allowed_hosts:
        return parsed.netloc in allowed_hosts
    
    # 같은 호스트만 허용
    target_host = parsed.netloc
    current_host = urlparse(request.host_url).netloc
    
    return target_host == current_host
