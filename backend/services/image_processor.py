"""
이미지 전처리 서비스 모듈

업로드된 이미지를 ONNX Runtime용 Numpy 배열로 전처리합니다.
"""

import io
from typing import Tuple

import numpy as np

from backend.utils import (
    LoggerMixin,
    InvalidImageError,
    ImageProcessingError,
    log_exception
)
from backend.utils.image_processor import preprocess_bytes_to_tensor


class ImageProcessor(LoggerMixin):
    """
    이미지 전처리 클래스
    
    업로드된 이미지를 ONNX 모델에 맞는 형식으로 변환합니다.
    """
    
    def __init__(self, target_size: Tuple[int, int] = (224, 224)):
        """
        이미지 프로세서 초기화
        
        Args:
            target_size (Tuple[int, int]): 리사이즈할 이미지 크기 (width, height)
        """
        self.target_size = target_size
        self.logger.info(f"ImageProcessor 초기화 (target_size: {target_size})")
    
    def preprocess(self, image_bytes: bytes) -> np.ndarray:
        """
        이미지 바이트를 모델 입력 형식으로 전처리
        
        Args:
            image_bytes (bytes): 원본 이미지 바이트 데이터
        
        Returns:
            np.ndarray: 전처리된 배열 (shape: [1, 224, 224, 3])
        """
        try:
            tensor = preprocess_bytes_to_tensor(image_bytes, self.target_size)
            self.logger.debug(f"전처리 완료: shape={tensor.shape}, dtype={tensor.dtype}")
            return tensor
            
        except (InvalidImageError, ImageProcessingError):
            # 이미 처리된 예외는 그대로 전파
            raise
        
        except Exception as e:
            # 예상치 못한 오류
            log_exception(self.logger, e, "이미지 전처리 중 예상치 못한 오류")
            raise ImageProcessingError(f"이미지 전처리 실패: {str(e)}")
    
    def preprocess_from_file(self, file_storage) -> np.ndarray:
        """
        Flask FileStorage 객체에서 직접 이미지 전처리
        
        Args:
            file_storage: Flask request.files에서 받은 파일 객체
        
        Returns:
            np.ndarray: 전처리된 배열
        """
        try:
            # 메모리에 파일 읽기
            in_memory_file = io.BytesIO()
            file_storage.save(in_memory_file)
            in_memory_file.seek(0)
            
            # 바이트로 읽어서 전처리
            image_bytes = in_memory_file.read()
            
            if len(image_bytes) == 0:
                self.logger.error("빈 파일이 업로드됨")
                raise InvalidImageError("빈 파일입니다")
            
            self.logger.debug(f"파일 읽기 완료 ({len(image_bytes)} bytes)")
            
            return self.preprocess(image_bytes)
            
        except (InvalidImageError, ImageProcessingError):
            raise
        
        except Exception as e:
            log_exception(self.logger, e, "파일에서 이미지 로딩 중 오류")
            raise InvalidImageError("파일을 읽을 수 없습니다")
    
    def validate_image(self, image_bytes: bytes) -> bool:
        """
        이미지가 유효한지 검증
        
        Args:
            image_bytes (bytes): 검증할 이미지 바이트
        
        Returns:
            bool: 유효한 이미지면 True
        """
        try:
            # 단순히 열 수 있는지 확인 (Pillow 사용)
            from PIL import Image
            img_stream = io.BytesIO(image_bytes)
            img = Image.open(img_stream)
            img.verify()  # 이미지 무결성 검증
            self.logger.debug("이미지 검증 성공")
            return True
        except Exception as e:
            self.logger.warning(f"이미지 검증 실패: {e}")
            return False
