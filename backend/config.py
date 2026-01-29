"""
애플리케이션 설정 관리 모듈

환경변수를 활용한 설정 관리와 개발/프로덕션 환경 분리를 제공합니다.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# .env 파일 로드 (있는 경우)
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


class Config:
    """기본 설정 클래스"""
    
    # 프로젝트 루트 디렉토리
    BASE_DIR = Path(__file__).parent
    
    # Flask 설정
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # 모델 설정
    MODEL_PATH = os.environ.get('MODEL_PATH', 'model.onnx')
    LABELS_PATH = os.environ.get('LABELS_PATH', 'labels.txt')
    
    # 이미지 처리 설정
    TARGET_IMAGE_SIZE = (224, 224)
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))  # 10MB
    
    # CORS 설정 (프로덕션에서는 특정 도메인으로 제한해야 함)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # 로깅 설정
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = BASE_DIR / 'logs'
    
    # Rate Limiting 설정
    API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', 30))  # 분당 30회
    API_BURST_SIZE = int(os.environ.get('API_BURST_SIZE', 10))  # 버스트 10회
    DEFAULT_RATE_LIMIT = int(os.environ.get('DEFAULT_RATE_LIMIT', 100))  # 분당 100회
    DEFAULT_BURST_SIZE = int(os.environ.get('DEFAULT_BURST_SIZE', 20))
    
    # 캐싱 설정
    CACHE_ENABLED = os.environ.get('CACHE_ENABLED', 'true').lower() == 'true'
    CACHE_MAX_SIZE = int(os.environ.get('CACHE_MAX_SIZE', 100))
    CACHE_TTL_SECONDS = int(os.environ.get('CACHE_TTL_SECONDS', 3600))  # 1시간
    
    # 보안 헤더 설정
    SECURITY_HEADERS_ENABLED = True
    CSP_ENABLED = True
    HSTS_ENABLED = False  # 개발 환경에서는 비활성화


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS', 
        'http://localhost:3000,http://127.0.0.1:3000'
    ).split(',')
    
    # 개발 환경에서는 Rate Limit 완화
    API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', 60))
    DEFAULT_RATE_LIMIT = int(os.environ.get('DEFAULT_RATE_LIMIT', 200))
    
    # 개발 환경에서는 HSTS 비활성화
    HSTS_ENABLED = False


class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False
    
    # 프로덕션에서는 반드시 환경변수로 설정해야 함
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    
    # 프로덕션에서는 엄격한 Rate Limit
    API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', 20))  # 분당 20회
    API_BURST_SIZE = int(os.environ.get('API_BURST_SIZE', 5))
    
    # HSTS 활성화
    HSTS_ENABLED = True
    
    @classmethod
    def validate(cls):
        """프로덕션 환경 필수 설정 검증"""
        required_vars = ['SECRET_KEY', 'CORS_ORIGINS']
        missing = [var for var in required_vars if not os.environ.get(var)]
        
        if missing:
            raise EnvironmentError(
                f"프로덕션 환경에서 다음 환경변수가 필요합니다: {', '.join(missing)}"
            )


class TestingConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    DEBUG = True
    MODEL_PATH = 'tests/fixtures/test_model.onnx'
    LABELS_PATH = 'tests/fixtures/test_labels.txt'
    
    # 테스트에서는 Rate Limit 및 캐시 비활성화
    API_RATE_LIMIT = 1000
    DEFAULT_RATE_LIMIT = 1000
    CACHE_ENABLED = False


# 환경별 설정 매핑
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """
    환경에 맞는 설정 객체 반환
    
    Args:
        env (str): 환경 이름 ('development', 'production', 'testing')
                  None인 경우 FLASK_ENV 환경변수 사용
    
    Returns:
        Config: 환경에 맞는 설정 클래스
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'default')
    
    config_class = config.get(env, config['default'])
    
    # 프로덕션 환경인 경우 설정 검증
    if env == 'production':
        config_class.validate()
    
    return config_class
