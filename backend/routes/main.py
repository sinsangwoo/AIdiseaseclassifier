from flask import Blueprint, current_app

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    """메인 엔드포인트"""
    config = current_app.config
    model_service = current_app.model_service
    health_checker = current_app.health_checker
    
    return {
        "service": "AI Disease Classifier API",
        "version": "8.0.0-phase3-4",
        "status": "running",
        "environment": current_app.config.get('ENV', 'default'),
        "features": {
            "model_caching": model_service.enable_cache,
            "cache_size": model_service.cache_size,
            "warmup": model_service.stats['warmup_completed'],
            "http_caching": True
        },
        "endpoints": {
            "health": "/health",
            "health_detailed": "/health/detailed",
            "health_ready": "/health/ready",
            "health_live": "/health/live",
            "model_info": "/model/info",
            "model_stats": "/model/stats",
            "model_cache": "/model/cache",
            "predict": "/predict"
        }
    }
