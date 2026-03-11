# AI Disease Classifier

흉부 X-ray 기반 폐렴 진단 AI — **Grad-CAM XAI 히트맵 시각화** 탑재

## 🌐 https://sinsangwoo.github.io/AIdiseaseclassifier/

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.1+](https://img.shields.io/badge/flask-3.1+-green.svg)](https://flask.palletsprojects.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **의료적 고지**: 이 시스템은 **교육 및 연구 목적**으로 개발된 프로토타입입니다.  
> 제공되는 분석 결과는 의학적 진단을 대체할 수 없으며, 최종 판단은 반드시 전문 의료진이 내려야 합니다.  
> FDA / CE 인증을 받지 않은 소프트웨어입니다.

---

## 📋 개요

**v6.0.0** — 기존 ONNX 기반 확률 수치 출력(v5)에서 **Grad-CAM XAI(설명 가능한 AI)** 히트맵 시각화로 업그레이드된 버전입니다.

AI가 폐렴을 판단할 때 **흉부 X-ray의 어느 부위를 주목했는지** 색상 히트맵으로 표시하여, 의사가 AI의 판단 근거를 직관적으로 확인할 수 있습니다.

### v5 → v6 주요 변화

| 항목 | v5.0.0 (이전) | v6.0.0 (현재) |
|------|--------------|--------------|
| 추론 엔진 | ONNX Runtime | ONNX + PyTorch 병렬 운영 |
| 모델 구조 | MobileNetV3-Small | MobileNetV3 (ONNX) + DenseNet-121 (PyTorch) |
| 결과 출력 | 확률 수치만 | 확률 수치 + **Grad-CAM 히트맵** |
| XAI | ❌ 없음 | ✅ 3탭 히트맵 뷰어 (오버레이·히트맵·비교) |
| 신뢰도 | ❌ 없음 | ✅ HIGH / MEDIUM / LOW 등급 |
| 안전장치 | 기본 파일 검증 | + 이미지 크기 검증, 법적 고지, LOW 신뢰도 차단 |

---

## 🔬 Grad-CAM이란?

**Grad-CAM (Gradient-weighted Class Activation Mapping)** — AI가 특정 판단을 내릴 때 이미지의 어느 부위에 집중했는지를 색상으로 시각화하는 기법입니다.

```
흉부 X-ray 입력
      ↓
DenseNet-121 추론 (PyTorch)
      ↓
마지막 합성곱 레이어 gradient 추출
      ↓
채널별 가중 평균 → CAM 생성 → ReLU → 정규화
      ↓
JET 컬러맵 적용 (파랑=낮음 → 빨강=높음)
      ↓
원본 이미지 위 오버레이
```

참고 논문: Selvaraju et al., *"Grad-CAM: Visual Explanations from Deep Networks via Gradient-based Localization"*, ICCV 2017

---

## 🏗️ 아키텍처

```
AIdiseaseclassifier/
├── backend/
│   ├── app.py                        # Flask 서버 + PyTorchPredictor 초기화
│   ├── config.py
│   ├── models/
│   │   ├── model_definition.py       # ✨ DenseNet-121 PyTorch 모델 정의
│   │   ├── model_weights.pth         # (파인튜닝 후 배치)
│   │   └── labels.txt
│   ├── services/
│   │   ├── gradcam.py                # ✨ Grad-CAM 엔진
│   │   ├── heatmap_renderer.py       # ✨ 히트맵 → 이미지 변환
│   │   ├── pytorch_predictor.py      # ✨ PyTorch 예측 + Grad-CAM 통합
│   │   └── image_processor.py
│   └── routes/
│       └── predict.py                # /predict 엔드포인트
├── frontend/
│   ├── index.html
│   ├── js/
│   │   ├── app.js
│   │   ├── ui/
│   │   │   ├── uiController.js
│   │   │   └── gradcam_viewer.js     # ✨ 히트맵 뷰어 컴포넌트
│   │   └── api/
│   └── css/
│       └── components/
│           └── heatmap.css           # ✨ 히트맵 뷰어 스타일
├── tests/
│   ├── test_gradcam.py               # ✨ Grad-CAM 단위 테스트
│   └── test_phase_e.py               # ✨ Phase E 통합 테스트
├── Dockerfile
└── requirements.txt
```

---

## 🛠️ 기술 스택

**Backend:** Flask 3.1, ONNX Runtime 1.19, PyTorch 2.0+, torchvision, OpenCV, Pillow, NumPy  
**Frontend:** Vanilla JavaScript (ES6 Module), HTML5, CSS3  
**DevOps:** Docker, Prometheus, GitHub Actions CI  
**Reports:** html2canvas, jsPDF

---

## ✨ 주요 기능

### Grad-CAM XAI 시각화
- **3탭 히트맵 뷰어**: 오버레이 / 히트맵 단독 / 원본 vs 히트맵 나란히 비교
- **신뢰도 배지**: HIGH(초록) · MEDIUM(노랑) · LOW(빨강) 자동 등급화
- **주목도 스코어 바**: attention_score 애니메이션 바 표시
- **범례 그라디언트**: 파랑(낮은 주목) → 빨강(높은 주목) 색상 범례

### 안전장치 (Phase E)
- **LOW 신뢰도 차단**: 예측 확률 < 50% 시 히트맵 이미지 생성 억제
- **이미지 크기 검증**: 32×32px 미만 입력 거부
- **법적 고지 자동 삽입**: 모든 히트맵 패널에 면책 배너 + 워터마크
- **API 고지 필드**: `metadata.xai_disclaimer` 문구 자동 포함

### 기존 기능 유지
- **ONNX 추론 병렬 운영**: PyTorch 미설치 시에도 ONNX 예측 정상 반환
- **LRU 캐싱**: 동일 이미지 반복 요청 90% 이상 속도 향상
- **보안**: 매직 바이트 검증, XSS 방어, CORS 화이트리스트
- **모니터링**: Prometheus 25+ 메트릭
- **리포트**: PNG / PDF 진단 리포트 저장

---

## 🚀 빠른 시작

### 로컬 개발

```bash
git clone https://github.com/sinsangwoo/AIdiseaseclassifier.git
cd AIdiseaseclassifier

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt

python backend/app.py
```

Grad-CAM 기능을 사용하려면 PyTorch가 필요합니다:

```bash
pip install torch torchvision
```

> PyTorch 미설치 시에도 서버는 정상 기동되며, ONNX 예측 결과만 반환됩니다 (`gradcam.available: false`).

### Docker

```bash
docker-compose up -d --build
```

---

## 📡 API

### `POST /predict`

흉부 X-ray 이미지를 업로드하면 예측 결과와 Grad-CAM 히트맵을 반환합니다.

**Request**
```
Content-Type: multipart/form-data
Body: file=<image.jpg|png>
```

**Response**
```json
{
  "success": true,
  "predictions": [
    { "className": "폐렴", "probability": 0.87 },
    { "className": "정상", "probability": 0.13 }
  ],
  "metadata": {
    "processing_time_ms": 312.5,
    "onnx_time_ms": 65.2,
    "gradcam_time_ms": 247.3,
    "xai_disclaimer": "이 히트맵은 AI 모델의 내부 연산을 시각화한 것으로, 의학적 진단을 대체하지 않습니다..."
  },
  "gradcam": {
    "available": true,
    "heatmap_overlay_base64": "iVBOR...",
    "heatmap_only_base64": "iVBOR...",
    "target_class": "폐렴",
    "target_class_index": 1,
    "attention_score": 0.94,
    "reliability": "HIGH",
    "low_confidence": false,
    "gradcam_time_ms": 247.3,
    "error": null
  }
}
```

### 기타 엔드포인트

| Endpoint | Method | 설명 |
|----------|--------|------|
| `/predict` | POST | 이미지 예측 + Grad-CAM |
| `/health` | GET | Liveness probe |
| `/metrics` | GET | Prometheus 메트릭 |

---

## 🧪 테스트

```bash
pytest tests/ -v
```

| 테스트 파일 | 범위 |
|------------|------|
| `tests/test_api.py` | Flask 엔드포인트 통합 테스트 |
| `tests/test_gradcam.py` | Grad-CAM 엔진 단위 테스트 (20개) |
| `tests/test_phase_e.py` | Phase E 안전장치 통합 테스트 (7개) |

PyTorch 미설치 환경에서는 `@requires_torch` 테스트가 자동으로 skip됩니다.

---

## 📈 성능

| 항목 | 수치 |
|------|------|
| ONNX 추론 시간 | < 100ms (CPU) |
| Grad-CAM 생성 시간 | ~200–500ms (CPU), ~50ms (GPU) |
| 메모리 사용량 | < 300MB (ONNX 단독) |
| 캐시 히트율 | > 85% (반복 요청) |

---

## 🗺️ 개발 히스토리

| 버전 | 주요 변경 |
|------|---------|
| v1–v4 | 초기 구조, 에러 핸들링, 보안 강화, 모니터링 |
| **v5.0.0** | ONNX 최적화, 메모리 85% 절감, LRU 캐싱 |
| **v6.0.0** | Grad-CAM XAI 히트맵 시각화 전면 도입 |

---

## 🤝 기여

1. 저장소 Fork
2. 기능 브랜치 생성 (`git checkout -b feature/your-feature`)
3. 변경 사항 커밋 (`git commit -m 'feat: Add your feature'`)
4. 브랜치 Push (`git push origin feature/your-feature`)
5. Pull Request 오픈

---

## 📄 라이선스

MIT License — [LICENSE](LICENSE) 참조

---

**개발자:** 신상우 (30814)  
아주대학교 소프트웨어학과
