/**
 * 환경변수 기반 설정 관리
 */

const CONFIG = {
  get API_BASE_URL() {
    if (window.ENV && window.ENV.API_URL) return window.ENV.API_URL;
    const h = window.location.hostname;
    if (h === 'localhost' || h === '127.0.0.1') return 'http://127.0.0.1:5000';
    if (h.includes('github.io'))              return 'https://pneumonia-api-j3t8.onrender.com';
    return 'http://127.0.0.1:5000';
  },

  ENDPOINTS: {
    HEALTH:          '/health',
    HEALTH_READY:    '/health/ready',
    HEALTH_DETAILED: '/health/detailed',
    MODEL_INFO:      '/model/info',
    PREDICT:         '/predict'
  },

  REQUEST: {
    // TIMEOUT: predict 요청의 블로즈 타임아웃 (180초)
    TIMEOUT: 180000,

    // RETRY_ATTEMPTS: predict CORS/네트워크 실패 시 서버 재시작 과도기를 커버하도록 3회
    // (RETRY_ATTEMPTS: 1 이면 단 1번 ERR_FAILED 만으로 에러가 사용자에게 표시됨)
    RETRY_ATTEMPTS: 3,

    // RETRY_DELAY: 첫 번째 재시도 전 10초 대기 (서버 재시작 후 준비 시간)
    RETRY_DELAY: 10000,

    RETRY_BACKOFF_MULTIPLIER: 1.5,
    RETRYABLE_STATUS_CODES: [0, 408, 429, 500, 502, 503, 504],
    HEADERS: { 'Accept': 'application/json' }
  },

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

  UI: {
    PROGRESS_ANIMATION_SPEED: 300,
    TOAST_DURATION: 3000,
    DEBOUNCE_DELAY: 300,
    ERROR_DISPLAY_DURATION: 5000,
    LOADING_DELAY: 200
  },

  get ENVIRONMENT() {
    if (window.ENV && window.ENV.ENVIRONMENT) return window.ENV.ENVIRONMENT;
    const h = window.location.hostname;
    if (h === 'localhost' || h === '127.0.0.1') return 'development';
    if (h.includes('github.io'))              return 'production';
    return 'unknown';
  },

  get DEBUG() {
    const p = new URLSearchParams(window.location.search);
    return p.has('debug') || this.ENVIRONMENT === 'development';
  },

  getFullURL(ep)       { return `${this.API_BASE_URL}${ep}`; },
  validateFileSize(s)  { return s <= this.FILE.MAX_SIZE; },
  validateFileType(t)  { return this.FILE.ALLOWED_TYPES.includes(t); },
  validateFileExtension(f) {
    const ext = f.toLowerCase().slice(f.lastIndexOf('.'));
    return this.FILE.ALLOWED_EXTENSIONS.includes(ext);
  },
  shouldCompressImage(s) {
    return this.FILE.OPTIMIZATION.ENABLED && s > this.FILE.OPTIMIZATION.MIN_SIZE_FOR_COMPRESSION;
  },
  isRetryableStatusCode(c) { return this.REQUEST.RETRYABLE_STATUS_CODES.includes(c); },
  getRetryDelay(n) {
    return this.REQUEST.RETRY_DELAY * Math.pow(this.REQUEST.RETRY_BACKOFF_MULTIPLIER, n - 1);
  },
  formatBytes(b) {
    if (b === 0) return '0 Bytes';
    const k = 1024, s = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(b) / Math.log(k));
    return Math.round(b / Math.pow(k, i) * 100) / 100 + ' ' + s[i];
  },
  log(...a)  { if (this.DEBUG) console.log('[CONFIG]', ...a); },
  error(...a){ console.error('[CONFIG ERROR]', ...a); },
  warn(...a) { if (this.DEBUG) console.warn('[CONFIG WARN]', ...a); }
};

export default CONFIG;
if (typeof window !== 'undefined') window.CONFIG = CONFIG;
