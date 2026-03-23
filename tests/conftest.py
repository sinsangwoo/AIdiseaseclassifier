"""
Pytest 설정 및 공통 Fixtures
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
    return TestingConfig()


@pytest.fixture(scope='function')
def app(test_config):
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    yield app


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    return app.test_cli_runner()


@pytest.fixture(scope='session')
def sample_image_bytes():
    img = Image.new('RGB', (224, 224), color='red')
    buf = BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf.read()


@pytest.fixture(scope='session')
def sample_png_bytes():
    img = Image.new('RGB', (224, 224), color='blue')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.read()


@pytest.fixture(scope='session')
def large_image_bytes():
    img = Image.new('RGB', (4096, 4096), color='green')
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=95)
    buf.seek(0)
    return buf.read()


@pytest.fixture(scope='session')
def small_image_bytes():
    img = Image.new('RGB', (10, 10), color='yellow')
    buf = BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf.read()


@pytest.fixture(scope='session')
def corrupted_image_bytes():
    return b'This is not an image file'


@pytest.fixture(scope='session')
def grayscale_image_bytes():
    img = Image.new('L', (224, 224), color=128)
    buf = BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf.read()


@pytest.fixture(scope='session')
def rgba_image_bytes():
    img = Image.new('RGBA', (224, 224), color=(255, 0, 0, 128))
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.read()


@pytest.fixture(scope='session')
def sample_numpy_array():
    return np.random.rand(1, 224, 224, 3).astype(np.float32)


@pytest.fixture(scope='function')
def sample_image_valid():
    """
    API 테스트용 유효한 이미지 BytesIO.
    scope='function': 닫힌 파일 재사용 오류 방지.
    """
    img = Image.new('RGB', (224, 224), color=(128, 128, 128))
    buf = BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf


@pytest.fixture(scope='function')
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope='function')
def temp_image_file(temp_dir, sample_image_bytes):
    path = temp_dir / 'test_image.jpg'
    path.write_bytes(sample_image_bytes)
    return path


@pytest.fixture(scope='session')
def mock_model_path(tmp_path_factory):
    d = tmp_path_factory.mktemp('models')
    return str(d / 'mock_model.onnx')


@pytest.fixture(scope='session')
def mock_labels_path(tmp_path_factory):
    d = tmp_path_factory.mktemp('labels')
    p = d / 'labels.txt'
    p.write_text('0 Normal\n1 Pneumonia\n2 COVID-19\n', encoding='utf-8')
    return str(p)


@pytest.fixture(autouse=True)
def reset_singletons():
    from models.predictor import ModelPredictor
    ModelPredictor._instance = None
    ModelPredictor._is_initialized = False
    yield
    ModelPredictor._instance = None
    ModelPredictor._is_initialized = False


def pytest_configure(config):
    config.addinivalue_line('markers', 'unit: Unit tests')
    config.addinivalue_line('markers', 'integration: Integration tests')
    config.addinivalue_line('markers', 'slow: Slow tests')
    config.addinivalue_line('markers', 'api: API integration tests')
    config.addinivalue_line('markers', 'frontend: Frontend JS contract tests')  # 프론트엔드 마커 등록


def pytest_collection_modifyitems(config, items):
    for item in items:
        if 'integration' in item.keywords:
            item.add_marker(pytest.mark.slow)
