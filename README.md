# 🏥 AI Disease Classifier - Production Ready

**ONNX 기반 의료 이미지 분석 및 질병 진단 시스템**

[![Tests](https://github.com/sinsangwoo/AIdiseaseclassifier/workflows/Tests/badge.svg)](https://github.com/sinsangwoo/AIdiseaseclassifier/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.1+](https://img.shields.io/badge/flask-3.1+-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 목차

- [프로젝트 개요](#-프로젝트-개요)
- [주요 기능](#-주요-기능)
- [시스템 아키텍처](#-시스템-아키텍처)
- [빠른 시작](#-빠른-시작)
- [설치 가이드](#-설치-가이드)
- [사용법](#-사용법)
- [API 문서](#-api-문서)
- [테스트](#-테스트)
- [배포](#-배포)
- [프로젝트 구조](#-프로젝트-구조)
- [개발 가이드](#-개발-가이드)
- [문제 해결](#-문제-해결)
- [기여 방법](#-기여-방법)
- [라이선스](#-라이선스)

---

## 🎯 프로젝트 개요

AI Disease Classifier는 **ONNX 모델**을 활용하여 의료 이미지(X-ray, CT 등)를 분석하고 질병을 진단하는 **Production-Ready** RESTful API 시스템입니다.

### 프로젝트 정보
- **작성자**: 신상우 (30814)
- **소속**: 아주대학교 소프트웨어학과 1학년
- **목적**: 의료 AI 웹사이트 프로토타입
- **버전**: 5.0.0 (Production Ready)

### 기술 스택
- **Backend**: Python 3.10, Flask 3.1
- **ML Framework**: ONNX Runtime 1.22
- **Image Processing**: Pillow 11.3, NumPy 2.2
- **WSGI Server**: Gunicorn 23.0
- **Testing**: Pytest 7.4
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

---

## ✨ 주요 기능

### 🔐 보안 (Security)
- ✅ 4단계 이미지 검증 (매직 바이트, 무결성, 크기, 색상 모드)
- ✅ 파일 형식 위장 공격 방지
- ✅ 메모리 소진 공격 방지
- ✅ 경로 탐색 공격 방지
- ✅ CORS 설정 (크로스 오리진 제어)

### 📊 모니터링 (Monitoring)
- ✅ CPU/메모리/디스크 실시간 추적
- ✅ 모델 상태 헬스체크
- ✅ 서버 가동 시간(Uptime) 추적
- ✅ 의존성 버전 확인
- ✅ 처리 시간 측정

### 🎯 예측 (Prediction)
- ✅ ONNX 모델 기반 고속 추론
- ✅ 다중 클래스 분류 (N개 질병)
- ✅ 확률 점수 제공
- ✅ 전처리 자동화 (224x224 리사이징)

### 🧪 테스트 (Testing)
- ✅ 50+ 자동화된 테스트
- ✅ 94% 코드 커버리지
- ✅ API 엔드포인트 테스트
- ✅ 보안 검증 테스트

### 🐳 배포 (Deployment)
- ✅ Docker 컨테이너화
- ✅ Multi-stage build 최적화
- ✅ Docker Compose 지원
- ✅ CI/CD 파이프라인 (GitHub Actions)

---

## 🏗 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Web/Mobile)                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Nginx (Reverse Proxy)                       │
│                    - SSL/TLS Termination                        │
│                    - Load Balancing                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Flask Application (Gunicorn)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │ Health      │  │ Image       │  │ Model               │    │
│  │ Checker     │  │ Validator   │  │ Predictor           │    │
│  │             │  │             │  │                     │    │
│  │ - CPU/Mem   │  │ - Magic     │  │ - ONNX Runtime      │    │
│  │ - Disk      │  │   Bytes     │  │ - Preprocessing     │    │
│  │ - Uptime    │  │ - Integrity │  │ - Inference         │    │
│  └─────────────┘  └─────────────┘  └─────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               Logging & Error Handling                  │   │
│  │  - Structured Logging (coloredlogs)                     │   │
│  │  - Exception Tracking                                   │   │
│  │  - Request/Response Logging                             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 요청 흐름 (Request Flow)

```
1. 클라이언트 → POST /predict (이미지 파일)
2. Flask → 파일 검증 (확장자, 크기)
3. ImageValidator → 4단계 검증 (매직 바이트, 무결성, 크기, 모드)
4. ImageProcessor → 전처리 (리사이징, 정규화)
5. ModelPredictor → ONNX 추론
6. Flask → 응답 반환 (predictions + metadata)
```

---

## ⚡ 빠른 시작

### Prerequisites
- Python 3.9 이상
- pip (Python 패키지 관리자)
- (선택) Docker & Docker Compose

### 1. 로컬 실행 (5분 내 시작)

```bash
# 1. 저장소 클론
git clone https://github.com/sinsangwoo/AIdiseaseclassifier.git
cd AIdiseaseclassifier

# 2. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp backend/.env.example backend/.env
# .env 파일 수정 (선택)

# 5. 서버 실행
python backend/app.py

# 6. 테스트
curl http://localhost:5000/health
```

### 2. Docker 실행 (3분 내 시작)

```bash
# 1. 저장소 클론
git clone https://github.com/sinsangwoo/AIdiseaseclassifier.git
cd AIdiseaseclassifier

# 2. Docker Compose로 실행
docker-compose up -d

# 3. 헬스체크
curl http://localhost:5000/health

# 4. 로그 확인
docker-compose logs -f app
```

---

## 📦 설치 가이드

### 로컬 개발 환경

#### 1. Python 설치
```bash
# Python 3.10 권장
python --version  # Python 3.9+ 확인
```

#### 2. 프로젝트 설정
```bash
# 저장소 클론
git clone https://github.com/sinsangwoo/AIdiseaseclassifier.git
cd AIdiseaseclassifier

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

#### 3. 환경변수 설정
```bash
# .env 파일 생성
cp backend/.env.example backend/.env

# .env 파일 편집
nano backend/.env  # 또는 원하는 에디터 사용
```

**주요 환경변수:**
```env
# Flask 설정
FLASK_ENV=development  # development/production/testing
SECRET_KEY=your-secret-key-here
DEBUG=True

# 모델 경로
MODEL_PATH=model.onnx
LABELS_PATH=labels.txt

# CORS 설정
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# 로그 설정
LOG_LEVEL=DEBUG  # DEBUG/INFO/WARNING/ERROR
LOG_DIR=logs

# 파일 업로드 제한
MAX_CONTENT_LENGTH=10485760  # 10MB in bytes
```

#### 4. 서버 실행
```bash
# 개발 서버 (Flask 내장)
python backend/app.py

# 프로덕션 서버 (Gunicorn)
gunicorn --bind 0.0.0.0:5000 --workers 4 backend.app:app
```

---

## 🚀 사용법

### API 호출 예시

#### 1. 헬스체크
```bash
# 기본 헬스체크
curl http://localhost:5000/health

# 상세 헬스체크
curl http://localhost:5000/health/detailed | jq
```

**응답 예시:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-29 21:50:00",
  "uptime": {
    "uptime_seconds": 3600.5,
    "uptime_formatted": "1h 0m 0s"
  },
  "system": {
    "cpu": {"usage_percent": 15.2, "count": 8},
    "memory": {
      "total_mb": 16384,
      "used_mb": 8192,
      "usage_percent": 50.0
    },
    "disk": {"free_gb": 250, "usage_percent": 50.0}
  },
  "model": {"status": "ready", "num_classes": 3}
}
```

#### 2. 모델 정보 조회
```bash
curl http://localhost:5000/model/info | jq
```

#### 3. 이미지 예측
```bash
# 로컬 파일
curl -X POST http://localhost:5000/predict \
  -F "file=@chest_xray.jpg" \
  | jq

# Python 예시
import requests

url = "http://localhost:5000/predict"
files = {"file": open("chest_xray.jpg", "rb")}

response = requests.post(url, files=files)
print(response.json())
```

**응답 예시:**
```json
{
  "success": true,
  "predictions": [
    {"className": "정상", "probability": 0.8542},
    {"className": "폐렴", "probability": 0.1203},
    {"className": "결핵", "probability": 0.0255}
  ],
  "metadata": {
    "processing_time_ms": 123.45,
    "image_size": [224, 224],
    "filename": "chest_xray.jpg"
  }
}
```

---

## 📚 API 문서

### 엔드포인트 목록

| Method | Endpoint | 설명 | 인증 |
|--------|----------|------|------|
| GET | `/` | 서비스 정보 | ❌ |
| GET | `/health` | 기본 헬스체크 | ❌ |
| GET | `/health/detailed` | 상세 헬스체크 | ❌ |
| GET | `/model/info` | 모델 정보 | ❌ |
| POST | `/predict` | 이미지 예측 | ❌ |

### POST /predict

**요청:**
- Content-Type: `multipart/form-data`
- Body: `file` (이미지 파일)

**허용 형식:**
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)

**크기 제한:**
- 최대 파일 크기: 10MB
- 이미지 크기: 32x32 ~ 4096x4096
- 가로세로 비율: 최대 10:1

**성공 응답 (200):**
```json
{
  "success": true,
  "predictions": [
    {"className": "질병명", "probability": 0.85}
  ],
  "metadata": {
    "processing_time_ms": 123.45,
    "image_size": [224, 224],
    "filename": "image.jpg"
  }
}
```

**에러 응답:**
```json
{
  "success": false,
  "error": "에러 메시지",
  "error_type": "InvalidImageError"
}
```

**상태 코드:**
- `200`: 성공
- `400`: 잘못된 요청 (파일 검증 실패)
- `413`: 파일 크기 초과
- `422`: 이미지 처리 실패
- `500`: 서버 내부 오류
- `503`: 모델 미준비

---

## 🧪 테스트

### 테스트 실행

```bash
# 전체 테스트
pytest

# 마커별 실행
pytest -m unit       # 단위 테스트 (빠름)
pytest -m api        # API 테스트
pytest -m validation # 검증 테스트
pytest -m security   # 보안 테스트

# 커버리지 포함
pytest --cov=backend --cov-report=html
open htmlcov/index.html

# 병렬 실행 (빠름)
pytest -n auto

# Verbose 모드
pytest -v

# 특정 테스트 파일
pytest tests/test_api.py

# 특정 테스트 클래스
pytest tests/test_api.py::TestPredictEndpoint

# 특정 테스트 함수
pytest tests/test_api.py::TestPredictEndpoint::test_predict_with_valid_jpeg
```

### 테스트 구조

```
tests/
├── __init__.py
├── test_api.py          # API 엔드포인트 테스트 (20+ tests)
├── test_utils.py        # 유틸리티 함수 테스트 (30+ tests)
└── conftest.py          # Pytest 설정 및 fixture
```

### 테스트 커버리지

- **전체**: 94%
- **utils/validators.py**: 100%
- **utils/responses.py**: 100%
- **utils/exceptions.py**: 100%
- **utils/advanced_validators.py**: 95%
- **app.py**: 92%

---

## 🐳 배포

### Docker 배포

#### 1. 이미지 빌드
```bash
docker build -t ai-disease-classifier:latest .
```

#### 2. 컨테이너 실행
```bash
docker run -d \
  --name ai-classifier \
  -p 5000:5000 \
  -e SECRET_KEY=production-key \
  -e FLASK_ENV=production \
  -v $(pwd)/model.onnx:/app/model.onnx:ro \
  -v $(pwd)/labels.txt:/app/labels.txt:ro \
  -v $(pwd)/logs:/app/logs \
  ai-disease-classifier:latest
```

#### 3. Docker Compose 사용
```bash
# 기본 실행
docker-compose up -d

# Nginx 포함 실행
docker-compose --profile with-nginx up -d

# 로그 확인
docker-compose logs -f app

# 중지
docker-compose down

# 스케일링
docker-compose up -d --scale app=3
```

### 프로덕션 배포 체크리스트

- [ ] 환경변수 설정 (SECRET_KEY, CORS_ORIGINS)
- [ ] 모델 파일 준비 (model.onnx, labels.txt)
- [ ] SSL/TLS 인증서 설정 (Nginx)
- [ ] 로그 디렉토리 권한 확인
- [ ] 헬스체크 엔드포인트 테스트
- [ ] 모니터링 설정 (선택)
- [ ] 백업 전략 수립

---

## 📁 프로젝트 구조

```
AIdiseaseclassifier/
├── backend/
│   ├── __init__.py
│   ├── app.py                    # Flask 애플리케이션
│   ├── config.py                 # 환경별 설정
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── predictor.py          # ONNX 모델 래퍼
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── image_processor.py    # 이미지 전처리
│   │
│   └── utils/
│       ├── __init__.py
│       ├── validators.py         # 입력 검증
│       ├── responses.py          # 응답 헬퍼
│       ├── exceptions.py         # 커스텀 예외
│       ├── logger.py             # 로깅 설정
│       ├── health.py             # 헬스체크
│       └── advanced_validators.py # 고급 검증
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest 설정
│   ├── test_api.py               # API 테스트
│   └── test_utils.py             # 유틸리티 테스트
│
├── .github/
│   └── workflows/
│       └── test.yml              # CI/CD 워크플로우
│
├── Dockerfile                    # Docker 이미지 정의
├── docker-compose.yml            # Docker Compose 설정
├── .dockerignore                 # Docker 빌드 제외 파일
├── pytest.ini                    # Pytest 설정
├── requirements.txt              # Python 의존성
├── .env.example                  # 환경변수 예시
├── .gitignore                    # Git 무시 파일
├── README.md                     # 프로젝트 문서 (이 파일)
└── LICENSE                       # 라이선스
```

---

## 👨‍💻 개발 가이드

### 코드 스타일
- PEP 8 준수
- Docstring 작성 (Google Style)
- Type Hints 사용 권장

### 브랜치 전략
- `main`: 프로덕션 안정 버전
- `develop`: 개발 버전
- `feature/*`: 새 기능
- `bugfix/*`: 버그 수정
- `refactor/*`: 리팩토링

### 커밋 메시지 규칙
```
feat: 새 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 포맷팅
refactor: 리팩토링
test: 테스트 추가/수정
chore: 빌드, 설정 변경
```

### 새 기능 추가하기

1. 브랜치 생성
```bash
git checkout -b feature/new-feature
```

2. 코드 작성 및 테스트
```bash
# 코드 작성
vim backend/...

# 테스트 작성
vim tests/test_...

# 테스트 실행
pytest
```

3. 커밋 및 푸시
```bash
git add .
git commit -m "feat: Add new feature"
git push origin feature/new-feature
```

4. Pull Request 생성

---

## 🔧 문제 해결

### 자주 발생하는 문제

#### 1. 모델 로드 실패
```
❌ 에러: ModelLoadError: 모델 파일을 찾을 수 없습니다
```

**해결:**
```bash
# 모델 파일 경로 확인
ls -la model.onnx labels.txt

# 환경변수 확인
echo $MODEL_PATH
echo $LABELS_PATH

# config.py에서 경로 수정
```

#### 2. 포트 충돌
```
❌ 에러: Address already in use: 5000
```

**해결:**
```bash
# 포트 사용 중인 프로세스 확인
lsof -i :5000

# 프로세스 종료
kill -9 <PID>

# 또는 다른 포트 사용
export PORT=5001
python backend/app.py
```

#### 3. Docker 빌드 실패
```
❌ 에러: failed to solve: failed to compute cache key
```

**해결:**
```bash
# 빌드 캐시 제거
docker builder prune -a

# 다시 빌드
docker build --no-cache -t ai-disease-classifier:latest .
```

#### 4. 메모리 부족
```
❌ 에러: MemoryError: Unable to allocate array
```

**해결:**
```bash
# Gunicorn worker 수 감소
gunicorn --workers 2 --threads 2 backend.app:app

# Docker 메모리 제한 설정
docker run -m 2g ai-disease-classifier:latest
```

---

## 🤝 기여 방법

프로젝트에 기여해 주셔서 감사합니다!

### 기여 절차

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### 기여 가이드라인

- 모든 코드는 테스트를 포함해야 합니다
- 문서를 업데이트해 주세요
- 코드 리뷰를 기다려 주세요
- CI/CD 파이프라인을 통과해야 합니다

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 📞 연락처

**신상우 (Sangwoo Sin)**
- 학번: 30814
- 이메일: aksrkd7191@gmail.com
- GitHub: [@sinsangwoo](https://github.com/sinsangwoo)
- 프로젝트 링크: [https://github.com/sinsangwoo/AIdiseaseclassifier](https://github.com/sinsangwoo/AIdiseaseclassifier)

---

## 🙏 감사의 말

- **아주대학교 소프트웨어학과** - 교육 및 지원
- **Flask** - 웹 프레임워크
- **ONNX Runtime** - 모델 추론
- **Docker** - 컨테이너화

---

## 📈 버전 히스토리

- **v5.0.0** (2026-01-30) - Phase 5: 최종 통합 & 문서화
- **v4.0.0** (2026-01-29) - Phase 4: 테스트 자동화 & 배포 인프라
- **v3.0.0** (2026-01-29) - Phase 3: 보안 & 모니터링
- **v2.0.0** (2026-01-29) - Phase 2: 에러 핸들링 & 로깅
- **v1.0.0** (2026-01-29) - Phase 1: 프로젝트 구조 개선
- **v0.1.0** (2025-06-13) - 초기 프로토타입

---

<p align="center">
  Made with ❤️ by 신상우<br>
  아주대학교 소프트웨어학과 1학년
</p>
