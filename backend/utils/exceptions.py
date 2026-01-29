"""
커스텀 예외 클래스 모듈

애플리케이션에서 발생하는 도메인 특화 예외를 정의합니다.
"""


class AIClassifierException(Exception):
    """
    기본 애플리케이션 예외 클래스
    
    모든 커스텀 예외의 부모 클래스입니다.
    """
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)


class ModelNotLoadedError(AIClassifierException):
    """
    모델이 로드되지 않았을 때 발생하는 예외
    
    Example:
        raise ModelNotLoadedError("ONNX 모델 파일을 찾을 수 없습니다")
    """
    def __init__(self, message: str = "모델이 로드되지 않았습니다"):
        super().__init__(message, error_code="MODEL_NOT_LOADED")


class ModelLoadError(AIClassifierException):
    """
    모델 로딩 중 오류가 발생했을 때 발생하는 예외
    
    Example:
        raise ModelLoadError("손상된 ONNX 파일입니다")
    """
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, error_code="MODEL_LOAD_ERROR")
        self.original_error = original_error


class InvalidImageError(AIClassifierException):
    """
    유효하지 않은 이미지일 때 발생하는 예외
    
    Example:
        raise InvalidImageError("지원하지 않는 이미지 형식입니다")
    """
    def __init__(self, message: str):
        super().__init__(message, error_code="INVALID_IMAGE")


class ImageProcessingError(AIClassifierException):
    """
    이미지 처리 중 오류가 발생했을 때 발생하는 예외
    
    Example:
        raise ImageProcessingError("이미지 리사이징 중 오류가 발생했습니다")
    """
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, error_code="IMAGE_PROCESSING_ERROR")
        self.original_error = original_error


class PredictionError(AIClassifierException):
    """
    예측 수행 중 오류가 발생했을 때 발생하는 예외
    
    Example:
        raise PredictionError("ONNX 런타임 오류가 발생했습니다")
    """
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, error_code="PREDICTION_ERROR")
        self.original_error = original_error


class FileValidationError(AIClassifierException):
    """
    파일 검증 실패 시 발생하는 예외
    
    Example:
        raise FileValidationError("파일 크기가 10MB를 초과합니다")
    """
    def __init__(self, message: str):
        super().__init__(message, error_code="FILE_VALIDATION_ERROR")


class ConfigurationError(AIClassifierException):
    """
    설정 관련 오류가 발생했을 때 발생하는 예외
    
    Example:
        raise ConfigurationError("필수 환경변수가 설정되지 않았습니다")
    """
    def __init__(self, message: str):
        super().__init__(message, error_code="CONFIGURATION_ERROR")
