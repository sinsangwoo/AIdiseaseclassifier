/**
 * Main Application Entry Point
 *
 * [Render 콜드 스타트 대응 - 최종 전략]
 *
 * 문제의 근본 원인:
 *   Render 재배포/재시작 시 포트 바인딩까지 최대 2~3분 소요.
 *   이 과도기에 fetch 요청은 ERR_FAILED (CORS 헤더 없음)로 실패.
 *   기존 4회×3초 = 12초 재시도는 과도기 안에서 모두 소진됨.
 *   → 실패 후 serverReady=true 강제 설정 → predict도 동일하게 실패.
 *
 * 해결 전략:
 *   - 재시도: 12회 × 8초 간격 = 최대 96초 커버 (재배포 과도기 완전 커버)
 *   - 웜업 실패 시 predict 절대 차단 (강제 통과 없음)
 *   - ERR_FAILED(statusCode:0) = 서버 미준비로 인식, 계속 재시도
 *   - UI에 서버 준비 상태 실시간 표시
 */

import CONFIG from './config.js';
import apiClient from './api/client.js';
import appState from './state/appState.js';
import UIController from './ui/uiController.js';
import ErrorHandler from './utils/errorHandler.js';

// ── 웜업 상태 ──────────────────────────────────────────────────────────────
let warmUpPromise  = null;   // 진행 중인 웜업 Promise
let serverReady    = false;  // 웜업 성공 완료 여부 (실패 시 절대 true 안 됨)
let warmUpFailed   = false;  // 모든 재시도 소진 여부

/**
 * /health 단일 요청 시도
 * @returns {boolean} 성공 여부
 */
async function tryHealthCheck(timeoutMs) {
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(`${CONFIG.API_BASE_URL}/health`, {
            method: 'GET',
            signal: controller.signal,
        });
        clearTimeout(tid);
        return res.ok;  // 2xx 만 성공
    } catch {
        clearTimeout(tid);
        return false;
    }
}

/**
 * Render 서버 웜업
 *
 * 정책:
 *   - 성공 시 serverReady = true → predict 허용
 *   - 12회 모두 실패 시 warmUpFailed = true → predict 차단 후 사용자에게 안내
 *   - ERR_FAILED(CORS/네트워크 오류) = 서버 미준비로 간주 → 재시도
 */
function warmUpServer() {
    if (CONFIG.ENVIRONMENT !== 'production') {
        serverReady = true;
        return Promise.resolve();
    }

    if (warmUpPromise) return warmUpPromise;

    warmUpPromise = (async () => {
        const MAX_ATTEMPTS  = 12;    // 12회 (재배포 과도기 2분 + 여유)
        const ATTEMPT_TIMEOUT = 15000; // 회당 15초
        const RETRY_DELAY   = 8000;  // 실패 후 8초 대기 (과도기 커버)

        for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            CONFIG.log(`[WarmUp] 시도 ${attempt}/${MAX_ATTEMPTS} ...`);

            const ok = await tryHealthCheck(ATTEMPT_TIMEOUT);

            if (ok) {
                serverReady = true;
                CONFIG.log(`[WarmUp] ✅ 서버 준비 완료 (시도 ${attempt})`);
                return;
            }

            CONFIG.log(`[WarmUp] ❌ 실패 (시도 ${attempt}) — ${RETRY_DELAY / 1000}초 후 재시도`);

            if (attempt < MAX_ATTEMPTS) {
                await new Promise(r => setTimeout(r, RETRY_DELAY));
            }
        }

        // 모든 시도 소진 — serverReady 는 false 유지, warmUpFailed = true
        warmUpFailed = true;
        CONFIG.log('[WarmUp] ⛔ 모든 재시도 실패. 서버 접근 불가.');
    })();

    return warmUpPromise;
}

/**
 * Application 클래스
 */
class Application {
    constructor() {
        this.ui = null;
        this.init();
    }

    async init() {
        CONFIG.log('='.repeat(50));
        CONFIG.log('🚀 AI Disease Classifier Frontend');
        CONFIG.log('Environment:', CONFIG.ENVIRONMENT);
        CONFIG.log('API URL:', CONFIG.API_BASE_URL);
        CONFIG.log('='.repeat(50));

        this.ui = new UIController();

        appState.subscribe((state) => {
            this.ui.render(state);
        });

        this.ui.onAnalyze         = () => this.handleAnalysis();
        this.ui.onFileSelect      = (file) => appState.setUploadedImage(file);
        this.ui.onClear           = () => appState.reset();
        this.ui.onAgreementChange = (checked) => appState.setAgreement(checked);

        this.ui.resetUI();

        // 웜업 백그라운드 시작 (UI 블로킹 없음)
        warmUpServer();

        if (CONFIG.DEBUG) this.performHealthCheck();
    }

    async performHealthCheck() {
        try {
            const health = await apiClient.healthCheck();
            CONFIG.log('✅ Health Check:', health);
        } catch (error) {
            CONFIG.log('⚠️ Health Check Failed:', error.message);
        }
    }

    async handleAnalysis() {
        const state = appState.getState();

        if (!state.uploadedImage) {
            ErrorHandler.handleError(new Error('분석할 이미지가 없습니다.'), 'Analysis');
            return;
        }
        if (!state.agreeChecked) {
            ErrorHandler.handleError(new Error('주의사항에 동의해주세요.'), 'Analysis');
            return;
        }

        appState.startAnalysis();

        try {
            // ── 서버 준비 대기 (핵심 로직) ────────────────────────────────
            if (!serverReady) {
                CONFIG.log('[App] 서버 웜업 대기 중 ...');
                appState.analyzing();
                await warmUpServer();
            }

            // 웜업 최종 실패 → 사용자에게 명확한 안내
            if (warmUpFailed) {
                throw new Error(
                    '서버가 아직 준비되지 않았습니다.\n' +
                    'Render 무료 서버는 첫 접속 시 최대 2분이 소요됩니다.\n' +
                    '잠시 후 다시 시도해 주세요.'
                );
            }

            appState.analyzing();

            CONFIG.log('[App] 분석 요청:', state.uploadedImage.name);
            const result = await apiClient.predict(state.uploadedImage);
            CONFIG.log('[App] 분석 완료:', result);

            appState.completeAnalysis(result);

        } catch (error) {
            CONFIG.log('[App] 분석 실패:', error);
            appState.setError(error);
            ErrorHandler.handleError(error, 'Image Analysis');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new Application();
});
