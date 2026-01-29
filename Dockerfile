# AI 질병 진단 시스템 - Production Docker Image
# Multi-stage build for optimized image size

# Stage 1: Builder
FROM python:3.10-slim as builder

WORKDIR /build

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim

# 메타데이터
LABEL maintainer="sinsangwoo <aksrkd7191@gmail.com>"
LABEL description="AI Disease Classifier - Production Ready"
LABEL version="3.0.0"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 사용자 생성 (보안)
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# Python 의존성 복사 (builder에서)
COPY --from=builder /root/.local /home/appuser/.local

# 애플리케이션 코드 복사
COPY --chown=appuser:appuser backend /app/backend
COPY --chown=appuser:appuser requirements.txt /app/

# 환경변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/appuser/.local/bin:$PATH \
    FLASK_APP=backend.app \
    FLASK_ENV=production

# 포트 노출
EXPOSE 5000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)"

# 비root 사용자로 전환
USER appuser

# Gunicorn으로 실행 (프로덕션)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--threads", "2", \
     "--worker-class", "gthread", \
     "--worker-tmp-dir", "/dev/shm", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "backend.app:app"]
