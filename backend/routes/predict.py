"""
예측 라우트 - Grad-CAM 통합 버전 (Phase A)

기존 ONNX 기반 예측은 그대로 유지하면서,
PyTorchPredictor가 준비된 경우 Grad-CAM 히트맵을 추가로 생성합니다.

응답 구조 변경:
  기존: { success, predictions, metadata }
  변경: { success, predictions, metadata, gradcam: { available, ... } }
"""

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
    이미지 질병 예측 엔드포인트 (Grad-CAM 통합, Phase A)
    """
    start_time = time.time()

    model_service    = current_app.model_service
    image_processor  = current_app.image_processor
    image_validator  = current_app.image_validator
    config           = current_app.config
    request_logger   = get_logger('aiclassifier.api')

    request_logger.info("📥 예측 요청 수신")

    try:
        # ── 1. 모델 준비 상태 확인 ─────────────────────────────────────
        if not model_service.is_ready():
            raise ModelNotLoadedError()

        # ── 2. 파일 존재 확인 ──────────────────────────────────────────
        if 'file' not in request.files:
            raise FileValidationError("요청에 파일이 없습니다")

        file = request.files['file']

        # ── 3. 기본 파일 검증 ──────────────────────────────────────────
        is_valid, error_msg = validate_file(
            file,
            allowed_extensions=config['ALLOWED_EXTENSIONS'],
            max_size=config['MAX_CONTENT_LENGTH']
        )
        if not is_valid:
            raise FileValidationError(error_msg)

        request_logger.info(f"📄 파일 수신: {file.filename}")

        # ── 4. 파일 읽기 (bytes 보존 - Grad-CAM 오버레이에 필요) ────────
        in_memory_file = io.BytesIO()
        file.save(in_memory_file)
        in_memory_file.seek(0)
        image_bytes = in_memory_file.read()

        # ── 5. 고급 이미지 검증 ────────────────────────────────────────
        if image_validator:
            image_validator.comprehensive_validation(image_bytes)
            request_logger.debug("✓ 고급 이미지 검증 통과")

        # ── 6. 이미지 전처리 (ONNX용) ────────────────────────────────
        processed_image = image_processor.preprocess(image_bytes)

        # ── 7. ONNX 예측 수행 (기존 로직 그대로 유지) ─────────────────
        predictions, from_cache = model_service.predict(processed_image)

        # ── 8. Grad-CAM 생성 (실패해도 예측 결과는 정상 반환) ──────────
        gradcam_result = {"available": False, "error": "Grad-CAM 서비스 미초기화"}
        pytorch_predictor = getattr(current_app, 'pytorch_predictor', None)
        if pytorch_predictor is not None:
            gradcam_result = pytorch_predictor.predict_with_gradcam(
                image_bytes=image_bytes,
                existing_predictions=predictions,
            )

        # ── 9. 처리 시간 계산 ─────────────────────────────────────────
        processing_time_ms = (time.time() - start_time) * 1000

        top_result  = predictions[0]
        cache_label = "캐시 히트" if from_cache else "추론"
        request_logger.info(
            f"✅ 예측 완료 [{cache_label}] - {file.filename}: "
            f"{top_result['className']} ({top_result['probability']:.4f}) "
            f"[{processing_time_ms:.0f}ms] "
            f"gradcam={gradcam_result.get('available', False)}"
        )

        # ── 10. 응답 반환 ─────────────────────────────────────────────
        response_data = {
            'success'    : True,
            'predictions': predictions,
            'metadata'   : {
                'processing_time_ms': round(processing_time_ms, 2),
                'image_size'        : list(config['TARGET_IMAGE_SIZE']),
                'filename'          : file.filename,
                'model_version'     : '1.0.0-phase-a-gradcam',
                'cache_enabled'     : model_service.enable_cache,
                'from_cache'        : from_cache,
            },
            'gradcam': gradcam_result,
        }

        return response_data, 200

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
            e.message, status_code=422, error_type=e.error_code,
            details={"original_error": str(e.original_error)} if getattr(e, 'original_error', None) else None
        )

    except PredictionError as e:
        log_exception(request_logger, e, "예측 오류")
        return error_response(
            "예측 중 오류가 발생했습니다", status_code=500, error_type=e.error_code,
            details={"original_error": str(e.original_error)} if getattr(e, 'original_error', None) else None
        )

    except Exception as e:
        log_exception(request_logger, e, "예상치 못한 오류")
        return error_response("서버 내부 오류가 발생했습니다", status_code=500, error_type="InternalServerError")
