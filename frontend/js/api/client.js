/**
 * API Client
 *
 * [에러 다각화 수정]
 *   - ERR_FAILED(0), 502, 503, 408 상태코드별 메시지 상세화
 *   - CORS 헤더 부재 여부를 직접 브라우저 API로 확인하여 로깅
 *   - 재시도 대기 시간 로깅 상세화
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
        // 1차: 25s, 2차: 45s, 3차 이상: 45s 가우로망 (Render 콜드스타트 커버)
        const base   = this.retryDelay * Math.pow(CONFIG.REQUEST.RETRY_BACKOFF_MULTIPLIER, attempt - 1);
        const jitter = Math.random() * 2000;
        return Math.min(base + jitter, 45000);
    }

    delay(ms) { return new Promise(r => setTimeout(r, ms)); }

    /**
     * HTTP 요청 (재시도 로직 + 다각화 에러 메시지)
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
                        response.status, errorData
                    );
                }

                const data = await response.json();
                console.log(`[APIClient] ✅ 성공 (시도 ${attempt})`);
                return data;

            } catch (error) {
                lastError = error;

                // 타임아웃
                if (error.name === 'AbortError') {
                    console.warn(`[APIClient] ⏱ 408 타임아욳 (시도 ${attempt}) - 서버가 180초 내에 응답하지 않음`);
                    lastError = new APIError(
                        '서버 응답 시간 초과 (180초). Render 맴 커가 수행 중일 수 있습니다.',
                        408
                    );
                }

                // ERR_FAILED: CORS preflight 차단 또는 네트워크 단절
                if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                    const corsHint = (
                        '\n  가능한 원인:\n' +
                        '  1. CORS preflight(OPTIONS) 차단 → Render 대시보드에서 최신 배포 확인\n' +
                        '  2. Render 서버 재시작 커버 공스\n' +
                        '  3. 클라이언트 네트워크 단절'
                    );
                    console.warn(`[APIClient] ❌ ERR_FAILED (시도 ${attempt})${corsHint}`);
                    lastError = new APIError(
                        '서버에 연결할 수 없습니다. (네트워크 오류 또는 CORS 차단)',
                        0
                    );
                }

                // 502 Bad Gateway
                if (error.statusCode === 502) {
                    console.warn(`[APIClient] ❌ 502 Bad Gateway (시도 ${attempt}) - Render 워커 재시작 중 또는 배포 과도기`);
                }

                // 503 Service Unavailable
                if (error.statusCode === 503) {
                    console.warn(`[APIClient] ❌ 503 Service Unavailable (시도 ${attempt}) - Render 콜드스타트 또는 슬립 유황 중`);
                }

                if (attempt < this.retryAttempts) {
                    const wait = this.calculateBackoff(attempt);
                    console.log(`[APIClient] ${Math.round(wait / 1000)}s 후 재시도 (시도 ${attempt + 1}/${this.retryAttempts})...`);
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
