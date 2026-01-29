"""
이미지 전처리 서비스 모듈

업로드된 이미지를 모델 입력에 맞게 전처리합니다.
"""

import io
import logging
from typing import Tuple

import numpy as np
from PIL import Image


logger = logging.getLogger(__name__)


class ImageProcessor:
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
    
    def preprocess(self, image_bytes: bytes) -> np.ndarray:
        """
        이미지 바이트를 모델 입력 형식으로 전처리
        
        Args:
            image_bytes (bytes): 원본 이미지 바이트 데이터
        
        Returns:
            np.ndarray: 전처리된 이미지 배열 (shape: [1, H, W, 3])
        
        Raises:
            ValueError: 이미지 로딩 또는 전처리 중 오류 발생 시
        """
        try:
            # 바이트 스트림에서 이미지 로드
            img_stream = io.BytesIO(image_bytes)
            img = Image.open(img_stream)
            
            # RGB 변환
            if img.mode != "RGB":
                logger.info(f"이미지 모드 {img.mode}를 RGB로 변환합니다")
                img = img.convert("RGB")
            
            # 리사이즈
            logger.debug(f"이미지를 {self.target_size}로 리사이즈합니다")
            img = img.resize(self.target_size, Image.LANCZOS)
            
            # numpy 배열로 변환 및 정규화
            img_array = np.array(img, dtype=np.float32)
            img_array = np.expand_dims(img_array, axis=0)  # 배치 차원 추가
            img_array /= 255.0  # [0, 1] 범위로 정규화
            
            logger.debug(f"전처리 완료: shape={img_array.shape}, dtype={img_array.dtype}")
            
            return img_array
            
        except Exception as e:
            logger.error(f"이미지 전처리 중 오류 발생: {e}")
            raise ValueError(f"이미지 전처리 실패: {e}")
    
    def preprocess_from_file(self, file_storage) -> np.ndarray:
        """
        Flask FileStorage 객체에서 직접 이미지 전처리
        
        Args:
            file_storage: Flask request.files에서 받은 파일 객체
        
        Returns:
            np.ndarray: 전처리된 이미지 배열
        """
        # 메모리에 파일 읽기
        in_memory_file = io.BytesIO()
        file_storage.save(in_memory_file)
        in_memory_file.seek(0)
        
        # 바이트로 읽어서 전처리
        image_bytes = in_memory_file.read()
        return self.preprocess(image_bytes)
    
    def validate_image(self, image_bytes: bytes) -> bool:
        """
        이미지가 유효한지 검증
        
        Args:
            image_bytes (bytes): 검증할 이미지 바이트
        
        Returns:
            bool: 유효한 이미지면 True
        """
        try:
            img_stream = io.BytesIO(image_bytes)
            img = Image.open(img_stream)
            img.verify()  # 이미지 무결성 검증
            return True
        except Exception as e:
            logger.warning(f"이미지 검증 실패: {e}")
            return False
