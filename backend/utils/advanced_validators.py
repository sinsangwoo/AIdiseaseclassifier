"""
고급 이미지 검증 모듈

매직 바이트, 크기, 비율 등 상세한 이미지 검증 기능을 제공합니다.
"""

import io
import logging
from typing import Tuple, Optional
from PIL import Image

from .exceptions import InvalidImageError


class ImageValidator:
    """
    고급 이미지 검증기
    
    매직 바이트, 이미지 크기, 가로세로 비율 등을 검증합니다.
    """
    
    # 매직 바이트 시그니처
    MAGIC_BYTES = {
        'jpeg': [b'\xff\xd8\xff'],
        'png': [b'\x89PNG\r\n\x1a\n'],
        'gif': [b'GIF87a', b'GIF89a'],
        'webp': [b'RIFF', b'WEBP']
    }
    
    def __init__(
        self,
        min_width: int = 32,
        min_height: int = 32,
        max_width: int = 4096,
        max_height: int = 4096,
        max_aspect_ratio: float = 10.0
    ):
        """
        Args:
            min_width (int): 최소 이미지 너비
            min_height (int): 최소 이미지 높이
            max_width (int): 최대 이미지 너비
            max_height (int): 최대 이미지 높이
            max_aspect_ratio (float): 최대 가로세로 비율 (예: 10.0 = 10:1)
        """
        self.min_width = min_width
        self.min_height = min_height
        self.max_width = max_width
        self.max_height = max_height
        self.max_aspect_ratio = max_aspect_ratio
        
        self.logger = logging.getLogger('aiclassifier.validation')
    
    def validate_magic_bytes(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        매직 바이트를 확인하여 실제 이미지 파일인지 검증
        
        Args:
            image_bytes (bytes): 이미지 바이트 데이터
        
        Returns:
            tuple: (is_valid: bool, image_format: str or None)
        """
        if len(image_bytes) < 12:
            self.logger.warning("파일이 너무 작습니다 (매직 바이트 확인 불가)")
            return False, None
        
        for img_format, signatures in self.MAGIC_BYTES.items():
            for signature in signatures:
                if image_bytes.startswith(signature):
                    self.logger.debug(f"이미지 형식 확인: {img_format.upper()}")
                    return True, img_format
        
        self.logger.warning("알 수 없는 파일 형식 (이미지가 아닐 수 있음)")
        return False, None
    
    def validate_image_dimensions(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        이미지 크기와 가로세로 비율 검증
        
        Args:
            image_bytes (bytes): 이미지 바이트 데이터
        
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            
            # 최소 크기 확인
            if width < self.min_width or height < self.min_height:
                error_msg = (
                    f"이미지가 너무 작습니다 ({width}x{height}). "
                    f"최소 {self.min_width}x{self.min_height} 필요"
                )
                self.logger.warning(error_msg)
                return False, error_msg
            
            # 최대 크기 확인
            if width > self.max_width or height > self.max_height:
                error_msg = (
                    f"이미지가 너무 큽니다 ({width}x{height}). "
                    f"최대 {self.max_width}x{self.max_height} 허용"
                )
                self.logger.warning(error_msg)
                return False, error_msg
            
            # 가로세로 비율 확인
            aspect_ratio = max(width / height, height / width)
            if aspect_ratio > self.max_aspect_ratio:
                error_msg = (
                    f"가로세로 비율이 비정상적입니다 ({aspect_ratio:.1f}:1). "
                    f"최대 {self.max_aspect_ratio}:1 허용"
                )
                self.logger.warning(error_msg)
                return False, error_msg
            
            self.logger.debug(
                f"이미지 크기 검증 통과: {width}x{height} "
                f"(비율: {aspect_ratio:.2f}:1)"
            )
            return True, None
            
        except Exception as e:
            error_msg = f"이미지 크기 확인 실패: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def comprehensive_validation(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        종합 이미지 검증 (매직 바이트 + 크기)
        
        Args:
            image_bytes (bytes): 이미지 바이트 데이터
        
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        
        Raises:
            InvalidImageError: 검증 실패 시
        """
        # 1. 매직 바이트 검증
        is_valid, img_format = self.validate_magic_bytes(image_bytes)
        if not is_valid:
            error_msg = "유효한 이미지 형식이 아닙니다"
            raise InvalidImageError(error_msg)
        
        # 2. 이미지 크기 검증
        is_valid, error_msg = self.validate_image_dimensions(image_bytes)
        if not is_valid:
            raise InvalidImageError(error_msg)
        
        self.logger.info(f"이미지 검증 완료 (형식: {img_format.upper()})")
        return True, None


# 글로벌 검증기 인스턴스
_global_validator: Optional[ImageValidator] = None


def init_image_validator(
    min_width: int = 32,
    min_height: int = 32,
    max_width: int = 4096,
    max_height: int = 4096,
    max_aspect_ratio: float = 10.0
) -> ImageValidator:
    """
    글로벌 이미지 검증기 초기화
    
    Args:
        min_width (int): 최소 이미지 너비
        min_height (int): 최소 이미지 높이
        max_width (int): 최대 이미지 너비
        max_height (int): 최대 이미지 높이
        max_aspect_ratio (float): 최대 가로세로 비율
    
    Returns:
        ImageValidator: 초기화된 검증기 인스턴스
    """
    global _global_validator
    _global_validator = ImageValidator(
        min_width=min_width,
        min_height=min_height,
        max_width=max_width,
        max_height=max_height,
        max_aspect_ratio=max_aspect_ratio
    )
    return _global_validator


def get_image_validator() -> Optional[ImageValidator]:
    """
    글로벌 이미지 검증기 가져오기
    
    Returns:
        ImageValidator or None: 검증기 인스턴스
    """
    return _global_validator
