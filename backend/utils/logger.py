"""
로깅 설정 모듈

구조화된 로깅 시스템을 제공합니다.
파일 로그, 콘솔 로그, 로그 로테이션 기능을 지원합니다.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(
    name: str = 'aiclassifier',
    log_level: str = 'INFO',
    log_dir: Optional[Path] = None,
    log_file: str = 'app.log',
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    구조화된 로거 설정
    
    Args:
        name (str): 로거 이름
        log_level (str): 로그 레벨 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_dir (Path, optional): 로그 파일 저장 디렉토리
        log_file (str): 로그 파일명
        max_bytes (int): 로그 파일 최대 크기 (바이트)
        backup_count (int): 백업 파일 개수
    
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 기존 핸들러 제거 (중복 방지)
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # 포맷터 생성
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러 (표준 출력)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (로그 디렉토리가 지정된 경우)
    if log_dir:
        # 로그 디렉토리 생성
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 일반 로그 파일 (로테이션)
        file_handler = RotatingFileHandler(
            filename=log_dir / log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # 에러 로그 파일 (ERROR 레벨 이상만)
        error_file_handler = RotatingFileHandler(
            filename=log_dir / 'error.log',
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_file_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    기존 로거 인스턴스를 가져오거나 새로 생성
    
    Args:
        name (str, optional): 로거 이름. None인 경우 'aiclassifier' 사용
    
    Returns:
        logging.Logger: 로거 인스턴스
    """
    if name is None:
        name = 'aiclassifier'
    return logging.getLogger(name)


class LoggerMixin:
    """
    로거를 클래스에 추가하는 믹스인
    
    사용 예:
        class MyClass(LoggerMixin):
            def my_method(self):
                self.logger.info("로그 메시지")
    """
    
    @property
    def logger(self) -> logging.Logger:
        """클래스 이름으로 로거 생성"""
        name = f"aiclassifier.{self.__class__.__name__}"
        return logging.getLogger(name)


def log_exception(logger: logging.Logger, exception: Exception, context: str = ""):
    """
    예외 정보를 상세하게 로깅
    
    Args:
        logger (logging.Logger): 로거 인스턴스
        exception (Exception): 발생한 예외
        context (str): 추가 컨텍스트 정보
    """
    logger.error(
        f"{context}{'- ' if context else ''}{type(exception).__name__}: {str(exception)}",
        exc_info=True
    )


# 로그 레벨별 편의 함수
def debug(message: str, logger_name: str = None):
    """DEBUG 레벨 로그"""
    get_logger(logger_name).debug(message)


def info(message: str, logger_name: str = None):
    """INFO 레벨 로그"""
    get_logger(logger_name).info(message)


def warning(message: str, logger_name: str = None):
    """WARNING 레벨 로그"""
    get_logger(logger_name).warning(message)


def error(message: str, logger_name: str = None):
    """ERROR 레벨 로그"""
    get_logger(logger_name).error(message)


def critical(message: str, logger_name: str = None):
    """CRITICAL 레벨 로그"""
    get_logger(logger_name).critical(message)
