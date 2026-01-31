/**
 * API Client Module
 * 
 * 백엔드 API와의 통신을 담당
 * - Exponential Backoff 재시도 로직
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
     * 지수 백오프 계산 (Exponential Backoff)
     * @param {number} attempt - 현재 시도 횟수 (1부터 시작)
     * @returns {number} 대기 시간 (ms)
     */
    calculateBackoff(attempt) {
        const exponentialDelay = this.retryDelay * Math.pow(2, attempt - 1);
        const jitter = Math.random() * 500;
        return Math.min(exponentialDelay + jitter, 10000);
    }

    /**
     * 지연 함수
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * HTTP 요청 실행 (재시도 로직 포함)
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        let lastError = null;

        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                CONFIG.log(`[APIClient] 요청 시도 ${attempt}/${this.retryAttempts}: ${url}`);

                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.timeout);

                const response = await fetch(url, {
                    ...options,
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

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

                if (error.name === 'AbortError') {
                    CONFIG.log(`[APIClient] 타임아웃 (시도 ${attempt})`);
                    lastError = new APIError(
                        '요청 시간이 초과되었습니다. 네트워크 상태를 확인해주세요.',
                        408
                    );
                }

                if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                    CONFIG.log(`[APIClient] 네트워크 오류 (시도 ${attempt})`);
                    lastError = new APIError(
                        '서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.',
                        0
                    );
                }

                if (attempt < this.retryAttempts) {
                    const backoffDelay = this.calculateBackoff(attempt);
                    CONFIG.log(`[APIClient] ${backoffDelay}ms 후 재시도...`);
                    await this.delay(backoffDelay);
                    continue;
                }
            }
        }

        CONFIG.log(`[APIClient] 모든 재시도 실패:`, lastError);
        throw lastError;
    }

    /**
     * GET 요청
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
     */
    async healthCheck() {
        return this.get('/health');
    }

    /**
     * 상세 헬스체크
     */
    async detailedHealthCheck() {
        return this.get('/health/detailed');
    }

    /**
     * 모델 정보 조회
     */
    async getModelInfo() {
        return this.get('/model/info');
    }

    /**
     * 이미지 예측 요청
     */
    async predict(imageFile) {
        const formData = new FormData();
        formData.append('file', imageFile);

        return this.post('/predict', formData);
    }
}

export const apiClient = new APIClient();
export default apiClient;
