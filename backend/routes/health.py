from flask import Blueprint, current_app

health_bp = Blueprint('health', __name__)

@health_bp.route("/health")
def health_check():
    """간단한 헬스체크"""
    model_service = current_app.model_service
    health_checker = current_app.health_checker
    
    model_status = "ready" if model_service.is_ready() else "not_loaded"
    
    return {
        "status": "healthy" if model_service.is_ready() else "degraded",
        "model": model_status,
        "timestamp": health_checker.get_uptime()['start_time'],
        "version": "8.0.0-phase3-4"
    }

@health_bp.route("/health/detailed")
def detailed_health_check():
    """상세 헬스체크 (모니터링용)"""
    model_service = current_app.model_service
    health_checker = current_app.health_checker
    
    return health_checker.comprehensive_health_check(
        predictor=model_service._predictor if model_service._predictor else None,
        cache=None,
        metrics=model_service.get_statistics()
    )

@health_bp.route("/health/ready")
def readiness_check():
    """Readiness probe (Render/K8s용)"""
    import psutil
    model_service = current_app.model_service
    
    checks = {
        'model': model_service.is_ready(),
        'disk': psutil.disk_usage('/').percent < 90,
        'memory': psutil.virtual_memory().percent < 90
    }
    
    is_ready = all(checks.values())
    
    return {
        'status': 'ready' if is_ready else 'not_ready',
        'checks': checks
    }, 200 if is_ready else 503

@health_bp.route("/health/live")
def liveness_check():
    """Liveness probe (Render/K8s용)"""
    health_checker = current_app.health_checker
    return {
        'status': 'alive',
        'uptime_seconds': health_checker.get_uptime()['uptime_seconds']
    }, 200
