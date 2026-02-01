/**
 * Main Application Controller (Phase 3-4)
 * 
 * 애플리케이션의 핵심 로직 및 이벤트 처리
 * Phase 4: 이미지 최적화 및 진행 상태 UI 통합
 */

import { appState } from './state/appState.js';
import { imageOptimizer } from './imageOptimizer.js';
import { apiClient } from './api/apiClient.js';
import { uiController } from './ui/uiController.js';

class MainController {
    constructor() {
        this.fileInput = document.getElementById('file-input');
        this.uploadArea = document.getElementById('upload-area');
        this.analyzeBtn = document.getElementById('analyze-btn');
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.subscribeToState();
        console.log('🚀 AI 질병 진단 앱 초기화 완료 (Phase 3-4)');
    }

    setupEventListeners() {
        // 파일 선택
        this.fileInput?.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // 드래그 앤 드롭
        this.uploadArea?.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea?.addEventListener('drop', (e) => this.handleDrop(e));
        this.uploadArea?.addEventListener('click', () => this.fileInput?.click());
        
        // 분석 버튼
        this.analyzeBtn?.addEventListener('click', () => this.handleAnalyze());
    }

    subscribeToState() {
        appState.subscribe((state) => {
            uiController.render(state);
        });
    }

    async handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            await this.processFile(file);
        }
    }

    handleDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        this.uploadArea?.classList.add('drag-over');
    }

    async handleDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        this.uploadArea?.classList.remove('drag-over');
        
        const file = event.dataTransfer.files[0];
        if (file) {
            await this.processFile(file);
        }
    }

    async processFile(file) {
        try {
            // Phase 4: 클라이언트 측 이미지 최적화
            console.log('📸 원본 파일:', file.name, this.formatBytes(file.size));
            
            const optimizedFile = await imageOptimizer.optimize(file);
            
            // 최적화된 파일을 File 객체로 변환
            const processedFile = new File(
                [optimizedFile],
                file.name,
                { type: optimizedFile.type || file.type }
            );
            
            appState.setUploadedImage(processedFile);
            console.log('✅ 이미지 처리 완료');
            
        } catch (error) {
            console.error('❌ 파일 처리 실패:', error);
            appState.setError('이미지 처리 중 오류가 발생했습니다.');
        }
    }

    async handleAnalyze() {
        const state = appState.getState();
        
        if (!state.uploadedImage) {
            appState.setError('먼저 이미지를 선택해주세요.');
            return;
        }

        try {
            // Phase 4: 분석 시작 (진행 상태 표시)
            appState.startAnalysis();
            
            // 업로드 진행 표시
            setTimeout(() => {
                appState.analyzing();
            }, 300);
            
            // API 호출
            const result = await apiClient.predict(state.uploadedImage);
            
            // 분석 완료
            appState.completeAnalysis(result);
            
            console.log('🎉 분석 완료:', result);
            
        } catch (error) {
            console.error('❌ 분석 실패:', error);
            appState.setError(error.message || '분석 중 오류가 발생했습니다.');
        }
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
}

// 앱 시작
document.addEventListener('DOMContentLoaded', () => {
    new MainController();
});
