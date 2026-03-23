/**
 * 환경변수 기반 설정 관리
 *
 * [Render 재시작 대응 설정]
 * RETRY_ATTEMPTS: 5 — 재시작 후 90초 과도기를 커버하도록
 * RETRY_DELAY:    25000ms (25초) — 선형 증가: 25s, 30s, 35s, 40s
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
    TIMEOUT:         180000,  // 3분 (Render cold start + inference 커버)
    RETRY_ATTEMPTS:  5,       // 5회 재시도
    RETRY_DELAY:     25000,   // 25초 기본 (25→30→35→40→45s 선형 증가)
    RETRY_BACKOFF_MULTIPLIER: 1,
    RETRYABLE_STATUS_CODES: [0, 408, 429, 500, 502, 503, 504],
    HEADERS: { 'Accept': 'application/json' }
  },

  FILE: {
    MAX_SIZE: 10 * 1024 * 1024,
    ALLOWED_TYPES: ['image/jpeg', 'image/jpg', 'image/png'],
    ALLOWED_EXTENSIONS: ['.jpg', '.jpeg', '.png'],
    OPTIMIZATION: {
      ENABLED: true, MAX_WIDTH: 1024, MAX_HEIGHT: 1024,
      QUALITY: 0.85, FORMAT: 'image/jpeg', MIN_SIZE_FOR_COMPRESSION: 500 * 1024
    }
  },

  UI: {
    PROGRESS_ANIMATION_SPEED: 300, TOAST_DURATION: 3000,
    DEBOUNCE_DELAY: 300, ERROR_DISPLAY_DURATION: 5000, LOADING_DELAY: 200
  },

  get ENVIRONMENT() {
    if (window.ENV && window.ENV.ENVIRONMENT) return window.ENV.ENVIRONMENT;
    const h = window.location.hostname;
    if (h === 'localhost' || h === '127.0.0.1') return 'development';
    if (h.includes('github.io'))              return 'production';
    return 'unknown';
  },

  get DEBUG() {
    return new URLSearchParams(window.location.search).has('debug') ||
           this.ENVIRONMENT === 'development';
  },

  getFullURL(ep)       { return `${this.API_BASE_URL}${ep}`; },
  validateFileSize(s)  { return s <= this.FILE.MAX_SIZE; },
  validateFileType(t)  { return this.FILE.ALLOWED_TYPES.includes(t); },
  validateFileExtension(f) {
    const ext = f.toLowerCase().slice(f.lastIndexOf('.'));
    return this.FILE.ALLOWED_EXTENSIONS.includes(ext);
  },
  isRetryableStatusCode(c) { return this.REQUEST.RETRYABLE_STATUS_CODES.includes(c); },
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
