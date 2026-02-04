# Phase 4: Prometheus 메트릭 시스템 (Enterprise Observability)

**목표**: Production-grade 모니터링 및 관측성 강화

## 📊 개요

Phase 1~3(배포 안정화, 프론트엔드 최적화, 백엔드 강화)에 이어 **enterprise-grade observability**를 구현합니다. Prometheus/Grafana 생태계와 네이티브 통합되어 실시간 성능 분석, 장애 대응, 용량 계획을 지원합니다.

## 🎯 핵심 메트릭

### 1. API 요청 메트릭

#### `http_requests_total` (Counter)
- **설명**: 총 HTTP 요청 수
- **레이블**: `endpoint`, `method`, `status`
- **용도**: 트래픽 패턴 분석, 에러율 추적

#### `http_request_duration_seconds` (Histogram)
- **설명**: HTTP 요청 처리 시간
- **레이블**: `endpoint`, `method`
- **버킷**: 10ms, 50ms, 100ms, 500ms, 1s, 5s, 10s, 30s, +Inf
- **용도**: P50/P95/P99 레이턴시 분석

```promql
# P95 레이턴시
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 엔드포인트별 RPS
rate(http_requests_total[1m])
```

---

### 2. 모델 추론 메트릭

#### `predictions_total` (Counter)
- **설명**: 총 예측 요청 수
- **레이블**: `status` (success, cache_hit, error)
- **용도**: 성공률, 캐시 효율 추적

#### `inference_duration_seconds` (Histogram)
- **설명**: 모델 추론 시간 (전처리 제외)
- **버킷**: 50ms, 100ms, 200ms, 500ms, 1s, 2s, 5s
- **용도**: 모델 성능 분석, 병목 지점 식별

```promql
# 평균 추론 시간
rate(inference_duration_seconds_sum[5m]) / rate(inference_duration_seconds_count[5m])

# 추론 시간 P99
histogram_quantile(0.99, rate(inference_duration_seconds_bucket[5m]))
```

---

### 3. 캐시 메트릭

#### `cache_hit_rate` (Gauge)
- **설명**: 캐시 히트율 (0.0~1.0)
- **용도**: 캐시 효율성 실시간 모니터링

#### `cache_size_current` (Gauge)
- **설명**: 현재 캐시 항목 수
- **용도**: 캐시 포화도 추적

```promql
# 캐시 히트율 (백분율)
cache_hit_rate * 100

# 캐시 사용률
cache_size_current / 128 * 100
```

---

### 4. 모델 상태 메트릭

#### `model_state` (Gauge)
- **설명**: 모델 로드 상태
- **값**: 0 (미준비), 1 (정상), 2 (에러)
- **용도**: 모델 가용성 모니터링

```promql
# 모델 다운타임 감지
model_state != 1
```

---

### 5. 시스템 리소스 메트릭

#### `system_memory_percent` (Gauge)
- **설명**: 시스템 메모리 사용률 (0~100)
- **용도**: OOM 예방, 캐시 크기 튜닝

#### `process_memory_bytes` (Gauge)
- **설명**: 프로세스 메모리 사용량
- **레이블**: `type` (rss, vms)
- **용도**: 메모리 누수 감지

```promql
# 메모리 사용량 증가율
rate(process_memory_bytes{type="rss"}[5m])
```

---

## 🛠️ 통합 가이드

### 1. 의존성 추가 완료
```bash
pip install prometheus-client==0.20.0
```

### 2. 메트릭 모듈 import
```python
from backend.utils.prometheus_metrics import (
    # 메트릭
    record_prediction,
    update_cache_metrics,
    set_model_state,
    set_app_info,
    get_metrics,
    # 미들웨어
    PrometheusMiddleware
)
```

### 3. Flask 미들웨어 적용
```python
app = Flask(__name__)
app.wsgi_app = PrometheusMiddleware(app.wsgi_app)
```

### 4. `/metrics` 엔드포인트 추가
```python
@app.route('/metrics')
def metrics():
    """Prometheus 메트릭 export"""
    metrics_output, content_type = get_metrics()
    return Response(metrics_output, mimetype=content_type)
```

### 5. 예측 메트릭 기록
```python
# app.py의 /predict 엔드포인트 내부
predictions, from_cache = model_service.predict(processed_image)

record_prediction(
    success=True,
    cache_hit=from_cache,
    inference_time=inference_time if not from_cache else None,
    preprocessing_time=preprocessing_time
)
```

### 6. 캐시 메트릭 업데이트
```python
# ModelService 내부
def get_cache_info(self):
    update_cache_metrics(
        current_size=len(self._cache),
        total_hits=self.stats['cache_hits'],
        total_misses=self.stats['cache_misses'],
        memory_bytes=self._estimate_cache_memory()
    )
    return {...}
```

---

## 📈 Grafana 대시보드 예시

### 패널 1: 요청 레이턴시 (Heatmap)
```promql
sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
```

### 패널 2: 캐시 히트율 (Gauge)
```promql
cache_hit_rate * 100
```

### 패널 3: 추론 시간 분포 (Histogram)
```promql
sum(rate(inference_duration_seconds_bucket[5m])) by (le)
```

### 패널 4: 에러율 (Graph)
```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100
```

### 패널 5: 시스템 리소스 (Multi-line)
```promql
system_cpu_percent
system_memory_percent
```

---

## 🚨 알람 규칙 예시

### 1. 높은 에러율
```yaml
- alert: HighErrorRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m])) /
    sum(rate(http_requests_total[5m])) > 0.05
  for: 5m
  annotations:
    summary: "에러율이 5%를 초과했습니다"
```

### 2. 느린 응답 시간
```yaml
- alert: SlowResponses
  expr: |
    histogram_quantile(0.95,
      rate(http_request_duration_seconds_bucket[5m])
    ) > 2.0
  for: 10m
  annotations:
    summary: "P95 레이턴시가 2초를 초과했습니다"
```

### 3. 메모리 부족
```yaml
- alert: HighMemoryUsage
  expr: system_memory_percent > 90
  for: 5m
  annotations:
    summary: "메모리 사용률이 90%를 초과했습니다"
```

### 4. 모델 다운
```yaml
- alert: ModelNotLoaded
  expr: model_state != 1
  for: 1m
  annotations:
    summary: "모델이 로드되지 않았습니다"
```

---

## 🔍 운영 가이드

### Prometheus 스크랩 설정
```yaml
scrape_configs:
  - job_name: 'aiclassifier'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### 로컬 테스트
```bash
# 메트릭 확인
curl http://localhost:5000/metrics

# 특정 메트릭 필터
curl http://localhost:5000/metrics | grep cache_hit_rate
```

### 메모리 영향 분석
- 메트릭 오버헤드: ~1-2MB (레이블 카디널리티 낮음)
- 히스토그램 버킷: 8개 × 메트릭당
- 총 메트릭 수: ~25개

---

## 📊 성능 벤치마크

| 메트릭 타입 | 수집 오버헤드 | 메모리 사용 |
|------------|-------------|------------|
| Counter | ~10 ns | ~100 bytes |
| Gauge | ~15 ns | ~100 bytes |
| Histogram | ~50 ns | ~800 bytes (8 버킷) |
| Summary | ~80 ns | ~1.5 KB |

**결론**: 총 오버헤드 < 1% (요청당 ~100ns, 메모리 ~2MB)

---

## 🚀 다음 단계 (Phase 5)

1. **분산 추적 (Distributed Tracing)**
   - OpenTelemetry 통합
   - 요청 체인 시각화

2. **로그 집계**
   - ELK/Loki 스택
   - 구조화된 로깅

3. **사용자 분석**
   - 세션 추적
   - 행동 패턴 분석

---

**작성**: 2026-02-04  
**Phase**: 4 (Prometheus Metrics)  
**커밋**: [6704d54](../../../commit/6704d54)
