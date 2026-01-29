"""
AI 질병 진단 Flask 애플리케이션

ONNX 모델을 사용하여 의료 이미지를 분석하고 질병을 예측합니다.
"""

from flask import Flask, request
from flask_cors import CORS

from config import get_config
from models import ModelPredictor
from services import ImageProcessor
from utils import (
    validate_file,
    error_response,
    prediction_response,
    setup_logger,
    get_logger,
    # Exceptions
    ModelNotLoadedError,
    ModelLoadError,
    InvalidImageError,
    ImageProcessingError,
    PredictionError,
    FileValidationError,
    log_exception
)


def create_app(config_name=None):
    """
    Flask 애플리케이션 팩토리 함수
    
    Args:
        config_name (str): 환경 설정 이름 ('development', 'production', 'testing')
    
    Returns:
        Flask: 설정된 Flask 애플리케이션
    """
    app = Flask(__name__)
    
    # 설정 로드
    config = get_config(config_name)
    app.config.from_object(config)
    
    # 로깅 설정
    logger = setup_logger(
        name='aiclassifier',
        log_level=config.LOG_LEVEL,
        log_dir=config.LOG_DIR if hasattr(config, 'LOG_DIR') else None
    )
    
    logger.info("="*60)
    logger.info("AI 질병 진단 서버 시작")
    logger.info(f"환경: {config_name or 'default'}")
    logger.info(f"디버그 모드: {config.DEBUG}")
    logger.info("="*60)
    
    # CORS 설정
    CORS(app, origins=config.CORS_ORIGINS)
    logger.info(f"CORS 설정 완료: {config.CORS_ORIGINS}")
    
    # 모델 초기화
    predictor = ModelPredictor(
        model_path=config.MODEL_PATH,
        labels_path=config.LABELS_PATH
    )
    
    try:
        predictor.load_model()
        logger.info("✓ 모델 로드 완료")
    except ModelLoadError as e:
        logger.error(f"✗ 모델 로드 실패: {e.message}")
        logger.warning("서버는 시작되지만 예측 기능이 작동하지 않습니다")
    
    # 이미지 프로세서 초기화
    image_processor = ImageProcessor(target_size=config.TARGET_IMAGE_SIZE)
    logger.info("✓ 이미지 프로세서 초기화 완료")
    
    # === 라우트 정의 ===
    
    @app.route("/")
    def health_check():
        """서버 상태 확인 엔드포인트"""
        model_status = "ready" if predictor.is_ready() else "not_loaded"
        return {
            "status": "running",
            "message": "AI 질병 진단 서버가 작동 중입니다",
            "model_status": model_status
        }
    
    @app.route("/model/info")
    def model_info():
        """모델 정보 조회 엔드포인트"""
        return predictor.get_model_info()
    
    @app.route("/predict", methods=['POST'])
    def predict():
        """
        이미지 질병 예측 엔드포인트
        
        Request:
            - Method: POST
            - Content-Type: multipart/form-data
            - Body: file (이미지 파일)
        
        Response:
            {
                "success": true,
                "predictions": [
                    {"className": "질병명", "probability": 0.85},
                    ...
                ]
            }
        """
        request_logger = get_logger('aiclassifier.api')
        request_logger.info("예측 요청 수신")
        
        try:
            # 1. 모델 준비 상태 확인
            if not predictor.is_ready():
                raise ModelNotLoadedError()
            
            # 2. 파일 존재 확인
            if 'file' not in request.files:
                raise FileValidationError("요청에 파일이 없습니다")
            
            file = request.files['file']
            
            # 3. 파일 검증
            is_valid, error_msg = validate_file(
                file,
                allowed_extensions=app.config['ALLOWED_EXTENSIONS'],
                max_size=app.config['MAX_CONTENT_LENGTH']
            )
            
            if not is_valid:
                raise FileValidationError(error_msg)
            
            request_logger.info(f"파일 수신 및 검증 완료: {file.filename}")
            
            # 4. 이미지 전처리
            processed_image = image_processor.preprocess_from_file(file)
            
            # 5. 예측 수행
            predictions = predictor.predict(processed_image)
            
            top_result = predictions[0]
            request_logger.info(
                f"예측 성공 - {file.filename}: "
                f"{top_result['className']} ({top_result['probability']:.4f})"
            )
            
            # 6. 응답 반환
            return prediction_response(predictions)
        
        # === 커스텀 예외 처리 ===
        
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
                details={"original_error": str(e.original_error)} if e.original_error else None
            )
        
        except PredictionError as e:
            log_exception(request_logger, e, "예측 오류")
            return error_response(
                "예측 중 오류가 발생했습니다",
                status_code=500,
                error_type=e.error_code,
                details={"original_error": str(e.original_error)} if e.original_error else None
            )
        
        # === 일반 예외 처리 ===
        
        except Exception as e:
            log_exception(request_logger, e, "예상치 못한 오류")
            return error_response(
                "서버 내부 오류가 발생했습니다",
                status_code=500,
                error_type="InternalServerError"
            )
    
    # === 에러 핸들러 ===
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        """파일 크기 초과 에러 핸들러"""
        max_mb = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
        logger.warning(f"파일 크기 초과: {max_mb}MB 제한")
        return error_response(
            f"파일 크기가 너무 큽니다. 최대 {max_mb:.0f}MB까지 허용됩니다",
            status_code=413,
            error_type="FileTooLargeError"
        )
    
    @app.errorhandler(404)
    def not_found(error):
        """404 에러 핸들러"""
        logger.warning(f"404 에러: {request.path}")
        return error_response(
            "요청한 경로를 찾을 수 없습니다",
            status_code=404,
            error_type="NotFoundError"
        )
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """500 에러 핸들러"""
        logger.exception("서버 내부 오류")
        return error_response(
            "서버 내부 오류가 발생했습니다",
            status_code=500,
            error_type="InternalServerError"
        )
    
    logger.info("라우트 및 에러 핸들러 등록 완료")
    logger.info("서버 준비 완료")
    
    return app


# 애플리케이션 인스턴스 생성
app = create_app()


if __name__ == "__main__":
    # 개발 서버 실행
    logger = get_logger('aiclassifier')
    logger.info("개발 서버 시작 중...")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )
