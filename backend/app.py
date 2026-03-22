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

    # ===== 로깅 =====
    logger = setup_logger(
        name='aiclassifier',
        log_level=config.LOG_LEVEL,
        log_dir=config.LOG_DIR if hasattr(config, 'LOG_DIR') else None
    )

    # config_name 이 None 이면 get_config() 가 선택한 실제 환경명을 로그에 기록
    resolved_env = config_name or os.environ.get('FLASK_ENV') or (
        'production'
        if (os.environ.get('RENDER') or os.environ.get('RENDER_SERVICE_ID'))
        else 'default'
    )
    logger.info("=" * 70)
    logger.info("🚀 AI 질병 진단 서버 시작")
    logger.info(f"환경: {resolved_env}")
    logger.info(f"FLASK_ENV 환경변수: {os.environ.get('FLASK_ENV', '(미설정)')}")
    logger.info(f"디버그 모드: {config.DEBUG}")
    logger.info(f"CORS Origins: {getattr(config, 'CORS_ORIGINS', '*')}")
    logger.info("=" * 70)

    # ===== CORS 설정 =====
    #
    # 핵심 원칙: 어떤 환경에서도 GitHub Pages → API 요청이 차단되지 않아야 합니다.
    #
    # Render 무료 플랜의 CORS 문제 원인:
    #   슬립/재시작 중 Render 게이트웨이가 Flask를 우회하여 502를 반환할 때
    #   CORS 헤더가 없어 브라우저가 CORS 에러로 표시합니다.
    #   → after_request 에서 모든 응답에 강제로 헤더를 삽입해 방어합니다.
    #
    # flask-cors 설정: origins='*' 고정 (환경 무관)
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        methods=['GET', 'POST', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
        expose_headers=['Content-Type', 'X-Request-ID'],
        max_age=3600,
        supports_credentials=False,
        send_wildcard=True,
    )
    logger.info("✓ CORS 설정 완료 (origins=*, send_wildcard=True)")

    # ===== 종속성 서비스 초기화 =====
    app.health_checker = init_health_checker(app)
    app.image_validator = init_image_validator(
        min_width=32, min_height=32,
        max_width=4096, max_height=4096,
        max_aspect_ratio=10.0
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
        logger.warning("⚠ PyTorch Grad-CAM 비활성화 → ONNX로 정상 제공")

    # ===== 블루프린트 =====
    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(predict_bp)
    logger.info("✓ 블루프린트 등록 완료")

    # ===== 에러 핸들러 =====
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

    # ===== CORS 헤더 강제 삽입 (최후 방어선) =====
    #
    # flask-cors 가 처리한 응답에도, 에러 응답에도, 모든 케이스에 헤더를 보장합니다.
    # 헤더가 이미 있어도 덮어씁니다 (Render 프록시가 제거하는 케이스 방어).
    @app.after_request
    def force_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Max-Age'] = '3600'

        # 캐시 및 보안 헤더
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


# gunicorn 진입점: create_app() 을 함수로 호출하여
# --preload 옵션과 환경변수 주입 타이밍 문제를 회피합니다.
def get_app():
    return create_app()


# 하위 호환: 모듈 레벨 app 변수 (기존 `backend.app:app` 진입점 유지)
app = create_app()

if __name__ == "__main__":
    logger = get_logger('aiclassifier')
    logger.info("🔧 개발 서버 시작 중...")
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))
