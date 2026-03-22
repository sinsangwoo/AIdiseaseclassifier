/**
 * UI Controller Module
 *
 * 상태에 따른 UI 렌더링 및 이벤트 핸들링
 * Phase D: GradCAMViewer 연동
 */

import CONFIG from '../config.js';
import { GradCAMViewer } from './gradcam_viewer.js';

export default class UIController {
    constructor() {
        // ── DOM 참조 ──────────────────────────────────────────────────────
        this.uploadSection    = document.getElementById('uploadSection');
        this.imageInput       = document.getElementById('imageInput');
        this.previewContainer = document.getElementById('previewContainer');
        this.imagePreview     = document.getElementById('imagePreview');
        this.analyzeBtn       = document.getElementById('analyzeBtn');
        this.clearBtn         = document.getElementById('clearBtn');
        this.agreeCheckbox    = document.getElementById('agreeCheckbox');
        this.progressContainer = document.getElementById('progressContainer');
        this.progressBarFill  = document.getElementById('progressBarFill');
        this.reportContainer  = document.getElementById('reportContainer');
        this.reportImage      = document.getElementById('reportImage');
        this.resultsContent   = document.getElementById('resultsContent');
        this.resultComment    = document.getElementById('resultComment');
        this.reportTimestamp  = document.getElementById('reportTimestamp');
        this.reportId         = document.getElementById('reportId');
        this.savePngBtn       = document.getElementById('savePngBtn');
        this.savePdfBtn       = document.getElementById('savePdfBtn');
        this.progressLabel    = document.querySelector('#progressContainer .text-muted.mb-lg');

        // ── 콜백 (app.js에서 주입) ────────────────────────────────────────
        this.onAnalyze         = null;
        this.onFileSelect      = null;
        this.onClear           = null;
        this.onAgreementChange = null;

        // ── Grad-CAM 뷰어 ─────────────────────────────────────────────────
        this.gradcamViewer = new GradCAMViewer('gradcamViewer');

        // ── 진행 상태 추적 ────────────────────────────────────────────────
        this._progressInterval = null;
        this._progressValue    = 0;

        this._bindEvents();
        CONFIG.log('UIController Initialized');
    }

    // ────────────────────────────────────────────────────────────────────
    // 이벤트 바인딩
    // ────────────────────────────────────────────────────────────────────
    _bindEvents() {
        // 드래그 앤 드롭
        if (this.uploadSection) {
            this.uploadSection.addEventListener('click',     () => this.imageInput?.click());
            this.uploadSection.addEventListener('dragover',  (e) => { e.preventDefault(); this.uploadSection.classList.add('upload--dragover'); });
            this.uploadSection.addEventListener('dragleave', ()  => this.uploadSection.classList.remove('upload--dragover'));
            this.uploadSection.addEventListener('drop',      (e) => {
                e.preventDefault();
                this.uploadSection.classList.remove('upload--dragover');
                const file = e.dataTransfer?.files?.[0];
                if (file) this._handleFileSelect(file);
            });
        }

        if (this.imageInput) {
            this.imageInput.addEventListener('change', (e) => {
                const file = e.target.files?.[0];
                if (file) this._handleFileSelect(file);
            });
        }

        if (this.analyzeBtn) {
            this.analyzeBtn.addEventListener('click', () => this.onAnalyze?.());
        }

        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => this.onClear?.());
        }

        if (this.agreeCheckbox) {
            this.agreeCheckbox.addEventListener('change', (e) => {
                this.onAgreementChange?.(e.target.checked);
            });
        }

        if (this.savePngBtn) this.savePngBtn.addEventListener('click', () => this._saveAsPng());
        if (this.savePdfBtn) this.savePdfBtn.addEventListener('click', () => this._saveAsPdf());
    }

    _handleFileSelect(file) {
        // 미리보기
        const reader = new FileReader();
        reader.onload = (e) => {
            if (this.imagePreview) this.imagePreview.src = e.target.result;
        };
        reader.readAsDataURL(file);
        this.onFileSelect?.(file);
    }

    // ────────────────────────────────────────────────────────────────────
    // 상태 기반 렌더링
    // ────────────────────────────────────────────────────────────────────
    render(state) {
        switch (state.status) {
            case 'idle':        this._renderIdle();              break;
            case 'preview':     this._renderPreview(state);      break;
            case 'analyzing':   this._renderAnalyzing(state);    break;
            case 'complete':    this._renderComplete(state);     break;
            case 'error':       this._renderError(state);        break;
        }
    }

    _renderIdle() {
        this._hide(this.previewContainer);
        this._hide(this.progressContainer);
        this._hide(this.reportContainer);
        this._show(this.uploadSection);
    }

    _renderPreview(state) {
        this._show(this.previewContainer);
        this._hide(this.progressContainer);
        this._hide(this.reportContainer);
        if (this.analyzeBtn) {
            this.analyzeBtn.disabled = !state.agreeChecked;
        }
        if (this.agreeCheckbox) {
            this.agreeCheckbox.checked = state.agreeChecked || false;
        }
    }

    _renderAnalyzing(state) {
        this._hide(this.previewContainer);
        this._show(this.progressContainer);
        this._hide(this.reportContainer);

        // 서버 웜업 중이면 라벨 변경
        if (this.progressLabel) {
            const isWarmingUp = !window.__serverReady__;
            this.progressLabel.textContent = isWarmingUp
                ? '서버를 깨우는 중입니다. 처음 접속 시 최대 2분이 소요됩니다...'
                : '딥러닝 모델이 흉부 영상을 분석하고 있습니다.';
        }

        this._startProgressAnimation();
    }

    _renderComplete(state) {
        this._stopProgressAnimation();
        this._hide(this.progressContainer);
        this._show(this.reportContainer);

        if (!state.result) return;

        // 타임스탬프 & ID
        if (this.reportTimestamp) {
            this.reportTimestamp.textContent = new Date().toLocaleString('ko-KR');
        }
        if (this.reportId) {
            this.reportId.textContent = `REQ-${Date.now().toString(36).toUpperCase()}`;
        }

        // 원본 이미지
        if (this.reportImage && state.uploadedImageUrl) {
            this.reportImage.src = state.uploadedImageUrl;
        }

        // 예측 결과
        this._renderPredictions(state.result);

        // Grad-CAM 뷰어
        if (state.result.gradcam) {
            this.gradcamViewer.render(state.result.gradcam, state.uploadedImageUrl);
        }
    }

    _renderError(state) {
        this._stopProgressAnimation();
        this._hide(this.progressContainer);
        this._show(this.previewContainer);
    }

    // ────────────────────────────────────────────────────────────────────
    // 예측 결과 렌더링
    // ────────────────────────────────────────────────────────────────────
    _renderPredictions(result) {
        if (!this.resultsContent || !result.predictions) return;

        const predictions = result.predictions;
        const topResult   = predictions[0];
        const isPneumonia = topResult.className === '폐렴';

        // 결과 카드
        this.resultsContent.innerHTML = predictions.map(pred => {
            const pct       = (pred.probability * 100).toFixed(1);
            const isTop     = pred === topResult;
            const cardClass = isTop ? (isPneumonia ? 'result-card--danger' : 'result-card--success') : '';
            return `
                <div class="result-card ${cardClass}">
                    <div class="result-card__header">
                        <span class="result-card__label">${pred.className}</span>
                        <span class="result-card__value">${pct}%</span>
                    </div>
                    <div class="result-card__bar">
                        <div class="result-card__bar-fill" style="width: ${pct}%"></div>
                    </div>
                </div>
            `;
        }).join('');

        // 코멘트
        if (this.resultComment) {
            const comment = isPneumonia
                ? { icon: '⚠️', cls: 'notice--danger',  text: '폐렴 소견이 감지되었습니다. 전문의 상담을 권장합니다.' }
                : { icon: '✅', cls: 'notice--success', text: '정상 소견입니다. 정기적인 검진을 권장합니다.' };
            this.resultComment.className = `notice notice--diagnosis ${comment.cls}`;
            this.resultComment.innerHTML = `<span>${comment.icon}</span><span>${comment.text}</span>`;
        }

        // 처리 시간
        if (result.metadata?.processing_time_ms) {
            const timeEl = document.createElement('p');
            timeEl.className = 'text-tiny text-muted mt-sm text-right';
            timeEl.textContent = `처리 시간: ${result.metadata.processing_time_ms.toFixed(0)}ms`;
            this.resultsContent.appendChild(timeEl);
        }
    }

    // ────────────────────────────────────────────────────────────────────
    // 프로그레스 바 애니메이션
    // ────────────────────────────────────────────────────────────────────
    _startProgressAnimation() {
        this._stopProgressAnimation();
        this._progressValue = 0;
        if (!this.progressBarFill) return;

        this._progressInterval = setInterval(() => {
            // 95%까지 서서히 증가 (완료는 _stopProgressAnimation에서)
            if (this._progressValue < 95) {
                const increment = this._progressValue < 30 ? 2
                                : this._progressValue < 60 ? 1
                                : 0.3;
                this._progressValue = Math.min(95, this._progressValue + increment);
                this.progressBarFill.style.width = `${this._progressValue}%`;
            }
        }, 200);
    }

    _stopProgressAnimation() {
        if (this._progressInterval) {
            clearInterval(this._progressInterval);
            this._progressInterval = null;
        }
        if (this.progressBarFill) {
            this.progressBarFill.style.width = '100%';
        }
    }

    // ────────────────────────────────────────────────────────────────────
    // 저장 기능
    // ────────────────────────────────────────────────────────────────────
    async _saveAsPng() {
        try {
            const reportCard = document.getElementById('reportCard');
            if (!reportCard || !window.html2canvas) return;
            const canvas = await html2canvas(reportCard, { scale: 2, useCORS: true });
            const link   = document.createElement('a');
            link.download = `diagnosis_${Date.now()}.png`;
            link.href     = canvas.toDataURL('image/png');
            link.click();
        } catch (e) {
            CONFIG.log('PNG 저장 실패:', e);
        }
    }

    async _saveAsPdf() {
        try {
            const reportCard = document.getElementById('reportCard');
            if (!reportCard || !window.html2canvas || !window.jspdf) return;
            const canvas = await html2canvas(reportCard, { scale: 2, useCORS: true });
            const { jsPDF } = window.jspdf;
            const pdf    = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
            const imgData = canvas.toDataURL('image/png');
            const w = pdf.internal.pageSize.getWidth();
            const h = (canvas.height * w) / canvas.width;
            pdf.addImage(imgData, 'PNG', 0, 0, w, h);
            pdf.save(`diagnosis_${Date.now()}.pdf`);
        } catch (e) {
            CONFIG.log('PDF 저장 실패:', e);
        }
    }

    // ────────────────────────────────────────────────────────────────────
    // 유틸
    // ────────────────────────────────────────────────────────────────────
    _show(el) { el?.classList.remove('hidden'); }
    _hide(el) { el?.classList.add('hidden'); }

    resetUI() {
        CONFIG.log('🧹 UI Reset Triggered');
        this._hide(this.previewContainer);
        this._hide(this.progressContainer);
        this._hide(this.reportContainer);
        if (this.imageInput)    this.imageInput.value    = '';
        if (this.analyzeBtn)    this.analyzeBtn.disabled = true;
        if (this.agreeCheckbox) this.agreeCheckbox.checked = false;
        this._stopProgressAnimation();
        this.gradcamViewer?.reset();
    }
}
