/**
 * Main Application Entry Point
 *
 * [Render 콜드 스타트 대응 전략]
 *
 * predict ERR_FAILED 대응:
 *   apiClient.request() 에서 RETRY_ATTEMPTS=3, RETRY_DELAY=10s 이므로
 *   ERR_FAILED 후 10s, 15s 대기 후 재시도 → Render 재시작 후 콴다라도 복구됨
 *
 * 웜업 실패 정책:
 *   warmUpFailed=true 시 predict 를 차단하지 않고 직접 시도 (서버가 살아있을 수 있음)
 */

import CONFIG from './config.js';
import apiClient from './api/client.js';
import appState from './state/appState.js';
import UIController from './ui/uiController.js';
import ErrorHandler from './utils/errorHandler.js';

let warmUpPromise = null;
let serverReady   = false;
let warmUpFailed  = false;

async function tryHealthCheck(timeoutMs) {
    const ctrl = new AbortController();
    const tid  = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
        const res = await fetch(`${CONFIG.API_BASE_URL}/health`, { method: 'GET', signal: ctrl.signal });
        clearTimeout(tid);
        return res.ok;
    } catch { clearTimeout(tid); return false; }
}

function warmUpServer() {
    if (CONFIG.ENVIRONMENT !== 'production') { serverReady = true; return Promise.resolve(); }
    if (warmUpPromise) return warmUpPromise;
    warmUpPromise = (async () => {
        const MAX = 12, TIMEOUT = 15000, DELAY = 8000;
        for (let i = 1; i <= MAX; i++) {
            console.log(`[WarmUp] 시도 ${i}/${MAX}...`);
            if (await tryHealthCheck(TIMEOUT)) {
                serverReady = true;
                console.log(`[WarmUp] ✅ 서버 준비 (시도 ${i})`);
                return;
            }
            console.warn(`[WarmUp] ❌ 실패 (${i}) - ${DELAY/1000}s 후 재시도`);
            if (i < MAX) await new Promise(r => setTimeout(r, DELAY));
        }
        warmUpFailed = true;
        console.warn('[WarmUp] ⚠️ 웜업 실패 - predict 직접 시도 허용');
    })();
    return warmUpPromise;
}

/** 웜업 상태 완전 리셋 (재시도 허용) */
function resetWarmUp() {
    warmUpPromise = null;
    serverReady   = false;
    warmUpFailed  = false;
}

class Application {
    constructor() { this.ui = null; this._init(); }

    async _init() {
        console.log('[App] 초기화 시작 - 환경:', CONFIG.ENVIRONMENT, '- API:', CONFIG.API_BASE_URL);
        try {
            this.ui = new UIController();
            console.log('[App] UIController 생성 완료');
        } catch (e) {
            console.error('[App] UIController 생성 실패:', e);
            return;
        }

        appState.subscribe((state) => {
            console.log(`[App] 상태 -> ${state.status}`);
            try { this.ui.render(state); }
            catch (e) { console.error('[App] UI 렌더링 실패:', e); }
        });

        this.ui.onAnalyze         = () => this._handleAnalysis();
        this.ui.onFileSelect      = (file) => { console.log('[App] 파일:', file.name); appState.setUploadedImage(file); };
        this.ui.onClear           = () => { console.log('[App] 리셋'); appState.reset(); };
        this.ui.onAgreementChange = (checked) => { console.log('[App] 동의:', checked); appState.setAgreement(checked); };

        this.ui.resetUI();
        console.log('[App] 초기화 완료 - 웜업 시작');
        warmUpServer();
    }

    async _handleAnalysis() {
        const state = appState.getState();
        console.log('[App] 분석 요청, status:', state.status);

        if (!state.uploadedImage) {
            console.warn('[App] 이미지 없음');
            ErrorHandler.handleError(new Error('분석할 이미지가 없습니다.'), 'Analysis');
            return;
        }
        if (!state.agreeChecked) {
            console.warn('[App] 동의 미체크');
            ErrorHandler.handleError(new Error('주의사항에 동의해주세요.'), 'Analysis');
            return;
        }

        appState.startAnalysis();

        try {
            if (!serverReady && !warmUpFailed) {
                console.log('[App] 웜업 대기...');
                appState.analyzing();
                await warmUpServer();
            }
            if (warmUpFailed) console.warn('[App] 웜업 실패 - predict 직접 시도');

            appState.analyzing();
            console.log('[App] predict:', state.uploadedImage.name);

            // apiClient 내부에서 RETRY_ATTEMPTS=3으로 자동 재시도
            // ERR_FAILED 시 10s, 15s 대기 후 재시도 → Render 재시작 커버
            const result = await apiClient.predict(state.uploadedImage);
            console.log('[App] predict 성공');
            appState.completeAnalysis(result);

        } catch (error) {
            console.error('[App] 분석 실패:', error.message);

            // ERR_FAILED 실패 후 웜업 상태 리셋 (다음 시도 시 웜업 재실행)
            if (error.statusCode === 0) {
                console.log('[App] ERR_FAILED - 웹업 상태 리셋');
                resetWarmUp();
                warmUpServer(); // 백그라운드 웹업 재시작
            }

            appState.setError(error);
            ErrorHandler.handleError(error, 'Image Analysis');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('[App] DOMContentLoaded');
    new Application();
});
