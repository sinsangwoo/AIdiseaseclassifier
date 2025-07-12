// --- 전역 변수 ---
const API_URL = "https://pneumonia-api-j3t8.onrender.com/predict"; 

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

function handleFile(file) {
    if (file && file.type.startsWith('image/')) {
        uploadedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            analyzeBtn.disabled = !agreeCheckbox.checked;
            uploadSection.style.display = 'none';
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

async function analyzeImage() {
    if (!uploadedFile) {
        alert("분석할 이미지가 없습니다.");
        return;
    }

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
        setLoadingState(false);
    }
}

function displayResults(predictions) {
    reportImageContainer.innerHTML = '';
    const imgClone = imagePreview.cloneNode(true);
    imgClone.style.maxWidth = '100%';
    imgClone.style.maxHeight = 'none';
    reportImageContainer.appendChild(imgClone);

    const sorted = predictions.sort((a, b) => b.probability - a.probability);
    const pneumoniaResult = sorted.find(p => !(p.className.toLowerCase().includes('정상') || p.className.toLowerCase().includes('normal')));
    
    if (!pneumoniaResult) {
        alert("결과에 '폐렴' 클래스가 없습니다. Render 서버의 모델을 확인해주세요.");
        setLoadingState(false);
        return;
    }

    const pneumoniaProbability = pneumoniaResult.probability * 100;
    drawGaugeChart(pneumoniaProbability);

    resultsContent.innerHTML = '';
    sorted.forEach(p => {
        const item = createResultItem(p.className, p.probability);
        resultsContent.appendChild(item);
    });
    const { text, className } = getResultComment(pneumoniaProbability);
    resultComment.innerHTML = `<i class="fa-solid fa-comment-medical"></i> <div>${text}</div>`;
    resultComment.className = `notice-box ${className}`;
    resultComment.style.display = 'flex';

    reportTimestamp.textContent = `진단 시각: ${new Date().toLocaleString()}`;
    setLoadingState(false);
    previewContainer.style.display = 'none';
    reportContainer.style.display = 'block';

    document.getElementById('savePngBtn').onclick = () => saveReport('png');
    document.getElementById('savePdfBtn').onclick = () => saveReport('pdf');
}

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
    progressContainer.style.display = 'none';
    uploadSection.style.display = 'block';
}

// --- 보조 함수들 ---
function setLoadingState(isLoading) {
    if (isLoading) {
        analyzeBtn.disabled = true;
        clearBtn.disabled = true;
        progressContainer.style.display = 'block';
        previewContainer.style.display = 'none';
        agreementBox.style.display = 'none';
        simulateProgress();
    } else {
        analyzeBtn.disabled = false;
        clearBtn.disabled = false;
        progressContainer.style.display = 'none';
    }
}

function simulateProgress() { /* ... (기존과 동일) ... */ }
function drawGaugeChart(value) { /* ... (기존과 동일) ... */ }
function createResultItem(className, probability) { /* ... (기존과 동일) ... */ }
function getResultComment(probability) { /* ... (기존과 동일) ... */ }
function saveReport(format) { /* ... (기존과 동일) ... */ }

// --- 이벤트 리스너 설정 ---
document.addEventListener('DOMContentLoaded', () => {
    clearAll(); 

    if (uploadSection) {
        uploadSection.onclick = () => imageInput.click();
        uploadSection.addEventListener('dragover', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--primary-color)'; });
        uploadSection.addEventListener('dragleave', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--border-color)'; });
        uploadSection.addEventListener('drop', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--border-color)'; handleFile(e.dataTransfer.files[0]); });
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
});