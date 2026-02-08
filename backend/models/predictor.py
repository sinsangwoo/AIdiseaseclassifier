"""
ONNX Runtime 기반 예측 모듈

PyTorch 의존성을 제거하고 ONNX Runtime을 사용하여 메모리 효율적인 추론을 수행합니다.
"""

from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import onnxruntime as ort

from backend.utils import (
    LoggerMixin,
    ModelNotLoadedError,
    ModelLoadError,
    PredictionError,
    log_exception
)

class ModelPredictor(LoggerMixin):
    """
    ONNX Runtime 예측 클래스 (싱글톤)
    
    ONNX 모델을 로드하여 CPU에서 효율적으로 추론합니다.
    Render Free Tier (512MB RAM) 환경에 최적화되어 있습니다.
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
        self.input_name = None
        self.output_name = None
        self.class_names = []
        
        if model_path and labels_path:
            self.load_model()
    
    def load_model(self):
        """
        ONNX 모델과 레이블 파일 로드
        
        Raises:
            ModelLoadError: 모델 또는 레이블 파일 로딩 실패 시
        """
        try:
            # 1. 레이블 파일 로드
            if not Path(self.labels_path).exists():
                raise FileNotFoundError(f"레이블 파일을 찾을 수 없습니다: {self.labels_path}")
            
            self.logger.info(f"레이블 파일 로드 시작: {self.labels_path}")
            with open(self.labels_path, 'r', encoding='utf-8') as f:
                self.class_names = [
                    line.strip().split(' ', 1)[1]
                    for line in f.readlines()
                    if line.strip()
                ]
            num_classes = len(self.class_names)
            self.logger.info(f"레이블 로드 성공: {num_classes}개 클래스 - {self.class_names}")
            
            # 2. ONNX 모델 로드
            if not Path(self.model_path).exists():
                raise FileNotFoundError(f"ONNX 모델 파일을 찾을 수 없습니다: {self.model_path}")
            
            self.logger.info(f"ONNX Runtime 세션 초기화: {self.model_path}")
            
            # CPU Provider 명시 (Render Free Tier 호환)
            providers = ['CPUExecutionProvider']
            
            # 세션 옵션 설정 (메모리 최적화)
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = 1  # 단일 스레드 (컨테이너 환경 권장)
            sess_options.inter_op_num_threads = 1
            sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            self.session = ort.InferenceSession(
                self.model_path, 
                sess_options=sess_options, 
                providers=providers
            )
            
            # 입력/출력 노드 정보 추출
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            
            input_shape = self.session.get_inputs()[0].shape
            self.logger.info(f"모델 로드 성공 - Input: {self.input_name} {input_shape}, Output: {self.output_name}")
            
            self._is_initialized = True
            self.logger.info("모델 초기화 완료")
            
        except FileNotFoundError as e:
            log_exception(self.logger, e, "파일을 찾을 수 없음")
            raise ModelLoadError(str(e), original_error=e)
        
        except Exception as e:
            log_exception(self.logger, e, "모델 로딩 중 오류")
            raise ModelLoadError(f"모델 로딩 실패: {str(e)}", original_error=e)
    
    def predict(self, image_array: np.ndarray) -> List[Dict[str, Any]]:
        """
        이미지 배열에 대한 예측 수행
        
        Args:
            image_array (np.ndarray): 전처리된 Numpy 배열 (shape: [1, 224, 224, 3])
        
        Returns:
            List[Dict[str, Any]]: 예측 결과 리스트
                [{'className': str, 'probability': float}, ...]
        """
        if not self.is_ready():
            self.logger.error("예측 시도했으나 모델이 준비되지 않음")
            raise ModelNotLoadedError("모델이 아직 로드되지 않았습니다")
        
        try:
            self.logger.debug(f"예측 시작 (입력 shape: {image_array.shape})")
            
            # ONNX Inference
            logits = self.session.run(
                [self.output_name], 
                {self.input_name: image_array}
            )[0]
            
            # Softmax 적용 (Logits -> Probabilities)
            def softmax(x):
                e_x = np.exp(x - np.max(x))
                return e_x / e_x.sum(axis=1, keepdims=True)
            
            probs = softmax(logits)[0]
            
            # 결과 포맷팅
            results = []
            for i, probability in enumerate(probs):
                if i < len(self.class_names):
                    results.append({
                        'className': self.class_names[i],
                        'probability': float(probability)
                    })
            
            # 확률 높은 순으로 정렬
            results.sort(key=lambda x: x['probability'], reverse=True)
            
            if results:
                top_result = results[0]
                self.logger.info(
                    f"예측 완료 - 최고 확률: {top_result['className']} "
                    f"({top_result['probability']:.4f})"
                )
            
            return results
            
        except Exception as e:
            log_exception(self.logger, e, "예측 수행 중 오류")
            raise PredictionError(f"예측 실패: {str(e)}", original_error=e)
    
    def is_ready(self) -> bool:
        """모델이 예측 가능한 상태인지 확인"""
        return self.session is not None and bool(self.class_names)
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        if not self.is_ready():
            return {'status': 'not_loaded'}
        
        return {
            'status': 'ready',
            'model_path': self.model_path,
            'framework': 'onnxruntime',
            'device': 'cpu',
            'input_name': self.input_name,
            'output_name': self.output_name,
            'num_classes': len(self.class_names),
            'classes': self.class_names
        }
