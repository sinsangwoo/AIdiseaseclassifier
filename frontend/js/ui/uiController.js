/**
 * UI Controller (Phase D - Grad-CAM 통합)
 *
 * 상태 변경에 따른 UI 업데이트 담당
 * Phase D: GradCAMViewer 연동 추가
 */

import GradCAMViewer from './gradcam_viewer.js';

class UIController {
    constructor() {
        console.log('\u2705 UIController Initialized');
        this.elements = {
            uploadSection:    document.getElementById('uploadSection'),
            imageInput:       document.getElementById('imageInput'),
            previewContainer: document.getElementById('previewContainer'),
            imagePreview:     document.getElementById('imagePreview'),
            analyzeBtn:       document.getElementById('analyzeBtn'),
            clearBtn:         document.getElementById('clearBtn'),
            reportContainer:  document.getElementById('reportContainer'),
            resultsContent:   document.getElementById('resultsContent'),
            resultComment:    document.getElementById('resultComment'),
            reportTimestamp:  document.getElementById('reportTimestamp'),
            agreementBox:     document.getElementById('agreementBox'),
            agreeCheckbox:    document.getElementById('agreeCheckbox'),
            progressContainer:document.getElementById('progressContainer'),
            progressBarFill:  document.getElementById('progressBarFill'),
            // Optional elements
            savePngBtn:       document.getElementById('savePngBtn'),
            savePdfBtn:       document.getElementById('savePdfBtn'),
            reportImage:      document.getElementById('reportImage'),
        };

        // Grad-CAM 히트맵 뷰어
        this.gradcamViewer = new GradCAMViewer('gradcamViewer');

        // Callbacks
        this.onAnalyze           = null;
        this.onFileSelect        = null;
        this.onClear             = null;
        this.onAgreementChange   = null;

        this.bindEvents();
    }

    bindEvents() {
        // File Input Change
        this.elements.imageInput?.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file && this.onFileSelect) this.onFileSelect(file);
        });

        // Upload Section Drag & Drop / Click
        if (this.elements.uploadSection) {
            this.elements.uploadSection.addEventListener('click', () => {
                this.elements.imageInput?.click();
            });
            this.elements.uploadSection.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.currentTarget.classList.add('upload--active');
            });
            this.elements.uploadSection.addEventListener('dragleave', (e) => {
                e.preventDefault();
                e.currentTarget.classList.remove('upload--active');
            });
            this.elements.uploadSection.addEventListener('drop', (e) => {
                e.preventDefault();
                e.currentTarget.classList.remove('upload--active');
                const file = e.dataTransfer.files[0];
                if (file && this.onFileSelect) this.onFileSelect(file);
            });
        }

        // Analyze Button
        this.elements.analyzeBtn?.addEventListener('click', () => {
            if (this.onAnalyze) this.onAnalyze();
        });

        // Clear Button
        this.elements.clearBtn?.addEventListener('click', () => {
            this.resetUI();
            if (this.onClear) this.onClear();
        });

        // Agreement Checkbox
        this.elements.agreeCheckbox?.addEventListener('change', (e) => {
            if (this.onAgreementChange) this.onAgreementChange(e.target.checked);
        });

        // Save PNG Button
        this.elements.savePngBtn?.addEventListener('click', () => this.handleSavePng());

        // Save PDF Button
        this.elements.savePdfBtn?.addEventListener('click', () => this.handleSavePdf());
    }

    resetUI() {
        console.log('\U0001f9f9 UI Reset Triggered');
        if (this.elements.imageInput)   this.elements.imageInput.value = '';
        if (this.elements.imagePreview) this.elements.imagePreview.src = '';
        if (this.elements.reportImage)  this.elements.reportImage.src  = '';
        if (this.elements.agreeCheckbox) this.elements.agreeCheckbox.checked = false;

        if (this._currentObjectURL) {
            URL.revokeObjectURL(this._currentObjectURL);
            this._currentObjectURL = null;
            this._lastFile = null;
        }

        if (this.elements.uploadSection) {
            this.elements.uploadSection.style.display = 'block';
            this.elements.uploadSection.classList.remove('hidden', 'upload--disabled');
        }
        if (this.elements.previewContainer) {
            this.elements.previewContainer.style.display = 'none';
            this.elements.previewContainer.classList.add('hidden');
        }
        if (this.elements.reportContainer) {
            this.elements.reportContainer.style.display = 'none';
            this.elements.reportContainer.classList.add('hidden');
        }
        if (this.elements.progressContainer) {
            this.elements.progressContainer.style.display = 'none';
            this.elements.progressContainer.classList.add('hidden');
        }
        if (this.elements.analyzeBtn) this.elements.analyzeBtn.disabled = true;

        // Grad-CAM 뷰어 리셋
        this.gradcamViewer.hide();
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
            if (this.elements.imagePreview) {
                if (this._lastFile !== state.uploadedImage) {
                    if (this._currentObjectURL) URL.revokeObjectURL(this._currentObjectURL);
                    this._currentObjectURL = URL.createObjectURL(state.uploadedImage);
                    this._lastFile = state.uploadedImage;
                }
                this.elements.imagePreview.src = this._currentObjectURL;
                this.elements.imagePreview.classList.add('preview__image--visible');
            }
            if (this.elements.uploadSection) {
                this.elements.uploadSection.style.display = 'none';
                this.elements.uploadSection.classList.add('upload--disabled');
            }
            if (this.elements.previewContainer) {
                this.elements.previewContainer.style.display = 'block';
                this.elements.previewContainer.classList.remove('hidden');
            }
        } else {
            if (this.elements.uploadSection)  this.elements.uploadSection.style.display  = 'block';
            if (this.elements.previewContainer) this.elements.previewContainer.style.display = 'none';
        }
    }

    renderAnalyzeButton(state) {
        if (this.elements.analyzeBtn) {
            const isEnabled = state.uploadedImage && state.agreeChecked;
            this.elements.analyzeBtn.disabled  = !isEnabled || state.isAnalyzing;
            this.elements.analyzeBtn.textContent = state.isAnalyzing ? '\ubd84\uc11d \uc911...' : 'AI \uc815\ubc00 \ubd84\uc11d \uc2dc\uc791';
        }
        if (this.elements.agreeCheckbox) {
            this.elements.agreeCheckbox.checked = !!state.agreeChecked;
        }
    }

    renderResults(state) {
        if (!this.elements.reportContainer) return;

        if (state.analysisResult && state.analysisResult.success) {
            this.elements.reportContainer.style.display = 'block';
            this.elements.reportContainer.classList.remove('hidden');
            this.elements.previewContainer.style.display = 'none';
            this.elements.previewContainer.classList.add('hidden');

            if (this.elements.reportImage && this._currentObjectURL) {
                this.elements.reportImage.src = this._currentObjectURL;
                this.elements.reportImage.classList.add('preview__image--visible');
            }

            this.renderPredictions(state.analysisResult.predictions);
            this.renderMetadata(state.analysisResult.metadata || {});

            // ── Grad-CAM 히트맵 렌더링 ────────────────────────────
            const gradcam = state.analysisResult.gradcam;
            if (gradcam) {
                this.gradcamViewer.render(gradcam, this._currentObjectURL || '');
            } else {
                this.gradcamViewer.hide();
            }
        } else {
            this.elements.reportContainer.style.display = 'none';
            this.elements.reportContainer.classList.add('hidden');
            this.gradcamViewer.hide();
        }
    }

    renderPredictions(predictions) {
        if (!this.elements.resultsContent) return;

        const sorted = [...predictions].sort((a, b) => b.probability - a.probability);

        this.elements.resultsContent.innerHTML = sorted.map(pred => {
            const percentage = (pred.probability * 100).toFixed(1);
            const isNormal   = pred.className.toLowerCase().includes('\uc815\uc0c1') ||
                               pred.className.toLowerCase().includes('normal');
            return `
                <div class="card--result card--result-${isNormal ? 'normal' : 'pneumonia'}">
                    <span>${pred.className}</span>
                    <span class="card__result-percentage">${percentage}%</span>
                </div>
            `;
        }).join('');

        const pneumonia = sorted.find(p =>
            !p.className.toLowerCase().includes('\uc815\uc0c1') &&
            !p.className.toLowerCase().includes('normal')
        );
        if (pneumonia && this.elements.resultComment) {
            const prob = pneumonia.probability * 100;
            let text = '', className = '';
            if (prob > 90) {
                text = '<strong>\ub192\uc740 \uc704\ud5d8:</strong> \ud3d0\ub834\uc77c \uac00\ub2a5\uc131\uc774 \ub9e4\uc6b0 \ub192\uc2b5\ub2c8\ub2e4.';
                className = 'warning';
            } else if (prob > 70) {
                text = '<strong>\uc8fc\uc758 \ud544\uc694:</strong> \ud3d0\ub834 \uac00\ub2a5\uc131\uc774 \uc788\uc2b5\ub2c8\ub2e4.';
                className = 'warning';
            } else {
                text = '<strong>\ub099\uc740 \uc704\ud5d8:</strong> \uc815\uc0c1 \ubc94\uc704\ub85c \ubcf4\uc785\ub2c8\ub2e4.';
                className = 'privacy';
            }
            this.elements.resultComment.innerHTML =
                `<i class="fa-solid fa-comment-medical"></i> <div>${text}</div>`;
            this.elements.resultComment.className =
                `notice notice--diagnosis ${className}`;
        }

        if (this.elements.reportTimestamp) {
            this.elements.reportTimestamp.textContent =
                `\uc9c4\ub2e8 \uc2dc\uac01: ${new Date().toLocaleString()}`;
        }

        const reportIdElem = document.getElementById('reportId');
        if (reportIdElem && reportIdElem.textContent.includes('REQ-2026-AI')) {
            reportIdElem.textContent = 'REQ-' +
                Math.random().toString(16).slice(2, 8).toUpperCase();
        }
    }

    /** PNG \uc800\uc7a5 */
    async handleSavePng() {
        const reportCard = document.getElementById('reportCard');
        if (!reportCard) return;
        try {
            const canvas = await html2canvas(reportCard, {
                useCORS: true, scale: 3, backgroundColor: '#0B0B0D', logging: false,
                onclone: (clonedDoc) => {
                    const el = clonedDoc.getElementById('reportCard');
                    if (el) {
                        [...el.getElementsByTagName('*')].forEach(e => {
                            e.style.letterSpacing = 'normal';
                            e.style.wordSpacing   = 'normal';
                        });
                        const btns = el.querySelector('.card__footer .btn-group');
                        if (btns) btns.style.display = 'none';
                    }
                }
            });
            const link = document.createElement('a');
            link.download = `AI_Diagnosis_Result_${Date.now()}.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
        } catch (err) {
            console.error('PNG \uc800\uc7a5 \uc2e4\ud328:', err);
            alert('PNG \uc800\uc7a5 \uc911 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4.');
        }
    }

    /** PDF \ub9ac\ud3ec\ud2b8 \uc0dd\uc131 */
    async handleSavePdf() {
        const reportCard = document.getElementById('reportCard');
        if (!reportCard) return;
        try {
            const { jsPDF } = window.jspdf;
            const canvas = await html2canvas(reportCard, {
                useCORS: true, scale: 3, backgroundColor: '#0B0B0D',
                onclone: (clonedDoc) => {
                    const el = clonedDoc.getElementById('reportCard');
                    if (el) {
                        [...el.getElementsByTagName('*')].forEach(e => {
                            e.style.letterSpacing = 'normal';
                            e.style.wordSpacing   = 'normal';
                        });
                        const btns = el.querySelector('.card__footer .btn-group');
                        if (btns) btns.style.display = 'none';
                    }
                }
            });
            const imgData = canvas.toDataURL('image/png');
            const doc = new jsPDF('p', 'mm', 'a4');
            const pageW = doc.internal.pageSize.getWidth();
            const pageH = doc.internal.pageSize.getHeight();
            const imgW  = pageW - 20;
            const imgH  = (canvas.height * imgW) / canvas.width;

            doc.setFontSize(18);
            doc.setTextColor(201, 169, 110);
            doc.text('AI Diagnosis Official Report', 10, 15);
            doc.addImage(imgData, 'PNG', 10, 25, imgW, imgH);
            doc.setFontSize(9);
            doc.setTextColor(150, 150, 150);
            doc.text(`Generated on ${new Date().toLocaleString()}`, 10, pageH - 10);
            doc.text(
                'Disclaimer: This report is for reference only and does not replace medical professional judgment.',
                50, pageH - 10
            );
            const reportId = document.getElementById('reportId')?.textContent || 'N/A';
            doc.save(`AI_Diagnosis_Report_${reportId}.pdf`);
        } catch (err) {
            console.error('PDF \uc0dd\uc131 \uc2e4\ud328:', err);
            alert('PDF \ub9ac\ud3ec\ud2b8 \uc0dd\uc131 \uc911 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4.');
        }
    }

    renderMetadata(_metadata) { /* \ud655\uc7a5\uc6a9 */ }

    renderProgress(state) {
        const { progress } = state;
        if (this.elements.progressContainer) {
            if (state.isAnalyzing) {
                this.elements.progressContainer.style.display = 'block';
                this.elements.progressContainer.classList.remove('hidden');
                if (this.elements.progressBarFill)
                    this.elements.progressBarFill.style.width = `${progress.percent}%`;
            } else {
                this.elements.progressContainer.style.display = 'none';
                this.elements.progressContainer.classList.add('hidden');
            }
        }
    }

    renderError(state) {
        if (state.error) alert(state.error);
    }
}

export default UIController;
