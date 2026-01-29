"""
헬스체크 모듈

시스템 상태를 모니터링하고 진단하는 기능을 제공합니다.
"""

import psutil
import time
from pathlib import Path
from typing import Dict, Any

from .logger import get_logger


logger = get_logger('aiclassifier.health')


class HealthChecker:
    """
    시스템 헬스체크 클래스
    
    시스템 리소스, 모델 상태, 디스크 상태 등을 모니터링합니다.
    """
    
    def __init__(self, app=None):
        """
        헬스체커 초기화
        
        Args:
            app: Flask 애플리케이션 인스턴스
        """
        self.app = app
        self.start_time = time.time()
    
    def check_system_resources(self) -> Dict[str, Any]:
        """
        시스템 리소스 상태 확인
        
        Returns:
            Dict: 시스템 리소스 정보
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'status': 'healthy',
                'cpu': {
                    'usage_percent': round(cpu_percent, 2),
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'total_mb': round(memory.total / (1024 * 1024), 2),
                    'used_mb': round(memory.used / (1024 * 1024), 2),
                    'available_mb': round(memory.available / (1024 * 1024), 2),
                    'usage_percent': round(memory.percent, 2)
                },
                'disk': {
                    'total_gb': round(disk.total / (1024 ** 3), 2),
                    'used_gb': round(disk.used / (1024 ** 3), 2),
                    'free_gb': round(disk.free / (1024 ** 3), 2),
                    'usage_percent': round(disk.percent, 2)
                }
            }
        except Exception as e:
            logger.error(f"시스템 리소스 확인 실패: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_model_status(self, predictor) -> Dict[str, Any]:
        """
        모델 상태 확인
        
        Args:
            predictor: ModelPredictor 인스턴스
        
        Returns:
            Dict: 모델 상태 정보
        """
        try:
            if predictor and predictor.is_ready():
                model_info = predictor.get_model_info()
                
                # 모델 파일 크기 확인
                model_path = Path(predictor.model_path)
                model_size_mb = 0
                if model_path.exists():
                    model_size_mb = round(model_path.stat().st_size / (1024 * 1024), 2)
                
                return {
                    'status': 'ready',
                    'model_path': predictor.model_path,
                    'labels_path': predictor.labels_path,
                    'num_classes': len(predictor.class_names),
                    'model_size_mb': model_size_mb
                }
            else:
                return {
                    'status': 'not_loaded',
                    'error': '모델이 로드되지 않았습니다'
                }
        except Exception as e:
            logger.error(f"모델 상태 확인 실패: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_dependencies(self) -> Dict[str, Any]:
        """
        주요 의존성 패키지 상태 확인
        
        Returns:
            Dict: 의존성 상태 정보
        """
        try:
            import flask
            import numpy
            import PIL
            import onnxruntime
            
            return {
                'status': 'healthy',
                'packages': {
                    'flask': flask.__version__,
                    'numpy': numpy.__version__,
                    'pillow': PIL.__version__,
                    'onnxruntime': onnxruntime.__version__
                }
            }
        except Exception as e:
            logger.error(f"의존성 확인 실패: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_uptime(self) -> Dict[str, Any]:
        """
        서버 가동 시간 반환
        
        Returns:
            Dict: 가동 시간 정보
        """
        uptime_seconds = time.time() - self.start_time
        
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        
        return {
            'uptime_seconds': round(uptime_seconds, 2),
            'uptime_formatted': f"{days}d {hours}h {minutes}m {seconds}s",
            'start_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))
        }
    
    def comprehensive_health_check(self, predictor=None, cache=None, metrics=None) -> Dict[str, Any]:
        """
        종합 헬스체크
        
        Args:
            predictor: ModelPredictor 인스턴스
            cache: PredictionCache 인스턴스
            metrics: PerformanceMetrics 인스턴스
        
        Returns:
            Dict: 종합 헬스체크 결과
        """
        overall_status = 'healthy'
        
        # 시스템 리소스 확인
        system = self.check_system_resources()
        if system.get('status') != 'healthy':
            overall_status = 'degraded'
        
        # 모델 상태 확인
        model = self.check_model_status(predictor)
        if model.get('status') != 'ready':
            overall_status = 'unhealthy'
        
        # 의존성 확인
        dependencies = self.check_dependencies()
        if dependencies.get('status') != 'healthy':
            overall_status = 'degraded'
        
        # 가동 시간
        uptime = self.get_uptime()
        
        # 캐시 상태 (선택적)
        cache_stats = None
        if cache:
            try:
                cache_stats = cache.get_stats()
            except Exception as e:
                logger.warning(f"캐시 통계 조회 실패: {e}")
        
        # 성능 메트릭 (선택적)
        performance_stats = None
        if metrics:
            try:
                performance_stats = metrics.get_stats()
            except Exception as e:
                logger.warning(f"성능 메트릭 조회 실패: {e}")
        
        result = {
            'status': overall_status,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'uptime': uptime,
            'system': system,
            'model': model,
            'dependencies': dependencies
        }
        
        if cache_stats:
            result['cache'] = cache_stats
        
        if performance_stats:
            result['performance'] = performance_stats
        
        return result


# 전역 헬스체커 인스턴스
_health_checker = None


def get_health_checker() -> HealthChecker:
    """전역 헬스체커 인스턴스 가져오기"""
    return _health_checker


def init_health_checker(app):
    """
    Flask 앱에 헬스체커 초기화
    
    Args:
        app: Flask 애플리케이션 인스턴스
    """
    global _health_checker
    _health_checker = HealthChecker(app)
    logger.info("헬스체커 초기화 완료")
    return _health_checker
