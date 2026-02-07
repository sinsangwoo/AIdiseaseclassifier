"""
AI 질병 진단 Flask 애플리케이션 (Production-Ready)

ONNX 모델을 사용하여 의료 이미지를 분석하고 질병을 예측합니다.
Phase 3-4 Rework: 백엔드 구조 개선, 모델 서비스 레이어 분리, 캐싱 도입, HTTP 캐싱
"""

import os
from flask import Flask, request
from flask_cors import CORS

from backend.config import get_config
from backend.services import ImageProcessor, ModelService
from backend.utils import (
    error_response,
    ModelLoadError,
    setup_logger,
    get_logger,
    init_health_checker,
    init_image_validator
)

# 블루프린트 임포트
from backend.routes.main import main_bp
from backend.routes.health import health_bp
from backend.routes.model import model_bp
from backend.routes.predict import predict_bp


def create_app(config_name=None):
    """
    Flask 애플리케이션 팩토리 함수
    """
    # 프론트엔드 경로 설정 (Robust path)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    frontend_dir = os.path.abspath(os.path.join(base_dir, '..', 'frontend'))
    
    app = Flask(__name__, static_folder=frontend_dir)
    
    # ===== 설정 로드 =====
    config = get_config(config_name)
    app.config.from_object(config)
    
    # ===== 로깅 설정 =====
    logger = setup_logger(
        name='aiclassifier',
        log_level=config.LOG_LEVEL,
        log_dir=config.LOG_DIR if hasattr(config, 'LOG_DIR') else None
    )
    
    logger.info("="*70)
    logger.info("🚀 AI 질병 진단 서버 시작 (Blueprints Refactored)")
    logger.info(f"환경: {config_name or 'default'}")
    logger.info(f"디버그 모드: {config.DEBUG}")
    logger.info(f"모델 경로: {config.MODEL_PATH}")
    logger.info("="*70)
    
    # ===== CORS 설정 =====
    CORS(app, origins=config.CORS_ORIGINS, methods=config.CORS_METHODS)
    logger.info(f"✓ CORS 설정 완료")
    
    # ===== 종속성 서비스 초기화 (애플리케이션 컨텍스트에 저장) =====
    # 헬스체커
    app.health_checker = init_health_checker(app)
    
    # 이미지 검증기
    app.image_validator = init_image_validator(
        min_width=32, min_height=32, max_width=4096, max_height=4096, max_aspect_ratio=10.0
    )
    
    # 모델 서비스
    app.model_service = ModelService(
        model_path=config.MODEL_PATH,
        labels_path=config.LABELS_PATH,
        enable_cache=getattr(config, 'ENABLE_MODEL_CACHE', True),
        cache_size=getattr(config, 'MODEL_CACHE_SIZE', 128)
    )
    
    try:
        app.model_service.load_model()
        logger.info("✓ 모델 서비스 로드 완료")
    except ModelLoadError as e:
        logger.error(f"✗ 모델 로드 실패: {e.message}")
    
    # 이미지 프로세서
    app.image_processor = ImageProcessor(target_size=config.TARGET_IMAGE_SIZE)
    logger.info("✓ 이미지 프로세서 초기화")
    
    # ===== 블루프린트 등록 =====
    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(predict_bp)
    logger.info("✓ 블루프린트 등록 완료")
    
    # ===== 전역 에러 핸들러 =====
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return error_response("파일 크기가 너무 큽니다", status_code=413, error_type="FileTooLargeError")
    
    @app.errorhandler(404)
    def not_found(error):
        return error_response("요청한 경로를 찾을 수 없습니다", status_code=404, error_type="NotFoundError")
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return error_response("서버 내부 오류가 발생했습니다", status_code=500, error_type="InternalServerError")
    
    # ===== HTTP 캐싱 및 보안 헤더 =====
    @app.after_request
    def add_cache_and_security_headers(response):
        if request.path.startswith('/static/') or \
           request.path.endswith(('.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico')):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif request.path in ['/', '/health', '/health/ready', '/health/live']:
            response.headers['Cache-Control'] = 'public, max-age=60'
        else:
            response.headers['Cache-Control'] = 'no-store'
        
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    return app


# 애플리케이션 인스턴스 생성
app = create_app()


if __name__ == "__main__":
    logger = get_logger('aiclassifier')
    logger.info("🔧 개발 서버 시작 중...")
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))
