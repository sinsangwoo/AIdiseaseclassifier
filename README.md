# 🏥 AI Disease Classifier

> **ONNX Runtime 기반의 경량화된 의료 이미지 분석 및 진단 시스템**
>
> **ONNX-based Medical Image Analysis & Disease Diagnosis System**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.1+](https://img.shields.io/badge/flask-3.1+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 개요 (Overview)

본 프로젝트는 **MobileNetV3-Small** 아키텍처를 기반으로 학습된 폐렴 진단 모델을 **ONNX(Open Neural Network Exchange) 형식으로 최적화**하여 배포한 엔드투엔드 의료 AI 솔루션입니다. 클라우드 환경의 제한된 리소스(RAM 512MB 이하) 내에서도 지연 시간(Latency)을 최소화하고 높은 추론 처리량을 확보하는 데 중점을 두었습니다.

This project is an end-to-end medical AI solution that deploys a pneumonia diagnosis model based on the **MobileNetV3-Small** architecture, **optimized in ONNX format**. It is engineered to minimize latency and ensure high inference throughput within resource-constrained cloud environments (under 512MB RAM).

---

## 🛠 핵심 기술 사양 (Technical Specifications)

### 1. 모델 최적화 및 추론 (Model Optimization & Inference)

Engine: ONNX Runtime (CPU Execution Provider)

Optimization: PyTorch 의존성을 완전히 제거하여 메모리 점유율을 85% 이상 절감했습니다.

Architecture: MobileNetV3-Small (Pre-trained & Fine-tuned)

### 2. 백엔드 아키텍처 (Backend Architecture)

Framework: Flask 3.1 (Production-ready configuration)

Security:

CORS Management: 화이트리스트 기반의 엄격한 Cross-Origin 정책 적용

File Validation: 매직 바이트(Magic Byte) 검증을 통한 위변조 파일 업로드 차단

Security Headers: XSS 및 Clickjacking 방지를 위한 전역 헤더 설정

### 3. 프론트엔드 및 리포팅 (Frontend & Reporting)

UI/UX: Vanilla JavaScript 기반의 반응형 인터페이스

Reporting:

html2canvas 기반의 고해상도 PNG 진단 결과 저장

jsPDF를 활용한 정식 의료 진단서 형식의 PDF 리포트 생성


## 📂 프로젝트 구조 (Project Structure)

AIdiseaseclassifier/
├── backend/
│   ├── app.py              # Flask API 서버 엔트리 포인트
│   ├── models/             # 최적화된 ONNX 모델 및 라벨 파일
│   ├── services/           # 추론 엔진 및 핵심 비즈니스 로직
│   └── utils/              # 보안 검증 및 구조화된 로거
├── frontend/
│   ├── index.html          # 메인 UI (Vanilla JS/CSS3)
│   ├── js/                 # API 통신 및 UI 상태 관리
│   └── css/                # 컴포넌트 기반 스타일시트
├── tests/                  # Pytest 기반 통합 테스트 스위트
├── Dockerfile              # 멀티 스테이지 빌드 설정
└── requirements.txt        # 최적화된 최소 의존성 라이브러리


---

## ✨ 주요 기능 (Key Features)

- **고성능 캐싱 (High-Performance Caching)**: LRU 캐시를 도입하여 반복 요청 처리 시간을 **90% 단축**했습니다.
  - Reduced repetitive request processing time by **90%** using LRU cache.
- **보안 강화 (Enhanced Security)**: XSS, Clickjacking, MIME-sniffing 방지 헤더를 적용했습니다.
  - Applied security headers to prevent XSS, Clickjacking, and MIME-sniffing.
- **모니터링 (Monitoring)**: Prometheus를 통해 API 요청 수, 처리 시간, 캐시 적중률 등 **25개 이상의 메트릭**을 수집합니다.
  - Collects **over 25 metrics** including API request count, processing time, and cache hit rate via Prometheus.
- **헬스체크 (Health Checks)**: k8s 호환성을 위한 Liveness/Readiness Probe 엔드포인트를 제공합니다.
  - Provides Liveness/Readiness Probe endpoints for Kubernetes compatibility.
- **이미지 검증 (Advanced Validation)**: 매직 바이트(Magic Byte) 검사를 통해 위변조된 이미지 파일을 차단합니다.
  - Blocks tampered image files through Magic Byte verification.
- **구조화된 로깅 (Structured Logging)**: 색상 코드 로깅 및 파일 로테이션을 지원합니다.
  - Supports color-coded logging and file rotation.

---

## 🛠 기술 스택 (Tech Stack)

| Category | Technology |
|----------|------------|
| **Backend** | Flask 3.1 (Python 3.10+) |
| **Frontend** | HTML5, CSS3, JavaScript (Vanilla) |
| **ML Core** | ONNX Runtime, Teachable Machine |
| **Processing** | Pillow, NumPy |
| **DevOps** | Docker, Docker Compose, GitHub Actions |
| **Monitoring** | Prometheus Metrics |

---

## 🚀 빠른 시작 (Quick Start)

로컬 환경 설정 (Local Setup)

### Repository 클론
git clone [https://github.com/sinsangwoo/AIdiseaseclassifier.git](https://github.com/sinsangwoo/AIdiseaseclassifier.git)
cd AIdiseaseclassifier

### 가상환경 구축 및 의존성 설치
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

### 서버 실행
python backend/app.py


컨테이너 환경 (Docker)

docker-compose up -d --build

---

## 🤝 기여 (Contributing)

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/NewFeature`)
3. Commit your Changes (`git commit -m 'Add some NewFeature'`)
4. Push to the Branch (`git push origin feature/NewFeature`)
5. Open a Pull Request

---

## ⚖️ 라이선스 (License)

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

<p align="center">
  <strong>Created by Sangwoo Sin</strong><br>
  1st-year Student, Dept. of Software, Ajou University
</p>
