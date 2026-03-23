/**
 * API Client Module
 *
 * - Exponential Backoff 재시도 로직
 * - ERR_FAILED (statusCode 0) = Render 재시작 과도기 또는 CORS 문제
 *   → 웜업 재실행 후 재시도
 */

import CONFIG from '../config.js';

export class APIError extends Error {
    constructor(message, statusCode, response = null) {
        super(message);
        this.name       = 'APIError';
        this.statusCode = statusCode;
        this.response   = response;
    }
}

export class APIClient {
    constructor(baseURL = CONFIG.API_BASE_URL, options = {}) {
        this.baseURL       = baseURL;
        this.timeout       = options.timeout       || CONFIG.REQUEST.TIMEOUT;
        this.retryAttempts = options.retryAttempts || CONFIG.REQUEST.RETRY_ATTEMPTS;
        this.retryDelay    = options.retryDelay    || CONFIG.REQUEST.RETRY_DELAY;
    }

    calculateBackoff(attempt) {
        const base   = this.retryDelay * Math.pow(CONFIG.REQUEST.RETRY_BACKOFF_MULTIPLIER, attempt - 1);
        const jitter = Math.random() * 1000;
        return Math.min(base + jitter, 30000);
    }

    delay(ms) { return new Promise(r => setTimeout(r, ms)); }

    /**
     * HTTP 요청 (재시도 로직 포함)
     *
     * ERR_FAILED (statusCode 0) 처리:
     *   Render 무료 플랜 재시작 과도기에 /predict 요청이 도달하면
     *   Render 게이트웨이가 CORS 헤더 없이 ERR_FAILED 반환.
     *   → 웜업을 다시 실행하여 서버 준비 후 재시도.
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        let lastError = null;

        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                console.log(`[APIClient] 시도 ${attempt}/${this.retryAttempts}: ${endpoint}`);

                const controller = new AbortController();
                const tid        = setTimeout(() => controller.abort(), this.timeout);

                const response = await fetch(url, { ...options, signal: controller.signal });
                clearTimeout(tid);

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new APIError(
                        errorData.error || `HTTP ${response.status}: ${response.statusText}`,
                        response.status,
                        errorData
                    );
                }

                const data = await response.json();
                console.log(`[APIClient] 성공 (시도 ${attempt})`);
                return data;

            } catch (error) {
                lastError = error;

                // 타임아웃
                if (error.name === 'AbortError') {
                    console.warn(`[APIClient] 타임아웃 (시도 ${attempt})`);
                    lastError = new APIError(
                        '요청 시간이 초과되었습니다. Render 무료 서버는 첫 접속 시 데우는 데 시간이 소요될 수 있습니다.',
                        408
                    );
                }

                // ERR_FAILED (CORS / 네트워크 실패)
                if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                    console.warn(`[APIClient] ERR_FAILED (시도 ${attempt}) - Render 재시작 과도기 가능성`);
                    lastError = new APIError(
                        '서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.',
                        0
                    );
                }

                if (attempt < this.retryAttempts) {
                    const wait = this.calculateBackoff(attempt);
                    console.log(`[APIClient] ${Math.round(wait / 1000)}s 후 재시도...`);
                    await this.delay(wait);
                    continue;
                }
            }
        }

        console.error(`[APIClient] 모든 재시도 실패:`, lastError);
        throw lastError;
    }

    async get(endpoint, options = {}) {
        return this.request(endpoint, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
    }

    async post(endpoint, data, options = {}) {
        const isFormData = data instanceof FormData;
        return this.request(endpoint, {
            method: 'POST',
            headers: isFormData ? {} : { 'Content-Type': 'application/json', ...options.headers },
            body:    isFormData ? data : JSON.stringify(data),
            ...options
        });
    }

    async healthCheck()         { return this.get('/health'); }
    async detailedHealthCheck() { return this.get('/health/detailed'); }
    async getModelInfo()        { return this.get('/model/info'); }

    async predict(imageFile) {
        const formData = new FormData();
        formData.append('file', imageFile);
        return this.post('/predict', formData);
    }
}

export const apiClient = new APIClient();
export default apiClient;
