"""
ONNX 모델 예측 모듈

싱글톤 패턴을 사용하여 모델을 한 번만 로드하고 재사용합니다.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import onnxruntime as rt


logger = logging.getLogger(__name__)


class ModelPredictor:
    """
    ONNX 모델 예측 클래스 (싱글톤)
    
    모델과 레이블을 한 번만 로드하여 메모리 효율성을 높입니다.
    """
    
    _instance = None
    _is_initialized = False
    
    def __new__(cls, model_path: str = None, labels_path: str = None):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_path: str = None, labels_path: str = None):
        """
        모델 예측기 초기화
        
        Args:
            model_path (str): ONNX 모델 파일 경로
            labels_path (str): 레이블 파일 경로
        """
        # 이미 초기화된 경우 스킵
        if self._is_initialized:
            return
        
        self.model_path = model_path
        self.labels_path = labels_path
        
        self.session = None
        self.class_names = []
        self.input_name = None
        self.output_name = None
        
        if model_path and labels_path:
            self.load_model()
    
    def load_model(self):
        """
        ONNX 모델과 레이블 파일 로드
        
        Raises:
            FileNotFoundError: 모델 또는 레이블 파일이 존재하지 않을 때
            RuntimeError: 모델 로딩 중 오류 발생 시
        """
        try:
            # 파일 존재 확인
            if not Path(self.model_path).exists():
                raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {self.model_path}")
            
            if not Path(self.labels_path).exists():
                raise FileNotFoundError(f"레이블 파일을 찾을 수 없습니다: {self.labels_path}")
            
            # ONNX 모델 로드
            logger.info(f"ONNX 모델 로드 중: {self.model_path}")
            self.session = rt.InferenceSession(self.model_path)
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            logger.info("모델 로드 성공")
            
            # 레이블 파일 로드
            logger.info(f"레이블 파일 로드 중: {self.labels_path}")
            with open(self.labels_path, 'r', encoding='utf-8') as f:
                self.class_names = [
                    line.strip().split(' ', 1)[1] 
                    for line in f.readlines() 
                    if line.strip()
                ]
            logger.info(f"레이블 로드 성공: {len(self.class_names)}개 클래스")
            
            self._is_initialized = True
            
        except FileNotFoundError as e:
            logger.error(f"파일을 찾을 수 없습니다: {e}")
            raise
        except Exception as e:
            logger.error(f"모델 로딩 중 오류 발생: {e}")
            raise RuntimeError(f"모델 로딩 실패: {e}")
    
    def predict(self, image_array: np.ndarray) -> List[Dict[str, Any]]:
        """
        이미지 배열에 대한 예측 수행
        
        Args:
            image_array (np.ndarray): 전처리된 이미지 배열 (shape: [1, H, W, 3])
        
        Returns:
            List[Dict[str, Any]]: 예측 결과 리스트
                [{'className': str, 'probability': float}, ...]
        
        Raises:
            RuntimeError: 모델이 로드되지 않았거나 예측 중 오류 발생 시
        """
        if not self.is_ready():
            raise RuntimeError("모델이 아직 로드되지 않았습니다. load_model()을 먼저 호출하세요.")
        
        try:
            # ONNX 모델 예측
            predictions = self.session.run(
                [self.output_name], 
                {self.input_name: image_array}
            )[0]
            
            # 결과 포맷팅
            results = []
            for i, probability in enumerate(predictions[0]):
                results.append({
                    'className': self.class_names[i],
                    'probability': float(probability)
                })
            
            # 확률 높은 순으로 정렬
            results.sort(key=lambda x: x['probability'], reverse=True)
            
            logger.info(f"예측 완료: 상위 클래스 = {results[0]['className']} ({results[0]['probability']:.4f})")
            
            return results
            
        except Exception as e:
            logger.error(f"예측 중 오류 발생: {e}")
            raise RuntimeError(f"예측 실패: {e}")
    
    def is_ready(self) -> bool:
        """
        모델이 예측 가능한 상태인지 확인
        
        Returns:
            bool: 모델이 로드되어 사용 가능하면 True
        """
        return (
            self.session is not None and 
            self.class_names and 
            self.input_name is not None and 
            self.output_name is not None
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        모델 정보 반환
        
        Returns:
            Dict[str, Any]: 모델 메타데이터
        """
        if not self.is_ready():
            return {'status': 'not_loaded'}
        
        return {
            'status': 'ready',
            'model_path': self.model_path,
            'num_classes': len(self.class_names),
            'classes': self.class_names,
            'input_name': self.input_name,
            'output_name': self.output_name
        }
