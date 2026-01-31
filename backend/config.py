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
    
    # ✅ 모델 설정 - Render 환경 우선 처리
    if os.environ.get('RENDER'):
        # Render 환경: 상대 경로 사용 (워킹 디렉토리 = 프로젝트 루트)
        MODEL_PATH = os.environ.get('MODEL_PATH', 'backend/models/artifacts/model.onnx')
        LABELS_PATH = os.environ.get('LABELS_PATH', 'backend/models/artifacts/labels.txt')
    else:
        # 로컬 환경: 절대 경로 사용
        MODEL_DIR = BASE_DIR / 'models' / 'artifacts'
        MODEL_PATH = os.environ.get(
            'MODEL_PATH',
            str(MODEL_DIR / 'model.onnx')
        )
        LABELS_PATH = os.environ.get(
            'LABELS_PATH', 
            str(MODEL_DIR / 'labels.txt')
        )
    
    # 이미지 처리 설정
    TARGET_IMAGE_SIZE = (224, 224)
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))  # 10MB
    
    # CORS 설정
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS_METHODS = ['GET', 'POST', 'OPTIONS']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With']
    CORS_EXPOSE_HEADERS = ['Content-Type', 'X-Request-ID']
    CORS_MAX_AGE = 3600
    CORS_SUPPORTS_CREDENTIALS = False
    
    # 로깅 설정
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = BASE_DIR / 'logs'


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS', 
        'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5500,http://127.0.0.1:5500'
    ).split(',')


class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False
    
    default_origins = 'https://sinsangwoo.github.io'
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', default_origins).split(',')
    
    SECURITY_HEADERS = True
    
    @classmethod
    def validate(cls):
        """프로덕션 환경 필수 설정 검증"""
        required_vars = ['SECRET_KEY']
        missing = [var for var in required_vars if not os.environ.get(var) or os.environ.get(var) == 'dev-secret-key-change-in-production']
        
        if missing:
            print(f"⚠️  WARNING: 프로덕션 환경에서 다음 환경변수 설정이 권장됩니다: {', '.join(missing)}")


class TestingConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    DEBUG = True
    
    MODEL_PATH = 'tests/fixtures/test_model.onnx'
    LABELS_PATH = 'tests/fixtures/test_labels.txt'
    
    CORS_ORIGINS = ['http://localhost:5000', 'http://127.0.0.1:5000']


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
    
    Returns:
        Config: 환경에 맞는 설정 클래스
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'default')
    
    config_class = config.get(env, config['default'])
    
    if env == 'production':
        config_class.validate()
    
    return config_class
