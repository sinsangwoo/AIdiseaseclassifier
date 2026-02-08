/**
 * UI Controller (Phase 4 Enhanced)
 * 
 * 상태 변경에 따른 UI 업데이트 담당
 * Phase 4: 진행 상태 표시 강화
 */

class UIController {
    constructor() {
        console.log('✅ UIController Initialized');
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
            savePdfBtn: document.getElementById('savePdfBtn'),
            reportImage: document.getElementById('reportImage')
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
            this.resetUI();
            if (this.onClear) {
                this.onClear();
            }
        });

        // Agreement Checkbox
        this.elements.agreeCheckbox?.addEventListener('change', (e) => {
            if (this.onAgreementChange) {
                this.onAgreementChange(e.target.checked);
            }
        });

        // Save PNG Button
        this.elements.savePngBtn?.addEventListener('click', () => {
            this.handleSavePng();
        });

        // Save PDF Button
        this.elements.savePdfBtn?.addEventListener('click', () => {
            this.handleSavePdf();
        });
    }

    resetUI() {
        console.log('🧹 UI Reset Triggered');
        // Reset DOM elements directly
        if (this.elements.imageInput) this.elements.imageInput.value = '';
        if (this.elements.imagePreview) this.elements.imagePreview.src = '';
        if (this.elements.reportImage) this.elements.reportImage.src = '';
        if (this.elements.agreeCheckbox) this.elements.agreeCheckbox.checked = false;

        // Revoke Object URL if exists
        if (this._currentObjectURL) {
            URL.revokeObjectURL(this._currentObjectURL);
            this._currentObjectURL = null;
            this._lastFile = null;
            console.log('🧹 Object URL Revoked');
        }

        // Hide/Show sections
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
            if (this.elements.imagePreview) {
                // Create object URL only if it's a new file
                if (this._lastFile !== state.uploadedImage) {
                    if (this._currentObjectURL) {
                        URL.revokeObjectURL(this._currentObjectURL);
                    }
                    this._currentObjectURL = URL.createObjectURL(state.uploadedImage);
                    this._lastFile = state.uploadedImage;
                    console.log('🖼️ New Object URL Created:', this._currentObjectURL);
                }
                this.elements.imagePreview.src = this._currentObjectURL;
                this.elements.imagePreview.classList.add('preview__image--visible');
            }

            // Show preview, hide upload
            if (this.elements.uploadSection) {
                this.elements.uploadSection.style.display = 'none';
                this.elements.uploadSection.classList.add('upload--disabled');
            }
            if (this.elements.previewContainer) {
                this.elements.previewContainer.style.display = 'block';
                this.elements.previewContainer.classList.remove('hidden');
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
            const isEnabled = state.uploadedImage && state.agreeChecked;
            this.elements.analyzeBtn.disabled = !isEnabled || state.isAnalyzing;
            this.elements.analyzeBtn.textContent = state.isAnalyzing ? '분석 중...' : 'AI 정밀 분석 시작';
        }

        // Sync checkbox with state
        if (this.elements.agreeCheckbox) {
            this.elements.agreeCheckbox.checked = !!state.agreeChecked;
        }
    }

    renderResults(state) {
        if (!this.elements.reportContainer) return;

        if (state.analysisResult && state.analysisResult.success) {
            this.elements.reportContainer.style.display = 'block';
            this.elements.reportContainer.classList.remove('hidden');
            this.elements.previewContainer.style.display = 'none'; // Hide preview when showing report
            this.elements.previewContainer.classList.add('hidden');

            // Set report image from the persisted URL
            if (this.elements.reportImage && this._currentObjectURL) {
                this.elements.reportImage.src = this._currentObjectURL;
            }

            this.renderPredictions(state.analysisResult.predictions);
            this.renderMetadata(state.analysisResult.metadata || {});
        } else {
            this.elements.reportContainer.style.display = 'none';
            this.elements.reportContainer.classList.add('hidden');
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

        // Update Report ID with a random one if not set
        const reportIdElem = document.getElementById('reportId');
        if (reportIdElem && reportIdElem.textContent.includes('REQ-2026-AI')) {
            const randomId = 'REQ-' + Math.random().toString(16).slice(2, 8).toUpperCase();
            reportIdElem.textContent = randomId;
        }
    }

    /**
     * PNG 저장 기능 (html2canvas)
     */
    async handleSavePng() {
        const reportCard = document.getElementById('reportCard');
        if (!reportCard) return;

        try {
            console.log('📸 Capturing PNG with optimizations...');
            const canvas = await html2canvas(reportCard, {
                useCORS: true,
                scale: 3, // 품질 향상을 위해 배율 증가
                backgroundColor: '#ffffff',
                logging: false,
                onclone: (clonedDoc) => {
                    // 클론된 문서에서 스타일 보정
                    const clonedReport = clonedDoc.getElementById('reportCard');
                    if (clonedReport) {
                        // html2canvas에서 겹침을 유발할 수 있는 스타일 초기화
                        const allElements = clonedReport.getElementsByTagName('*');
                        for (let el of allElements) {
                            el.style.letterSpacing = 'normal';
                            el.style.wordSpacing = 'normal';
                        }

                        // 버튼 등 불필요한 요소 숨기기 (선택 사항)
                        const footerButtons = clonedReport.querySelector('.card__footer .btn-group');
                        if (footerButtons) footerButtons.style.display = 'none';

                        // 갭(gap) 속성이 캔버스에서 무시되는 경우 대응
                        const flexContainers = clonedReport.querySelectorAll('.flex-center, .flex-between, .grid');
                        flexContainers.forEach(container => {
                            container.style.gap = '0'; // 갭 제거 후 자식에게 마진 부여가 더 안전할 수 있으나 일단 초기화
                        });
                    }
                }
            });

            const link = document.createElement('a');
            link.download = `AI_Diagnosis_Result_${new Date().getTime()}.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
            console.log('✅ Optimized PNG Saved');
        } catch (error) {
            console.error('PNG 저장 실패:', error);
            alert('PNG 저장 중 오류가 발생했습니다.');
        }
    }

    /**
     * PDF 리포트 생성 기능 (html2canvas -> jspdf)
     * 텍스트 직접 입력 방식은 한글 폰트 문제가 발생할 수 있어 
     * 리포트 화면을 캡처하여 PDF에 삽입하는 방식을 사용합니다.
     */
    async handleSavePdf() {
        const reportCard = document.getElementById('reportCard');
        if (!reportCard) return;

        try {
            console.log('📄 Generating PDF from screenshot...');
            const { jsPDF } = window.jspdf;

            // 1. Report Card 캡처
            const canvas = await html2canvas(reportCard, {
                useCORS: true,
                scale: 3, // 고해상도
                backgroundColor: '#ffffff',
                onclone: (clonedDoc) => {
                    const clonedReport = clonedDoc.getElementById('reportCard');
                    if (clonedReport) {
                        const allElements = clonedReport.getElementsByTagName('*');
                        for (let el of allElements) {
                            el.style.letterSpacing = 'normal';
                            el.style.wordSpacing = 'normal';
                        }
                        const footerButtons = clonedReport.querySelector('.card__footer .btn-group');
                        if (footerButtons) footerButtons.style.display = 'none';
                    }
                }
            });
            const imgData = canvas.toDataURL('image/png');

            // 2. PDF 생성
            const doc = new jsPDF('p', 'mm', 'a4');
            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();

            // 이미지 크기 계산 (비율 유지하며 맞춤)
            const imgWidth = pageWidth - 20; // 좌우 여백 10mm씩
            const imgHeight = (canvas.height * imgWidth) / canvas.width;

            // Header/Title
            doc.setFontSize(18);
            doc.setTextColor(0, 123, 255);
            doc.text('AI Diagnosis Official Report', 10, 15);

            // 캡처된 리포트 이미지 삽입
            doc.addImage(imgData, 'PNG', 10, 25, imgWidth, imgHeight);

            // Footer
            doc.setFontSize(9);
            doc.setTextColor(150, 150, 150);
            doc.text(`Generated on ${new Date().toLocaleString()}`, 10, pageHeight - 10);
            doc.text('Disclaimer: This report is for reference only and does not replace medical professional judgment.', 50, pageHeight - 10);

            const reportId = document.getElementById('reportId')?.textContent || 'N/A';
            doc.save(`AI_Diagnosis_Report_${reportId}.pdf`);
            console.log('✅ PDF Saved from Screenshot');
        } catch (error) {
            console.error('PDF 생성 실패:', error);
            alert('PDF 리포트 생성 중 오류가 발생했습니다.');
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
                this.elements.progressContainer.classList.remove('hidden');
                if (this.elements.progressBarFill) {
                    this.elements.progressBarFill.style.width = `${progress.percent}%`;
                }
            } else {
                this.elements.progressContainer.style.display = 'none';
                this.elements.progressContainer.classList.add('hidden');
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
