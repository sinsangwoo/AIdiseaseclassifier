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

    BASE_DIR = Path(__file__).parent

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False

    MODEL_PATH = os.environ.get('MODEL_PATH', str(BASE_DIR / 'models' / 'model.onnx'))
    LABELS_PATH = os.environ.get('LABELS_PATH', str(BASE_DIR / 'models' / 'labels.txt'))

    ENABLE_MODEL_CACHE = os.environ.get('ENABLE_MODEL_CACHE', 'true').lower() in ('true', '1', 'yes')
    MODEL_CACHE_SIZE = int(os.environ.get('MODEL_CACHE_SIZE', '128'))

    TARGET_IMAGE_SIZE = (224, 224)
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))

    # CORS: 기본값을 '*' 로 설정해 어떤 환경에서도 최소한 열림
    CORS_ORIGINS = ['*']
    CORS_METHODS = ['GET', 'POST', 'OPTIONS']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With']
    CORS_EXPOSE_HEADERS = ['Content-Type', 'X-Request-ID']
    CORS_MAX_AGE = 3600
    CORS_SUPPORTS_CREDENTIALS = False

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = BASE_DIR / 'logs'


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    CORS_ORIGINS = ['*']


class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False
    # CORS_ORIGINS 환경변수가 있으면 사용, 없으면 '*' (Render 프록시 문제 방어)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    SECURITY_HEADERS = True

    @classmethod
    def validate(cls):
        required_vars = ['SECRET_KEY']
        missing = [
            v for v in required_vars
            if not os.environ.get(v)
            or os.environ.get(v) == 'dev-secret-key-change-in-production'
        ]
        if missing:
            print(f"WARNING: 프로덕션 환경변수 권장: {', '.join(missing)}")
        if not os.path.exists(cls.MODEL_PATH):
            print(f"WARNING: 모델 파일 없음: {cls.MODEL_PATH}")
        if not os.path.exists(cls.LABELS_PATH):
            print(f"WARNING: 레이블 파일 없음: {cls.LABELS_PATH}")


class TestingConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    DEBUG = True
    BASE_DIR = Path(__file__).parent
    MODEL_PATH = str(BASE_DIR / 'models' / 'model.onnx')
    LABELS_PATH = str(BASE_DIR / 'models' / 'labels.txt')
    CORS_ORIGINS = ['*']
    ENABLE_MODEL_CACHE = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}


def get_config(env=None):
    """
    환경에 맞는 설정 객체 반환.

    우선순위:
      1. 인자로 전달된 env
      2. FLASK_ENV 환경변수
      3. RENDER / RENDER_SERVICE_ID / RENDER_EXTERNAL_URL 감지 → 'production'
      4. 기본값 'default'
    """
    if env is None:
        env = os.environ.get('FLASK_ENV') or ''

    if not env:
        # FLASK_ENV 미설정 시 Render 환경변수로 2차 감지
        if (
            os.environ.get('RENDER')
            or os.environ.get('RENDER_SERVICE_ID')
            or os.environ.get('RENDER_EXTERNAL_URL')
        ):
            env = 'production'
        else:
            env = 'default'

    config_class = config.get(env, config['default'])

    if env == 'production':
        config_class.validate()

    return config_class
