/**
 * UI Controller Module
 *
 * 상태에 따른 UI 렌더링 및 이벤트 핸들링
 * Phase D: GradCAMViewer 연동
 *
 * [state 스키마 - appState.js 스키마와 일치]
 * state.status:           'idle' | 'preview' | 'analyzing' | 'complete' | 'error'
 * state.uploadedImage:    File | null
 * state.uploadedImageUrl: string | null
 * state.result:           Object | null
 * state.agreeChecked:     boolean
 * state.error:            string | null
 */

import CONFIG from '../config.js';
import GradCAMViewer from './gradcam_viewer.js';

export default class UIController {
    constructor() {
        // ── DOM 참조 ──────────────────────────────────────────────────────
        this.uploadSection     = document.getElementById('uploadSection');
        this.imageInput        = document.getElementById('imageInput');
        this.previewContainer  = document.getElementById('previewContainer');
        this.imagePreview      = document.getElementById('imagePreview');
        this.analyzeBtn        = document.getElementById('analyzeBtn');
        this.clearBtn          = document.getElementById('clearBtn');
        this.agreeCheckbox     = document.getElementById('agreeCheckbox');
        this.progressContainer = document.getElementById('progressContainer');
        this.progressBarFill   = document.getElementById('progressBarFill');
        this.progressLabel     = document.querySelector('#progressContainer .text-muted.mb-lg');
        this.reportContainer   = document.getElementById('reportContainer');
        this.reportImage       = document.getElementById('reportImage');
        this.resultsContent    = document.getElementById('resultsContent');
        this.resultComment     = document.getElementById('resultComment');
        this.reportTimestamp   = document.getElementById('reportTimestamp');
        this.reportId          = document.getElementById('reportId');
        this.savePngBtn        = document.getElementById('savePngBtn');
        this.savePdfBtn        = document.getElementById('savePdfBtn');

        // DOM 요소 누락 경고
        const required = {
            uploadSection: this.uploadSection,
            imageInput:    this.imageInput,
            analyzeBtn:    this.analyzeBtn,
        };
        Object.entries(required).forEach(([id, el]) => {
            if (!el) console.error(`[UIController] #${id} 요소를 찾지 못함`);
        });

        // ── 콜백 (app.js에서 주입) ────────────────────────────────────────
        this.onAnalyze         = null;
        this.onFileSelect      = null;
        this.onClear           = null;
        this.onAgreementChange = null;

        // ── Grad-CAM 뷰어 ───────────────────────────────────────────────
        this.gradcamViewer = new GradCAMViewer('gradcamViewer');

        // ── 애니메이션 상태 ─────────────────────────────────────────────
        this._progressInterval = null;
        this._progressValue    = 0;

        this._bindEvents();
        console.log('[UIController] 초기화 완료');
    }

    // ────────────────────────────────────────────────────────────────────
    // 이벤트 바인딩
    // ────────────────────────────────────────────────────────────────────
    _bindEvents() {
        if (this.uploadSection) {
            this.uploadSection.addEventListener('click', () => {
                console.log('[UIController] 업로드 영역 클릭');
                this.imageInput?.click();
            });
            this.uploadSection.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.uploadSection.classList.add('upload--dragover');
            });
            this.uploadSection.addEventListener('dragleave', () =>
                this.uploadSection.classList.remove('upload--dragover')
            );
            this.uploadSection.addEventListener('drop', (e) => {
                e.preventDefault();
                this.uploadSection.classList.remove('upload--dragover');
                const file = e.dataTransfer?.files?.[0];
                if (file) {
                    console.log('[UIController] 드래그드롭 파일:', file.name);
                    this.onFileSelect?.(file);
                }
            });
        } else {
            console.error('[UIController] uploadSection 없음 — 이벤트 바인딩 불가');
        }

        if (this.imageInput) {
            this.imageInput.addEventListener('change', (e) => {
                const file = e.target.files?.[0];
                if (file) {
                    console.log('[UIController] 파일 선택:', file.name, file.type, file.size);
                    // 미리보기는 appState.setUploadedImage 안에서 FileReader로 처리
                    this.onFileSelect?.(file);
                } else {
                    console.warn('[UIController] 파일 선택 취소 또는 빈 파일');
                }
            });
        } else {
            console.error('[UIController] imageInput 없음 — 파일 선택 불가');
        }

        if (this.analyzeBtn) {
            this.analyzeBtn.addEventListener('click', () => {
                console.log('[UIController] 분석 버튼 클릭');
                this.onAnalyze?.();
            });
        }
        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => {
                console.log('[UIController] 초기화 버튼 클릭');
                this.onClear?.();
            });
        }
        if (this.agreeCheckbox) {
            this.agreeCheckbox.addEventListener('change', (e) => {
                console.log('[UIController] 동의 체크박스:', e.target.checked);
                this.onAgreementChange?.(e.target.checked);
            });
        }

        if (this.savePngBtn) this.savePngBtn.addEventListener('click', () => this._saveAsPng());
        if (this.savePdfBtn) this.savePdfBtn.addEventListener('click', () => this._saveAsPdf());
    }

    // ────────────────────────────────────────────────────────────────────
    // 상태 기반 렌더링 (state.status 로 분기)
    // ────────────────────────────────────────────────────────────────────
    render(state) {
        console.log('[UIController] render status:', state.status);
        switch (state.status) {
            case 'idle':      this._renderIdle();           break;
            case 'preview':   this._renderPreview(state);   break;
            case 'analyzing': this._renderAnalyzing(state); break;
            case 'complete':  this._renderComplete(state);  break;
            case 'error':     this._renderError(state);     break;
            default:
                console.warn('[UIController] 알 수 없는 status:', state.status);
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

        // 미리보기 이미지 설정 (appState에서 uploadedImageUrl 제공)
        if (this.imagePreview && state.uploadedImageUrl) {
            this.imagePreview.src = state.uploadedImageUrl;
        }
        if (this.analyzeBtn)    this.analyzeBtn.disabled  = !state.agreeChecked;
        if (this.agreeCheckbox) this.agreeCheckbox.checked = state.agreeChecked || false;
    }

    _renderAnalyzing(state) {
        this._hide(this.previewContainer);
        this._show(this.progressContainer);
        this._hide(this.reportContainer);

        if (this.progressLabel) {
            this.progressLabel.textContent =
                '딥러닝 모델이 흉부 영상을 분석하고 있습니다.';
        }
        this._startProgressAnimation();
    }

    _renderComplete(state) {
        this._stopProgressAnimation();
        this._hide(this.progressContainer);
        this._show(this.reportContainer);

        if (!state.result) {
            console.warn('[UIController] complete 상태인데 result가 없음');
            return;
        }

        if (this.reportTimestamp) {
            this.reportTimestamp.textContent = new Date().toLocaleString('ko-KR');
        }
        if (this.reportId) {
            this.reportId.textContent = `REQ-${Date.now().toString(36).toUpperCase()}`;
        }
        if (this.reportImage && state.uploadedImageUrl) {
            this.reportImage.src = state.uploadedImageUrl;
        }

        this._renderPredictions(state.result);

        if (state.result.gradcam) {
            this.gradcamViewer.render(state.result.gradcam, state.uploadedImageUrl);
        }
    }

    _renderError(state) {
        this._stopProgressAnimation();
        this._hide(this.progressContainer);
        this._show(this.previewContainer);
        console.error('[UIController] 에러 상태:', state.error);
    }

    // ────────────────────────────────────────────────────────────────────
    // 예측 결과 렌더링
    // ────────────────────────────────────────────────────────────────────
    _renderPredictions(result) {
        if (!this.resultsContent || !result.predictions) {
            console.warn('[UIController] 예측 결과 데이터 없음');
            return;
        }

        const predictions = result.predictions;
        const top         = predictions[0];
        const isPneumonia = top.className === '폐렴';

        this.resultsContent.innerHTML = predictions.map(pred => {
            const pct       = (pred.probability * 100).toFixed(1);
            const cardClass = pred === top
                ? (isPneumonia ? 'result-card--danger' : 'result-card--success')
                : '';
            return `
                <div class="result-card ${cardClass}">
                    <div class="result-card__header">
                        <span class="result-card__label">${pred.className}</span>
                        <span class="result-card__value">${pct}%</span>
                    </div>
                    <div class="result-card__bar">
                        <div class="result-card__bar-fill" style="width:${pct}%"></div>
                    </div>
                </div>`;
        }).join('');

        if (this.resultComment) {
            const c = isPneumonia
                ? { icon: '⚠️', cls: 'notice--danger',  text: '폐렴 소견이 감지되었습니다. 전문의 상담을 권장합니다.' }
                : { icon: '✅', cls: 'notice--success', text: '정상 소견입니다. 정기적인 검진을 권장합니다.' };
            this.resultComment.className = `notice notice--diagnosis ${c.cls}`;
            this.resultComment.innerHTML = `<span>${c.icon}</span><span>${c.text}</span>`;
        }

        if (result.metadata?.processing_time_ms) {
            const el = document.createElement('p');
            el.className   = 'text-tiny text-muted mt-sm text-right';
            el.textContent = `처리 시간: ${result.metadata.processing_time_ms.toFixed(0)}ms`;
            this.resultsContent.appendChild(el);
        }
    }

    // ────────────────────────────────────────────────────────────────────
    // 프로그레스 바
    // ────────────────────────────────────────────────────────────────────
    _startProgressAnimation() {
        this._stopProgressAnimation();
        this._progressValue = 0;
        if (!this.progressBarFill) return;
        this._progressInterval = setInterval(() => {
            if (this._progressValue < 95) {
                const inc = this._progressValue < 30 ? 2
                          : this._progressValue < 60 ? 1
                          : 0.3;
                this._progressValue = Math.min(95, this._progressValue + inc);
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
    // 저장
    // ────────────────────────────────────────────────────────────────────
    async _saveAsPng() {
        try {
            const card = document.getElementById('reportCard');
            if (!card || !window.html2canvas) return;
            const canvas = await html2canvas(card, { scale: 2, useCORS: true });
            const a = document.createElement('a');
            a.download = `diagnosis_${Date.now()}.png`;
            a.href     = canvas.toDataURL('image/png');
            a.click();
        } catch (e) { console.error('[UIController] PNG 저장 실패:', e); }
    }

    async _saveAsPdf() {
        try {
            const card = document.getElementById('reportCard');
            if (!card || !window.html2canvas || !window.jspdf) return;
            const canvas   = await html2canvas(card, { scale: 2, useCORS: true });
            const { jsPDF } = window.jspdf;
            const pdf       = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
            const imgData   = canvas.toDataURL('image/png');
            const w         = pdf.internal.pageSize.getWidth();
            pdf.addImage(imgData, 'PNG', 0, 0, w, (canvas.height * w) / canvas.width);
            pdf.save(`diagnosis_${Date.now()}.pdf`);
        } catch (e) { console.error('[UIController] PDF 저장 실패:', e); }
    }

    // ────────────────────────────────────────────────────────────────────
    // 유틸
    // ────────────────────────────────────────────────────────────────────
    _show(el) { el?.classList.remove('hidden'); }
    _hide(el) { el?.classList.add('hidden'); }

    resetUI() {
        console.log('[UIController] resetUI');
        this._hide(this.previewContainer);
        this._hide(this.progressContainer);
        this._hide(this.reportContainer);
        if (this.imageInput)    this.imageInput.value      = '';
        if (this.analyzeBtn)    this.analyzeBtn.disabled   = true;
        if (this.agreeCheckbox) this.agreeCheckbox.checked  = false;
        this._stopProgressAnimation();
        this.gradcamViewer?.hide();
    }
}
