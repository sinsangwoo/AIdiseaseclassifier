/**
 * UI Controller (Phase 4 Enhanced)
 * 
 * 상태 변경에 따른 UI 업데이트 담당
 * Phase 4: 진행 상태 표시 강화
 */

class UIController {
    constructor() {
        this.elements = {
            uploadSection: document.getElementById('uploadSection'),
            imageInput: document.getElementById('imageInput'),
            previewContainer: document.getElementById('previewContainer'),
            imagePreview: document.getElementById('imagePreview'),
            analyzeBtn: document.getElementById('analyzeBtn'),
            clearBtn: document.getElementById('clearBtn'),
            reportContainer: document.getElementById('reportContainer'),
            resultsContent: document.getElementById('resultsContent'),
            resultComment: document.getElementById('resultComment'),
            reportTimestamp: document.getElementById('reportTimestamp'),
            agreementBox: document.getElementById('agreementBox'),
            agreeCheckbox: document.getElementById('agreeCheckbox'),
            progressContainer: document.getElementById('progressContainer'),
            progressBarFill: document.getElementById('progressBarFill'),
            // Optional elements
            savePngBtn: document.getElementById('savePngBtn'),
            savePdfBtn: document.getElementById('savePdfBtn')
        };

        // Callbacks
        this.onAnalyze = null;
        this.onFileSelect = null;
        this.onClear = null;

        this.bindEvents();
    }

    bindEvents() {
        // File Input Change
        this.elements.imageInput?.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file && this.onFileSelect) {
                this.onFileSelect(file);
            }
        });

        // Upload Section Drag & Drop / Click
        if (this.elements.uploadSection) {
            this.elements.uploadSection.addEventListener('click', () => {
                this.elements.imageInput?.click();
            });

            this.elements.uploadSection.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.currentTarget.style.borderColor = 'var(--primary-color)';
            });

            this.elements.uploadSection.addEventListener('dragleave', (e) => {
                e.preventDefault();
                e.currentTarget.style.borderColor = 'var(--border-color)';
            });

            this.elements.uploadSection.addEventListener('drop', (e) => {
                e.preventDefault();
                e.currentTarget.style.borderColor = 'var(--border-color)';
                const file = e.dataTransfer.files[0];
                if (file && this.onFileSelect) {
                    this.onFileSelect(file);
                }
            });
        }

        // Analyze Button
        this.elements.analyzeBtn?.addEventListener('click', () => {
            if (this.onAnalyze) {
                this.onAnalyze();
            }
        });

        // Clear Button
        this.elements.clearBtn?.addEventListener('click', () => {
            this.handleClear();
            if (this.onClear) {
                this.onClear();
            }
        });

        // Agreement Checkbox
        this.elements.agreeCheckbox?.addEventListener('change', (e) => {
            // State update logic could go here or via app.js
            // For now, let's just update button state locally for immediate feedback
            // but ideally should be driven by state
            if (this.elements.analyzeBtn) {
                this.elements.analyzeBtn.disabled = !e.target.checked;
            }
            // Better: trigger a state update callback if we had one for agreement
        });
    }

    handleClear() {
        // Reset DOM elements directly
        if (this.elements.imageInput) this.elements.imageInput.value = '';
        if (this.elements.imagePreview) this.elements.imagePreview.src = '';
        if (this.elements.agreeCheckbox) this.elements.agreeCheckbox.checked = false;
        
        // Hide/Show sections
        if (this.elements.uploadSection) this.elements.uploadSection.style.display = 'block';
        if (this.elements.previewContainer) this.elements.previewContainer.style.display = 'none';
        if (this.elements.reportContainer) this.elements.reportContainer.style.display = 'none';
        if (this.elements.progressContainer) this.elements.progressContainer.style.display = 'none';
        
        // Reset buttons
        if (this.elements.analyzeBtn) this.elements.analyzeBtn.disabled = true;
    }

    render(state) {
        this.renderUploadArea(state);
        this.renderAnalyzeButton(state);
        this.renderResults(state);
        this.renderProgress(state);
        this.renderError(state);
    }

    renderUploadArea(state) {
        if (state.uploadedImage) {
            // Show preview, hide upload
            if (this.elements.uploadSection) this.elements.uploadSection.style.display = 'none';
            if (this.elements.previewContainer) this.elements.previewContainer.style.display = 'block';
            
            if (this.elements.imagePreview && this.elements.imagePreview.src !== state.uploadedImage.src) {
                 // Create object URL if not already set or handle based on state content
                 // Assuming state.uploadedImage is a File object
                 const reader = new FileReader();
                 reader.onload = (e) => {
                     this.elements.imagePreview.src = e.target.result;
                 };
                 reader.readAsDataURL(state.uploadedImage);
            }
        } else {
            // Show upload, hide preview
            if (this.elements.uploadSection) this.elements.uploadSection.style.display = 'block';
            if (this.elements.previewContainer) this.elements.previewContainer.style.display = 'none';
        }
    }

    renderAnalyzeButton(state) {
        if (this.elements.analyzeBtn) {
            // Button is enabled only if image exists AND agreement is checked
            // We might need agreement state in appState
            const isEnabled = state.uploadedImage && this.elements.agreeCheckbox?.checked;
            this.elements.analyzeBtn.disabled = !isEnabled || state.isAnalyzing;
            this.elements.analyzeBtn.textContent = state.isAnalyzing ? '분석 중...' : 'AI 정밀 분석 시작';
        }
    }

    renderResults(state) {
        if (!this.elements.reportContainer) return;

        if (state.analysisResult && state.analysisResult.success) {
            this.elements.reportContainer.style.display = 'block';
            this.elements.previewContainer.style.display = 'none'; // Hide preview when showing report
            this.renderPredictions(state.analysisResult.predictions);
            this.renderMetadata(state.analysisResult.metadata || {});
        } else {
            this.elements.reportContainer.style.display = 'none';
        }
    }

    renderPredictions(predictions) {
        if (!this.elements.resultsContent) return;

        // Sort predictions
        const sorted = predictions.sort((a, b) => b.probability - a.probability);
        
        this.elements.resultsContent.innerHTML = sorted.map(pred => {
            const percentage = (pred.probability * 100).toFixed(1);
            const isNormal = pred.className.toLowerCase().includes('정상') || pred.className.toLowerCase().includes('normal');
            const styleClass = isNormal ? 'result-normal' : 'result-pneumonia';
            
            return `
                <div class="result-item ${styleClass}">
                    <span>${pred.className}</span>
                    <span class="result-percentage">${percentage}%</span>
                </div>
            `;
        }).join('');

        // Update comment
        const pneumonia = sorted.find(p => !p.className.toLowerCase().includes('정상'));
        if (pneumonia && this.elements.resultComment) {
             const prob = pneumonia.probability * 100;
             let text = '', className = '';
             if (prob > 90) { text = "<strong>높은 위험:</strong> 폐렴일 가능성이 매우 높습니다."; className = 'warning'; }
             else if (prob > 70) { text = "<strong>주의 필요:</strong> 폐렴 가능성이 있습니다."; className = 'warning'; }
             else { text = "<strong>낮은 위험:</strong> 정상 범위로 보입니다."; className = 'privacy'; }
             
             this.elements.resultComment.innerHTML = `<i class="fa-solid fa-comment-medical"></i> <div>${text}</div>`;
             this.elements.resultComment.className = `notice-box ${className}`;
        }

        if (this.elements.reportTimestamp) {
            this.elements.reportTimestamp.textContent = `진단 시각: ${new Date().toLocaleString()}`;
        }
    }

    renderMetadata(metadata) {
        // Implementation for metadata if needed, or skip
    }

    renderProgress(state) {
        const { progress } = state;
        if (this.elements.progressContainer) {
            if (state.isAnalyzing) {
                this.elements.progressContainer.style.display = 'block';
                if (this.elements.progressBarFill) {
                    this.elements.progressBarFill.style.width = `${progress.percent}%`;
                }
            } else {
                this.elements.progressContainer.style.display = 'none';
            }
        }
    }

    renderError(state) {
        if (state.error) {
            alert(state.error); // Simple alert for now as per legacy behavior
        }
    }
}

export default UIController;
