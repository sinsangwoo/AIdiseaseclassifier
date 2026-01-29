"""
Pytest 설정 및 공통 Fixtures

모든 테스트에서 사용할 공통 설정과 픽스처를 정의합니다.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from io import BytesIO
from PIL import Image
import numpy as np

# 백엔드 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app import create_app
from config import TestingConfig


@pytest.fixture(scope='session')
def test_config():
    """테스트 설정 반환"""
    return TestingConfig()


@pytest.fixture(scope='function')
def app(test_config):
    """Flask 앱 인스턴스 (각 테스트마다 새로 생성)"""
    app = create_app('testing')
    
    # 테스트 컨텍스트 설정
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    yield app


@pytest.fixture(scope='function')
def client(app):
    """Flask 테스트 클라이언트"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Flask CLI 러너"""
    return app.test_cli_runner()


@pytest.fixture(scope='session')
def sample_image_bytes():
    """
    샘플 이미지 바이트 생성 (RGB, 224x224)
    """
    img = Image.new('RGB', (224, 224), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes.read()


@pytest.fixture(scope='session')
def sample_png_bytes():
    """
    샘플 PNG 이미지 바이트 생성
    """
    img = Image.new('RGB', (224, 224), color='blue')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.read()


@pytest.fixture(scope='session')
def large_image_bytes():
    """
    큰 이미지 바이트 생성 (4096x4096)
    """
    img = Image.new('RGB', (4096, 4096), color='green')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG', quality=95)
    img_bytes.seek(0)
    return img_bytes.read()


@pytest.fixture(scope='session')
def small_image_bytes():
    """
    작은 이미지 바이트 생성 (10x10)
    """
    img = Image.new('RGB', (10, 10), color='yellow')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes.read()


@pytest.fixture(scope='session')
def corrupted_image_bytes():
    """
    손상된 이미지 바이트
    """
    return b'This is not an image file'


@pytest.fixture(scope='session')
def grayscale_image_bytes():
    """
    그레이스케일 이미지 바이트
    """
    img = Image.new('L', (224, 224), color=128)
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes.read()


@pytest.fixture(scope='session')
def rgba_image_bytes():
    """
    RGBA 이미지 바이트 (투명도 포함)
    """
    img = Image.new('RGBA', (224, 224), color=(255, 0, 0, 128))
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.read()


@pytest.fixture(scope='session')
def sample_numpy_array():
    """
    샘플 NumPy 배열 (모델 입력 형식)
    """
    return np.random.rand(1, 224, 224, 3).astype(np.float32)


@pytest.fixture(scope='function')
def temp_dir():
    """
    임시 디렉토리 생성 (테스트 후 자동 삭제)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope='function')
def temp_image_file(temp_dir, sample_image_bytes):
    """
    임시 이미지 파일 생성
    """
    image_path = temp_dir / 'test_image.jpg'
    image_path.write_bytes(sample_image_bytes)
    return image_path


@pytest.fixture(scope='session')
def mock_model_path(tmp_path_factory):
    """
    Mock ONNX 모델 파일 경로
    """
    model_dir = tmp_path_factory.mktemp("models")
    model_path = model_dir / "mock_model.onnx"
    # 실제 모델 파일은 생성하지 않음 (로딩 테스트용)
    return str(model_path)


@pytest.fixture(scope='session')
def mock_labels_path(tmp_path_factory):
    """
    Mock 레이블 파일 생성
    """
    labels_dir = tmp_path_factory.mktemp("labels")
    labels_path = labels_dir / "labels.txt"
    
    # 샘플 레이블 작성
    labels_content = """0 Normal
1 Pneumonia
2 COVID-19
"""
    labels_path.write_text(labels_content, encoding='utf-8')
    return str(labels_path)


@pytest.fixture(autouse=True)
def reset_singletons():
    """
    각 테스트 전에 싱글톤 인스턴스 리셋
    """
    # ModelPredictor 싱글톤 리셋
    from models.predictor import ModelPredictor
    ModelPredictor._instance = None
    ModelPredictor._is_initialized = False
    
    yield
    
    # 테스트 후 정리
    ModelPredictor._instance = None
    ModelPredictor._is_initialized = False


# Pytest 플러그인 설정
def pytest_configure(config):
    """Pytest 설정"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")


def pytest_collection_modifyitems(config, items):
    """테스트 아이템 수정"""
    for item in items:
        # 통합 테스트는 느림으로 표시
        if "integration" in item.keywords:
            item.add_marker(pytest.mark.slow)
