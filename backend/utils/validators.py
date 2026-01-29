"""
입력 검증 유틸리티 모듈

파일 업로드 검증 및 유효성 검사 기능을 제공합니다.
"""

import logging
from typing import Set
from werkzeug.datastructures import FileStorage


logger = logging.getLogger(__name__)


def allowed_file(filename: str, allowed_extensions: Set[str]) -> bool:
    """
    파일 확장자가 허용된 확장자인지 확인
    
    Args:
        filename (str): 검사할 파일명
        allowed_extensions (Set[str]): 허용된 확장자 집합 (예: {'jpg', 'png'})
    
    Returns:
        bool: 허용된 확장자면 True
    """
    if not filename or '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions


def validate_file(file: FileStorage, allowed_extensions: Set[str], max_size: int = None) -> tuple:
    """
    업로드된 파일의 유효성 검증
    
    Args:
        file (FileStorage): Flask request.files에서 받은 파일 객체
        allowed_extensions (Set[str]): 허용된 확장자 집합
        max_size (int, optional): 최대 파일 크기 (바이트)
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    # 파일 존재 확인
    if not file:
        return False, "파일이 제공되지 않았습니다"
    
    # 파일명 확인
    if not file.filename:
        return False, "파일 이름이 비어있습니다"
    
    # 확장자 확인
    if not allowed_file(file.filename, allowed_extensions):
        allowed_str = ', '.join(allowed_extensions)
        return False, f"지원하지 않는 파일 형식입니다. 허용된 형식: {allowed_str}"
    
    # MIME 타입 확인
    allowed_mime_types = {
        'image/jpeg',
        'image/png',
        'image/jpg'
    }
    
    if file.content_type not in allowed_mime_types:
        logger.warning(f"의심스러운 MIME 타입: {file.content_type} (파일명: {file.filename})")
        return False, "잘못된 파일 형식입니다"
    
    # 파일 크기 확인 (선택적)
    if max_size:
        file.seek(0, 2)  # 파일 끝으로 이동
        file_size = file.tell()
        file.seek(0)  # 다시 처음으로
        
        if file_size > max_size:
            max_mb = max_size / (1024 * 1024)
            return False, f"파일 크기가 너무 큽니다. 최대 {max_mb:.1f}MB까지 허용됩니다"
        
        if file_size == 0:
            return False, "빈 파일입니다"
    
    logger.info(f"파일 검증 통과: {file.filename} ({file.content_type})")
    return True, None


def validate_image_header(file_bytes: bytes) -> bool:
    """
    이미지 파일의 매직 넘버 검증
    
    Args:
        file_bytes (bytes): 파일의 첫 바이트들
    
    Returns:
        bool: 유효한 이미지 헤더면 True
    """
    if len(file_bytes) < 8:
        return False
    
    # JPEG 매직 넘버: FF D8 FF
    if file_bytes[:3] == b'\xff\xd8\xff':
        return True
    
    # PNG 매직 넘버: 89 50 4E 47 0D 0A 1A 0A
    if file_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return True
    
    return False
