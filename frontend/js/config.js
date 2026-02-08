/**
 * 환경별 설정 관리 (Phase 2 개선)
 * 
 * - 환경별 API URL 자동 감지
 * - 재시도 로직 강화
 * - CORS 및 네트워크 에러 핸들링
 * - 이미지 최적화 설정 추가
 */

const CONFIG = {
  // ===== 환경 감지 및 API URL 설정 =====
  get API_BASE_URL() {
    // 1. 빌드 시 주입된 환경변수 우선 (GitHub Actions)
    if (window.ENV && window.ENV.API_URL) {
      return window.ENV.API_URL;
    }
    
    // 2. 호스트네임 기반 자동 감지
    const hostname = window.location.hostname;
    
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      // 로컬 개발 환경
      return 'http://127.0.0.1:5000';
    } else if (hostname.includes('github.io')) {
      // GitHub Pages 프로덕션 (Render 백엔드)
      return 'https://pneumonia-api-j3t8.onrender.com';
    } else {
      // 기타 환경 (기본값)
      return 'http://127.0.0.1:5000';
    }
  },
  
  // ===== API 엔드포인트 =====
  ENDPOINTS: {
    HEALTH: '/health',
    HEALTH_READY: '/health/ready',
    HEALTH_DETAILED: '/health/detailed',
    MODEL_INFO: '/model/info',
    PREDICT: '/predict'
  },
  
  // ===== 요청 설정 =====
  REQUEST: {
    TIMEOUT: 90000,
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000,
    RETRY_BACKOFF_MULTIPLIER: 2,
    RETRYABLE_STATUS_CODES: [408, 429, 500, 502, 503, 504],
    HEADERS: {
      'Accept': 'application/json',
    }
  },
  
  // ===== 파일 업로드 제한 =====
  FILE: {
    MAX_SIZE: 10 * 1024 * 1024,
    ALLOWED_TYPES: ['image/jpeg', 'image/jpg', 'image/png'],
    ALLOWED_EXTENSIONS: ['.jpg', '.jpeg', '.png'],
    OPTIMIZATION: {
      ENABLED: true,
      MAX_WIDTH: 1024,
      MAX_HEIGHT: 1024,
      QUALITY: 0.85,
      FORMAT: 'image/jpeg',
      MIN_SIZE_FOR_COMPRESSION: 500 * 1024
    }
  },
  
  // ===== UI 설정 =====
  UI: {
    PROGRESS_ANIMATION_SPEED: 300,
    TOAST_DURATION: 3000,
    DEBOUNCE_DELAY: 300,
    ERROR_DISPLAY_DURATION: 5000,
    LOADING_DELAY: 200
  },
  
  // ===== 환경 정보 =====
  get ENVIRONMENT() {
    if (window.ENV && window.ENV.ENVIRONMENT) {
      return window.ENV.ENVIRONMENT;
    }
    
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'development';
    } else if (hostname.includes('github.io')) {
      return 'production';
    } else {
      return 'unknown';
    }
  },
  
  // ===== 디버그 모드 =====
  get DEBUG() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('debug')) {
      return true;
    }
    return this.ENVIRONMENT === 'development';
  },
  
  // ===== 헬퍼 함수 =====
  getFullURL(endpoint) {
    return `${this.API_BASE_URL}${endpoint}`;
  },
  
  validateFileSize(size) {
    return size <= this.FILE.MAX_SIZE;
  },
  
  validateFileType(type) {
    return this.FILE.ALLOWED_TYPES.includes(type);
  },
  
  validateFileExtension(filename) {
    const extension = filename.toLowerCase().slice(filename.lastIndexOf('.'));
    return this.FILE.ALLOWED_EXTENSIONS.includes(extension);
  },
  
  shouldCompressImage(fileSize) {
    return this.FILE.OPTIMIZATION.ENABLED && 
           fileSize > this.FILE.OPTIMIZATION.MIN_SIZE_FOR_COMPRESSION;
  },
  
  isRetryableStatusCode(statusCode) {
    return this.REQUEST.RETRYABLE_STATUS_CODES.includes(statusCode);
  },
  
  getRetryDelay(attemptNumber) {
    return this.REQUEST.RETRY_DELAY * 
           Math.pow(this.REQUEST.RETRY_BACKOFF_MULTIPLIER, attemptNumber - 1);
  },
  
  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  },
  
  log(...args) {
    if (this.DEBUG) {
      console.log('[CONFIG]', ...args);
    }
  },
  
  error(...args) {
    console.error('[CONFIG ERROR]', ...args);
  },
  
  warn(...args) {
    if (this.DEBUG) {
      console.warn('[CONFIG WARN]', ...args);
    }
  }
};

CONFIG.log('=== 애플리케이션 설정 ===');
CONFIG.log('Environment:', CONFIG.ENVIRONMENT);
CONFIG.log('API Base URL:', CONFIG.API_BASE_URL);
CONFIG.log('Debug Mode:', CONFIG.DEBUG);
CONFIG.log('Image Optimization:', CONFIG.FILE.OPTIMIZATION.ENABLED ? 'ON' : 'OFF');
CONFIG.log('========================');

export default CONFIG;

if (typeof window !== 'undefined') {
  window.CONFIG = CONFIG;
}
