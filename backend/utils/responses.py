"""
API 응답 처리 유틸리티 모듈

표준화된 JSON 응답 포맷을 제공합니다.
"""

from typing import Any, Dict, Optional
from flask import jsonify


def success_response(data: Any, message: str = None, status_code: int = 200):
    """
    성공 응답 생성
    
    Args:
        data (Any): 응답 데이터
        message (str, optional): 성공 메시지
        status_code (int): HTTP 상태 코드 (기본값: 200)
    
    Returns:
        tuple: (response, status_code)
    """
    response = {
        'success': True,
        'data': data
    }
    
    if message:
        response['message'] = message
    
    return jsonify(response), status_code


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
        tuple: (response, status_code)
    """
    response = {
        'success': False,
        'error': {
            'type': error_type,
            'message': message
        }
    }
    
    if details:
        response['error']['details'] = details
    
    return jsonify(response), status_code


def prediction_response(predictions: list, status_code: int = 200):
    """
    예측 결과 응답 생성 (하위 호환성 유지)
    
    Args:
        predictions (list): 예측 결과 리스트
        status_code (int): HTTP 상태 코드
    
    Returns:
        tuple: (response, status_code)
    """
    return jsonify({
        'success': True,
        'predictions': predictions
    }), status_code
