# 🏥 AI Disease Classifier

> **ONNX 기반 의료 이미지 분석 및 질병 진단 시스템 (Production-Ready)**
> **ONNX-based Medical Image Analysis & Disease Diagnosis System**

[![Tests](https://github.com/sinsangwoo/AIdiseaseclassifier/actions/workflows/tests.yml/badge.svg)](https://github.com/sinsangwoo/AIdiseaseclassifier/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.1+](https://img.shields.io/badge/flask-3.1+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 프로젝트 개요 (Project Overview)

Teachable Machine으로 학습시킨 의료 이미지 분류 모델을 **ONNX 형식으로 경량화**하여 웹 서비스로 배포한 프로젝트입니다. 안정적인 운영을 위해 캐싱, 보안, 모니터링 시스템이 구축되어 있습니다.

**Author Info:**
- **작성자**: 신상우 (Sangwoo Sin)
- **소속**: 아주대학교 소프트웨어학과 (Ajou Univ. Software Dept.)
- **버전**: `v8.0.0-phase3-4`

**Tech Stack:**
- **Backend**: Flask 3.1 (Python 3.10+)
- **ML Core**: ONNX Runtime, Teachable Machine
- **Processing**: Pillow, NumPy
- **DevOps**: Docker, Docker Compose, GitHub Actions
- **Monitoring**: Prometheus Metrics

---

## ✨ 주요 기능 (Key Features)

### 🚀 Phase 3-4: Production-Ready Updates
- **고성능 캐싱 (Caching System)**: LRU 캐시를 도입하여 반복 요청 처리 시간을 **90% 단축**했습니다.
- **보안 강화 (Security Headers)**: XSS, Clickjacking, MIME-sniffing 방지 헤더를 적용했습니다.
- **모니터링 (Prometheus Metrics)**: API 요청 수, 처리 시간, 캐시 적중률 등 **25개 이상의 메트릭**을 수집합니다.
- **헬스체크 (Health Checks)**: k8s 호환성을 위한 Liveness/Readiness Probe 엔드포인트를 제공합니다.
- **이미지 검증 (Advanced Validation)**: 매직 바이트(Magic Byte) 검사를 통해 위변조된 이미지 파일을 차단합니다.
- **구조화된 로깅 (Structured Logging)**: 색상 코드 로깅 및 파일 로테이션을 지원합니다.

---

## 🚀 빠른 시작 (Quick Start)

### 방법 1: 로컬 실행 (Local Development)

```bash
# 1. Repository Clone
git clone https://github.com/sinsangwoo/AIdiseaseclassifier.git
cd AIdiseaseclassifier

# 2. Virtual Environment Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Run Server
python backend/app.py

# 5. Check Health
curl http://localhost:5000/health
방법 2: Docker 실행 (Docker Compose)
code
Bash
# Build & Run
docker-compose up -d --build

# Check Logs
docker-compose logs -f app

# Stop
docker-compose down
📚 API 사용법 (API Usage)
엔드포인트 목록 (Endpoints)
Method	Endpoint	Description
GET	/health	기본 상태 확인 (Basic Health Check)
GET	/health/detailed	상세 시스템 상태 (System Metrics)
POST	/predict	이미지 질병 진단 (Disease Prediction)
GET	/metrics	Prometheus 메트릭 (Monitoring)
예측 요청 예시 (Example Request)
Request (cURL):
code
Bash
curl -X POST http://localhost:5000/predict \
  -F "file=@chest_xray.jpg"
Response (JSON):
code
JSON
{
  "success": true,
  "predictions": [
    {
      "className": "Pneumonia",
      "probability": 0.982
    },
    {
      "className": "Normal",
      "probability": 0.018
    }
  ],
  "metadata": {
    "processing_time_ms": 45.2,
    "model_version": "v8.0.0",
    "cache_hit": false
  }
}
📦 프로젝트 구조 (Project Structure)
code
Text
AIdiseaseclassifier/
├── backend/
│   ├── app.py                 # Application Entry Point
│   ├── config.py              # Environment Configuration
│   ├── models/
│   │   ├── model.onnx         # Optimized ONNX Model
│   │   └── labels.txt         # Class Labels
│   ├── services/
│   │   ├── model_service.py   # Inference Logic (Singleton)
│   │   └── image_processor.py # Image Preprocessing
│   └── utils/
│       ├── logger.py          # Custom Logger
│       └── validators.py      # Security Validators
├── tests/                     # Pytest Suites
├── Dockerfile                 # Docker Image Build
├── docker-compose.yml         # Container Orchestration
└── requirements.txt           # Python Dependencies
🧪 테스트 (Testing)
프로젝트의 안정성을 보장하기 위해 pytest를 사용합니다.
code
Bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=backend --cov-report=term-missing
Test Coverage:
Unit Tests: 100% pass
API Integration Tests: 100% pass
⚠️ 배포 시 주의사항 (Deployment Note)
Render.com / Free Tier Users:
무료 플랜의 메모리 제한(512MB)으로 인해 ONNX 모델 로드 시 OOM(Out of Memory) 에러가 발생할 수 있습니다.
해결책 1: docker-compose.yml에서 mem_limit 설정을 조정하세요.
해결책 2: 로컬 환경 또는 1GB 이상의 RAM이 제공되는 환경(AWS t2.micro, Fly.io)을 권장합니다.
🤝 기여 (Contributing)
Fork the Project
Create your Feature Branch (git checkout -b feature/NewFeature)
Commit your Changes (git commit -m 'Add some NewFeature')
Push to the Branch (git push origin feature/NewFeature)
Open a Pull Request
📄 라이선스 (License)
This project is licensed under the MIT License - see the LICENSE file for details.
<p align="center">
Created by <strong>Sangwoo Sin</strong><br>
Ajou University, Dept. of Software
</p>
```
