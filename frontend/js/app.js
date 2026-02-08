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
            // 체크박스 상태 리셋 등의 로직이 필요하면 추가
        };
        this.ui.onClear = () => {
            appState.reset();
        };
        this.ui.onAgreementChange = (checked) => {
            appState.setAgreement(checked);
        };

        // 초기 상태 설정
        this.ui.resetUI();

        // 헬스체크 (optional)
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
            
            // 데이터 전처리 중 메시지 유지를 위해 강제 업데이트
            appState.analyzing();
            
            const result = await apiClient.predict(state.uploadedImage);
            
            CONFIG.log('[App] 분석 완료:', result);
            
            // 결과 저장
            appState.completeAnalysis(result);
            
        } catch (error) {
            CONFIG.log('[App] 분석 실패:', error);
            
            // 에러 처리
            appState.setError(error);
            ErrorHandler.handleError(error, 'Image Analysis');
        }
    }
}

// DOM 로드 완료 후 애플리케이션 시작
document.addEventListener('DOMContentLoaded', () => {
    new Application();
});
