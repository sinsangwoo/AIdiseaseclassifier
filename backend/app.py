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

    logger.info("=" * 70)
    logger.info("🚀 AI 질병 진단 서버 시작 (Phase A - Grad-CAM 통합)")
    logger.info(f"환경: {config_name or 'default'}")
    logger.info(f"디버그 모드: {config.DEBUG}")
    logger.info(f"모델 경로: {config.MODEL_PATH}")
    logger.info("=" * 70)

    # ===== CORS 설정 =====
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        methods=['GET', 'POST', 'OPTIONS'],
        allow_headers=getattr(config, 'CORS_ALLOW_HEADERS', None),
        expose_headers=getattr(config, 'CORS_EXPOSE_HEADERS', None),
        max_age=getattr(config, 'CORS_MAX_AGE', None),
        supports_credentials=getattr(config, 'CORS_SUPPORTS_CREDENTIALS', False),
        send_wildcard=True
    )
    logger.info("✓ CORS 설정 완료")

    # ===== 종속성 서비스 초기화 =====
    app.health_checker = init_health_checker(app)
    app.image_validator = init_image_validator(
        min_width=32, min_height=32, max_width=4096, max_height=4096, max_aspect_ratio=10.0
    )

    # ONNX 모델 서비스 (기존 유지)
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

    # 이미지 프로세서
    app.image_processor = ImageProcessor(target_size=config.TARGET_IMAGE_SIZE)
    logger.info("✓ 이미지 프로세서 초기화")

    # ── PyTorch Grad-CAM 예측기 초기화 (Phase A) ─────────────────────────
    # 가중치 파일 경로: 환경변수 PYTORCH_WEIGHTS_PATH 로 지정 가능
    # 파일이 없으면 랜덤 초기화 모델로 동작 (히트맵 품질은 낮지만 구조 검증용)
    pytorch_weights = os.environ.get(
        'PYTORCH_WEIGHTS_PATH',
        os.path.join(os.path.dirname(__file__), '..', 'backend', 'models', 'model_weights.pth')
    )
    app.pytorch_predictor = PyTorchPredictor(
        weights_path=pytorch_weights if os.path.exists(pytorch_weights) else None,
        labels_path=config.LABELS_PATH,
        num_classes=2,  # labels.txt: 0 정상 / 1 폐렴
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

    @app.route("/", methods=["OPTIONS"])
    @app.route("/<path:path>", methods=["OPTIONS"])
    def options_preflight(path=None):
        return "", 200

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

        if 'Access-Control-Allow-Origin' not in response.headers:
            response.headers['Access-Control-Allow-Origin'] = '*'
        if 'Access-Control-Allow-Methods' not in response.headers:
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        if 'Access-Control-Allow-Headers' not in response.headers:
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        if 'Access-Control-Max-Age' not in response.headers:
            response.headers['Access-Control-Max-Age'] = str(getattr(config, 'CORS_MAX_AGE', 3600))

        return response

    return app


# 애플리케이션 인스턴스 생성
app = create_app()

if __name__ == "__main__":
    logger = get_logger('aiclassifier')
    logger.info("🔧 개발 서버 시작 중...")
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))
