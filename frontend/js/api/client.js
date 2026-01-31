/**
 * API Client Module
 * 
 * 백엔드 API와의 통신을 담당하는 클라이언트
 * - Exponential Backoff 기반 재시도 로직
 * - 타임아웃 관리
 * - 에러 핸들링
 */

import CONFIG from '../config.js';

/**
 * API 에러 클래스
 */
export class APIError extends Error {
    constructor(message, statusCode, response = null) {
        super(message);
        this.name = 'APIError';
        this.statusCode = statusCode;
        this.response = response;
    }
}

/**
 * API Client 클래스
 */
export class APIClient {
    constructor(baseURL = CONFIG.API_BASE_URL, options = {}) {
        this.baseURL = baseURL;
        this.timeout = options.timeout || CONFIG.REQUEST.TIMEOUT;
        this.retryAttempts = options.retryAttempts || CONFIG.REQUEST.RETRY_ATTEMPTS;
        this.retryDelay = options.retryDelay || CONFIG.REQUEST.RETRY_DELAY;
    }

    /**
     * 지수 백오프 계산
     * @param {number} attempt - 현재 시도 횟수 (1부터 시작)
     * @returns {number} 대기 시간 (ms)
     */
    calculateBackoff(attempt) {
        // Exponential backoff: delay * 2^(attempt-1) + jitter
        const exponentialDelay = this.retryDelay * Math.pow(2, attempt - 1);
        const jitter = Math.random() * 500; // 0-500ms 랜덤 지터
        return Math.min(exponentialDelay + jitter, 10000); // 최대 10초
    }

    /**
     * 지연 함수
     * @param {number} ms - 대기 시간 (ms)
     * @returns {Promise}
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * HTTP 요청 실행 (재시도 로직 포함)
     * @param {string} endpoint - API 엔드포인트
     * @param {Object} options - Fetch 옵션
     * @returns {Promise<Object>} 응답 데이터
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        let lastError = null;

        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                CONFIG.log(`[APIClient] 요청 시도 ${attempt}/${this.retryAttempts}: ${url}`);

                // AbortController로 타임아웃 구현
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.timeout);

                const response = await fetch(url, {
                    ...options,
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                // 응답 처리
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new APIError(
                        errorData.error || `HTTP ${response.status}: ${response.statusText}`,
                        response.status,
                        errorData
                    );
                }

                const data = await response.json();
                CONFIG.log(`[APIClient] 요청 성공 (시도 ${attempt})`);
                return data;

            } catch (error) {
                lastError = error;

                // AbortError (타임아웃)
                if (error.name === 'AbortError') {
                    CONFIG.log(`[APIClient] 타임아웃 (시도 ${attempt})`);
                    lastError = new APIError(
                        '요청 시간이 초과되었습니다. 네트워크 상태를 확인해주세요.',
                        408
                    );
                }

                // TypeError (네트워크 오류)
                if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                    CONFIG.log(`[APIClient] 네트워크 오류 (시도 ${attempt})`);
                    lastError = new APIError(
                        '서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.',
                        0
                    );
                }

                // 마지막 시도가 아니면 재시도
                if (attempt < this.retryAttempts) {
                    const backoffDelay = this.calculateBackoff(attempt);
                    CONFIG.log(`[APIClient] ${backoffDelay}ms 후 재시도...`);
                    await this.delay(backoffDelay);
                    continue;
                }
            }
        }

        // 모든 재시도 실패
        CONFIG.log(`[APIClient] 모든 재시도 실패:`, lastError);
        throw lastError;
    }

    /**
     * GET 요청
     * @param {string} endpoint - API 엔드포인트
     * @param {Object} options - 추가 옵션
     * @returns {Promise<Object>}
     */
    async get(endpoint, options = {}) {
        return this.request(endpoint, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
    }

    /**
     * POST 요청
     * @param {string} endpoint - API 엔드포인트
     * @param {*} data - 전송 데이터
     * @param {Object} options - 추가 옵션
     * @returns {Promise<Object>}
     */
    async post(endpoint, data, options = {}) {
        const isFormData = data instanceof FormData;

        return this.request(endpoint, {
            method: 'POST',
            headers: isFormData ? {} : {
                'Content-Type': 'application/json',
                ...options.headers
            },
            body: isFormData ? data : JSON.stringify(data),
            ...options
        });
    }

    /**
     * 헬스체크
     * @returns {Promise<Object>}
     */
    async healthCheck() {
        return this.get('/health');
    }

    /**
     * 상세 헬스체크
     * @returns {Promise<Object>}
     */
    async detailedHealthCheck() {
        return this.get('/health/detailed');
    }

    /**
     * 모델 정보 조회
     * @returns {Promise<Object>}
     */
    async getModelInfo() {
        return this.get('/model/info');
    }

    /**
     * 이미지 예측 요청
     * @param {File} imageFile - 이미지 파일
     * @returns {Promise<Object>} 예측 결과
     */
    async predict(imageFile) {
        const formData = new FormData();
        formData.append('file', imageFile);

        return this.post('/predict', formData);
    }
}

// 싱글톤 인스턴스 생성
export const apiClient = new APIClient();

export default apiClient;
