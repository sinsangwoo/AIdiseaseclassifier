/**
 * Main Application Entry Point
 *
 * 애플리케이션 초기화 및 메인 로직
 *
 * [Render 콜드 스타트 대응 전략]
 * Render 무료 플랜은 15분 비활성 시 슬립합니다.
 * 슬립 해제에 최대 50초가 소요되며, 이 시간이 /predict 타임아웃에
 * 포함되면 분석이 실패합니다.
 *
 * 해결책: 3단계 웜업 전략
 *   1. 페이지 로드 직후 /health 로 웜업 시작 (백그라운드)
 *   2. 사용자가 분석 버튼을 클릭하면 서버가 이미 깨어있는지 확인
 *   3. 아직 웜업 중이라면 준비될 때까지 대기 후 predict 실행
 */

import CONFIG from './config.js';
import apiClient from './api/client.js';
import appState from './state/appState.js';
import UIController from './ui/uiController.js';
import ErrorHandler from './utils/errorHandler.js';

// ── 웜업 상태 추적 ────────────────────────────────────────────────────────
let warmUpPromise = null;   // 진행 중인 웜업 Promise
let serverReady = false;    // 웜업 완료 여부

/**
 * Render 서버 웜업
 * - 페이지 로드 시 백그라운드에서 실행
 * - 완료되면 serverReady = true
 * - 분석 버튼 클릭 시 이 Promise를 await 하여 준비를 보장
 */
function warmUpServer() {
    if (CONFIG.ENVIRONMENT !== 'production') {
        serverReady = true;
        return Promise.resolve();
    }

    if (warmUpPromise) return warmUpPromise;

    warmUpPromise = (async () => {
        const MAX_ATTEMPTS = 4;          // 최대 4회 재시도
        const ATTEMPT_TIMEOUT = 20000;   // 회당 20초
        const RETRY_DELAY = 3000;        // 실패 후 3초 대기

        for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            try {
                CONFIG.log(`[WarmUp] 시도 ${attempt}/${MAX_ATTEMPTS}...`);

                const controller = new AbortController();
                const tid = setTimeout(() => controller.abort(), ATTEMPT_TIMEOUT);

                const res = await fetch(`${CONFIG.API_BASE_URL}/health`, {
                    method: 'GET',
                    signal: controller.signal
                });

                clearTimeout(tid);

                if (res.ok) {
                    serverReady = true;
                    CONFIG.log(`[WarmUp] ✅ 완료 (시도 ${attempt}, HTTP ${res.status})`);
                    return;
                }

                CONFIG.log(`[WarmUp] HTTP ${res.status} — 재시도`);
            } catch (err) {
                CONFIG.log(`[WarmUp] 실패 (시도 ${attempt}): ${err.message}`);
            }

            if (attempt < MAX_ATTEMPTS) {
                await new Promise(r => setTimeout(r, RETRY_DELAY));
            }
        }

        // 웜업 최종 실패 시에도 serverReady=true 로 설정하여
        // 사용자가 predict를 시도할 수 있게 합니다.
        // (predict 자체에서 타임아웃 에러를 사용자에게 표시)
        serverReady = true;
        CONFIG.log('[WarmUp] ⚠ 모든 웜업 시도 실패 — predict 직접 시도');
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

        this.ui.onAnalyze        = () => this.handleAnalysis();
        this.ui.onFileSelect     = (file) => appState.setUploadedImage(file);
        this.ui.onClear          = () => appState.reset();
        this.ui.onAgreementChange = (checked) => appState.setAgreement(checked);

        this.ui.resetUI();

        // 웜업 시작 — await 없이 백그라운드 실행 (UI 블로킹 없음)
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
            // ── 핵심: 서버가 준비될 때까지 대기 ──────────────────────────
            // 사용자가 빠르게 버튼을 클릭했을 때 웜업이 아직 진행 중이면
            // 웜업 완료를 기다린 후 predict 를 보냅니다.
            // 이미 완료된 경우(serverReady=true) await 는 즉시 통과합니다.
            if (!serverReady) {
                CONFIG.log('[App] 서버 웜업 대기 중...');
                appState.analyzing(); // 프로그레스 바 표시
                await warmUpServer();
                CONFIG.log('[App] 서버 웜업 완료 — predict 시작');
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
