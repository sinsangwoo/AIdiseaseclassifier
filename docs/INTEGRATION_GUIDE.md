# Prometheus 메트릭 통합 가이드

## 빠른 시작 (3단계)

### 1단계: 의존성 설치 확인
```bash
pip install prometheus-client==0.20.0
```

### 2단계: /metrics 엔드포인트 추가

`backend/app.py`에 다음 추가:

```python
# 상단 import 섹션
from flask import Response
from backend.utils.prometheus_metrics import get_metrics, set_app_info, set_model_state

# 라우트 섹션 (create_app 함수 내부)
@app.route('/metrics')
def metrics():
    """Prometheus 메트릭 export"""
    metrics_output, content_type = get_metrics()
    return Response(metrics_output, mimetype=content_type)
```

### 3단계: 앱 메타데이터 설정

`create_app()` 함수 내부, 모델 로드 후:

```python
# 모델 로드 성공 시
if PROMETHEUS_AVAILABLE:
    set_app_info(
        version='1.0.0',
        environment=config_name or 'default',
        python_version=sys.version.split()[0]
    )
    set_model_state('loaded', load_time=load_duration)

# 모델 로드 실패 시
if PROMETHEUS_AVAILABLE:
    set_model_state('error')
```

---

## 메트릭 확인

```bash
# 로컬 개발 서버 시작
python backend/app.py

# 메트릭 확인
curl http://localhost:5000/metrics
```

---

## 예상 출력

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/predict",method="POST",status="200"} 42.0

# HELP cache_hit_rate Cache hit rate (0.0 to 1.0)
# TYPE cache_hit_rate gauge
cache_hit_rate 0.67

# HELP model_state Model state (0=not_loaded, 1=loaded, 2=error)
# TYPE model_state gauge
model_state 1.0
```

---

## Prometheus 스크랩 설정

`prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'aiclassifier'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

---

## 옵션: 예측 메트릭 기록

`/predict` 엔드포인트에 메트릭 기록 추가:

```python
from backend.utils.prometheus_metrics import record_prediction

# 예측 성공 후
record_prediction(
    success=True,
    cache_hit=from_cache,
    inference_time=inference_time if not from_cache else None,
    preprocessing_time=preprocessing_time
)
```

---

## 문제 해결

### prometheus_client ImportError
```bash
pip install prometheus-client==0.20.0
```

### /metrics 404 에러
- `@app.route('/metrics')` 엔드포인트가 추가되었는지 확인
- Flask 앱 재시작

### 빈 메트릭 출력
- 앱 트래픽 생성 (예: `/predict` 호출)
- `set_app_info()` 호출 확인

---

**최소 침습적 통합**: 기존 코드 변경 최소화, 선택적 활성화 가능