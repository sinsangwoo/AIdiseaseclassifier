"""
AI 질병 진단 Flask 애플리케이션 (Production-Ready)

ONNX 모델을 사용하여 의료 이미지를 분석하고 질병을 예측합니다.
Phase 3 Rework: 백엔드 구조 개선, 모델 서비스 레이어 분리, 캐싱 도입
"""

import io
from flask import Flask, request
from flask_cors import CORS

from config import get_config
from services import ImageProcessor, ModelService
from utils import (
    # 검증
    validate_file,
    # 응답
    error_response,
    prediction_response,
    # 예외
    ModelNotLoadedError,
    ModelLoadError,
    InvalidImageError,
    ImageProcessingError,
    PredictionError,
    FileValidationError,
    # 로깅
    setup_logger,
    get_logger,
    log_exception,
    # 헬스체크
    init_health_checker,
    get_health_checker,
    # 고급 검증
    init_image_validator,
    get_image_validator
)


def create_app(config_name=None):
    """
    Flask 애플리케이션 팩토리 함수 (Production-Ready, Phase 3)
    
    Args:
        config_name (str): 환경 설정 이름 ('development', 'production', 'testing')
    
    Returns:
        Flask: 설정된 Flask 애플리케이션
    """
    app = Flask(__name__)
    
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
    logger.info("🚀 AI 질병 진단 서버 시작 (Rework Phase 3)")
    logger.info(f"환경: {config_name or 'default'}")
    logger.info(f"디버그 모드: {config.DEBUG}")
    logger.info(f"모델 경로: {config.MODEL_PATH}")
    logger.info("="*70)
    
    # ===== CORS 설정 (상세) =====
    cors_config = {
        'origins': config.CORS_ORIGINS,
        'methods': config.CORS_METHODS,
        'allow_headers': config.CORS_ALLOW_HEADERS,
        'expose_headers': getattr(config, 'CORS_EXPOSE_HEADERS', []),
        'max_age': getattr(config, 'CORS_MAX_AGE', 3600),
        'supports_credentials': getattr(config, 'CORS_SUPPORTS_CREDENTIALS', False)
    }
    
    CORS(app, **cors_config)
    logger.info(f"✓ CORS 설정 완료")
    logger.info(f"  - 허용된 Origins: {config.CORS_ORIGINS}")
    logger.info(f"  - 허용된 Methods: {config.CORS_METHODS}")
    
    # ===== 헬스체커 초기화 =====
    health_checker = init_health_checker(app)
    
    # ===== 이미지 검증기 초기화 =====
    image_validator = init_image_validator(
        min_width=32,
        min_height=32,
        max_width=4096,
        max_height=4096,
        max_aspect_ratio=10.0
    )
    logger.info("✓ 이미지 검증기 초기화")
    
    # ===== 모델 서비스 초기화 (Phase 3 - 새로운 서비스 레이어) =====
    model_service = ModelService(
        model_path=config.MODEL_PATH,
        labels_path=config.LABELS_PATH,
        enable_cache=getattr(config, 'ENABLE_MODEL_CACHE', True),
        cache_size=getattr(config, 'MODEL_CACHE_SIZE', 128)
    )
    
    try:
        model_service.load_model()
        logger.info("✓ 모델 서비스 로드 완료")
    except ModelLoadError as e:
        logger.error(f"✗ 모델 로드 실패: {e.message}")
        logger.warning("⚠  서버는 시작되지만 예측 기능이 작동하지 않습니다")
    
    # ===== 이미지 프로세서 초기화 =====
    image_processor = ImageProcessor(target_size=config.TARGET_IMAGE_SIZE)
    logger.info("✓ 이미지 프로세서 초기화")
    
    # ===== 라우트 정의 =====
    
    @app.route("/")
    def index():
        """메인 엔드포인트"""
        return {
            "service": "AI Disease Classifier API",
            "version": "7.0.0-phase3",
            "status": "running",
            "environment": config_name or "default",
            "features": {
                "model_caching": model_service.enable_cache,
                "cache_size": model_service.cache_size,
                "warmup": model_service.stats['warmup_completed']
            },
            "endpoints": {
                "health": "/health",
                "health_detailed": "/health/detailed",
                "health_ready": "/health/ready",
                "health_live": "/health/live",
                "model_info": "/model/info",
                "model_stats": "/model/stats",
                "model_cache": "/model/cache",
                "predict": "/predict"
            }
        }
    
    @app.route("/health")
    def health_check():
        """간단한 헬스체크"""
        model_status = "ready" if model_service.is_ready() else "not_loaded"
        
        return {
            "status": "healthy" if model_service.is_ready() else "degraded",
            "model": model_status,
            "timestamp": health_checker.get_uptime()['start_time'],
            "version": "7.0.0-phase3"
        }
    
    @app.route("/health/detailed")
    def detailed_health_check():
        """상세 헬스체크 (모니터링용)"""
        return health_checker.comprehensive_health_check(
            predictor=model_service._predictor if model_service._predictor else None,
            cache=None,
            metrics=model_service.get_statistics()
        )
    
    @app.route("/health/ready")
    def readiness_check():
        """Readiness probe (Render/K8s용)"""
        import psutil
        
        checks = {
            'model': model_service.is_ready(),
            'disk': psutil.disk_usage('/').percent < 90,
            'memory': psutil.virtual_memory().percent < 90
        }
        
        is_ready = all(checks.values())
        
        return {
            'status': 'ready' if is_ready else 'not_ready',
            'checks': checks
        }, 200 if is_ready else 503
    
    @app.route("/health/live")
    def liveness_check():
        """Liveness probe (Render/K8s용)"""
        return {
            'status': 'alive',
            'uptime_seconds': health_checker.get_uptime()['uptime_seconds']
        }, 200
    
    @app.route("/model/info")
    def model_info():
        """모델 정보 조회"""
        return model_service.get_model_info()
    
    @app.route("/model/stats")
    def model_stats():
        """
        모델 서비스 통계 조회 (Phase 3 신규 엔드포인트)
        
        캐시 히트율, 평균 추론 시간 등의 통계 제공
        """
        return {
            "success": True,
            "statistics": model_service.get_statistics(),
            "cache_info": model_service.get_cache_info() if model_service.enable_cache else None
        }
    
    @app.route("/model/cache", methods=['GET', 'DELETE'])
    def model_cache():
        """
        모델 캐시 관리 (Phase 3 신규 엔드포인트)
        
        GET: 캐시 정보 조회
        DELETE: 캐시 초기화
        """
        if request.method == 'GET':
            if not model_service.enable_cache:
                return {
                    "success": False,
                    "message": "캐싱이 비활성화되어 있습니다"
                }, 400
            
            return {
                "success": True,
                "cache_info": model_service.get_cache_info(),
                "statistics": {
                    "cache_hits": model_service.stats['cache_hits'],
                    "cache_misses": model_service.stats['cache_misses']
                }
            }
        
        elif request.method == 'DELETE':
            if not model_service.enable_cache:
                return {
                    "success": False,
                    "message": "캐싱이 비활성화되어 있습니다"
                }, 400
            
            model_service.clear_cache()
            
            return {
                "success": True,
                "message": "캐시가 초기화되었습니다"
            }
    
    @app.route("/predict", methods=['POST'])
    def predict():
        """
        이미지 질병 예측 엔드포인트 (Production-Grade, Phase 3)
        
        Phase 3 개선사항:
        - ModelService를 통한 캐싱 지원
        - 상세한 성능 메트릭 제공
        """
        import time
        start_time = time.time()
        
        request_logger = get_logger('aiclassifier.api')
        request_logger.info("📥 예측 요청 수신")
        
        try:
            # 1. 모델 준비 상태 확인
            if not model_service.is_ready():
                raise ModelNotLoadedError()
            
            # 2. 파일 존재 확인
            if 'file' not in request.files:
                raise FileValidationError("요청에 파일이 없습니다")
            
            file = request.files['file']
            
            # 3. 기본 파일 검증
            is_valid, error_msg = validate_file(
                file,
                allowed_extensions=app.config['ALLOWED_EXTENSIONS'],
                max_size=app.config['MAX_CONTENT_LENGTH']
            )
            
            if not is_valid:
                raise FileValidationError(error_msg)
            
            request_logger.info(f"📄 파일 수신: {file.filename}")
            
            # 4. 파일 읽기
            in_memory_file = io.BytesIO()
            file.save(in_memory_file)
            in_memory_file.seek(0)
            image_bytes = in_memory_file.read()
            
            # 5. 고급 이미지 검증
            if image_validator:
                image_validator.comprehensive_validation(image_bytes)
                request_logger.debug("✓ 고급 이미지 검증 통과")
            
            # 6. 이미지 전처리
            in_memory_file.seek(0)
            processed_image = image_processor.preprocess(image_bytes)
            
            # 7. 예측 수행 (캐싱 지원)
            predictions = model_service.predict(processed_image)
            
            # 8. 처리 시간 계산
            processing_time_ms = (time.time() - start_time) * 1000
            
            top_result = predictions[0]
            request_logger.info(
                f"✅ 예측 완료 - {file.filename}: "
                f"{top_result['className']} ({top_result['probability']:.4f}) "
                f"[{processing_time_ms:.0f}ms]"
            )
            
            # 9. 응답 반환 (메타데이터 포함)
            response = {
                'success': True,
                'predictions': predictions,
                'metadata': {
                    'processing_time_ms': round(processing_time_ms, 2),
                    'image_size': list(config.TARGET_IMAGE_SIZE),
                    'filename': file.filename,
                    'model_version': '1.0.0-phase3',
                    'cache_enabled': model_service.enable_cache,
                    'from_cache': model_service.stats['cache_hits'] > 0
                }
            }
            
            return response, 200
        
        # ===== 커스텀 예외 처리 =====
        
        except ModelNotLoadedError as e:
            log_exception(request_logger, e, "모델 미준비")
            return error_response(
                e.message,
                status_code=503,
                error_type=e.error_code
            )
        
        except FileValidationError as e:
            request_logger.warning(f"파일 검증 실패: {e.message}")
            return error_response(
                e.message,
                status_code=400,
                error_type=e.error_code
            )
        
        except InvalidImageError as e:
            request_logger.warning(f"유효하지 않은 이미지: {e.message}")
            return error_response(
                e.message,
                status_code=400,
                error_type=e.error_code
            )
        
        except ImageProcessingError as e:
            log_exception(request_logger, e, "이미지 처리 오류")
            return error_response(
                e.message,
                status_code=422,
                error_type=e.error_code,
                details={
                    "original_error": str(e.original_error)
                } if hasattr(e, 'original_error') and e.original_error else None
            )
        
        except PredictionError as e:
            log_exception(request_logger, e, "예측 오류")
            return error_response(
                "예측 중 오류가 발생했습니다",
                status_code=500,
                error_type=e.error_code,
                details={
                    "original_error": str(e.original_error)
                } if hasattr(e, 'original_error') and e.original_error else None
            )
        
        # ===== 일반 예외 처리 =====
        
        except Exception as e:
            log_exception(request_logger, e, "예상치 못한 오류")
            return error_response(
                "서버 내부 오류가 발생했습니다",
                status_code=500,
                error_type="InternalServerError"
            )
    
    # ===== 전역 에러 핸들러 =====
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        """파일 크기 초과 에러"""
        max_mb = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
        logger.warning(f"파일 크기 초과: {max_mb}MB 제한")
        return error_response(
            f"파일 크기가 너무 큽니다. 최대 {max_mb:.0f}MB까지 허용됩니다",
            status_code=413,
            error_type="FileTooLargeError"
        )
    
    @app.errorhandler(404)
    def not_found(error):
        """404 에러"""
        logger.warning(f"404: {request.path}")
        return error_response(
            "요청한 경로를 찾을 수 없습니다",
            status_code=404,
            error_type="NotFoundError"
        )
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """405 에러"""
        logger.warning(f"405: {request.method} {request.path}")
        return error_response(
            f"허용되지 않는 메소드입니다. {request.method}는 이 엔드포인트에서 지원되지 않습니다",
            status_code=405,
            error_type="MethodNotAllowedError"
        )
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """500 에러"""
        logger.exception("서버 내부 오류")
        return error_response(
            "서버 내부 오류가 발생했습니다",
            status_code=500,
            error_type="InternalServerError"
        )
    
    # ===== 보안 헤더 추가 =====
    @app.after_request
    def add_security_headers(response):
        """보안 헤더 추가"""
        if getattr(config, 'SECURITY_HEADERS', False):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # HTTPS에서만 Strict-Transport-Security
            if request.is_secure:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    logger.info("✓ 라우트 및 에러 핸들러 등록 완료")
    logger.info("="*70)
    logger.info("🎉 서버 준비 완료! Rework Phase 3 적용됨")
    logger.info(f"   - 모델 캐싱: {'활성화' if model_service.enable_cache else '비활성화'}")
    logger.info(f"   - 캐시 크기: {model_service.cache_size}")
    logger.info("="*70)
    
    return app


# 애플리케이션 인스턴스 생성
app = create_app()


if __name__ == "__main__":
    # 개발 서버 실행
    logger = get_logger('aiclassifier')
    logger.info("🔧 개발 서버 시작 중...")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )
