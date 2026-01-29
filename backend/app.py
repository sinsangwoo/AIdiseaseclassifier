"""
AI 질병 진단 Flask 애플리케이션

ONNX 모델을 사용하여 의료 이미지를 분석하고 질병을 예측합니다.
"""

import logging
from flask import Flask, request
from flask_cors import CORS

from config import get_config
from models import ModelPredictor
from services import ImageProcessor
from utils import validate_file, error_response, prediction_response


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    
    # CORS 설정
    CORS(app, origins=config.CORS_ORIGINS)
    
    # 모델 초기화
    predictor = ModelPredictor(
        model_path=config.MODEL_PATH,
        labels_path=config.LABELS_PATH
    )
    
    try:
        predictor.load_model()
        logger.info("모델 로드 완료")
    except Exception as e:
        logger.error(f"모델 로드 실패: {e}")
        logger.warning("서버는 시작되지만 예측 기능이 작동하지 않을 수 있습니다")
    
    # 이미지 프로세서 초기화
    image_processor = ImageProcessor(target_size=config.TARGET_IMAGE_SIZE)
    
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
        logger.info("예측 요청 수신")
        
        # 1. 모델 준비 상태 확인
        if not predictor.is_ready():
            logger.error("모델이 준비되지 않음")
            return error_response(
                "서버에 모델이 아직 준비되지 않았습니다",
                status_code=500,
                error_type="ModelNotReadyError"
            )
        
        # 2. 파일 존재 확인
        if 'file' not in request.files:
            logger.warning("파일 누락")
            return error_response("요청에 파일이 없습니다")
        
        file = request.files['file']
        
        # 3. 파일 검증
        is_valid, error_msg = validate_file(
            file,
            allowed_extensions=app.config['ALLOWED_EXTENSIONS'],
            max_size=app.config['MAX_CONTENT_LENGTH']
        )
        
        if not is_valid:
            logger.warning(f"파일 검증 실패: {error_msg}")
            return error_response(error_msg)
        
        logger.info(f"파일 수신: {file.filename}")
        
        try:
            # 4. 이미지 전처리
            processed_image = image_processor.preprocess_from_file(file)
            
            # 5. 예측 수행
            predictions = predictor.predict(processed_image)
            
            logger.info(f"예측 성공: {predictions[0]['className']} ({predictions[0]['probability']:.4f})")
            
            # 6. 응답 반환
            return prediction_response(predictions)
        
        except ValueError as e:
            # 이미지 처리 오류
            logger.error(f"이미지 처리 오류: {e}")
            return error_response(
                str(e),
                status_code=400,
                error_type="ImageProcessingError"
            )
        
        except RuntimeError as e:
            # 예측 오류
            logger.error(f"예측 오류: {e}")
            return error_response(
                "예측 중 오류가 발생했습니다",
                status_code=500,
                error_type="PredictionError",
                details={"original_error": str(e)}
            )
        
        except Exception as e:
            # 예상치 못한 오류
            logger.exception(f"예상치 못한 오류: {e}")
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
        return error_response(
            f"파일 크기가 너무 큽니다. 최대 {max_mb:.0f}MB까지 허용됩니다",
            status_code=413,
            error_type="FileTooLargeError"
        )
    
    @app.errorhandler(404)
    def not_found(error):
        """404 에러 핸들러"""
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
    
    return app


# 애플리케이션 인스턴스 생성
app = create_app()


if __name__ == "__main__":
    # 개발 서버 실행
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )
