"""
AI 질병 진단 Flask 애플리케이션 (Production-Ready)

ONNX 모델을 사용하여 의료 이미지를 분석하고 질병을 예측합니다.
Phase A: Grad-CAM PyTorchPredictor 병렬 초기화 추가
"""

import os
from flask import Flask, request
from flask_cors import CORS

from backend.config import get_config
from backend.services import ImageProcessor, ModelService, PyTorchPredictor
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

    logger.info("=" * 70)
    logger.info("🚀 AI 질병 진단 서버 시작 (Phase A - Grad-CAM 통합)")
    logger.info(f"환경: {config_name or 'default'}")
    logger.info(f"디버그 모드: {config.DEBUG}")
    logger.info(f"모델 경로: {config.MODEL_PATH}")
    logger.info("=" * 70)

    # ===== CORS 설정 =====
    #
    # ★ origins="*" (와일드카드) 를 명시적으로 사용합니다.
    #
    # 이유: Render 무료 플랜에서 슬립 해제 중 502/503 응답이 올 때
    #   flask-cors 가 헤더를 붙이기 전에 Render 게이트웨이가 먼저 응답합니다.
    #   이 경우 Access-Control-Allow-Origin 헤더가 누락되어 브라우저에서
    #   CORS 에러로 보입니다. (실제 원인은 서버 슬립이지만 브라우저는 CORS 에러 표시)
    #
    #   after_request 훅으로 모든 응답에 CORS 헤더를 추가하는 방어 로직도
    #   함께 유지합니다.
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        methods=['GET', 'POST', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
        expose_headers=['Content-Type', 'X-Request-ID'],
        max_age=3600,
        supports_credentials=False,
        send_wildcard=True
    )
    logger.info("✓ CORS 설정 완료 (origins=*, send_wildcard=True)")

    # ===== 종속성 서비스 초기화 =====
    app.health_checker = init_health_checker(app)
    app.image_validator = init_image_validator(
        min_width=32, min_height=32, max_width=4096, max_height=4096, max_aspect_ratio=10.0
    )

    app.model_service = ModelService(
        model_path=config.MODEL_PATH,
        labels_path=config.LABELS_PATH,
        enable_cache=getattr(config, 'ENABLE_MODEL_CACHE', True),
        cache_size=getattr(config, 'MODEL_CACHE_SIZE', 128)
    )
    try:
        app.model_service.load_model()
        logger.info("✓ ONNX 모델 서비스 로드 완료")
    except ModelLoadError as e:
        logger.error(f"✗ 모델 로드 실패: {e.message}")

    app.image_processor = ImageProcessor(target_size=config.TARGET_IMAGE_SIZE)
    logger.info("✓ 이미지 프로세서 초기화")

    pytorch_weights = os.environ.get(
        'PYTORCH_WEIGHTS_PATH',
        os.path.join(os.path.dirname(__file__), '..', 'backend', 'models', 'model_weights.pth')
    )
    app.pytorch_predictor = PyTorchPredictor(
        weights_path=pytorch_weights if os.path.exists(pytorch_weights) else None,
        labels_path=config.LABELS_PATH,
        num_classes=2,
    )
    if app.pytorch_predictor.is_ready:
        logger.info("✓ PyTorch Grad-CAM 예측기 초기화 완료")
    else:
        logger.warning(
            "⚠ PyTorch Grad-CAM 비활성화 (torch 미설치 또는 가중치 없음) "
            "→ 예측 결과는 ONNX로 정상 제공됩니다"
        )

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

    @app.errorhandler(405)
    def method_not_allowed(error):
        return error_response("허용되지 않은 메서드입니다", status_code=405, error_type="MethodNotAllowedError")

    @app.errorhandler(500)
    def internal_server_error(error):
        return error_response("서버 내부 오류가 발생했습니다", status_code=500, error_type="InternalServerError")

    # ===== 모든 응답에 CORS 헤더 강제 삽입 (방어 로직) =====
    #
    # flask-cors 가 헤더를 붙이지 못하는 엣지 케이스(에러 응답, 모델 로드 실패 등)
    # 에도 CORS 헤더가 항상 포함되도록 after_request 에서 한 번 더 보장합니다.
    @app.after_request
    def ensure_cors_and_cache_headers(response):
        # CORS 헤더 강제 보장
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Max-Age'] = '3600'

        # 캐시 헤더
        if request.path.startswith('/static/') or \
                request.path.endswith(('.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico')):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif request.path in ['/', '/health', '/health/ready', '/health/live']:
            response.headers['Cache-Control'] = 'public, max-age=60'
        else:
            response.headers['Cache-Control'] = 'no-store'

        # 보안 헤더
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
