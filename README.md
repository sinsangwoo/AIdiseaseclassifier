# AI Disease Classifier

ONNX-optimized medical image classification system for pneumonia diagnosis.

## https://sinsangwoo.github.io/AIdiseaseclassifier/

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.1+](https://img.shields.io/badge/flask-3.1+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

A production-ready pneumonia diagnosis system built on MobileNetV3-Small, converted to ONNX for efficient inference. Designed for resource-constrained environments (≤512MB RAM) with minimal latency.

**Key Achievements:**
- 85% memory reduction by eliminating PyTorch dependencies
- 90% faster repeat request processing via LRU caching
- Full CORS security and file validation pipeline

## Architecture

```
AIdiseaseclassifier/
├── backend/
│   ├── app.py              # Flask API server
│   ├── models/             # ONNX model and labels
│   ├── services/           # Inference engine
│   └── utils/              # Security and logging
├── frontend/
│   ├── index.html
│   ├── js/                 # API client
│   └── css/
├── tests/                  # Pytest suite
├── Dockerfile
└── requirements.txt
```

## Tech Stack

**Backend:** Flask 3.1, ONNX Runtime, Pillow, NumPy  
**Frontend:** Vanilla JavaScript, HTML5, CSS3  
**DevOps:** Docker, Prometheus, GitHub Actions  
**Reporting:** html2canvas, jsPDF

## Features

- **Optimized Inference**: ONNX Runtime with CPU execution provider
- **Security**: Magic byte validation, XSS/Clickjacking prevention, CORS whitelist
- **Monitoring**: 25+ Prometheus metrics (request count, latency, cache hits)
- **Reports**: High-resolution PNG and PDF diagnosis reports
- **Kubernetes-Ready**: Liveness/readiness probe endpoints

## Quick Start

### Local Development

```bash
git clone https://github.com/sinsangwoo/AIdiseaseclassifier.git
cd AIdiseaseclassifier

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

python backend/app.py
```

### Docker

```bash
docker-compose up -d --build
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict` | POST | Image classification |
| `/health` | GET | Liveness probe |
| `/metrics` | GET | Prometheus metrics |

## Performance

- **Inference Time**: <100ms per image (CPU)
- **Memory Usage**: <300MB under load
- **Cache Hit Rate**: >85% for repeated requests

## Security

- Magic byte verification for uploaded files
- Content Security Policy headers
- CORS whitelist configuration
- Rate limiting on prediction endpoint

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/enhancement`)
3. Commit changes (`git commit -m 'Add enhancement'`)
4. Push to branch (`git push origin feature/enhancement`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Author:** Sangwoo Sin  
Dept. of Software, Ajou University
