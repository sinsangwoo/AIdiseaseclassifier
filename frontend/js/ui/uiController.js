/**
 * UI Controller
 *
 * state.status 로 화면을 전환합니다.
 *
 * [화면 전환 정리]
 * idle      : uploadSection 표시, 나머지 숨김
 * preview   : previewContainer 표시, uploadSection 숨김, 나머지 숨김
 * analyzing : progressContainer 표시, 다른 설 숨김
 * complete  : reportContainer 표시, 다른 설 숨김
 * error     : previewContainer 표시(에러 메시지포함), uploadSection 숨김
 */

import CONFIG from '../config.js';
import GradCAMViewer from './gradcam_viewer.js';

export default class UIController {
    constructor() {
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

        const required = { uploadSection: this.uploadSection, imageInput: this.imageInput, analyzeBtn: this.analyzeBtn };
        Object.entries(required).forEach(([id, el]) => {
            if (!el) console.error(`[UIController] #${id} 요소를 찾지 못함`);
        });

        this.onAnalyze         = null;
        this.onFileSelect      = null;
        this.onClear           = null;
        this.onAgreementChange = null;

        this.gradcamViewer = new GradCAMViewer('gradcamViewer');

        this._progressInterval = null;
        this._progressValue    = 0;

        this._bindEvents();
        console.log('[UIController] 초기화 완료');
    }

    // ── 이벤트 바인딩 ──────────────────────────────────────────────────────
    _bindEvents() {
        if (this.uploadSection) {
            this.uploadSection.addEventListener('click', () => {
                console.log('[UIController] 업로드 영역 클릭');
                this.imageInput?.click();
            });
            this.uploadSection.addEventListener('dragover',  (e) => { e.preventDefault(); this.uploadSection.classList.add('upload--dragover'); });
            this.uploadSection.addEventListener('dragleave', ()  => this.uploadSection.classList.remove('upload--dragover'));
            this.uploadSection.addEventListener('drop',      (e) => {
                e.preventDefault();
                this.uploadSection.classList.remove('upload--dragover');
                const file = e.dataTransfer?.files?.[0];
                if (file) { console.log('[UIController] 드래그드롭:', file.name); this.onFileSelect?.(file); }
            });
        }

        if (this.imageInput) {
            this.imageInput.addEventListener('change', (e) => {
                const file = e.target.files?.[0];
                if (file) {
                    console.log('[UIController] 파일 선택:', file.name, file.type, file.size);
                    this.onFileSelect?.(file);
                    // input 초기화: 같은 파일 재선택 허용
                    e.target.value = '';
                }
            });
        }

        if (this.analyzeBtn) this.analyzeBtn.addEventListener('click', () => { console.log('[UIController] 분석 버튼'); this.onAnalyze?.(); });
        if (this.clearBtn)   this.clearBtn.addEventListener('click',   () => { console.log('[UIController] 초기화 버튼'); this.onClear?.(); });
        if (this.agreeCheckbox) {
            this.agreeCheckbox.addEventListener('change', (e) => {
                console.log('[UIController] 동의:', e.target.checked);
                this.onAgreementChange?.(e.target.checked);
            });
        }
        if (this.savePngBtn) this.savePngBtn.addEventListener('click', () => this._saveAsPng());
        if (this.savePdfBtn) this.savePdfBtn.addEventListener('click', () => this._saveAsPdf());
    }

    // ── 상태 기반 렌더링 ─────────────────────────────────────────────────────
    render(state) {
        console.log('[UIController] render:', state.status);
        switch (state.status) {
            case 'idle':      this._renderIdle();           break;
            case 'preview':   this._renderPreview(state);   break;
            case 'analyzing': this._renderAnalyzing();      break;
            case 'complete':  this._renderComplete(state);  break;
            case 'error':     this._renderError(state);     break;
            default: console.warn('[UIController] 알 수 없는 status:', state.status);
        }
    }

    // idle: uploadSection 만 표시
    _renderIdle() {
        this._show(this.uploadSection);
        this._hide(this.previewContainer);
        this._hide(this.progressContainer);
        this._hide(this.reportContainer);
    }

    // preview: previewContainer 만 표시, uploadSection 반드시 숨김
    _renderPreview(state) {
        this._hide(this.uploadSection);      // ★ 핵심 수정 1: 업로드 영역 숨김
        this._show(this.previewContainer);
        this._hide(this.progressContainer);
        this._hide(this.reportContainer);

        if (this.imagePreview && state.uploadedImageUrl) {
            this.imagePreview.src = state.uploadedImageUrl;
            console.log('[UIController] 미리보기 이미지 설정 완료');
        }
        if (this.analyzeBtn)    this.analyzeBtn.disabled  = !state.agreeChecked;
        if (this.agreeCheckbox) this.agreeCheckbox.checked = state.agreeChecked || false;
    }

    // analyzing: progressContainer 만 표시
    _renderAnalyzing() {
        this._hide(this.uploadSection);
        this._hide(this.previewContainer);
        this._show(this.progressContainer);
        this._hide(this.reportContainer);
        if (this.progressLabel) this.progressLabel.textContent = '딥러닝 모델이 흉부 영상을 분석하고 있습니다.';
        this._startProgressAnimation();
    }

    // complete: reportContainer 만 표시
    _renderComplete(state) {
        this._stopProgressAnimation();
        this._hide(this.uploadSection);
        this._hide(this.previewContainer);
        this._hide(this.progressContainer);
        this._show(this.reportContainer);

        if (!state.result) { console.warn('[UIController] result 없음'); return; }

        if (this.reportTimestamp) this.reportTimestamp.textContent = new Date().toLocaleString('ko-KR');
        if (this.reportId)        this.reportId.textContent = `REQ-${Date.now().toString(36).toUpperCase()}`;
        if (this.reportImage && state.uploadedImageUrl) this.reportImage.src = state.uploadedImageUrl;

        this._renderPredictions(state.result);
        if (state.result.gradcam) this.gradcamViewer.render(state.result.gradcam, state.uploadedImageUrl);
    }

    // error: previewContainer 표시(uploadSection 숨김), 에러 메시지 표시
    _renderError(state) {
        this._stopProgressAnimation();
        this._hide(this.uploadSection);      // ★ 핵심 수정 2: 에러 시에도 uploadSection 숨김
        this._show(this.previewContainer);
        this._hide(this.progressContainer);
        this._hide(this.reportContainer);
        console.error('[UIController] 에러:', state.error);

        // 에러 메시지를 previewContainer 안에 표시
        this._showErrorBanner(state.error);
    }

    _showErrorBanner(msg) {
        const existing = this.previewContainer?.querySelector('.ui-error-banner');
        if (existing) existing.remove();
        if (!msg || !this.previewContainer) return;

        const banner = document.createElement('div');
        banner.className = 'ui-error-banner notice notice--danger';
        banner.style.cssText = 'margin-bottom:1rem;padding:0.75rem 1rem;border-radius:var(--radius-md,8px);background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);color:#ef4444;font-size:0.85rem;';
        banner.innerHTML = `<i class="fa-solid fa-circle-exclamation" style="margin-right:0.5rem;"></i>${msg}<br><small style="opacity:0.7;">잠시 후 다시 시도하세요.</small>`;
        this.previewContainer.insertBefore(banner, this.previewContainer.firstChild);
    }

    // ── 예측 결과 렌더링 ─────────────────────────────────────────────────────
    _renderPredictions(result) {
        if (!this.resultsContent || !result.predictions) return;
        const top = result.predictions[0];
        const isPneumonia = top.className === '폐렴';
        this.resultsContent.innerHTML = result.predictions.map(pred => {
            const pct = (pred.probability * 100).toFixed(1);
            const cls = pred === top ? (isPneumonia ? 'result-card--danger' : 'result-card--success') : '';
            return `<div class="result-card ${cls}"><div class="result-card__header"><span class="result-card__label">${pred.className}</span><span class="result-card__value">${pct}%</span></div><div class="result-card__bar"><div class="result-card__bar-fill" style="width:${pct}%"></div></div></div>`;
        }).join('');
        if (this.resultComment) {
            const c = isPneumonia
                ? { icon: '⚠️', cls: 'notice--danger',  text: '폐렴 소견입니다. 전문의 상담을 권장합니다.' }
                : { icon: '✅', cls: 'notice--success', text: '정상 소견입니다. 정기적인 검진을 권장합니다.' };
            this.resultComment.className = `notice notice--diagnosis ${c.cls}`;
            this.resultComment.innerHTML = `<span>${c.icon}</span><span>${c.text}</span>`;
        }
        if (result.metadata?.processing_time_ms) {
            const el = document.createElement('p');
            el.className = 'text-tiny text-muted mt-sm text-right';
            el.textContent = `처리시간: ${result.metadata.processing_time_ms.toFixed(0)}ms`;
            this.resultsContent.appendChild(el);
        }
    }

    // ── 프로그레스 ───────────────────────────────────────────────────────────
    _startProgressAnimation() {
        this._stopProgressAnimation();
        this._progressValue = 0;
        if (!this.progressBarFill) return;
        this._progressInterval = setInterval(() => {
            if (this._progressValue < 95) {
                const inc = this._progressValue < 30 ? 2 : this._progressValue < 60 ? 1 : 0.3;
                this._progressValue = Math.min(95, this._progressValue + inc);
                this.progressBarFill.style.width = `${this._progressValue}%`;
            }
        }, 200);
    }

    _stopProgressAnimation() {
        if (this._progressInterval) { clearInterval(this._progressInterval); this._progressInterval = null; }
        if (this.progressBarFill) this.progressBarFill.style.width = '100%';
    }

    // ── 저장 ──────────────────────────────────────────────────────────────
    async _saveAsPng() {
        try {
            const card = document.getElementById('reportCard');
            if (!card || !window.html2canvas) return;
            const canvas = await html2canvas(card, { scale: 2, useCORS: true });
            const a = document.createElement('a');
            a.download = `diagnosis_${Date.now()}.png`; a.href = canvas.toDataURL('image/png'); a.click();
        } catch (e) { console.error('[UIController] PNG 실패:', e); }
    }

    async _saveAsPdf() {
        try {
            const card = document.getElementById('reportCard');
            if (!card || !window.html2canvas || !window.jspdf) return;
            const canvas = await html2canvas(card, { scale: 2, useCORS: true });
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
            const w = pdf.internal.pageSize.getWidth();
            pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, w, (canvas.height * w) / canvas.width);
            pdf.save(`diagnosis_${Date.now()}.pdf`);
        } catch (e) { console.error('[UIController] PDF 실패:', e); }
    }

    // ── 유틸 ────────────────────────────────────────────────────────────────
    _show(el) { el?.classList.remove('hidden'); }
    _hide(el) { el?.classList.add('hidden'); }

    resetUI() {
        console.log('[UIController] resetUI');
        this._show(this.uploadSection);
        this._hide(this.previewContainer);
        this._hide(this.progressContainer);
        this._hide(this.reportContainer);
        if (this.imageInput)    this.imageInput.value      = '';
        if (this.analyzeBtn)    this.analyzeBtn.disabled   = true;
        if (this.agreeCheckbox) this.agreeCheckbox.checked  = false;
        this._stopProgressAnimation();
        this.gradcamViewer?.hide();
        // 에러 배너 제거
        this.previewContainer?.querySelector('.ui-error-banner')?.remove();
    }
}
