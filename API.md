# 📡 API 문서

AI Disease Classifier RESTful API 상세 문서

---

## 목차

- [개요](#개요)
- [인증](#인증)
- [엔드포인트](#엔드포인트)
- [에러 코드](#에러-코드)
- [Rate Limiting](#rate-limiting)
- [예제 코드](#예제-코드)

---

## 개요

### Base URL
```
http://localhost:5000
```

### Content Types
- Request: `multipart/form-data` (파일 업로드)
- Response: `application/json`

### 응답 형식
모든 API 응답은 다음 구조를 따릅니다:

**성공 응답:**
```json
{
  "success": true,
  "data": { ... },
  "message": "optional message"
}
```

**에러 응답:**
```json
{
  "success": false,
  "error": "error message",
  "error_type": "ErrorType",
  "details": { ... }
}
```

---

## 인증

현재 버전은 인증이 필요하지 않습니다. 향후 버전에서 API Key 기반 인증이 추가될 예정입니다.

---

## 엔드포인트

### 1. GET / - 서비스 정보

**요청:**
```bash
GET /
```

**응답:**
```json
{
  "service": "AI Disease Classifier API",
  "version": "5.0.0",
  "status": "running",
  "endpoints": {
    "health": "/health",
    "health_detailed": "/health/detailed",
    "model_info": "/model/info",
    "predict": "/predict"
  }
}
```

---

### 2. GET /health - 기본 헬스체크

서버가 정상 작동 중인지 빠르게 확인합니다.

**요청:**
```bash
GET /health
```

**응답 (200 OK):**
```json
{
  "status": "healthy",
  "model": "ready",
  "timestamp": "2026-01-29 21:50:00"
}
```

**응답 필드:**
- `status`: 전체 상태 (`healthy`, `degraded`, `unhealthy`)
- `model`: 모델 상태 (`ready`, `not_loaded`)
- `timestamp`: 서버 시작 시간

---

### 3. GET /health/detailed - 상세 헬스체크

시스템 리소스, 모델 상태, 의존성 등을 상세하게 확인합니다.

**요청:**
```bash
GET /health/detailed
```

**응답 (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-29 21:50:00",
  "uptime": {
    "uptime_seconds": 3600.5,
    "uptime_formatted": "1h 0m 0s",
    "start_time": "2026-01-29 20:50:00"
  },
  "system": {
    "status": "healthy",
    "cpu": {
      "usage_percent": 15.2,
      "count": 8
    },
    "memory": {
      "total_mb": 16384,
      "used_mb": 8192,
      "available_mb": 8192,
      "usage_percent": 50.0
    },
    "disk": {
      "total_gb": 500,
      "used_gb": 250,
      "free_gb": 250,
      "usage_percent": 50.0
    }
  },
  "model": {
    "status": "ready",
    "model_path": "model.onnx",
    "labels_path": "labels.txt",
    "num_classes": 3,
    "model_size_mb": 25.4
  },
  "dependencies": {
    "status": "healthy",
    "packages": {
      "flask": "3.1.1",
      "numpy": "2.2.6",
      "pillow": "11.3.0",
      "onnxruntime": "1.22.1"
    }
  }
}
```

**응답 필드:**
- `status`: 전체 상태
- `uptime`: 서버 가동 시간 정보
- `system`: CPU, 메모리, 디스크 사용량
- `model`: 모델 상태 및 정보
- `dependencies`: 주요 패키지 버전

**사용 사례:**
- 모니터링 시스템 연동
- 서버 상태 대시보드
- 디버깅

---

### 4. GET /model/info - 모델 정보

현재 로드된 모델의 정보를 조회합니다.

**요청:**
```bash
GET /model/info
```

**응답 (200 OK):**
```json
{
  "model_path": "model.onnx",
  "labels_path": "labels.txt",
  "num_classes": 3,
  "class_names": [
    "정상",
    "폐렴",
    "결핵"
  ]
}
```

**응답 필드:**
- `model_path`: 모델 파일 경로
- `labels_path`: 라벨 파일 경로
- `num_classes`: 클래스 수
- `class_names`: 클래스 이름 목록

**에러 (503 Service Unavailable):**
```json
{
  "success": false,
  "error": "모델이 로드되지 않았습니다",
  "error_type": "ModelNotLoadedError"
}
```

---

### 5. POST /predict - 이미지 예측 ⭐

이미지를 업로드하여 질병을 예측합니다.

**요청:**
```bash
POST /predict
Content-Type: multipart/form-data

file: <image_file>
```

**허용 형식:**
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)

**파일 제한:**
- 최대 크기: 10MB
- 이미지 크기: 32x32 ~ 4096x4096 픽셀
- 가로세로 비율: 최대 10:1

**cURL 예시:**
```bash
curl -X POST http://localhost:5000/predict \
  -F "file=@chest_xray.jpg"
```

**Python 예시:**
```python
import requests

url = "http://localhost:5000/predict"
files = {"file": open("chest_xray.jpg", "rb")}

response = requests.post(url, files=files)
print(response.json())
```

**JavaScript 예시:**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:5000/predict', {
  method: 'POST',
  body: formData
})
  .then(res => res.json())
  .then(data => console.log(data));
```

**성공 응답 (200 OK):**
```json
{
  "success": true,
  "predictions": [
    {
      "className": "정상",
      "probability": 0.8542
    },
    {
      "className": "폐렴",
      "probability": 0.1203
    },
    {
      "className": "결핵",
      "probability": 0.0255
    }
  ],
  "metadata": {
    "processing_time_ms": 123.45,
    "image_size": [224, 224],
    "filename": "chest_xray.jpg"
  }
}
```

**응답 필드:**
- `success`: 성공 여부
- `predictions`: 예측 결과 배열 (확률 내림차순 정렬)
  - `className`: 질병 이름
  - `probability`: 확률 (0~1)
- `metadata`: 메타데이터
  - `processing_time_ms`: 처리 시간 (밀리초)
  - `image_size`: 전처리 후 이미지 크기
  - `filename`: 업로드된 파일명

---

## 에러 코드

### HTTP 상태 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 성공 |
| 400 | Bad Request | 잘못된 요청 (파일 검증 실패) |
| 404 | Not Found | 엔드포인트 없음 |
| 405 | Method Not Allowed | 허용되지 않는 HTTP 메소드 |
| 413 | Payload Too Large | 파일 크기 초과 (10MB) |
| 422 | Unprocessable Entity | 이미지 처리 실패 |
| 500 | Internal Server Error | 서버 내부 오류 |
| 503 | Service Unavailable | 모델 미준비 |

### 커스텀 에러 타입

#### ModelNotLoadedError (503)
```json
{
  "success": false,
  "error": "모델이 로드되지 않았습니다. 서버를 다시 시작해주세요",
  "error_type": "ModelNotLoadedError"
}
```

**원인:** 모델 파일이 로드되지 않음  
**해결:** 서버 재시작 또는 모델 파일 경로 확인

#### FileValidationError (400)
```json
{
  "success": false,
  "error": "요청에 파일이 없습니다",
  "error_type": "FileValidationError"
}
```

**원인:** 파일이 업로드되지 않음  
**해결:** `file` 필드에 이미지 파일 업로드

#### InvalidImageError (400)
```json
{
  "success": false,
  "error": "지원하지 않는 파일 형식입니다. JPG, JPEG, PNG만 허용됩니다",
  "error_type": "InvalidImageError"
}
```

**원인:** 
- 잘못된 파일 형식
- 손상된 이미지
- 너무 작거나 큰 이미지
- 비정상적인 가로세로 비율

**해결:** 올바른 이미지 파일 업로드

#### ImageProcessingError (422)
```json
{
  "success": false,
  "error": "이미지 전처리에 실패했습니다",
  "error_type": "ImageProcessingError"
}
```

**원인:** 이미지 리사이징 또는 정규화 실패  
**해결:** 다른 이미지로 시도

#### PredictionError (500)
```json
{
  "success": false,
  "error": "예측 중 오류가 발생했습니다",
  "error_type": "PredictionError"
}
```

**원인:** 모델 추론 중 오류  
**해결:** 서버 로그 확인

#### FileTooLargeError (413)
```json
{
  "success": false,
  "error": "파일 크기가 너무 큽니다. 최대 10MB까지 허용됩니다",
  "error_type": "FileTooLargeError"
}
```

**원인:** 10MB 초과  
**해결:** 파일 크기 줄이기

---

## Rate Limiting

현재 버전은 Rate Limiting이 적용되지 않았습니다. 

향후 버전에서 추가될 예정:
- API Key 기반 제한
- IP 기반 제한
- 시간당 요청 수 제한

---

## 예제 코드

### Python (requests)
```python
import requests
import json

def predict_disease(image_path):
    """이미지를 업로드하여 질병 예측"""
    url = "http://localhost:5000/predict"
    
    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        result = response.json()
        if result["success"]:
            predictions = result["predictions"]
            top_pred = predictions[0]
            
            print(f"질병: {top_pred['className']}")
            print(f"확률: {top_pred['probability']:.2%}")
            print(f"처리 시간: {result['metadata']['processing_time_ms']:.0f}ms")
        else:
            print(f"에러: {result['error']}")
    else:
        print(f"HTTP 에러: {response.status_code}")

# 사용 예시
predict_disease("chest_xray.jpg")
```

### JavaScript (Fetch API)
```javascript
async function predictDisease(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('http://localhost:5000/predict', {
      method: 'POST',
      body: formData
    });

    const result = await response.json();

    if (result.success) {
      const topPrediction = result.predictions[0];
      console.log(`질병: ${topPrediction.className}`);
      console.log(`확률: ${(topPrediction.probability * 100).toFixed(2)}%`);
      console.log(`처리 시간: ${result.metadata.processing_time_ms.toFixed(0)}ms`);
    } else {
      console.error(`에러: ${result.error}`);
    }
  } catch (error) {
    console.error('네트워크 에러:', error);
  }
}

// 사용 예시 (파일 입력에서)
const fileInput = document.getElementById('fileInput');
fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) {
    predictDisease(file);
  }
});
```

### cURL
```bash
# 기본 예측
curl -X POST http://localhost:5000/predict \
  -F "file=@chest_xray.jpg"

# 결과를 jq로 포맷팅
curl -X POST http://localhost:5000/predict \
  -F "file=@chest_xray.jpg" | jq

# 처리 시간만 출력
curl -X POST http://localhost:5000/predict \
  -F "file=@chest_xray.jpg" | jq '.metadata.processing_time_ms'
```

---

## 추가 정보

### 이미지 전처리
업로드된 이미지는 다음과 같이 전처리됩니다:

1. **리사이징**: 224x224 픽셀로 조정
2. **정규화**: RGB 값을 0~1 범위로 정규화
3. **배치 차원 추가**: (1, 3, 224, 224) 형태로 변환

### 모델 정보
- **프레임워크**: ONNX Runtime 1.22
- **입력 형태**: (1, 3, 224, 224) - NCHW 포맷
- **출력 형태**: (1, num_classes)
- **활성화 함수**: Softmax

### 보안 고려사항
- 모든 업로드된 이미지는 4단계 검증을 거칩니다
- 메모리 소진 공격 방지를 위한 크기 제한
- 파일 형식 위장 공격 방지 (매직 바이트 검증)

---

**문서 버전**: 5.0.0  
**최종 업데이트**: 2026-01-30
