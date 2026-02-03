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
    
    # ─── 매직 바이트 시그니처 ──────────────────────────────────────
    #
    # JPEG : FF D8 FF (3B prefix)
    # PNG  : 89 50 4E 47 0D 0A 1A 0A (8B prefix)
    # GIF  : 'GIF87a' 또는 'GIF89a' (6B prefix)
    # WebP : 'RIFF' (4B) + [4B size] + 'WEBP' (4B)
    #         → prefix 체크로는 바이트 0~3만 확인되어
    #           AVI('RIFF????AVI ') 등과 오감지됨
    #         → _validate_webp()에서 바이트 8~12를 별도 확인
    #
    # MAGIC_BYTES는 prefix-only 형식인 포맷만 포함합니다.
    # WebP는 구조가 다르므로 별도 핸들링됩니다.
    # ───────────────────────────────────────────────────────────────
    MAGIC_BYTES = {
        'jpeg': [b'\xff\xd8\xff'],
        'png':  [b'\x89PNG\r\n\x1a\n'],
        'gif':  [b'GIF87a', b'GIF89a'],
    }

    # WebP는 고정 prefix가 아닌 구조체 형식이므로 별도 상수
    _WEBP_RIFF   = b'RIFF'   # bytes 0..3
    _WEBP_MARKER = b'WEBP'   # bytes 8..11
    
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

    # ─── WebP 전용 검증 ────────────────────────────────────────────

    @classmethod
    def _is_webp(cls, image_bytes: bytes) -> bool:
        """
        WebP 파일 구조체 검증

        WebP는 RIFF 컨테이너를 사용하며, 구조는 다음과 같습니다:
          bytes  0.. 3 : 'RIFF'
          bytes  4.. 7 : 파일 크기 (LE uint32, 검증 대상 아님)
          bytes  8..11 : 'WEBP'  ← 이 부분이 실제 형식 식별자

        'RIFF'만 확인하면 AVI, WAV 등 다른 RIFF 기반 형식과
        오감지됩니다. 최소 12바이트가 있고 바이트 8~12가 'WEBP'인지
        확인하여 정확히 판별합니다.
        """
        if len(image_bytes) < 12:
            return False
        return (
            image_bytes[0:4] == cls._WEBP_RIFF
            and image_bytes[8:12] == cls._WEBP_MARKER
        )

    # ─── 매직 바이트 검증 ──────────────────────────────────────────

    def validate_magic_bytes(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        매직 바이트를 확인하여 실제 이미지 파일인지 검증
        
        검증 순서:
          1. WebP 구조체 검증 (_is_webp — RIFF + WEBP 복합 체크)
          2. MAGIC_BYTES prefix 매칭 (JPEG / PNG / GIF)
        
        Args:
            image_bytes (bytes): 이미지 바이트 데이터
        
        Returns:
            tuple: (is_valid: bool, image_format: str or None)
        """
        if len(image_bytes) < 12:
            self.logger.warning("파일이 너무 작습니다 (매직 바이트 확인 불가)")
            return False, None

        # 1. WebP 구조체 검증 (RIFF 오감지 방지)
        if self._is_webp(image_bytes):
            self.logger.debug("이미지 형식 확인: WEBP")
            return True, 'webp'
        
        # 2. prefix-only 포맷 매칭
        for img_format, signatures in self.MAGIC_BYTES.items():
            for signature in signatures:
                if image_bytes.startswith(signature):
                    self.logger.debug(f"이미지 형식 확인: {img_format.upper()}")
                    return True, img_format
        
        self.logger.warning("알 수 없는 파일 형식 (이미지가 아닐 수 있음)")
        return False, None
    
    # ─── 크기·비율 검증 ────────────────────────────────────────────

    def validate_image_dimensions(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        이미지 크기와 가로세로 비율 검증
        
        검증 순서 (주의: 순서 변경 시 테스트도 함께 수정 필요)
          1. 최소 크기
          2. 최대 크기
          3. 가로세로 비율

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
    
    # ─── 종합 검증 ─────────────────────────────────────────────────

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


# ─── 글로벌 검증기 싱글턴 ──────────────────────────────────────────

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
