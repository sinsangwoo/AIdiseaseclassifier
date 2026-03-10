"""
PyTorch 모델 정의 모듈 (Phase A - Grad-CAM 준비)

현재 ONNX 모델과 동일한 구조를 PyTorch로 정의합니다.
Grad-CAM은 PyTorch의 gradient 접근이 필요하기 때문에
ONNX 대신 이 모델을 사용합니다.

선택 근거:
  DenseNet-121은 Stanford의 CheXNet 논문(2017)에서
  폐렴 분류 표준 모델로 채택된 아키텍처입니다.
  Grad-CAM의 target layer는 features.denseblock4 입니다.
"""

try:
    import torch
    import torch.nn as nn
    import torchvision.models as models
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Grad-CAM이 훅을 걸 레이어 이름 (DenseNet-121 기준)
GRADCAM_TARGET_LAYER = "backbone.features.denseblock4"

# 모델 입력 스펙
MODEL_INPUT_SIZE = (224, 224)   # (width, height)
MODEL_INPUT_CHANNELS = 3
# 정규화 파라미터 (ImageNet 표준)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]


if TORCH_AVAILABLE:
    class PneumoniaClassifier(nn.Module):
        """
        DenseNet-121 기반 폐렴/정상 분류 모델

        구조:
          backbone  : DenseNet-121 (ImageNet 사전학습)
          classifier: Linear(1024 → num_classes)  ← 마지막 레이어만 교체

        Grad-CAM 훅 위치:
          backbone.features.denseblock4  (7×7 feature map)
        """

        def __init__(self, num_classes: int = 2):
            super().__init__()
            # pretrained=False: 가중치는 load_weights()로 별도 로드
            backbone = models.densenet121(weights=None)
            # 마지막 분류 레이어를 num_classes에 맞게 교체
            in_features = backbone.classifier.in_features  # 1024
            backbone.classifier = nn.Linear(in_features, num_classes)
            self.backbone = backbone

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            return self.backbone(x)

        @property
        def gradcam_target_layer_name(self) -> str:
            """Grad-CAM이 사용할 레이어 이름 반환"""
            return GRADCAM_TARGET_LAYER


def build_model(num_classes: int = 2, weights_path: str = None) -> "PneumoniaClassifier | None":
    """
    모델 생성 헬퍼 함수

    Args:
        num_classes  : 분류 클래스 수 (labels.txt 줄 수와 일치해야 함)
        weights_path : .pth 가중치 파일 경로 (None 이면 랜덤 초기화)

    Returns:
        PneumoniaClassifier 인스턴스, 또는 PyTorch 미설치 시 None
    """
    if not TORCH_AVAILABLE:
        return None

    model = PneumoniaClassifier(num_classes=num_classes)
    model.eval()

    if weights_path:
        import os
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"가중치 파일 없음: {weights_path}")
        state_dict = torch.load(weights_path, map_location="cpu")
        model.load_state_dict(state_dict)

    return model
