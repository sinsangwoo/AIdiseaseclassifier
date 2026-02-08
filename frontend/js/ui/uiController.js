/**
 * UI Controller (Phase 4 Enhanced)
 * 
 * 상태 변경에 따른 UI 업데이트 담당
 * Phase 4: 진행 상태 표시 강화
 */

class UIController {
    constructor() {
        this.elements = {
            uploadArea: document.getElementById('upload-area'),
            previewImage: document.getElementById('preview-image'),
            analyzeBtn: document.getElementById('analyze-btn'),
            resultsSection: document.getElementById('results-section'),
            errorMessage: document.getElementById('error-message'),
            // Phase 4: 진행 상태 UI
            progressContainer: document.getElementById('progress-container'),
            progressBar: document.getElementById('progress-bar'),
            progressText: document.getElementById('progress-text'),
            spinner: document.getElementById('spinner')
        };
    }

    render(state) {
        this.renderUploadArea(state);
        this.renderAnalyzeButton(state);
        this.renderResults(state);
        this.renderError(state);
        // Phase 4: 진행 상태 렌더링
        this.renderProgress(state);
    }

    renderUploadArea(state) {
        if (state.uploadedImage && this.elements.previewImage) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.elements.previewImage.src = e.target.result;
                this.elements.previewImage.style.display = 'block';
            };
            reader.readAsDataURL(state.uploadedImage);
        }
    }

    renderAnalyzeButton(state) {
        if (this.elements.analyzeBtn) {
            this.elements.analyzeBtn.disabled = !state.uploadedImage || state.isAnalyzing;
            this.elements.analyzeBtn.textContent = state.isAnalyzing ? '분석 중...' : '분석 시작';
        }
    }

    renderResults(state) {
        if (!this.elements.resultsSection) return;

        if (state.analysisResult && state.analysisResult.success) {
            this.elements.resultsSection.style.display = 'block';
            this.renderPredictions(state.analysisResult.predictions);
            this.renderMetadata(state.analysisResult.metadata);
        } else {
            this.elements.resultsSection.style.display = 'none';
        }
    }

    renderPredictions(predictions) {
        const container = document.getElementById('predictions-list');
        if (!container) return;

        container.innerHTML = predictions.map((pred, index) => `
            <div class="prediction-item ${index === 0 ? 'top-prediction' : ''}">
                <div class="prediction-label">${pred.className}</div>
                <div class="prediction-bar">
                    <div class="prediction-fill" style="width: ${(pred.probability * 100).toFixed(1)}%"></div>
                </div>
                <div class="prediction-value">${(pred.probability * 100).toFixed(1)}%</div>
            </div>
        `).join('');
    }

    renderMetadata(metadata) {
        const container = document.getElementById('metadata-info');
        if (!container) return;

        container.innerHTML = `
            <div class="metadata-item">
                <span class="label">처리 시간:</span>
                <span class="value">${metadata.processing_time_ms.toFixed(0)}ms</span>
            </div>
            <div class="metadata-item">
                <span class="label">모델 버전:</span>
                <span class="value">${metadata.model_version}</span>
            </div>
            ${metadata.from_cache ? '<div class="cache-badge">캐시됨 ⚡</div>' : ''}
        `;
    }

    renderError(state) {
        if (this.elements.errorMessage) {
            if (state.error) {
                this.elements.errorMessage.textContent = state.error;
                this.elements.errorMessage.style.display = 'block';
            } else {
                this.elements.errorMessage.style.display = 'none';
            }
        }
    }

    /**
     * Phase 4: 진행 상태 렌더링
     */
    renderProgress(state) {
        const { progress } = state;
        
        if (this.elements.progressContainer) {
            // 분석 중일 때만 표시
            if (state.isAnalyzing && progress.stage) {
                this.elements.progressContainer.style.display = 'block';
                
                // 프로그레스 바 업데이트
                if (this.elements.progressBar) {
                    this.elements.progressBar.style.width = `${progress.percent}%`;
                }
                
                // 텍스트 업데이트
                if (this.elements.progressText) {
                    this.elements.progressText.textContent = progress.message;
                }
                
                // 스피너 표시
                if (this.elements.spinner) {
                    this.elements.spinner.style.display = 'block';
                }
            } else {
                this.elements.progressContainer.style.display = 'none';
                if (this.elements.spinner) {
                    this.elements.spinner.style.display = 'none';
                }
            }
        }
    }
}

export default UIController;
