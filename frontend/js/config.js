/**
 * 환경변수 기반 설정
 */

const CONFIG = {
    get API_BASE_URL() {
        if (window.ENV && window.ENV.API_URL) return window.ENV.API_URL;
        const h = window.location.hostname;
        if (h === 'localhost' || h === '127.0.0.1') return 'http://127.0.0.1:5000';
        if (h.includes('github.io'))               return 'https://pneumonia-api-j3t8.onrender.com';
        return 'http://127.0.0.1:5000';
    },

    REQUEST: {
        TIMEOUT:                  180000,
        // RETRY_ATTEMPTS 5로 상향 (CORS 실패 + Render 재시작 커버)
        RETRY_ATTEMPTS:           5,
        // 1차 25s 구간에 Render 콜드스타트 커버
        RETRY_DELAY:              25000,
        RETRY_BACKOFF_MULTIPLIER: 1.8,
        RETRYABLE_STATUS_CODES:   [0, 408, 429, 500, 502, 503, 504],
        HEADERS: { 'Accept': 'application/json' }
    },

    FILE: {
        MAX_SIZE:             10 * 1024 * 1024,
        ALLOWED_TYPES:        ['image/jpeg', 'image/jpg', 'image/png'],
        ALLOWED_EXTENSIONS:   ['.jpg', '.jpeg', '.png'],
    },

    get ENVIRONMENT() {
        if (window.ENV && window.ENV.ENVIRONMENT) return window.ENV.ENVIRONMENT;
        const h = window.location.hostname;
        if (h === 'localhost' || h === '127.0.0.1') return 'development';
        if (h.includes('github.io'))               return 'production';
        return 'unknown';
    },

    get DEBUG() {
        return new URLSearchParams(window.location.search).has('debug') ||
               this.ENVIRONMENT === 'development';
    },

    log(...a)  { if (this.DEBUG) console.log('[CONFIG]', ...a); },
    error(...a){ console.error('[CONFIG ERROR]', ...a); },
    warn(...a) { if (this.DEBUG) console.warn('[CONFIG WARN]', ...a); }
};

export default CONFIG;
if (typeof window !== 'undefined') window.CONFIG = CONFIG;
