/**
 * Main Application Entry Point
 *
 * 애플리케이션 초기화 및 메인 로직
 */

import CONFIG from './config.js';
import apiClient from './api/client.js';
import appState from './state/appState.js';
import UIController from './ui/uiController.js';
import ErrorHandler from './utils/errorHandler.js';

// ── Render 무료 플랜 콜드스타트 웜업 ─────────────────────────────────────
//
// Render 무료 플랜은 15분 비활성 시 슬립 상태로 전환됩니다.
// 슬립에서 깨어나는 데 최대 50초가 소요될 수 있으며,
// 이 시간이 predict 요청의 타임아웃에 포함되면 분석이 실패합니다.
//
// 해결: 페이지 로드 직후 /health 엔드포인트로 가벼운 요청을 보내
// 서버를 미리 깨워둡니다. 웜업은 백그라운드에서 조용히 진행되며
// 실패해도 사용자 경험에 영향을 주지 않습니다.
// ─────────────────────────────────────────────────────────────────────────
async function warmUpServer() {
    // 로컬 개발 환경에서는 웜업 불필요
    if (CONFIG.ENVIRONMENT !== 'production') return;

    try {
        CONFIG.log('[WarmUp] Render 서버 웜업 요청 시작...');

        const controller = new AbortController();
        // 웜업용 타임아웃은 60초 (슬립 해제에 최대 50초 소요)
        const timeoutId = setTimeout(() => controller.abort(), 60000);

        const res = await fetch(`${CONFIG.API_BASE_URL}/health`, {
            method: 'GET',
            signal: controller.signal
        });

        clearTimeout(timeoutId);
        CONFIG.log(`[WarmUp] 완료 — HTTP ${res.status}`);
    } catch (err) {
        // 웜업 실패는 무시 (사용자에게 표시하지 않음)
        CONFIG.log('[WarmUp] 웜업 실패 (무시):', err.message);
    }
}

/**
 * Application 클래스
 */
class Application {
    constructor() {
        this.ui = null;
        this.init();
    }

    /**
     * 애플리케이션 초기화
     */
    async init() {
        CONFIG.log('='.repeat(50));
        CONFIG.log('🚀 AI Disease Classifier Frontend');
        CONFIG.log('Environment:', CONFIG.ENVIRONMENT);
        CONFIG.log('API URL:', CONFIG.API_BASE_URL);
        CONFIG.log('Debug Mode:', CONFIG.DEBUG);
        CONFIG.log('='.repeat(50));

        // UI 컨트롤러 초기화
        this.ui = new UIController();

        // 상태 변경 구독
        appState.subscribe((state) => {
            this.ui.render(state);
        });

        // UI 이벤트 핸들러 연결
        this.ui.onAnalyze = () => this.handleAnalysis();
        this.ui.onFileSelect = (file) => {
            appState.setUploadedImage(file);
        };
        this.ui.onClear = () => {
            appState.reset();
        };
        this.ui.onAgreementChange = (checked) => {
            appState.setAgreement(checked);
        };

        // 초기 상태 설정
        this.ui.resetUI();

        // 백그라운드 웜업 — await 없이 실행하여 UI 초기화를 블로킹하지 않음
        warmUpServer();

        // 헬스체크 (debug 모드 전용)
        if (CONFIG.DEBUG) {
            this.performHealthCheck();
        }
    }

    /**
     * 헬스체크 수행
     */
    async performHealthCheck() {
        try {
            const health = await apiClient.healthCheck();
            CONFIG.log('✅ API Health Check:', health);
        } catch (error) {
            CONFIG.log('⚠️ API Health Check Failed:', error.message);
        }
    }

    /**
     * 분석 처리
     */
    async handleAnalysis() {
        const state = appState.getState();

        if (!state.uploadedImage) {
            ErrorHandler.handleError(
                new Error('분석할 이미지가 없습니다.'),
                'Analysis'
            );
            return;
        }

        if (!state.agreeChecked) {
            ErrorHandler.handleError(
                new Error('주의사항에 동의해주세요.'),
                'Analysis'
            );
            return;
        }

        // 분석 시작
        appState.startAnalysis();

        try {
            CONFIG.log('[App] 분석 요청 시작:', state.uploadedImage.name);

            appState.analyzing();

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

// DOM 로드 완료 후 애플리케이션 시작
document.addEventListener('DOMContentLoaded', () => {
    new Application();
});
