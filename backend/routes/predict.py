import io
import time
from flask import Blueprint, current_app, request
from backend.utils import (
    validate_file,
    error_response,
    ModelNotLoadedError,
    FileValidationError,
    InvalidImageError,
    ImageProcessingError,
    PredictionError,
    get_logger,
    log_exception
)

predict_bp = Blueprint('predict', __name__)

@predict_bp.route("/predict", methods=['POST'])
def predict():
    """
    이미지 질병 예측 엔드포인트 (Production-Grade, Phase 3-4)
    """
    start_time = time.time()
    
    model_service = current_app.model_service
    image_processor = current_app.image_processor
    image_validator = current_app.image_validator
    config = current_app.config
    
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
            allowed_extensions=config['ALLOWED_EXTENSIONS'],
            max_size=config['MAX_CONTENT_LENGTH']
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
        processed_image = image_processor.preprocess(image_bytes)
        
        # 7. 예측 수행 (캐싱 지원)
        predictions, from_cache = model_service.predict(processed_image)
        
        # 8. 처리 시간 계산
        processing_time_ms = (time.time() - start_time) * 1000
        
        top_result = predictions[0]
        cache_label = "캐시 히트" if from_cache else "추론"
        request_logger.info(
            f"✅ 예측 완료 [{cache_label}] - {file.filename}: "
            f"{top_result['className']} ({top_result['probability']:.4f}) "
            f"[{processing_time_ms:.0f}ms]"
        )
        
        # 9. 응답 반환 (메타데이터 포함)
        response = {
            'success': True,
            'predictions': predictions,
            'metadata': {
                'processing_time_ms': round(processing_time_ms, 2),
                'image_size': list(config['TARGET_IMAGE_SIZE']),
                'filename': file.filename,
                'model_version': '1.0.0-phase3-4',
                'cache_enabled': model_service.enable_cache,
                'from_cache': from_cache
            }
        }
        
        return response, 200
    
    except ModelNotLoadedError as e:
        log_exception(request_logger, e, "모델 미준비")
        return error_response(e.message, status_code=503, error_type=e.error_code)
    
    except FileValidationError as e:
        request_logger.warning(f"파일 검증 실패: {e.message}")
        return error_response(e.message, status_code=400, error_type=e.error_code)
    
    except InvalidImageError as e:
        request_logger.warning(f"유효하지 않은 이미지: {e.message}")
        return error_response(e.message, status_code=400, error_type=e.error_code)
    
    except ImageProcessingError as e:
        log_exception(request_logger, e, "이미지 처리 오류")
        return error_response(
            e.message,
            status_code=422,
            error_type=e.error_code,
            details={"original_error": str(e.original_error)} if hasattr(e, 'original_error') and e.original_error else None
        )
    
    except PredictionError as e:
        log_exception(request_logger, e, "예측 오류")
        return error_response(
            "예측 중 오류가 발생했습니다",
            status_code=500,
            error_type=e.error_code,
            details={"original_error": str(e.original_error)} if hasattr(e, 'original_error') and e.original_error else None
        )
    
    except Exception as e:
        log_exception(request_logger, e, "예상치 못한 오류")
        return error_response("서버 내부 오류가 발생했습니다", status_code=500, error_type="InternalServerError")
