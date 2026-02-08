"""
ONNX Runtime 이미지 전처리 유틸

MobileNetV3-Small ONNX 모델에 맞는 전처리(224x224 Resize, Normalize, NHWC Layout)를 제공합니다.
"""

import io
from typing import Tuple

import numpy as np
from PIL import Image


# ImageNet 정규화 상수
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _load_rgb(image_bytes: bytes) -> Image.Image:
    """
    이미지 바이트를 RGB PIL 이미지로 로드
    """
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def preprocess_bytes_to_tensor(image_bytes: bytes, target_size: Tuple[int, int] = (224, 224)) -> np.ndarray:
    """
    이미지 바이트를 ONNX 모델 입력용 numpy 배열로 변환
    
    Processing Steps:
    1. Load as RGB
    2. Resize to target_size (Bicubic)
    3. Normalize (ImageNet statistics)
    4. Add batch dimension -> [1, 224, 224, 3] (NHWC)
    
    Returns:
        np.ndarray: 전처리된 이미지 배 (shape: [1, 224, 224, 3], dtype: float32)
    """
    img = _load_rgb(image_bytes)
    
    # 1. Resize
    img = img.resize(target_size, Image.BICUBIC)
    
    # 2. To Numpy & Normalize
    # PIL image is (H, W, C) with values 0-255
    img_array = np.array(img, dtype=np.float32) / 255.0
    
    # Normalize: (x - mean) / std
    img_array = (img_array - IMAGENET_MEAN) / IMAGENET_STD
    
    # 3. Add Batch Dimension [1, H, W, C]
    # CAUTION: ONNX attributes show input shape as ['unk__606', 224, 224, 3] -> NHWC format
    return np.expand_dims(img_array, axis=0).astype(np.float32)
