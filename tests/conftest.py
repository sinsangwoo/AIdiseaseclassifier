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
def sample_image_valid():
    """
    API 테스트용 유효한 이미지 BytesIO 객체.

    scope='function' 으로 각 테스트마다 새로운 BytesIO 인스턴스를 생성합니다.
    scope='session' 으로 설정하면 첫 번째 테스트가 스트림을 소비한 뒤
    닫힌 상태로 재사용되어 'ValueError: I/O operation on closed file' 이 발생합니다.
    """
    img = Image.new('RGB', (224, 224), color=(128, 128, 128))
    buf = BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf


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
    return str(model_path)


@pytest.fixture(scope='session')
def mock_labels_path(tmp_path_factory):
    """
    Mock 레이블 파일 생성
    """
    labels_dir = tmp_path_factory.mktemp("labels")
    labels_path = labels_dir / "labels.txt"
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
    from models.predictor import ModelPredictor
    ModelPredictor._instance = None
    ModelPredictor._is_initialized = False
    yield
    ModelPredictor._instance = None
    ModelPredictor._is_initialized = False


# Pytest 플러그인 설정
def pytest_configure(config):
    """Pytest 설정"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "api: API integration tests")


def pytest_collection_modifyitems(config, items):
    """테스트 아이템 수정"""
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(pytest.mark.slow)
