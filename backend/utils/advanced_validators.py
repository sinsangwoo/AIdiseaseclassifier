"""
고급 입력 검증 모듈

이미지 파일의 심층 검증을 수행합니다.
"""

import io
import imghdr
from typing import Tuple, Optional
from PIL import Image

from .exceptions import InvalidImageError
from .logger import get_logger


logger = get_logger('aiclassifier.validation')


class ImageValidator:
    """
    이미지 파일 고급 검증 클래스
    
    매직 넘버, 파일 구조, 이미지 특성 등을 검증합니다.
    """
    
    def __init__(
        self,
        min_width: int = 32,
        min_height: int = 32,
        max_width: int = 4096,
        max_height: int = 4096,
        max_aspect_ratio: float = 10.0
    ):
        """
        이미지 검증기 초기화
        
        Args:
            min_width (int): 최소 너비
            min_height (int): 최소 높이
            max_width (int): 최대 너비
            max_height (int): 최대 높이
            max_aspect_ratio (float): 최대 가로세로 비율
        """
        self.min_width = min_width
        self.min_height = min_height
        self.max_width = max_width
        self.max_height = max_height
        self.max_aspect_ratio = max_aspect_ratio
    
    def validate_magic_bytes(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        매직 바이트로 이미지 형식 검증
        
        Args:
            image_bytes (bytes): 이미지 데이터
        
        Returns:
            Tuple[bool, Optional[str]]: (유효 여부, 이미지 형식)
        """
        if len(image_bytes) < 12:
            return False, None
        
        # imghdr를 사용한 형식 감지
        img_format = imghdr.what(None, h=image_bytes)
        
        if img_format not in ['jpeg', 'png', 'jpg']:
            logger.warning(f"지원하지 않는 이미지 형식: {img_format}")
            return False, img_format
        
        logger.debug(f"이미지 형식 확인: {img_format}")
        return True, img_format
    
    def validate_image_integrity(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        이미지 파일 무결성 검증
        
        Args:
            image_bytes (bytes): 이미지 데이터
        
        Returns:
            Tuple[bool, Optional[str]]: (유효 여부, 오류 메시지)
        """
        try:
            img_stream = io.BytesIO(image_bytes)
            img = Image.open(img_stream)
            
            # verify()는 파일 구조만 검증 (실제 픽셀 데이터는 로드하지 않음)
            img.verify()
            
            # 실제 이미지 로드 시도 (손상된 픽셀 데이터 감지)
            img_stream.seek(0)
            img = Image.open(img_stream)
            img.load()  # 강제로 픽셀 데이터 로드
            
            logger.debug("이미지 무결성 검증 성공")
            return True, None
            
        except Exception as e:
            error_msg = f"손상된 이미지 파일: {str(e)}"
            logger.warning(error_msg)
            return False, error_msg
    
    def validate_image_dimensions(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        이미지 크기 검증
        
        Args:
            image_bytes (bytes): 이미지 데이터
        
        Returns:
            Tuple[bool, Optional[str]]: (유효 여부, 오류 메시지)
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
                logger.warning(error_msg)
                return False, error_msg
            
            # 최대 크기 확인
            if width > self.max_width or height > self.max_height:
                error_msg = (
                    f"이미지가 너무 큽니다 ({width}x{height}). "
                    f"최대 {self.max_width}x{self.max_height} 허용"
                )
                logger.warning(error_msg)
                return False, error_msg
            
            # 가로세로 비율 확인
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > self.max_aspect_ratio:
                error_msg = (
                    f"비정상적인 가로세로 비율: {aspect_ratio:.2f}. "
                    f"최대 {self.max_aspect_ratio} 허용"
                )
                logger.warning(error_msg)
                return False, error_msg
            
            logger.debug(f"이미지 크기 검증 성공: {width}x{height} (비율: {aspect_ratio:.2f})")
            return True, None
            
        except Exception as e:
            error_msg = f"이미지 크기 확인 실패: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def validate_image_mode(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        이미지 색상 모드 검증
        
        Args:
            image_bytes (bytes): 이미지 데이터
        
        Returns:
            Tuple[bool, Optional[str]]: (유효 여부, 오류 메시지)
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            mode = img.mode
            
            # 지원하는 모드: RGB, RGBA, L (grayscale), P (palette)
            supported_modes = ['RGB', 'RGBA', 'L', 'P']
            
            if mode not in supported_modes:
                error_msg = f"지원하지 않는 색상 모드: {mode}"
                logger.warning(error_msg)
                return False, error_msg
            
            logger.debug(f"이미지 색상 모드 확인: {mode}")
            return True, None
            
        except Exception as e:
            error_msg = f"이미지 모드 확인 실패: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def comprehensive_validation(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        종합 이미지 검증
        
        Args:
            image_bytes (bytes): 이미지 데이터
        
        Returns:
            Tuple[bool, Optional[str]]: (유효 여부, 오류 메시지)
        
        Raises:
            InvalidImageError: 검증 실패 시
        """
        # 1. 매직 바이트 검증
        is_valid, img_format = self.validate_magic_bytes(image_bytes)
        if not is_valid:
            raise InvalidImageError(
                f"지원하지 않는 파일 형식입니다. "
                f"JPG, JPEG, PNG만 허용됩니다."
            )
        
        # 2. 무결성 검증
        is_valid, error_msg = self.validate_image_integrity(image_bytes)
        if not is_valid:
            raise InvalidImageError(error_msg)
        
        # 3. 크기 검증
        is_valid, error_msg = self.validate_image_dimensions(image_bytes)
        if not is_valid:
            raise InvalidImageError(error_msg)
        
        # 4. 색상 모드 검증
        is_valid, error_msg = self.validate_image_mode(image_bytes)
        if not is_valid:
            raise InvalidImageError(error_msg)
        
        logger.info("이미지 종합 검증 통과")
        return True, None


# 전역 이미지 검증기 인스턴스
_image_validator = None


def get_image_validator() -> Optional[ImageValidator]:
    """전역 이미지 검증기 인스턴스 가져오기"""
    return _image_validator


def init_image_validator(
    min_width: int = 32,
    min_height: int = 32,
    max_width: int = 4096,
    max_height: int = 4096,
    max_aspect_ratio: float = 10.0
):
    """
    이미지 검증기 초기화
    
    Args:
        min_width (int): 최소 너비
        min_height (int): 최소 높이
        max_width (int): 최대 너비
        max_height (int): 최대 높이
        max_aspect_ratio (float): 최대 가로세로 비율
    """
    global _image_validator
    _image_validator = ImageValidator(
        min_width=min_width,
        min_height=min_height,
        max_width=max_width,
        max_height=max_height,
        max_aspect_ratio=max_aspect_ratio
    )
    
    logger.info(
        f"이미지 검증기 초기화 완료 "
        f"(크기: {min_width}x{min_height} ~ {max_width}x{max_height}, "
        f"비율: {max_aspect_ratio})"
    )
    
    return _image_validator
