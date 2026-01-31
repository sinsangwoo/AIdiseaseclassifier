"""
Pytest 설정 파일

테스트 환경 초기화, fixture 정의, 설정 관리
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope='session')
def app():
    """Flask 애플리케이션 fixture (전체 세션)"""
    from backend.app import create_app
    
    app = create_app('testing')
    app.config['TESTING'] = True
    
    yield app


@pytest.fixture(scope='function')
def client(app):
    """Flask 테스트 클라이언트 fixture (각 테스트마다)"""
    return app.test_client()


@pytest.fixture(scope='session')
def sample_image_valid():
    """유효한 샘플 이미지 (JPEG)"""
    from PIL import Image
    import io
    
    # 224x224 RGB 이미지 생성
    img = Image.new('RGB', (224, 224), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes


@pytest.fixture(scope='session')
def sample_image_png():
    """유효한 샘플 이미지 (PNG)"""
    from PIL import Image
    import io
    
    # 300x300 RGB 이미지 생성
    img = Image.new('RGB', (300, 300), color='green')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes


@pytest.fixture(scope='session')
def sample_image_small():
    """너무 작은 이미지 (검증 실패용)"""
    from PIL import Image
    import io
    
    # 20x20 이미지 (최소 크기 32x32 미만)
    img = Image.new('RGB', (20, 20), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes


@pytest.fixture(scope='session')
def sample_image_large():
    """너무 큰 이미지 (검증 실패용)"""
    from PIL import Image
    import io
    
    # 5000x5000 이미지 (최대 크기 4096x4096 초과)
    img = Image.new('RGB', (5000, 5000), color='yellow')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes


@pytest.fixture(scope='session')
def sample_image_wrong_aspect():
    """비정상적인 가로세로 비율 이미지"""
    from PIL import Image
    import io
    
    # 1000x50 이미지 (비율 20:1 > 최대 10:1)
    img = Image.new('RGB', (1000, 50), color='purple')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes


@pytest.fixture(scope='session')
def sample_text_file():
    """텍스트 파일 (이미지가 아님)"""
    import io
    
    content = b"This is a text file, not an image!"
    return io.BytesIO(content)


@pytest.fixture(scope='session')
def mock_model_predictor():
    """모의 모델 Predictor"""
    from backend.models import ModelPredictor
    from unittest.mock import Mock
    
    predictor = Mock(spec=ModelPredictor)
    predictor.is_ready.return_value = True
    predictor.predict.return_value = [
        {'className': '정상', 'probability': 0.85},
        {'className': '폐렴', 'probability': 0.10},
        {'className': '결핵', 'probability': 0.05}
    ]
    predictor.get_model_info.return_value = {
        'model_path': 'test_model.onnx',
        'labels_path': 'test_labels.txt',
        'num_classes': 3,
        'class_names': ['정상', '폐렴', '결핵']
    }
    
    return predictor


# Pytest 설정
def pytest_configure(config):
    """Pytest 전역 설정"""
    config.addinivalue_line(
        "markers", "unit: 단위 테스트 (빠름)"
    )
    config.addinivalue_line(
        "markers", "integration: 통합 테스트 (느림)"
    )
    config.addinivalue_line(
        "markers", "api: API 엔드포인트 테스트"
    )
    config.addinivalue_line(
        "markers", "validation: 입력 검증 테스트"
    )
    config.addinivalue_line(
        "markers", "security: 보안 테스트"
    )
