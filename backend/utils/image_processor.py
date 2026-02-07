"""
PyTorch 이미지 전처리 유틸

ResNet50에 맞는 전처리(224x224 Resize, ToTensor, Normalize)를 제공합니다.
"""

import io
from typing import Tuple

import torch
from PIL import Image
from torchvision import transforms as T


# ImageNet 정규화 상수
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def _load_rgb(image_bytes: bytes) -> Image.Image:
    """
    이미지 바이트를 RGB PIL 이미지로 로드
    """
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def build_torch_transform(target_size: Tuple[int, int] = (224, 224)) -> T.Compose:
    """
    ResNet50용 전처리 파이프라인 생성
    """
    return T.Compose([
        T.Resize(target_size, interpolation=Image.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def preprocess_bytes_to_tensor(image_bytes: bytes, target_size: Tuple[int, int] = (224, 224)) -> torch.Tensor:
    """
    이미지 바이트를 ResNet50 입력 텐서로 변환
    반환 텐서 shape: [1, 3, H, W]
    """
    img = _load_rgb(image_bytes)
    transform = build_torch_transform(target_size)
    tensor = transform(img)  # [3, H, W]
    return tensor.unsqueeze(0)  # [1, 3, H, W]
