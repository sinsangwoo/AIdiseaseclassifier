/**
 * Main Application Entry Point
 *
 * [Render 콜드 스타트 대응 전략]
 * - 페이지 로드 시 /health 로 백그라운드 웹 업
 * - 분석 버튼 클릭 시 serverReady 확인, 미완료 시 await
 * - 웹 업 실패(12회×8초 소진) 시 warmUpFailed=true → predict 차단
 */

import CONFIG from './config.js';
import apiClient from './api/client.js';
import appState from './state/appState.js';
import UIController from './ui/uiController.js';
import ErrorHandler from './utils/errorHandler.js';

// ── 웹 업 상태 ─────────────────────────────────────────────────────────────
let warmUpPromise = null;
let serverReady   = false;
let warmUpFailed  = false;

async function tryHealthCheck(timeoutMs) {
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(`${CONFIG.API_BASE_URL}/health`, {
            method: 'GET',
            signal: controller.signal,
        });
        clearTimeout(tid);
        return res.ok;
    } catch {
        clearTimeout(tid);
        return false;
    }
}

function warmUpServer() {
    if (CONFIG.ENVIRONMENT !== 'production') {
        serverReady = true;
        return Promise.resolve();
    }
    if (warmUpPromise) return warmUpPromise;

    warmUpPromise = (async () => {
        const MAX_ATTEMPTS    = 12;
        const ATTEMPT_TIMEOUT = 15000;
        const RETRY_DELAY     = 8000;

        for (let i = 1; i <= MAX_ATTEMPTS; i++) {
            console.log(`[WarmUp] 시도 ${i}/${MAX_ATTEMPTS}...`);
            const ok = await tryHealthCheck(ATTEMPT_TIMEOUT);
            if (ok) {
                serverReady = true;
                console.log(`[WarmUp] ✅ 서버 준비 완료 (시도 ${i})`);
                return;
            }
            console.warn(`[WarmUp] ❌ 실패 (${i}) — ${RETRY_DELAY/1000}s 후 재시도`);
            if (i < MAX_ATTEMPTS) await new Promise(r => setTimeout(r, RETRY_DELAY));
        }

        warmUpFailed = true;
        console.error('[WarmUp] ⛔ 모든 재시도 실패 — 서버 접근 불가');
    })();

    return warmUpPromise;
}

// ── Application ────────────────────────────────────────────────────────────

class Application {
    constructor() {
        this.ui = null;
        this._init();
    }

    async _init() {
        console.log('[App] 초기화 시작');
        console.log('[App] 환경:', CONFIG.ENVIRONMENT);
        console.log('[App] API URL:', CONFIG.API_BASE_URL);

        try {
            this.ui = new UIController();
            console.log('[App] UIController 생성 완료');
        } catch (e) {
            console.error('[App] UIController 생성 실패:', e);
            return;
        }

        // 상태 변경 시 UI 렌더링
        appState.subscribe((state) => {
            console.log(`[App] 상태 변경 → ${state.status}`);
            try {
                this.ui.render(state);
            } catch (e) {
                console.error('[App] UI 렌더링 실패:', e);
            }
        });

        // 콜백 연결
        this.ui.onAnalyze         = () => this._handleAnalysis();
        this.ui.onFileSelect      = (file) => {
            console.log('[App] 파일 선택:', file.name);
            appState.setUploadedImage(file);
        };
        this.ui.onClear           = () => {
            console.log('[App] 초기화');
            appState.reset();
        };
        this.ui.onAgreementChange = (checked) => {
            console.log('[App] 동의:', checked);
            appState.setAgreement(checked);
        };

        this.ui.resetUI();
        console.log('[App] 초기화 완료 — 웹 업 시작');

        // 백그라운드 웹 업 (블로킹 없음)
        warmUpServer();
    }

    async _handleAnalysis() {
        const state = appState.getState();
        console.log('[App] 분석 요청, 현재 상태:', state.status);

        if (!state.uploadedImage) {
            const msg = '분석할 이미지가 없습니다.';
            console.warn('[App]', msg);
            ErrorHandler.handleError(new Error(msg), 'Analysis');
            return;
        }
        if (!state.agreeChecked) {
            const msg = '주의사항에 동의해주세요.';
            console.warn('[App]', msg);
            ErrorHandler.handleError(new Error(msg), 'Analysis');
            return;
        }

        appState.startAnalysis();

        try {
            if (!serverReady) {
                console.log('[App] 웹 업 대기 중...');
                appState.analyzing();
                await warmUpServer();
            }

            if (warmUpFailed) {
                throw new Error(
                    '서버가 아직 준비되지 않았습니다.\n' +
                    'Render 무료 서버는 첫 접속 시 최대 2분이 소요됩니다.\n' +
                    '잠시 후 다시 시도해 주세요.'
                );
            }

            appState.analyzing();
            console.log('[App] predict 요청:', state.uploadedImage.name);

            const result = await apiClient.predict(state.uploadedImage);
            console.log('[App] predict 성공:', result);

            appState.completeAnalysis(result);

        } catch (error) {
            console.error('[App] 분석 실패:', error);
            appState.setError(error);
            ErrorHandler.handleError(error, 'Image Analysis');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('[App] DOMContentLoaded — Application 시작');
    new Application();
});
