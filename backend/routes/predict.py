"""
예측 라우트 - Phase E (품질 검증 및 안전장치)

Phase E 변경사항:
  E-4: metadata 에 gradcam_time_ms 성능 필드 노출
  E-3: 응답 metadata 에 xai_disclaimer 법적 고지 문구 포함
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

# E-3: API 응답에 포함할 법적 고지 문구 (영/한 이중 언어)
XAI_DISCLAIMER = (
    "이 히트맵은 AI 모델의 내부 연산을 시각화한 것으로, "
    "의학적 진단을 대체하지 않습니다. "
    "최종 진단은 반드시 의료 면허를 보유한 전문의가 내려야 합니다. "
    "(For research/educational use only. Not FDA/CE approved.)"
)


@predict_bp.route("/predict", methods=['POST'])
def predict():
    """
    이미지 질병 예측 엔드포인트 (Phase E - 품질 검증 및 안전장치)
    """
    start_time = time.time()

    model_service   = current_app.model_service
    image_processor = current_app.image_processor
    image_validator = current_app.image_validator
    config          = current_app.config
    request_logger  = get_logger('aiclassifier.api')

    request_logger.info("📥 예측 요청 수신")

    try:
        # ── 1. 모델 준비 상태 확인 ────────────────────────────────────
        if not model_service.is_ready():
            raise ModelNotLoadedError()

        # ── 2. 파일 존재 확인 ─────────────────────────────────────────
        if 'file' not in request.files:
            raise FileValidationError("요청에 파일이 없습니다")

        file = request.files['file']

        # ── 3. 기본 파일 검증 ─────────────────────────────────────────
        is_valid, error_msg = validate_file(
            file,
            allowed_extensions=config['ALLOWED_EXTENSIONS'],
            max_size=config['MAX_CONTENT_LENGTH']
        )
        if not is_valid:
            raise FileValidationError(error_msg)

        request_logger.info(f"📄 파일 수신: {file.filename}")

        # ── 4. 파일 읽기 ──────────────────────────────────────────────
        in_memory_file = io.BytesIO()
        file.save(in_memory_file)
        in_memory_file.seek(0)
        image_bytes = in_memory_file.read()

        # ── 5. 고급 이미지 검증 ───────────────────────────────────────
        if image_validator:
            image_validator.comprehensive_validation(image_bytes)
            request_logger.debug("✓ 고급 이미지 검증 통과")

        # ── 6. 이미지 전처리 (ONNX용) ────────────────────────────────
        processed_image = image_processor.preprocess(image_bytes)

        # ── 7. ONNX 예측 수행 ─────────────────────────────────────────
        predictions, from_cache = model_service.predict(processed_image)

        # ── 8. Grad-CAM 생성 ──────────────────────────────────────────
        gradcam_result = {"available": False, "error": "Grad-CAM 서비스 미초기화",
                          "gradcam_time_ms": 0.0, "low_confidence": False}
        pytorch_predictor = getattr(current_app, 'pytorch_predictor', None)
        if pytorch_predictor is not None:
            gradcam_result = pytorch_predictor.predict_with_gradcam(
                image_bytes=image_bytes,
                existing_predictions=predictions,
            )

        # ── 9. 처리 시간 계산 ─────────────────────────────────────────
        total_time_ms    = (time.time() - start_time) * 1000
        gradcam_time_ms  = gradcam_result.get("gradcam_time_ms", 0.0)  # E-4
        onnx_time_ms     = round(total_time_ms - gradcam_time_ms, 2)

        top_result  = predictions[0]
        cache_label = "캐시 히트" if from_cache else "추론"
        request_logger.info(
            f"✅ 예측 완료 [{cache_label}] - {file.filename}: "
            f"{top_result['className']} ({top_result['probability']:.4f}) "
            f"[전체={total_time_ms:.0f}ms | ONNX={onnx_time_ms:.0f}ms | "
            f"GradCAM={gradcam_time_ms:.0f}ms] "
            f"gradcam={gradcam_result.get('available', False)} "
            f"low_conf={gradcam_result.get('low_confidence', False)}"
        )

        # ── 10. 응답 반환 ─────────────────────────────────────────────
        response_data = {
            'success'    : True,
            'predictions': predictions,
            'metadata'   : {
                'processing_time_ms' : round(total_time_ms, 2),
                'onnx_time_ms'       : onnx_time_ms,          # E-4
                'gradcam_time_ms'    : gradcam_time_ms,       # E-4
                'image_size'         : list(config['TARGET_IMAGE_SIZE']),
                'filename'           : file.filename,
                'model_version'      : '1.0.0-phase-e',
                'cache_enabled'      : model_service.enable_cache,
                'from_cache'         : from_cache,
                'xai_disclaimer'     : XAI_DISCLAIMER,        # E-3
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
