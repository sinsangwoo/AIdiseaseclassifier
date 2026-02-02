"""
유틸리티 함수 단위 테스트

validators, responses, exceptions 등을 테스트합니다.
"""

import pytest
import io
from werkzeug.datastructures import FileStorage
from PIL import Image


class TestValidators:
    """파일 검증 함수 테스트"""
    
    @pytest.mark.unit
    @pytest.mark.validation
    def test_allowed_file_with_valid_extensions(self):
        """allowed_file - 유효한 확장자"""
        from backend.utils.validators import allowed_file
        
        assert allowed_file('image.jpg', {'jpg', 'png'}) is True
        assert allowed_file('photo.jpeg', {'jpg', 'jpeg', 'png'}) is True
        assert allowed_file('picture.png', {'png'}) is True
    
    @pytest.mark.unit
    @pytest.mark.validation
    def test_allowed_file_with_invalid_extensions(self):
        """allowed_file - 유효하지 않은 확장자"""
        from backend.utils.validators import allowed_file
        
        assert allowed_file('document.txt', {'jpg', 'png'}) is False
        assert allowed_file('script.py', {'jpg', 'png'}) is False
        assert allowed_file('noextension', {'jpg', 'png'}) is False
    
    @pytest.mark.unit
    @pytest.mark.validation
    def test_allowed_file_case_insensitive(self):
        """allowed_file - 대소문자 구분 없음"""
        from backend.utils.validators import allowed_file
        
        assert allowed_file('IMAGE.JPG', {'jpg', 'png'}) is True
        assert allowed_file('Photo.PNG', {'jpg', 'png'}) is True
        assert allowed_file('picture.JpEg', {'jpg', 'jpeg', 'png'}) is True
    
    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_file_success(self):
        """validate_file - 유효한 파일"""
        from backend.utils.validators import validate_file
        
        # 작은 JPEG 이미지 생성
        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        file = FileStorage(
            stream=img_bytes,
            filename='test.jpg',
            content_type='image/jpeg'
        )
        
        is_valid, error_msg = validate_file(
            file,
            allowed_extensions={'jpg', 'jpeg', 'png'},
            max_size=10 * 1024 * 1024  # 10MB
        )
        
        assert is_valid is True
        assert error_msg is None
    
    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_file_empty_filename(self):
        """validate_file - 파일명 없음"""
        from backend.utils.validators import validate_file
        
        file = FileStorage(
            stream=io.BytesIO(b"test"),
            filename='',
            content_type='image/jpeg'
        )
        
        is_valid, error_msg = validate_file(file, {'jpg', 'png'})
        
        assert is_valid is False
        assert '파일명이 없습니다' in error_msg
    
    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_file_invalid_extension(self):
        """validate_file - 유효하지 않은 확장자"""
        from backend.utils.validators import validate_file
        
        file = FileStorage(
            stream=io.BytesIO(b"test"),
            filename='document.txt',
            content_type='text/plain'
        )
        
        is_valid, error_msg = validate_file(file, {'jpg', 'png'})
        
        assert is_valid is False
        assert '허용되지 않는 파일 형식' in error_msg


class TestResponses:
    """응답 헬퍼 함수 테스트"""
    
    @pytest.mark.unit
    def test_success_response(self):
        """success_response - 성공 응답"""
        from backend.utils.responses import success_response
        
        response = success_response(data={'key': 'value'}, message='성공')
        
        assert response['success'] is True
        assert response['data'] == {'key': 'value'}
        assert response['message'] == '성공'
    
    @pytest.mark.unit
    def test_error_response(self):
        """error_response - 에러 응답"""
        from backend.utils.responses import error_response
        
        response, status_code = error_response(
            message='에러 발생',
            status_code=400,
            error_type='TestError'
        )
        
        assert response['success'] is False
        assert response['error'] == '에러 발생'
        assert response['error_type'] == 'TestError'
        assert status_code == 400
    
    @pytest.mark.unit
    def test_prediction_response(self):
        """prediction_response - 예측 응답"""
        from backend.utils.responses import prediction_response
        
        predictions = [
            {'className': '정상', 'probability': 0.8},
            {'className': '폐렴', 'probability': 0.2}
        ]
        
        response = prediction_response(
            predictions=predictions,
            processing_time=123.45,
            image_size=(224, 224)
        )
        
        assert response['success'] is True
        assert response['predictions'] == predictions
        assert 'metadata' in response
        assert response['metadata']['processing_time_ms'] == 123.45


class TestExceptions:
    """커스텀 예외 테스트"""
    
    @pytest.mark.unit
    def test_ai_classifier_exception(self):
        """AIClassifierException - 기본 예외"""
        from backend.utils.exceptions import AIClassifierException
        
        exc = AIClassifierException("테스트 에러", error_code="TEST_ERROR")
        
        assert str(exc) == "테스트 에러"
        assert exc.message == "테스트 에러"
        assert exc.error_code == "TEST_ERROR"
    
    @pytest.mark.unit
    def test_model_not_loaded_error(self):
        """ModelNotLoadedError"""
        from backend.utils.exceptions import ModelNotLoadedError
        
        exc = ModelNotLoadedError()
        
        assert "모델이 로드되지 않았습니다" in exc.message
        assert exc.error_code == "MODEL_NOT_LOADED"
    
    @pytest.mark.unit
    def test_invalid_image_error(self):
        """InvalidImageError"""
        from backend.utils.exceptions import InvalidImageError
        
        exc = InvalidImageError("잘못된 이미지")
        
        assert exc.message == "잘못된 이미지"
        assert exc.error_code == "INVALID_IMAGE"
    
    @pytest.mark.unit
    def test_file_validation_error(self):
        """FileValidationError"""
        from backend.utils.exceptions import FileValidationError
        
        exc = FileValidationError("파일 검증 실패")
        
        assert exc.message == "파일 검증 실패"
        assert exc.error_code == "FILE_VALIDATION_ERROR"


class TestImageValidator:
    """고급 이미지 검증기 테스트"""
    
    @pytest.mark.unit
    @pytest.mark.validation
    @pytest.mark.security
    def test_validate_magic_bytes_jpeg(self):
        """매직 바이트 검증 - JPEG"""
        from backend.utils.advanced_validators import ImageValidator
        
        validator = ImageValidator()
        
        # 유효한 JPEG 생성
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        is_valid, img_format = validator.validate_magic_bytes(img_bytes.read())
        
        assert is_valid is True
        assert img_format == 'jpeg'
    
    @pytest.mark.unit
    @pytest.mark.validation
    @pytest.mark.security
    def test_validate_magic_bytes_text_file(self):
        """매직 바이트 검증 - 텍스트 파일 (실패)"""
        from backend.utils.advanced_validators import ImageValidator
        
        validator = ImageValidator()
        
        # 텍스트 파일
        text_bytes = b"This is not an image"
        
        is_valid, img_format = validator.validate_magic_bytes(text_bytes)
        
        assert is_valid is False
    
    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_image_dimensions_valid(self):
        """이미지 크기 검증 - 유효"""
        from backend.utils.advanced_validators import ImageValidator
        
        validator = ImageValidator(
            min_width=32,
            min_height=32,
            max_width=4096,
            max_height=4096
        )
        
        # 200x200 이미지 (유효)
        img = Image.new('RGB', (200, 200), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        is_valid, error_msg = validator.validate_image_dimensions(img_bytes.read())
        
        assert is_valid is True
        assert error_msg is None
    
    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_image_dimensions_too_small(self):
        """이미지 크기 검증 - 너무 작음"""
        from backend.utils.advanced_validators import ImageValidator
        
        validator = ImageValidator(min_width=32, min_height=32)
        
        # 20x20 이미지 (너무 작음)
        img = Image.new('RGB', (20, 20), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        is_valid, error_msg = validator.validate_image_dimensions(img_bytes.read())
        
        assert is_valid is False
        assert '너무 작습니다' in error_msg
    
    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_image_dimensions_wrong_aspect_ratio(self):
        """이미지 크기 검증 - 비정상 비율"""
        from backend.utils.advanced_validators import ImageValidator
        
        validator = ImageValidator(max_aspect_ratio=10.0)
        
        # 1000x50 이미지 (비율 20:1, 최소 크기는 만족)
        img = Image.new('RGB', (1000, 50), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        is_valid, error_msg = validator.validate_image_dimensions(img_bytes.read())
        
        assert is_valid is False
        assert '가로세로 비율' in error_msg
