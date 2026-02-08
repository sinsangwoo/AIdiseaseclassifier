// --- 전역 변수 ---
// ✅ CONFIG 사용 (하드코딩된 URL 제거)
const API_URL = CONFIG.getFullURL(CONFIG.ENDPOINTS.PREDICT);

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
function handleFile(file) {
    if (file && file.type.startsWith('image/')) {
        // ✅ 파일 크기 검증 추가
        if (file.size > CONFIG.FILE.MAX_SIZE) {
            alert(`파일 크기가 너무 큽니다. 최대 ${CONFIG.FILE.MAX_SIZE / (1024 * 1024)}MB까지 허용됩니다.`);
            return;
        }

        uploadedFile = file;

        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            analyzeBtn.disabled = !agreeCheckbox.checked;
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
 * ✅ 개선: 재시도 로직, 타임아웃, 더 나은 에러 처리
 */
async function analyzeImage() {
    if (!uploadedFile) {
        alert("분석할 이미지가 없습니다.");
        return;
    }

    setLoadingState(true);

    const formData = new FormData();
    formData.append('file', uploadedFile);

    let lastError = null;

    // ✅ 재시도 로직 추가
    for (let attempt = 1; attempt <= CONFIG.REQUEST.RETRY_ATTEMPTS; attempt++) {
        try {
            CONFIG.log(`분석 시도 ${attempt}/${CONFIG.REQUEST.RETRY_ATTEMPTS}...`);

            // ✅ AbortController로 타임아웃 구현
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST.TIMEOUT);

            const response = await fetch(API_URL, {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `서버 응답 오류 (${response.status})`);
            }

            const data = await response.json();
            
            // ✅ 응답 검증
            if (!data.predictions || !Array.isArray(data.predictions)) {
                throw new Error('서버 응답 형식이 올바르지 않습니다');
            }

            setTimeout(() => {
                displayResults(data.predictions);
            }, 500);

            return; // 성공 시 함수 종료

        } catch (error) {
            lastError = error;
            CONFIG.log(`시도 ${attempt} 실패:`, error.message);

            // ✅ 타임아웃 에러 특별 처리
            if (error.name === 'AbortError') {
                lastError = new Error('요청 시간 초과. 네트워크 상태를 확인해주세요.');
            }

            // 마지막 시도가 아니면 재시도
            if (attempt < CONFIG.REQUEST.RETRY_ATTEMPTS) {
                await new Promise(resolve => setTimeout(resolve, CONFIG.REQUEST.RETRY_DELAY * attempt));
                continue;
            }
        }
    }

    // ✅ 모든 재시도 실패
    console.error("분석 요청 실패:", lastError);
    
    let userMessage = "분석 중 오류가 발생했습니다.";
    
    if (lastError.message.includes('Failed to fetch')) {
        userMessage = "서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.";
    } else if (lastError.message.includes('시간 초과')) {
        userMessage = lastError.message;
    } else {
        userMessage += `\n${lastError.message}`;
    }
    
    alert(userMessage);
    setLoadingState(false);
}

/**
 * 분석 결과를 받아 화면에 리포트를 표시하는 함수
 * @param {Array} predictions 서버로부터 받은 예측 결과 배열
 */
function displayResults(predictions) {
    reportImageContainer.innerHTML = '';
    const imgClone = imagePreview.cloneNode(true);
    imgClone.id = ''; 
    reportImageContainer.appendChild(imgClone);

    const sorted = predictions.sort((a, b) => b.probability - a.probability);
    const pneumoniaResult = sorted.find(p => !(p.className.toLowerCase().includes('정상') || p.className.toLowerCase().includes('normal')));
    
    if (!pneumoniaResult) {
        alert("결과에 '폐렴' 클래스가 없습니다. 모델을 확인해주세요.");
        setLoadingState(false);
        return;
    }

    const pneumoniaProbability = pneumoniaResult.probability * 100;
    
    resultsContent.innerHTML = '';
    sorted.forEach(p => {
        const item = createResultItem(p.className, p.probability);
        resultsContent.appendChild(item);
    });
    
    const { text, className } = getResultComment(pneumoniaProbability);
    resultComment.innerHTML = `<i class="fa-solid fa-comment-medical"></i> <div>${text}</div>`;
    resultComment.className = `notice-box ${className}`;
    
    reportTimestamp.textContent = `진단 시각: ${new Date().toLocaleString()}`;
    setLoadingState(false);
    previewContainer.style.display = 'none';
    reportContainer.style.display = 'block'; 
    resultComment.style.display = 'flex';    

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
    
    analyzeBtn.disabled = true;
    clearBtn.style.display = 'none';
    reportContainer.style.display = 'none';
    agreementBox.style.display = 'none';
    previewContainer.style.display = 'none';
    uploadSection.style.display = 'block';
    progressContainer.style.display = 'none';
}

// --- 보조 함수들 ---

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
    }, CONFIG.UI.PROGRESS_ANIMATION_SPEED);
}

function drawGaugeChart(value) {
    const ctx = document.getElementById('gaugeChart').getContext('2d');
    if (gaugeChart) gaugeChart.destroy();
    const needleColor = value > 50 ? 'rgba(231, 76, 60, 1)' : 'rgba(40, 167, 69, 1)';
    // Chart.js 초기화 (기존 코드 유지)
}

function createResultItem(className, probability) {
    const percentage = (probability * 100).toFixed(1);
    const item = document.createElement('div');
    item.className = 'result-item';
    
    const isNormal = className.toLowerCase().includes('정상') || className.toLowerCase().includes('normal');
    item.classList.add(isNormal ? 'result-normal' : 'result-pneumonia');
    
    item.innerHTML = `<span>${className}</span> <span class="result-percentage">${percentage}%</span>`;
    return item;
}

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
document.addEventListener('DOMContentLoaded', () => {
    // ✅ 환경 정보 표시 (개발 모드에서만)
    if (CONFIG.DEBUG) {
        console.log('='.repeat(50));
        console.log('🚀 AI Disease Classifier Frontend');
        console.log('Environment:', CONFIG.ENVIRONMENT);
        console.log('API URL:', API_URL);
        console.log('='.repeat(50));
    }

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
    
    if (uploadSection) {
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
            handleFile(e.dataTransfer.files[0]); 
        });
    }
});

// 초기 UI 상태 설정
clearAll();
