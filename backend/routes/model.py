from flask import Blueprint, current_app, request

model_bp = Blueprint('model', __name__)

@model_bp.route("/model/info")
def model_info():
    """모델 정보 조회"""
    return current_app.model_service.get_model_info()

@model_bp.route("/model/stats")
def model_stats():
    """
    모델 서비스 통계 조회 (Phase 3 신규 엔드포인트)
    
    캐시 히트율, 평균 추론 시간 등의 통계 제공
    """
    model_service = current_app.model_service
    return {
        "success": True,
        "statistics": model_service.get_statistics(),
        "cache_info": model_service.get_cache_info() if model_service.enable_cache else None
    }

@model_bp.route("/model/cache", methods=['GET', 'DELETE'])
def model_cache():
    """
    모델 캐시 관리 (Phase 3 신규 엔드포인트)
    
    GET: 캐시 정보 조회
    DELETE: 캐시 초기화
    """
    model_service = current_app.model_service
    if request.method == 'GET':
        if not model_service.enable_cache:
            return {
                "success": False,
                "message": "캐싱이 비활성화되어 있습니다"
            }, 400
        
        return {
            "success": True,
            "cache_info": model_service.get_cache_info(),
            "statistics": {
                "cache_hits": model_service.stats['cache_hits'],
                "cache_misses": model_service.stats['cache_misses']
            }
        }
    
    elif request.method == 'DELETE':
        if not model_service.enable_cache:
            return {
                "success": False,
                "message": "캐싱이 비활성화되어 있습니다"
            }, 400
        
        model_service.clear_cache()
        
        return {
            "success": True,
            "message": "캐시가 초기화되었습니다"
        }
