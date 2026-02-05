# 🏥 AI Disease Classifier

> **ONNX 기반 의료 이미지 분석 및 질병 진단 시스템 (Production-Ready)**

[![Tests](https://github.com/sinsangwoo/AIdiseaseclassifier/workflows/Tests/badge.svg)](https://github.com/sinsangwoo/AIdiseaseclassifier/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.1+](https://img.shields.io/badge/flask-3.1+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 프로젝트 개요

Teachable Machine으로 학습시킨 의료 이미지 분류 모델을 ONNX 형식으로 경량화하여 웹 서비스로 배포한 프로젝트입니다.

**프로젝트 정보:**
- **작성자**: 신상우 (학번: 30814)
- **소속**: 아주대학교 소프트웨어학과 1학년
- **버전**: 8.0.0-phase3-4

**핵심 기술:**
- 🔧 Backend: Flask 3.1 (Python 3.10+)
- 🧠 ML: ONNX Runtime + Teachable Machine 모델
- 🖼️ Processing: Pillow, NumPy
- 🐳 Deployment: Docker, Docker Compose
- ✅ CI/CD: GitHub Actions

---

## ✨ 주요 기능

### 🎯 Phase 3-4 완료 기능
- ✅ **모델 캐싱 시스템**: LRU 캐시로 반복 요청 처리 시간 90% 단축
- ✅ **HTTP 캐싱**: 정적 자원 1년 캐싱, API는 no-store
- ✅ **보안 헤더**: XSS, Clickjacking, MIME-sniffing 방어
- ✅ **Prometheus 메트릭**: 25개 메트릭 수집 (API, 모델, 캐시, 시스템)
- ✅ **헬스체크 엔드포인트**: Readiness/Liveness probe 지원
- ✅ **고급 이미지 검증**: 매직 바이트, 무결성, 크기, 비율 검증
- ✅ **에러 핸들링**: 커스텀 예외 + 구조화된 에러 응답
- ✅ **로깅**: 색상 코드 로깅 + 파일 로테이션

---

## 🚀 빠른 시작

### 방법 1: 로컬 실행 (5분)

```bash
# 1. 저장소 클론
git clone https://github.com/sinsangwoo/AIdiseaseclassifier.git
cd AIdiseaseclassifier

# 2. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 서버 실행
python backend/app.py

# 5. 테스트
curl http://localhost:5000/health
```

### 방법 2: Docker (3분)

```bash
# Docker Compose로 실행
docker-compose up -d

# 헬스체크
curl http://localhost:5000/health

# 로그 확인
docker-compose logs -f app
```

---

## 📚 API 문서

### 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/` | 서비스 정보 |
| GET | `/health` | 기본 헬스체크 |
| GET | `/health/detailed` | 상세 헬스체크 (모니터링용) |
| GET | `/health/ready` | Readiness probe |
| GET | `/health/live` | Liveness probe |
| GET | `/model/info` | 모델 정보 |
| GET | `/model/stats` | 캐시 통계 (Phase 3) |
| GET/DELETE | `/model/cache` | 캐시 관리 (Phase 3) |
| POST | `/predict` | 이미지 예측 |

### POST /predict 사용 예시

```bash
# cURL
curl -X POST http://localhost:5000/predict \
  -F "file=@image.jpg" | jq

# Python
import requests

response = requests.post(
    'http://localhost:5000/predict',
    files={'file': open('image.jpg', 'rb')}
)
print(response.json())
```

**성공 응답:**
```json
{
  "success": true,
  "predictions": [
    {"className": "정상", "probability": 0.85},
    {"className": "폐렴", "probability": 0.10},
    {"className": "결핵", "probability": 0.05}
  ],
  "metadata": {
    "processing_time_ms": 45.2,
    "image_size": [224, 224],
    "filename": "image.jpg",
    "from_cache": false,
    "cache_enabled": true
  }
}
```

**에러 응답:**
```json
{
  "success": false,
  "error": "Invalid image format",
  "error_type": "InvalidImageError",
  "timestamp": "2026-02-05T13:00:00Z"
}
```

자세한 내용은 [API.md](API.md) 참조.

---

## 🧪 테스트

```bash
# 전체 테스트
pytest

# 마커별 실행
pytest -m unit       # 단위 테스트
pytest -m api        # API 테스트
pytest -m validation # 검증 테스트

# 커버리지 포함
pytest --cov=backend --cov-report=html
open htmlcov/index.html
```

**테스트 커버리지:** ~94%

---

## 📦 프로젝트 구조

```
AIdiseaseclassifier/
├── backend/
│   ├── app.py                    # Flask 애플리케이션 (Phase 3-4)
│   ├── config.py                 # 환경별 설정
│   ├── models/
│   │   ├── predictor.py          # ONNX 모델 래퍼
│   │   ├── keras_model.h5        # Teachable Machine 원본 모델
│   │   ├── model.onnx            # ONNX 경량화 모델
│   │   └── labels.txt            # 클래스 레이블
│   ├── services/
│   │   ├── image_processor.py    # 이미지 전처리
│   │   └── model_service.py      # 모델 서비스 레이어 (Phase 3)
│   └── utils/
│       ├── validators.py         # 입력 검증
│       ├── exceptions.py         # 커스텀 예외
│       ├── logger.py             # 로깅 시스템
│       ├── health.py             # 헬스체크
│       └── advanced_validators.py # 고급 검증
├── tests/                        # 50+ 테스트
├── .github/workflows/            # CI/CD
├── docs/                         # 추가 문서
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🐳 배포

### Docker

```bash
# 이미지 빌드
docker build -t ai-disease-classifier:latest .

# 컨테이너 실행
docker run -d -p 5000:5000 ai-disease-classifier:latest
```

### Docker Compose (권장)

```bash
# 실행
docker-compose up -d

# 스케일링
docker-compose up -d --scale app=3

# 중지
docker-compose down
```

### Render 배포 (현재 이슈)

⚠️ **알려진 문제**: Render 무료 플랜의 메모리 제한(512MB)으로 인해 ONNX 모델 로딩 시 서버가 터지는 문제가 있습니다.

**해결 방안:**
1. **Render 유료 플랜** 사용 (1GB+ RAM)
2. **Railway** 또는 **Fly.io** 사용 (더 관대한 무료 플랜)
3. **모델 추가 경량화** (현재 2.1MB → 목표 1MB 이하)
4. **프론트엔드만 배포** + 백엔드는 로컬/유료 서버

자세한 내용은 [DEPLOYMENT.md](DEPLOYMENT.md) 참조.

---

## 🔧 개발 환경 설정

### 환경변수

```bash
# .env 파일 생성
cp backend/.env.example backend/.env
```

**주요 환경변수:**
```env
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key
MODEL_PATH=backend/models/model.onnx
LABELS_PATH=backend/models/labels.txt
LOG_LEVEL=DEBUG
MAX_CONTENT_LENGTH=10485760  # 10MB
```

---

## 📖 추가 문서

- [API.md](API.md) - API 상세 문서
- [DEPLOYMENT.md](DEPLOYMENT.md) - 배포 가이드
- [PHASE3_4_FINAL.md](PHASE3_4_FINAL.md) - Phase 3-4 완료 보고서
- docs/ - 아키텍처, 보안, 모니터링 등

---

## 🛠️ 문제 해결

### 테스트 실패: 모델 파일을 찾을 수 없음

```bash
# 모델 파일 확인
ls -lh backend/models/

# 필요 파일:
# - keras_model.h5 (2.4MB)
# - model.onnx (2.1MB)
# - labels.txt
```

### Docker 빌드 실패

```bash
# 캐시 제거 후 재빌드
docker builder prune -a
docker build --no-cache -t ai-disease-classifier:latest .
```

### 포트 충돌

```bash
# 포트 5000 사용 중인 프로세스 확인
lsof -i :5000

# 프로세스 종료 또는 다른 포트 사용
export PORT=5001
python backend/app.py
```

---

## 🤝 기여 방법

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: Add AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 버전 히스토리

- **v8.0.0** (2026-02-05) - Phase 3-4: 백엔드 강화 + Prometheus 메트릭
- **v7.0.0** (2026-02-04) - Phase 3: 모델 서비스 레이어 분리 + 캐싱
- **v6.0.0** (2026-01-30) - Phase 2: 에러 핸들링 + 로깅 개선
- **v5.0.0** (2026-01-30) - Phase 1: 프로젝트 구조 재편
- **v1.0.0** (2025-06) - 초기 프로토타입

---

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 참조

---

## 📞 연락처

**신상우 (Sangwoo Sin)**
- 이메일: aksrkd7191@gmail.com
- GitHub: [@sinsangwoo](https://github.com/sinsangwoo)

---

<p align="center">
  Made with ❤️ by 신상우<br>
  아주대학교 소프트웨어학과 1학년
</p>
