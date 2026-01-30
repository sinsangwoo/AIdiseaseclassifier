# 🚀 배포 가이드

AI Disease Classifier를 프로덕션 환경에 배포하는 완벽한 가이드

---

## 목차

- [배포 옵션](#배포-옵션)
- [로컬 배포](#로컬-배포)
- [Docker 배포](#docker-배포)
- [클라우드 배포](#클라우드-배포)
- [환경 설정](#환경-설정)
- [모니터링 & 로깅](#모니터링--로깅)
- [보안 설정](#보안-설정)
- [성능 최적화](#성능-최적화)
- [백업 & 복구](#백업--복구)
- [문제 해결](#문제-해결)

---

## 배포 옵션

### 1. 로컬 서버
- **난이도**: ⭐
- **비용**: 무료
- **용도**: 개발, 테스트
- **확장성**: 낮음

### 2. Docker + VPS
- **난이도**: ⭐⭐
- **비용**: 월 $5~20
- **용도**: 소규모 프로덕션
- **확장성**: 중간

### 3. Kubernetes
- **난이도**: ⭐⭐⭐⭐
- **비용**: 월 $50+
- **용도**: 대규모 프로덕션
- **확장성**: 높음

### 4. 서버리스 (AWS Lambda, Google Cloud Run)
- **난이도**: ⭐⭐⭐
- **비용**: 사용량 기반
- **용도**: 불규칙한 트래픽
- **확장성**: 자동

---

## 로컬 배포

### 개발 서버 (Flask 내장)

```bash
# 1. 환경 설정
export FLASK_ENV=development
export DEBUG=True

# 2. 실행
python backend/app.py
```

**특징:**
- ✅ 빠른 재시작
- ✅ 자동 리로드
- ❌ 단일 워커
- ❌ 낮은 성능

### 프로덕션 서버 (Gunicorn)

```bash
# 1. Gunicorn 설치
pip install gunicorn

# 2. 실행
gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --threads 2 \
  --worker-class gthread \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  backend.app:app
```

**워커 수 계산:**
```
권장 워커 수 = (2 × CPU 코어 수) + 1
예: 4 코어 → (2 × 4) + 1 = 9 워커
```

### Systemd 서비스 등록

```bash
# 1. 서비스 파일 생성
sudo nano /etc/systemd/system/ai-classifier.service
```

```ini
[Unit]
Description=AI Disease Classifier
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/ai-classifier
Environment="PATH=/opt/ai-classifier/venv/bin"
ExecStart=/opt/ai-classifier/venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    backend.app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 2. 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable ai-classifier
sudo systemctl start ai-classifier

# 3. 상태 확인
sudo systemctl status ai-classifier

# 4. 로그 확인
sudo journalctl -u ai-classifier -f
```

---

## Docker 배포

### 단일 컨테이너

```bash
# 1. 이미지 빌드
docker build -t ai-classifier:latest .

# 2. 컨테이너 실행
docker run -d \
  --name ai-classifier \
  --restart unless-stopped \
  -p 5000:5000 \
  -e SECRET_KEY="your-production-secret-key" \
  -e FLASK_ENV=production \
  -e CORS_ORIGINS="https://yourdomain.com" \
  -v $(pwd)/model.onnx:/app/model.onnx:ro \
  -v $(pwd)/labels.txt:/app/labels.txt:ro \
  -v $(pwd)/logs:/app/logs \
  --memory="2g" \
  --cpus="2" \
  ai-classifier:latest

# 3. 로그 확인
docker logs -f ai-classifier

# 4. 헬스체크
curl http://localhost:5000/health
```

### Docker Compose (권장)

```bash
# 1. docker-compose.yml 생성 (이미 제공됨)

# 2. 환경변수 설정
cat > .env << EOF
SECRET_KEY=your-production-secret-key
CORS_ORIGINS=https://yourdomain.com
FLASK_ENV=production
LOG_LEVEL=INFO
EOF

# 3. 실행
docker-compose up -d

# 4. 확인
docker-compose ps
docker-compose logs -f app

# 5. 스케일링 (필요시)
docker-compose up -d --scale app=3
```

### Nginx 리버스 프록시 포함

```bash
# 1. Nginx 설정 생성
mkdir -p nginx
cat > nginx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream app {
        least_conn;
        server app:5000;
    }

    server {
        listen 80;
        server_name yourdomain.com;

        client_max_body_size 10M;

        location / {
            proxy_pass http://app;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location /health {
            proxy_pass http://app/health;
            access_log off;
        }
    }
}
EOF

# 2. Nginx 포함하여 실행
docker-compose --profile with-nginx up -d
```

---

## 클라우드 배포

### AWS EC2 + Docker

```bash
# 1. EC2 인스턴스 생성
# - Ubuntu 22.04 LTS
# - t2.medium (2 vCPU, 4GB RAM) 이상
# - Security Group: 80, 443, 5000 포트 오픈

# 2. 서버 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 3. Docker 설치
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu
newgrp docker

# 4. 프로젝트 배포
git clone https://github.com/sinsangwoo/AIdiseaseclassifier.git
cd AIdiseaseclassifier

# 5. Docker Compose 실행
docker-compose up -d

# 6. Nginx 설치 (선택)
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/ai-classifier
```

### Google Cloud Run

```bash
# 1. gcloud CLI 설치 및 인증
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Dockerfile 확인

# 3. 이미지 빌드 및 푸시
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ai-classifier

# 4. Cloud Run 배포
gcloud run deploy ai-classifier \
  --image gcr.io/YOUR_PROJECT_ID/ai-classifier \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10
```

### Azure Container Instances

```bash
# 1. Azure CLI 로그인
az login

# 2. 리소스 그룹 생성
az group create --name ai-classifier-rg --location eastus

# 3. 컨테이너 레지스트리 생성
az acr create --resource-group ai-classifier-rg \
  --name aiclassifieracr --sku Basic

# 4. 이미지 빌드 및 푸시
az acr build --registry aiclassifieracr \
  --image ai-classifier:latest .

# 5. 컨테이너 인스턴스 생성
az container create \
  --resource-group ai-classifier-rg \
  --name ai-classifier \
  --image aiclassifieracr.azurecr.io/ai-classifier:latest \
  --dns-name-label ai-classifier \
  --ports 5000 \
  --cpu 2 --memory 4
```

---

## 환경 설정

### 프로덕션 환경변수

```bash
# .env.production
FLASK_ENV=production
DEBUG=False
SECRET_KEY=<64자 이상의 랜덤 문자열>

# 모델
MODEL_PATH=/app/model.onnx
LABELS_PATH=/app/labels.txt

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 로그
LOG_LEVEL=INFO
LOG_DIR=/app/logs

# 파일 업로드
MAX_CONTENT_LENGTH=10485760

# Gunicorn
WORKERS=4
THREADS=2
TIMEOUT=30
```

### SECRET_KEY 생성

```python
# Python으로 안전한 SECRET_KEY 생성
import secrets
print(secrets.token_urlsafe(64))
```

```bash
# 또는 OpenSSL 사용
openssl rand -hex 64
```

---

## 모니터링 & 로깅

### 로그 관리

```bash
# 1. 로그 디렉토리 생성
mkdir -p logs

# 2. 로그 확인
tail -f logs/app.log

# 3. 로그 로테이션 (logrotate)
sudo nano /etc/logrotate.d/ai-classifier
```

```
/opt/ai-classifier/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
}
```

### Prometheus + Grafana (선택)

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-classifier'
    static_configs:
      - targets: ['app:5000']
```

### 헬스체크 모니터링

```bash
# 1. 헬스체크 스크립트
cat > healthcheck.sh << 'EOF'
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
if [ $response -eq 200 ]; then
  echo "OK"
  exit 0
else
  echo "FAIL: HTTP $response"
  exit 1
fi
EOF

chmod +x healthcheck.sh

# 2. Cron으로 주기적 체크
crontab -e
*/5 * * * * /opt/ai-classifier/healthcheck.sh || /usr/bin/systemctl restart ai-classifier
```

---

## 보안 설정

### HTTPS 설정 (Let's Encrypt)

```bash
# 1. Certbot 설치
sudo apt install -y certbot python3-certbot-nginx

# 2. 인증서 발급
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 3. 자동 갱신 설정
sudo crontab -e
0 3 * * * /usr/bin/certbot renew --quiet
```

### 방화벽 설정 (UFW)

```bash
# 1. UFW 설치
sudo apt install -y ufw

# 2. 규칙 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 3. 활성화
sudo ufw enable
sudo ufw status
```

### 환경변수 보안

```bash
# 민감한 정보는 환경변수나 Secret Manager 사용
# .env 파일은 .gitignore에 추가
echo ".env" >> .gitignore
```

---

## 성능 최적화

### Gunicorn 튜닝

```bash
# CPU 바운드 작업
gunicorn --workers 4 --threads 1 --worker-class sync backend.app:app

# I/O 바운드 작업
gunicorn --workers 2 --threads 4 --worker-class gthread backend.app:app

# 비동기 처리
gunicorn --workers 4 --worker-class gevent --worker-connections 1000 backend.app:app
```

### Docker 리소스 제한

```yaml
# docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 캐싱 전략

```python
# Flask-Caching 추가 (선택)
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@cache.cached(timeout=300)
def expensive_function():
    pass
```

---

## 백업 & 복구

### 백업 전략

```bash
# 1. 자동 백업 스크립트
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backup/$DATE

mkdir -p $BACKUP_DIR
cp model.onnx $BACKUP_DIR/
cp labels.txt $BACKUP_DIR/
cp -r logs $BACKUP_DIR/
tar -czf /backup/backup_$DATE.tar.gz -C /backup $DATE
rm -rf $BACKUP_DIR

# 7일 이상 된 백업 삭제
find /backup -name "backup_*.tar.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# 2. Cron 등록 (매일 새벽 3시)
0 3 * * * /opt/ai-classifier/backup.sh
```

### 복구 절차

```bash
# 1. 최신 백업 찾기
LATEST_BACKUP=$(ls -t /backup/backup_*.tar.gz | head -1)

# 2. 복구
tar -xzf $LATEST_BACKUP -C /tmp
cp /tmp/backup_*/model.onnx /opt/ai-classifier/
cp /tmp/backup_*/labels.txt /opt/ai-classifier/

# 3. 서비스 재시작
sudo systemctl restart ai-classifier
```

---

## 문제 해결

### 서비스가 시작되지 않음

```bash
# 1. 로그 확인
sudo journalctl -u ai-classifier -n 100

# 2. 포트 충돌 확인
sudo lsof -i :5000

# 3. 권한 확인
ls -la /opt/ai-classifier
```

### 높은 메모리 사용량

```bash
# 1. 워커 수 감소
gunicorn --workers 2 --threads 2 backend.app:app

# 2. Docker 메모리 제한
docker update --memory 1g ai-classifier
```

### 느린 응답 시간

```bash
# 1. 헬스체크 확인
curl http://localhost:5000/health/detailed | jq '.system'

# 2. 로그 확인
tail -f logs/app.log | grep "processing_time"

# 3. 워커 수 증가 (CPU 여유가 있다면)
gunicorn --workers 8 backend.app:app
```

---

## 체크리스트

### 배포 전

- [ ] 환경변수 설정 완료
- [ ] SECRET_KEY 생성 및 설정
- [ ] CORS 설정 확인
- [ ] 모델 파일 준비 (model.onnx, labels.txt)
- [ ] 로그 디렉토리 생성
- [ ] 방화벽 규칙 설정
- [ ] 테스트 실행 (pytest)

### 배포 후

- [ ] 헬스체크 확인 (`/health`)
- [ ] 예측 API 테스트 (`/predict`)
- [ ] 로그 확인
- [ ] 모니터링 설정
- [ ] 백업 설정
- [ ] SSL/TLS 인증서 설정 (프로덕션)
- [ ] 도메인 연결

---

**문서 버전**: 5.0.0  
**최종 업데이트**: 2026-01-30
