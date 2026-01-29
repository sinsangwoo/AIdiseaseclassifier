"""
API 엔드포인트 테스트

Flask API의 모든 엔드포인트를 테스트합니다.
"""

import pytest
import json
import io
from PIL import Image


class TestRootEndpoint:
    """루트 엔드포인트 테스트"""
    
    @pytest.mark.api
    def test_root_endpoint_returns_service_info(self, client):
        """GET / - 서비스 정보 반환"""
        response = client.get('/')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'service' in data
        assert 'version' in data
        assert 'status' in data
        assert data['status'] == 'running'
        assert 'endpoints' in data


class TestHealthEndpoints:
    """헬스체크 엔드포인트 테스트"""
    
    @pytest.mark.api
    def test_health_endpoint_basic(self, client):
        """GET /health - 기본 헬스체크"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'status' in data
        assert data['status'] in ['healthy', 'degraded']
        assert 'model' in data
        assert 'timestamp' in data
    
    @pytest.mark.api
    def test_health_detailed_endpoint(self, client):
        """GET /health/detailed - 상세 헬스체크"""
        response = client.get('/health/detailed')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # 필수 필드 확인
        assert 'status' in data
        assert 'timestamp' in data
        assert 'uptime' in data
        assert 'system' in data
        assert 'model' in data
        assert 'dependencies' in data
        
        # Uptime 구조 확인
        uptime = data['uptime']
        assert 'uptime_seconds' in uptime
        assert 'uptime_formatted' in uptime
        assert 'start_time' in uptime
        
        # 시스템 리소스 확인
        system = data['system']
        assert 'cpu' in system
        assert 'memory' in system
        assert 'disk' in system
        
        # CPU 정보
        assert 'usage_percent' in system['cpu']
        assert 'count' in system['cpu']
        
        # 메모리 정보
        assert 'total_mb' in system['memory']
        assert 'used_mb' in system['memory']
        assert 'available_mb' in system['memory']
        assert 'usage_percent' in system['memory']


class TestModelInfoEndpoint:
    """모델 정보 엔드포인트 테스트"""
    
    @pytest.mark.api
    def test_model_info_endpoint(self, client):
        """GET /model/info - 모델 정보 조회"""
        response = client.get('/model/info')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # 모델 정보 필드 확인
        assert 'model_path' in data
        assert 'labels_path' in data


class TestPredictEndpoint:
    """예측 엔드포인트 테스트"""
    
    @pytest.mark.api
    def test_predict_without_file(self, client):
        """POST /predict - 파일 없이 요청 (400 에러)"""
        response = client.post('/predict')
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['success'] is False
        assert 'error' in data
        assert data['error_type'] == 'FileValidationError'
    
    @pytest.mark.api
    def test_predict_with_valid_jpeg(self, client, sample_image_valid):
        """POST /predict - 유효한 JPEG 이미지로 예측"""
        data = {
            'file': (sample_image_valid, 'test_image.jpg', 'image/jpeg')
        }
        
        response = client.post(
            '/predict',
            data=data,
            content_type='multipart/form-data'
        )
        
        # 모델이 로드되지 않은 경우 503, 로드된 경우 200
        assert response.status_code in [200, 503]
        
        result = response.get_json()
        
        if response.status_code == 200:
            # 성공 응답 구조 확인
            assert result['success'] is True
            assert 'predictions' in result
            assert 'metadata' in result
            
            # Predictions 구조 확인
            predictions = result['predictions']
            assert isinstance(predictions, list)
            assert len(predictions) > 0
            
            # 첫 번째 예측 확인
            first_pred = predictions[0]
            assert 'className' in first_pred
            assert 'probability' in first_pred
            assert 0 <= first_pred['probability'] <= 1
            
            # Metadata 확인
            metadata = result['metadata']
            assert 'processing_time_ms' in metadata
            assert 'image_size' in metadata
            assert 'filename' in metadata
        else:
            # 503 에러 (모델 미준비)
            assert result['success'] is False
            assert result['error_type'] == 'ModelNotLoadedError'
    
    @pytest.mark.api
    def test_predict_with_valid_png(self, client, sample_image_png):
        """POST /predict - 유효한 PNG 이미지로 예측"""
        data = {
            'file': (sample_image_png, 'test_image.png', 'image/png')
        }
        
        response = client.post(
            '/predict',
            data=data,
            content_type='multipart/form-data'
        )
        
        assert response.status_code in [200, 503]
    
    @pytest.mark.api
    @pytest.mark.validation
    def test_predict_with_text_file(self, client, sample_text_file):
        """POST /predict - 텍스트 파일 (400 에러)"""
        data = {
            'file': (sample_text_file, 'test.txt', 'text/plain')
        }
        
        response = client.post(
            '/predict',
            data=data,
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 400
        result = response.get_json()
        
        assert result['success'] is False
        assert 'error' in result
    
    @pytest.mark.api
    @pytest.mark.validation
    def test_predict_with_small_image(self, client, sample_image_small):
        """POST /predict - 너무 작은 이미지 (400 에러)"""
        data = {
            'file': (sample_image_small, 'small.jpg', 'image/jpeg')
        }
        
        response = client.post(
            '/predict',
            data=data,
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 400
        result = response.get_json()
        
        assert result['success'] is False
        assert 'error_type' in result
    
    @pytest.mark.api
    @pytest.mark.validation
    def test_predict_with_large_image(self, client, sample_image_large):
        """POST /predict - 너무 큰 이미지 (400 에러)"""
        data = {
            'file': (sample_image_large, 'large.jpg', 'image/jpeg')
        }
        
        response = client.post(
            '/predict',
            data=data,
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 400
        result = response.get_json()
        
        assert result['success'] is False


class TestErrorHandlers:
    """에러 핸들러 테스트"""
    
    @pytest.mark.api
    def test_404_not_found(self, client):
        """404 Not Found 에러"""
        response = client.get('/nonexistent-endpoint')
        
        assert response.status_code == 404
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_type'] == 'NotFoundError'
    
    @pytest.mark.api
    def test_405_method_not_allowed(self, client):
        """405 Method Not Allowed 에러"""
        # /predict는 POST만 허용
        response = client.get('/predict')
        
        assert response.status_code == 405
        data = response.get_json()
        
        assert data['success'] is False
        assert data['error_type'] == 'MethodNotAllowedError'


class TestCORSHeaders:
    """CORS 헤더 테스트"""
    
    @pytest.mark.api
    def test_cors_headers_present(self, client):
        """CORS 헤더 존재 확인"""
        response = client.get('/')
        
        # CORS 헤더가 설정되어 있어야 함
        assert 'Access-Control-Allow-Origin' in response.headers
