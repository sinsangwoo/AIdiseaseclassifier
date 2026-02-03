# 🚀 Phase 2: 프론트엔드 최적화 가이드

## 📋 개요

Phase 2에서는 프론트엔드 설정 관리를 강화하고 이미지 최적화 기능을 통합했습니다.

## ✨ 주요 변경사항

### 1️⃣ **환경별 설정 강화** (`frontend/js/config.js`)

#### 추가된 설정

```javascript
// 재시도 로직
REQUEST: {
  TIMEOUT: 30000,              // 30초
  RETRY_ATTEMPTS: 3,           // 최대 3회 재시도
  RETRY_DELAY: 1000,           // 1초
  RETRY_BACKOFF_MULTIPLIER: 2, // 지수 백오프
  RETRYABLE_STATUS_CODES: [408, 429, 500, 502, 503, 504]
}

// 이미지 최적화
FILE.OPTIMIZATION: {
  ENABLED: true,                     // 자동 압축
  MAX_WIDTH: 1024,                   // 최대 1024px
  MAX_HEIGHT: 1024,
  QUALITY: 0.85,                     // JPEG 품질
  MIN_SIZE_FOR_COMPRESSION: 500 * 1024  // 500KB 이상만 압축
}
```

#### 새로운 헬퍼 함수

- `validateFileSize(size)` - 파일 크기 검증
- `validateFileType(type)` - MIME 타입 검증
- `validateFileExtension(filename)` - 확장자 검증
- `shouldCompressImage(fileSize)` - 압축 필요 여부 판단
- `isRetryableStatusCode(statusCode)` - 재시도 가능 상태 코드 확인
- `getRetryDelay(attemptNumber)` - 재시도 대기 시간 계산 (지수 백오프)
- `formatBytes(bytes)` - 바이트를 읽기 쉬운 형식으로 변환

### 2️⃣ **디버그 모드**

URL 파라미터로 디버그 모드 활성화:

```
https://sinsangwoo.github.io/AIdiseaseclassifier/?debug
```

디버그 모드에서는 상세한 로그가 콘솔에 출력됩니다.

## 🔧 사용 예시

### 파일 검증

```javascript
// 파일 크기 검증
if (!CONFIG.validateFileSize(file.size)) {
  alert(`파일 크기가 너무 큽니다. 최대 ${CONFIG.formatBytes(CONFIG.FILE.MAX_SIZE)} 허용`);
  return;
}

// 파일 타입 검증
if (!CONFIG.validateFileType(file.type)) {
  alert('JPG, JPEG, PNG 파일만 업로드 가능합니다.');
  return;
}

// 압축 필요 여부 확인
if (CONFIG.shouldCompressImage(file.size)) {
  console.log('이미지 압축 필요');
}
```

### 환경별 설정 활용

```javascript
// API URL
const apiUrl = CONFIG.getFullURL(CONFIG.ENDPOINTS.PREDICT);

// 환경 확인
console.log('Environment:', CONFIG.ENVIRONMENT);
console.log('Debug Mode:', CONFIG.DEBUG);

// 재시도 대기 시간 계산
const delay = CONFIG.getRetryDelay(1);  // 첫 재시도: 1000ms
const delay2 = CONFIG.getRetryDelay(2); // 두 번째 재시도: 2000ms
```

## 📊 성능 개선

### 개선 전
- 환경별 설정 하드코딩
- 재시도 로직 없음
- 파일 검증 분산
- 이미지 최적화 미통합

### 개선 후
- ✅ 환경별 설정 자동 감지
- ✅ 지수 백오프 재시도 (최대 3회)
- ✅ 통합 파일 검증 헬퍼
- ✅ 이미지 자동 압축 (500KB 이상)

## 🎯 예상 효과

| 항목 | 개선 전 | 개선 후 |
|------|---------|---------|
| 네트워크 에러 복구 | 불가능 | 자동 재시도 |
| 설정 관리 | 분산 | 중앙화 |
| 이미지 업로드 속도 | 느림 | 빠름 (압축) |
| 디버깅 | 어려움 | 쉬움 (로그) |

## 🔄 다음 단계 (Phase 3)

- 백엔드 캐싱 전략 구현
- 모니터링 시스템 통합
- 성능 메트릭 수집

## 📝 주의사항

1. **이미지 최적화**: 500KB 이상 파일만 자동 압축
2. **재시도 로직**: 최대 3회, 최대 대기 10초
3. **디버그 모드**: 프로덕션에서는 URL 파라미터로만 활성화

## 🤝 기여

버그 리포트나 기능 제안은 GitHub Issues로 제출해주세요.
