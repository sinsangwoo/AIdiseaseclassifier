/**
 * UI Controller Module
 * 
 * UI 요소 제어 및 사용자 인터랙션 처리
 */

import appState from '../state/appState.js';
import FileValidator from '../utils/fileValidator.js';
import ErrorHandler from '../utils/errorHandler.js';

/**
 * UIController 클래스
 */
export class UIController {
    constructor() {
        this.elements = this.initElements();
        this.setupEventListeners();
        this.subscribeToState();
    }

    /**
     * DOM 요소 초기화
     */
    initElements() {
        return {
            uploadSection: document.getElementById('uploadSection'),
            imageInput: document.getElementById('imageInput'),
            analyzeBtn: document.getElementById('analyzeBtn'),
            clearBtn: document.getElementById('clearBtn'),
            progressContainer: document.getElementById('progressContainer'),
            progressBarFill: document.getElementById('progressBarFill'),
            reportContainer: document.getElementById('reportContainer'),
            imagePreview: document.getElementById('imagePreview'),
            resultsContent: document.getElementById('resultsContent'),
            reportTimestamp: document.getElementById('reportTimestamp'),
            agreeCheckbox: document.getElementById('agreeCheckbox'),
            agreementBox: document.getElementById('agreementBox'),
            resultComment: document.getElementById('resultComment'),
            previewContainer: document.getElementById('previewContainer'),
            reportImageContainer: document.getElementById('reportImageContainer')
        };
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        const { imageInput, analyzeBtn, clearBtn, agreeCheckbox, uploadSection } = this.elements;

        // 파일 선택 이벤트
        imageInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });

        // 분석 버튼
        analyzeBtn.addEventListener('click', () => {
            this.handleAnalyze();
        });

        // 초기화 버튼
        clearBtn.addEventListener('click', () => {
            this.handleClear();
        });

        // 동의 체크박스
        agreeCheckbox.addEventListener('click', () => {
            appState.setAgreeChecked(agreeCheckbox.checked);
        });

        // 드래그 앤 드롭
        this.setupDragAndDrop();
    }

    /**
     * 드래그 앤 드롭 설정
     */
    setupDragAndDrop() {
        const { uploadSection } = this.elements;

        uploadSection.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.currentTarget.style.borderColor = 'var(--primary-color)';
        });

        uploadSection.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.currentTarget.style.borderColor = 'var(--border-color)';
        });

        uploadSection.addEventListener('drop', (e) => {
            e.preventDefault();
            e.currentTarget.style.borderColor = 'var(--border-color)';
            this.handleFileSelect(e.dataTransfer.files[0]);
        });
    }

    /**
     * 파일 선택 처리
     */
    handleFileSelect(file) {
        if (!file) return;

        // 파일 검증
        const { isValid, error } = FileValidator.validate(file);
        
        if (!isValid) {
            ErrorHandler.handleError(new Error(error), 'File Validation');
            return;
        }

        // 이미지 미리보기 생성
        const reader = new FileReader();
        reader.onload = (e) => {
            appState.setUploadedFile(file, e.target.result);
        };
        reader.readAsDataURL(file);
    }

    /**
     * 분석 처리 (외부에서 호출)
     */
    handleAnalyze() {
        // app.js에서 구현
        if (this.onAnalyze) {
            this.onAnalyze();
        }
    }

    /**
     * 초기화 처리
     */
    handleClear() {
        const { imageInput } = this.elements;
        
        imageInput.value = '';
        appState.reset();
    }

    /**
     * 상태 변경 구독
     */
    subscribeToState() {
        appState.subscribe((state) => {
            this.updateUI(state);
        });
    }

    /**
     * UI 업데이트
     */
    updateUI(state) {
        const {
            uploadSection,
            imagePreview,
            previewContainer,
            agreementBox,
            analyzeBtn,
            clearBtn,
            progressContainer,
            reportContainer,
            agreeCheckbox
        } = this.elements;

        // 파일 업로드 상태
        if (state.uploadedFile) {
            uploadSection.style.display = 'none';
            imagePreview.src = state.imagePreviewURL;
            imagePreview.style.display = 'block';
            previewContainer.style.display = 'block';
            agreementBox.style.display = 'flex';
            clearBtn.style.display = 'inline-flex';
            reportContainer.style.display = 'none';
            
            analyzeBtn.disabled = !state.agreeChecked;
        }

        // 분석 중 상태
        if (state.isAnalyzing) {
            analyzeBtn.disabled = true;
            clearBtn.disabled = true;
            progressContainer.style.display = 'block';
            this.simulateProgress();
        } else {
            progressContainer.style.display = 'none';
            
            if (state.uploadedFile) {
                analyzeBtn.disabled = !state.agreeChecked;
                clearBtn.disabled = false;
            }
        }

        // 분석 결과 상태
        if (state.analysisResult) {
            previewContainer.style.display = 'none';
            reportContainer.style.display = 'block';
            this.displayResults(state.analysisResult);
        }

        // 초기화 상태
        if (!state.uploadedFile && !state.isAnalyzing && !state.analysisResult) {
            uploadSection.style.display = 'block';
            previewContainer.style.display = 'none';
            agreementBox.style.display = 'none';
            clearBtn.style.display = 'none';
            reportContainer.style.display = 'none';
            analyzeBtn.disabled = true;
            agreeCheckbox.checked = false;
        }
    }

    /**
     * 진행 바 애니메이션
     */
    simulateProgress() {
        const { progressBarFill } = this.elements;
        let width = 0;
        progressBarFill.style.width = '0%';
        
        const interval = setInterval(() => {
            width += Math.random() * 10;
            if (width >= 100) {
                width = 100;
                clearInterval(interval);
            }
            progressBarFill.style.width = width + '%';
        }, 300);
    }

    /**
     * 분석 결과 표시
     */
    displayResults(data) {
        const { 
            reportImageContainer,
            resultsContent,
            resultComment,
            reportTimestamp,
            imagePreview
        } = this.elements;

        // 이미지 복제
        reportImageContainer.innerHTML = '';
        const imgClone = imagePreview.cloneNode(true);
        imgClone.id = '';
        reportImageContainer.appendChild(imgClone);

        // 예측 결과 정렬
        const predictions = data.predictions || [];
        const sorted = predictions.sort((a, b) => b.probability - a.probability);
        const pneumoniaResult = sorted.find(p => 
            !(p.className.toLowerCase().includes('정상') || 
              p.className.toLowerCase().includes('normal'))
        );

        if (!pneumoniaResult) {
            ErrorHandler.handleError(
                new Error('결과에 폐렴 클래스가 없습니다. 모델을 확인해주세요.'),
                'Display Results'
            );
            return;
        }

        const pneumoniaProbability = pneumoniaResult.probability * 100;

        // 상세 확률 표시
        resultsContent.innerHTML = '';
        sorted.forEach(p => {
            const item = this.createResultItem(p.className, p.probability);
            resultsContent.appendChild(item);
        });

        // 코멘트 표시
        const { text, className } = this.getResultComment(pneumoniaProbability);
        resultComment.innerHTML = `<i class="fa-solid fa-comment-medical"></i> <div>${text}</div>`;
        resultComment.className = `notice-box ${className}`;

        // 타임스탬프
        reportTimestamp.textContent = `진단 시각: ${new Date().toLocaleString()}`;
        resultComment.style.display = 'flex';

        // 리포트 저장 버튼
        document.getElementById('savePngBtn').onclick = () => this.saveReport('png');
        document.getElementById('savePdfBtn').onclick = () => this.saveReport('pdf');
    }

    /**
     * 결과 항목 생성
     */
    createResultItem(className, probability) {
        const percentage = (probability * 100).toFixed(1);
        const item = document.createElement('div');
        item.className = 'result-item';
        
        const isNormal = className.toLowerCase().includes('정상') || 
                        className.toLowerCase().includes('normal');
        item.classList.add(isNormal ? 'result-normal' : 'result-pneumonia');
        
        item.innerHTML = `<span>${className}</span> <span class="result-percentage">${percentage}%</span>`;
        return item;
    }

    /**
     * 결과 코멘트 생성
     */
    getResultComment(probability) {
        let text = '', className = '';
        
        if (probability > 90) {
            text = "<strong>높은 위험:</strong> 폐렴일 가능성이 매우 높게 예측되었습니다. 즉시 의료 전문가의 진단이 필요합니다.";
            className = 'warning';
        } else if (probability > 70) {
            text = "<strong>주의 필요:</strong> 폐렴 가능성이 있습니다. 의료 전문가와 상담하여 정확한 진단을 받는 것을 권장합니다.";
            className = 'warning';
        } else if (probability > 50) {
            text = "<strong>경계:</strong> 일부 비정상적인 패턴이 감지되었습니다. 상태를 지켜보거나 예방 차원에서 상담을 고려해볼 수 있습니다.";
            className = 'privacy';
        } else {
            text = "<strong>낮은 위험:</strong> 정상 범위로 예측되었습니다. 하지만 이 결과는 참고용이며, 의심 증상이 있다면 반드시 의사와 상담하세요.";
            className = 'privacy';
        }
        
        if (probability > 40 && probability < 60) {
            text += "<br><br><strong>참고:</strong> AI가 이미지를 판단하기 어려워하는 경계선상의 확률입니다. X-ray 이미지의 품질이나 각도에 따라 결과가 달라질 수 있습니다.";
        }
        
        return { text, className };
    }

    /**
     * 리포트 저장
     */
    saveReport(format) {
        const reportCard = document.getElementById('reportCard');
        const filename = `AI_폐렴_진단_리포트_${Date.now()}`;

        html2canvas(reportCard, { scale: 2, useCORS: true }).then(canvas => {
            if (format === 'png') {
                const link = document.createElement('a');
                link.download = `${filename}.png`;
                link.href = canvas.toDataURL('image/png');
                link.click();
            } else if (format === 'pdf') {
                const { jsPDF } = window.jspdf;
                const imgData = canvas.toDataURL('image/png');
                const pdf = new jsPDF({ orientation: 'p', unit: 'mm', format: 'a4' });
                const imgProps = pdf.getImageProperties(imgData);
                const pdfWidth = pdf.internal.pageSize.getWidth() - 20;
                const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
                pdf.addImage(imgData, 'PNG', 10, 10, pdfWidth, pdfHeight);
                pdf.save(`${filename}.pdf`);
            }
        });
    }
}

export default UIController;
