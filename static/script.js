// --- 전역 변수 ---
// API 서버 주소
const API_URL = "http://127.0.0.1:5000/predict";

// HTML 요소 가져오기
const uploadSection = document.getElementById('uploadSection');
const imageInput = document.getElementById('imageInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const clearBtn = document.getElementById('clearBtn');
const progressContainer = document.getElementById('progressContainer');
const progressBarFill = document.getElementById('progressBarFill');
const reportContainer = document.getElementById('reportContainer');
const imagePreview = document.getElementById('imagePreview');
const resultsContent = document.getElementById('resultsContent');
const reportTimestamp = document.getElementById('reportTimestamp');
const agreeCheckbox = document.getElementById('agreeCheckbox');
const agreementBox = document.getElementById('agreementBox');
const resultComment = document.getElementById('resultComment');
const previewContainer = document.getElementById('previewContainer');
const reportImageContainer = document.getElementById('reportImageContainer');
const reportActions = document.querySelector('.report-actions');

// 상태 관리 변수
let uploadedFile = null;
let gaugeChart = null;

// --- 핵심 함수들 ---

/**
 * 파일이 업로드되었을 때 UI를 처리하는 함수
 * @param {File} file 사용자가 업로드한 파일 객체
 */
// handleFile 함수 
function handleFile(file) {
    if (file && file.type.startsWith('image/')) {
        uploadedFile = file;

        const reader = new FileReader();
        reader.onload = (e) => {
            // 1. 이미지 데이터 설정
            imagePreview.src = e.target.result;
            
            // 2. 버튼 상태 제어
            analyzeBtn.disabled = !agreeCheckbox.checked;

            // 3. UI 가시성 제어
            uploadSection.style.display = 'none';
            imagePreview.style.display = 'block'; 
            previewContainer.style.display = 'block';
            agreementBox.style.display = 'flex';
            clearBtn.style.display = 'inline-flex';
            reportContainer.style.display = 'none';
        };
        reader.readAsDataURL(file);
    } else {
        uploadedFile = null;
        alert("이미지 파일(JPG, PNG 등)을 선택해주세요.");
    }
}

/**
 * 'AI 분석 시작' 버튼 클릭 시 서버로 이미지를 전송하고 결과를 받는 함수
 */
async function analyzeImage() {
    if (!uploadedFile) {
        alert("분석할 이미지가 없습니다.");
        return;
    }

    // UI 상태 변경: 로딩 시작
    setLoadingState(true);

    const formData = new FormData();
    formData.append('file', uploadedFile);

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `서버 응답 오류: ${response.status}`);
        }

        const data = await response.json();
        
        setTimeout(() => {
            displayResults(data.predictions);
        }, 500);

    } catch (error) {
        console.error("분석 요청 중 오류 발생:", error);
        alert(`분석 중 오류가 발생했습니다: ${error.message}`);
        setLoadingState(false); // 오류 발생 시 로딩 상태 해제
    }
}

/**
 * 분석 결과를 받아 화면에 리포트를 표시하는 함수
 * @param {Array} predictions 서버로부터 받은 예측 결과 배열
 */
function displayResults(predictions) {
    // 1. 리포트 카드에 이미지 복제
    reportImageContainer.innerHTML = '';
    const imgClone = imagePreview.cloneNode(true);
    // cloneNode로 복제된 img는 id를 제거해주는 것이 좋습니다.
    imgClone.id = ''; 
    reportImageContainer.appendChild(imgClone);

    // 2. 예측 결과 정렬 및 폐렴 클래스 찾기
    const sorted = predictions.sort((a, b) => b.probability - a.probability);
    const pneumoniaResult = sorted.find(p => !(p.className.toLowerCase().includes('정상') || p.className.toLowerCase().includes('normal')));
    
    if (!pneumoniaResult) {
        alert("결과에 '폐렴' 클래스가 없습니다. Teachable Machine 모델을 확인해주세요.");
        setLoadingState(false);
        return;
    }

    // 3. 게이지 차트 그리기
    const pneumoniaProbability = pneumoniaResult.probability * 100;
    // drawGaugeChart(pneumoniaProbability); // drawGaugeChart 함수가 없으면 이 줄은 주석 처리 또는 삭제
    
    // 4. 상세 확률 및 동적 코멘트 표시
    resultsContent.innerHTML = '';
    sorted.forEach(p => {
        const item = createResultItem(p.className, p.probability);
        resultsContent.appendChild(item);
    });
    const { text, className } = getResultComment(pneumoniaProbability);
    resultComment.innerHTML = `<i class="fa-solid fa-comment-medical"></i> <div>${text}</div>`;
    resultComment.className = `notice-box ${className}`;
    
    // 5. 타임스탬프 및 UI 상태 변경 (순서 중요!)
    reportTimestamp.textContent = `진단 시각: ${new Date().toLocaleString()}`;
    setLoadingState(false);
    previewContainer.style.display = 'none'; // 미리보기 영역은 확실히 숨김
    reportContainer.style.display = 'block'; 
    resultComment.style.display = 'flex';    

    // 6. 리포트 저장 버튼 이벤트 연결
    document.getElementById('savePngBtn').onclick = () => saveReport('png');
    document.getElementById('savePdfBtn').onclick = () => saveReport('pdf');
}

/**
 * 모든 상태와 UI를 초기 상태로 되돌리는 함수
 */
function clearAll() {
    uploadedFile = null;
    imageInput.value = '';
    imagePreview.src = '';
    agreeCheckbox.checked = false;

    if (gaugeChart) {
        gaugeChart.destroy();
        gaugeChart = null;
    }
    
    // UI 요소 가시성 제어
    analyzeBtn.disabled = true;
    clearBtn.style.display = 'none';
    reportContainer.style.display = 'none';
    agreementBox.style.display = 'none';
    previewContainer.style.display = 'none';
    uploadSection.style.display = 'block';
    progressContainer.style.display = 'none';
}

// --- 보조 함수들 (코드를 더 깔끔하게 만들기 위함) ---

/**
 * 로딩 상태에 따라 UI를 변경하는 함수
 * @param {boolean} isLoading 로딩 중인지 여부
 */
function setLoadingState(isLoading) {
    if (isLoading) {
        analyzeBtn.disabled = true;
        clearBtn.disabled = true;
        progressContainer.style.display = 'block';
        simulateProgress();
    } else {
        analyzeBtn.disabled = false;
        clearBtn.disabled = false;
        progressContainer.style.display = 'none';
    }
}

/**
 * 프로그레스 바 애니메이션을 시뮬레이션하는 함수
 */
function simulateProgress() {
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
 * 게이지 차트를 그리는 함수
 * @param {number} value 폐렴 확률 (0-100)
 */
function drawGaugeChart(value) {
    const ctx = document.getElementById('gaugeChart').getContext('2d');
    if (gaugeChart) gaugeChart.destroy();

    const needleColor = value > 50 ? 'rgba(231, 76, 60, 1)' : 'rgba(40, 167, 69, 1)';
    gaugeChart = new Chart(ctx, { /* ... 차트 옵션 (기존과 동일) ... */ });
}

/**
 * 예측 결과 항목(div)을 생성하는 함수
 * @param {string} className 클래스 이름
 * @param {number} probability 확률 (0-1)
 * @returns {HTMLElement} 생성된 div 요소
 */
function createResultItem(className, probability) {
    const percentage = (probability * 100).toFixed(1);
    const item = document.createElement('div');
    item.className = 'result-item';
    
    const isNormal = className.toLowerCase().includes('정상') || className.toLowerCase().includes('normal');
    item.classList.add(isNormal ? 'result-normal' : 'result-pneumonia');
    
    item.innerHTML = `<span>${className}</span> <span class="result-percentage">${percentage}%</span>`;
    return item;
}

/**
 * 폐렴 확률에 따라 동적 코멘트를 반환하는 함수
 * @param {number} probability 폐렴 확률 (0-100)
 * @returns {{text: string, className: string}} 코멘트 텍스트와 CSS 클래스
 */
function getResultComment(probability) {
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
 * 리포트를 이미지나 PDF로 저장하는 함수
 * @param {'png' | 'pdf'} format 저장할 형식
 */
function saveReport(format) {
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

// --- 이벤트 리스너 설정 ---
// 페이지가 완전히 로드된 후 이벤트 리스너를 추가하여 'null' 오류를 방지합니다.
document.addEventListener('DOMContentLoaded', () => {
    // 각 요소가 존재하는지 다시 한번 확인 (방어적 코딩)
    if (analyzeBtn) analyzeBtn.addEventListener('click', analyzeImage);
    if (clearBtn) clearBtn.addEventListener('click', clearAll);
    if (imageInput) imageInput.addEventListener('change', (e) => handleFile(e.target.files[0]));
    if (agreeCheckbox) {
        agreeCheckbox.addEventListener('click', () => {
            if (uploadedFile) {
                analyzeBtn.disabled = !agreeCheckbox.checked;
            }
        });
    }
    // 드래그 앤 드롭 이벤트
    if (uploadSection) {
        uploadSection.addEventListener('dragover', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--primary-color)'; });
        uploadSection.addEventListener('dragleave', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--border-color)'; });
        uploadSection.addEventListener('drop', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--border-color)'; handleFile(e.dataTransfer.files[0]); });
    }
});

// 초기 UI 상태 설정
clearAll();