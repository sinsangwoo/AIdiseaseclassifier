/**
 * 환경별 설정 관리
 * 
 * GitHub Pages와 Render 분리 배포를 위한 동적 API URL 설정
 */

const CONFIG = {
  // 환경 감지 및 API URL 설정
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
      return 'https://pneumonia-api.onrender.com';  // Render 서비스 이름에 맞게 수정
    } else {
      // 기타 환경 (기본값)
      return 'http://127.0.0.1:5000';
    }
  },
  
  // API 엔드포인트
  ENDPOINTS: {
    HEALTH: '/health',
    HEALTH_DETAILED: '/health/detailed',
    MODEL_INFO: '/model/info',
    PREDICT: '/predict'
  },
  
  // 요청 설정
  REQUEST: {
    TIMEOUT: 30000,  // 30초
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000  // 1초
  },
  
  // 파일 업로드 제한
  FILE: {
    MAX_SIZE: 10 * 1024 * 1024,  // 10MB
    ALLOWED_TYPES: ['image/jpeg', 'image/jpg', 'image/png'],
    ALLOWED_EXTENSIONS: ['.jpg', '.jpeg', '.png']
  },
  
  // UI 설정
  UI: {
    PROGRESS_ANIMATION_SPEED: 300,  // ms
    TOAST_DURATION: 3000,  // 3초
    DEBOUNCE_DELAY: 300  // 300ms
  },
  
  // 환경 정보
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
  
  // 디버그 모드
  get DEBUG() {
    return this.ENVIRONMENT === 'development';
  },
  
  // 전체 URL 생성 헬퍼
  getFullURL(endpoint) {
    return `${this.API_BASE_URL}${endpoint}`;
  },
  
  // 로깅 헬퍼
  log(...args) {
    if (this.DEBUG) {
      console.log('[CONFIG]', ...args);
    }
  }
};

// 초기화 시 설정 정보 출력
CONFIG.log('Environment:', CONFIG.ENVIRONMENT);
CONFIG.log('API Base URL:', CONFIG.API_BASE_URL);
CONFIG.log('Debug Mode:', CONFIG.DEBUG);

// ES6 모듈로 내보내기 (모던 브라우저)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
}

// 전역 객체로도 사용 가능
window.CONFIG = CONFIG;
