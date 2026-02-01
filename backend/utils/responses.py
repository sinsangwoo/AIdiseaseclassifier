"""
API 응답 처리 유틸리티 모듈

표준화된 JSON 응답 포맷을 제공합니다.
"""

from typing import Any, Dict, Optional
from flask import jsonify, has_app_context


def _safe_jsonify(data):
    """Flask 애플리케이션 컨텍스트가 없을 때도 안전하게 동작하는 jsonify"""
    if has_app_context():
        return jsonify(data)
    else:
        # 테스트 환경에서는 딕셔너리 그대로 반환
        return data


def success_response(data: Any, message: str = None, status_code: int = 200):
    """
    성공 응답 생성
    
    Args:
        data (Any): 응답 데이터
        message (str, optional): 성공 메시지
        status_code (int): HTTP 상태 코드 (기본값: 200)
    
    Returns:
        tuple: (response, status_code) 또는 dict (테스트 환경)
    """
    response = {
        'success': True,
        'data': data
    }
    
    if message:
        response['message'] = message
    
    if has_app_context():
        return jsonify(response), status_code
    else:
        # 테스트 환경: 딕셔너리만 반환
        return response


def error_response(
    message: str,
    status_code: int = 400,
    error_type: str = "ValidationError",
    details: Optional[Dict] = None
):
    """
    에러 응답 생성
    
    Args:
        message (str): 에러 메시지
        status_code (int): HTTP 상태 코드 (기본값: 400)
        error_type (str): 에러 타입 (기본값: "ValidationError")
        details (Dict, optional): 추가 에러 상세 정보
    
    Returns:
        tuple: (response, status_code) 또는 (dict, status_code) (테스트 환경)
    """
    response = {
        'success': False,
        'error': message,
        'error_type': error_type
    }
    
    if details:
        response['details'] = details
    
    if has_app_context():
        return jsonify(response), status_code
    else:
        # 테스트 환경: 딕셔너리와 status_code 반환
        return response, status_code


def prediction_response(
    predictions: list,
    processing_time: float = None,
    image_size: tuple = None,
    status_code: int = 200
):
    """
    예측 결과 응답 생성
    
    Args:
        predictions (list): 예측 결과 리스트
        processing_time (float, optional): 처리 시간 (ms)
        image_size (tuple, optional): 이미지 크기 (width, height)
        status_code (int): HTTP 상태 코드
    
    Returns:
        dict 또는 tuple: 테스트 환경에서는 dict, 프로덕션에서는 (response, status_code)
    """
    response = {
        'success': True,
        'predictions': predictions
    }
    
    # 메타데이터 추가
    if processing_time is not None or image_size is not None:
        response['metadata'] = {}
        if processing_time is not None:
            response['metadata']['processing_time_ms'] = processing_time
        if image_size is not None:
            response['metadata']['image_size'] = image_size
    
    if has_app_context():
        return jsonify(response), status_code
    else:
        # 테스트 환경: 딕셔너리만 반환
        return response
