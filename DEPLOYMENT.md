# 🚀 배포 가이드 (Deployment Guide)

> AI Disease Classifier를 프로덕션 환경에 배포하는 종합 가이드

---

## 📋 목차

1. [배포 전 체크리스트](#-배포-전-체크리스트)
2. [Docker 배포](#-docker-배포)
3. [클라우드 플랫폼](#-클라우드-플랫폼)
4. [프론트엔드 배포](#-프론트엔드-배포)
5. [모니터링 설정](#-모니터링-설정)
6. [문제 해결](#-문제-해결)

---

## ✅ 배포 전 체크리스트

### 필수 사항
- [ ] 모델 파일 준비 완료 (`model.onnx`, `labels.txt`)
- [ ] 환경변수 설정 완료 (`.env` 파일)
- [ ] 로컬 테스트 통과 (`pytest`)
- [ ] Docker 이미지 빌드 성공
- [ ] 메모리 요구사항 확인 (최소 1GB RAM 권장)

### 보안 사항
- [ ] `SECRET_KEY` 변경 (프로덕션 키 생성)
- [ ] `DEBUG=False` 설정
- [ ] CORS 오리진 제한 설정
- [ ] SSL/TLS 인증서 준비 (HTTPS)

### 모니터링
- [ ] 헬스체크 엔드포인트 동작 확인
- [ ] 로그 수집 설정
- [ ] 에러 알림 설정 (선택)

---

## 🐳 Docker 배포

### 방법 1: Docker Run

```bash
# 1. 이미지 빌드
docker build -t ai-disease-classifier:latest .

# 2. 컨테이너 실행
docker run -d \
  --name ai-classifier \
  -p 5000:5000 \
  -e SECRET_KEY="production-secret-key-here" \
  -e FLASK_ENV=production \
  -e DEBUG=False \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  --memory="1g" \
  ai-disease-classifier:latest

# 3. 헬스체크
curl http://localhost:5000/health

# 4. 로그 확인
docker logs -f ai-classifier
```

### 방법 2: Docker Compose (권장)

```bash
# 1. 기본 실행
docker-compose up -d

# 2. 스케일링 (로드 밸런싱)
docker-compose up -d --scale app=3

# 3. Nginx 포함 실행 (리버스 프록시)
docker-compose --profile with-nginx up -d

# 4. 상태 확인
docker-compose ps

# 5. 로그 확인
docker-compose logs -f app

# 6. 중지 및 삭제
docker-compose down
```

**docker-compose.yml 예시:**
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=False
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## ☁️ 클라우드 플랫폼

### 1. Railway (추천 ⭐)

**장점:**
- ✅ 무료 플랜 $5/월 크레딧 (충분함)
- ✅ GitHub 연동 자동 배포
- ✅ 메모리 제한 관대함 (8GB까지 무료)
- ✅ PostgreSQL, Redis 통합 지원

**배포 방법:**

1. Railway 계정 생성: https://railway.app
2. "New Project" → "Deploy from GitHub repo" 선택
3. 저장소 연결 및 환경변수 설정
4. 자동 배포 시작 (완료 시 URL 제공)

**환경변수 설정 (Railway Dashboard):**
```
FLASK_ENV=production
SECRET_KEY=your-secret-key
DEBUG=False
PORT=5000
```

### 2. Fly.io (추천 ⭐⭐)

**장점:**
- ✅ 무료 플랜 (VM 3개, 256MB RAM)
- ✅ 글로벌 엣지 네트워크
- ✅ 도커 기반 배포
- ✅ 자동 스케일링

**배포 방법:**

```bash
# 1. Fly CLI 설치
curl -L https://fly.io/install.sh | sh

# 2. 로그인
fly auth login

# 3. 앱 초기화
fly launch

# 4. 배포
fly deploy

# 5. 스케일링 (선택)
fly scale count 2
fly scale memory 512

# 6. 상태 확인
fly status
```

**fly.toml 예시:**
```toml
app = "ai-disease-classifier"
primary_region = "nrt"  # Tokyo

[build]
  dockerfile = "Dockerfile"

[env]
  FLASK_ENV = "production"
  PORT = "8080"

[[services]]
  http_checks = []
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = 80
    force_https = true

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [services.health_check]
    path = "/health"
    interval = "15s"
    timeout = "10s"
```

### 3. Render ⚠️

**현재 문제:**
- ❌ 무료 플랜 메모리 제한 (512MB) → ONNX 모델 로드 시 OOM
- ❌ 서버가 자주 터짐

**해결 방안:**
1. **유료 플랜 사용** ($7/월, 1GB RAM)
2. **모델 추가 경량화** (현재 2.1MB → 목표 1MB)
3. **다른 플랫폼 사용** (Railway, Fly.io 권장)

**배포 방법 (유료 플랜 사용 시):**

1. Render 계정 생성: https://render.com
2. "New Web Service" 선택
3. GitHub 저장소 연결
4. 설정:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT backend.app:app`
   - **Plan**: Starter ($7/월)
5. 환경변수 설정
6. "Create Web Service" 클릭

**render.yaml 예시:**
```yaml
services:
  - type: web
    name: ai-disease-classifier
    env: python
    plan: starter  # 유료 플랜 필요!
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn --bind 0.0.0.0:$PORT --workers 2 backend.app:app"
    envVars:
      - key: FLASK_ENV
        value: production
      - key: SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: False
    healthCheckPath: /health
```

### 4. Heroku (비추천)

**이유:**
- ❌ 무료 플랜 폐지 (2022년 11월)
- ❌ 최소 $5/월부터 시작
- ❌ Railway, Fly.io보다 비싸고 기능 적음

---

## 🌐 프론트엔드 배포

### GitHub Pages (무료, 추천)

```bash
# 1. frontend/index.html 수정 (API URL 변경)
# API_URL을 배포된 백엔드 URL로 변경
const API_URL = 'https://your-backend-url.railway.app';

# 2. GitHub Pages 활성화
# Settings → Pages → Source: main branch, /frontend 폴더

# 3. 접속
# https://sinsangwoo.github.io/AIdiseaseclassifier/
```

### Vercel (무료, 추천)

```bash
# 1. Vercel CLI 설치
npm i -g vercel

# 2. 배포
cd frontend
vercel

# 3. 도메인 설정 (선택)
vercel --prod
```

### Netlify (무료)

```bash
# 1. Netlify CLI 설치
npm i -g netlify-cli

# 2. 배포
cd frontend
netlify deploy --prod
```

---

## 📊 모니터링 설정

### 1. Prometheus + Grafana (선택)

프로젝트에 이미 Prometheus 메트릭이 구현되어 있습니다.

**docker-compose.yml에 추가:**
```yaml
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
```

**prometheus.yml:**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-classifier'
    static_configs:
      - targets: ['app:5000']
```

자세한 내용은 [PHASE3-4_COMPLETE.md](PHASE3-4_COMPLETE.md) 참조.

### 2. 로그 수집

**Papertrail (무료 100MB/월):**
```bash
# 환경변수 추가
PAPERTRAIL_HOST=logs.papertrailapp.com
PAPERTRAIL_PORT=12345
```

---

## 🔧 문제 해결

### 문제 1: 메모리 부족 (OOM Killed)

**증상:**
```
Container killed due to memory usage
```

**해결:**
1. 플랫폼 메모리 증설 (최소 1GB 권장)
2. Gunicorn worker 수 감소: `--workers 2 --threads 2`
3. 모델 경량화 고려

### 문제 2: 배포 후 404 에러

**원인:** 프론트엔드 API URL 미설정

**해결:**
```javascript
// frontend/script.js
const API_URL = 'https://your-backend-url.com';  // 배포 URL로 변경
```

### 문제 3: CORS 에러

**원인:** CORS_ORIGINS 미설정

**해결:**
```python
# backend/.env
CORS_ORIGINS=https://your-frontend-url.com,https://sinsangwoo.github.io
```

### 문제 4: 모델 로드 실패

**증상:**
```
ModelLoadError: 모델 파일을 찾을 수 없습니다
```

**해결:**
```bash
# 모델 파일 경로 확인
ls -lh backend/models/

# 필수 파일:
# - model.onnx (2.1MB)
# - labels.txt
```

---

## 🎉 배포 완료 체크리스트

- [ ] 백엔드 배포 완료 및 헬스체크 통과
- [ ] 프론트엔드 배포 완료 및 API 연결 확인
- [ ] HTTPS 설정 완료
- [ ] CORS 설정 확인
- [ ] 모니터링 설정 (선택)
- [ ] 에러 알림 설정 (선택)
- [ ] 백업 전략 수립
- [ ] 도메인 연결 (선택)

---

## 📞 지원

문제가 발생하면 GitHub Issues에 등록해주세요:
https://github.com/sinsangwoo/AIdiseaseclassifier/issues

---

**작성자**: 신상우 (aksrkd7191@gmail.com)
**최종 수정**: 2026-02-05
