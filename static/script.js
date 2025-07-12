// --- 전역 변수 ---
const API_URL = "https://pneumonia-api-j3t8.onrender.com/predict";

// HTML 요소 가져오기
const uploadSection = document.getElementById('uploadSection');
const imageInput = document.getElementById('imageInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const clearBtn = document.getElementById('clearBtn');
const progressContainer = document.getElementById('progressContainer');
const reportContainer = document.getElementById('reportContainer');
const imagePreview = document.getElementById('imagePreview');
const resultsContent = document.getElementById('resultsContent');
const reportTimestamp = document.getElementById('reportTimestamp');
const agreeCheckbox = document.getElementById('agreeCheckbox');
const agreementBox = document.getElementById('agreementBox');
const resultComment = document.getElementById('resultComment');
const previewContainer = document.getElementById('previewContainer');
const reportImageContainer = document.getElementById('reportImageContainer');

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
            // UI 상태 변경
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
    if (!uploadedFile) return alert("분석할 이미지가 없습니다.");

    setLoadingState(true);

    const formData = new FormData();
    formData.append('file', uploadedFile);

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            // 서버가 보낸 에러 메시지를 파싱하여 throw
            const errorData = await response.json();
            throw new Error(errorData.error || `서버 응답 오류: ${response.status}`);
        }

        const data = await response.json();
        
        // 성공적으로 데이터를 받으면 결과 표시
        displayResults(data.predictions);

    } catch (error) {
        console.error("분석 요청 중 오류 발생:", error);
        // 사용자에게 간결한 에러 메시지 표시
        let userMessage = error.message.includes("Failed to fetch") 
            ? "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
            : `분석 실패: ${error.message}`;
        alert(userMessage);
        setLoadingState(false);
    }
}

function displayResults(predictions) {
    // 리포트 UI 업데이트 로직 (이전과 동일)
    reportImageContainer.innerHTML = '';
    const imgClone = imagePreview.cloneNode(true);
    imgClone.style.maxWidth = '100%';
    reportImageContainer.appendChild(imgClone);

    const sorted = predictions.sort((a, b) => b.probability - a.probability);
    const pneumoniaResult = sorted.find(p => !p.className.toLowerCase().includes('정상'));
    
    if (!pneumoniaResult) {
        alert("결과에 '폐렴' 클래스가 없습니다.");
        setLoadingState(false);
        return;
    }

    const pneumoniaProbability = pneumoniaResult.probability * 100;
    drawGaugeChart(pneumoniaProbability);

    resultsContent.innerHTML = '';
    sorted.forEach(p => resultsContent.appendChild(createResultItem(p.className, p.probability)));
    
    const { text, className } = getResultComment(pneumoniaProbability);
    resultComment.innerHTML = `<i class="fa-solid fa-comment-medical"></i> <div>${text}</div>`;
    resultComment.className = `notice-box ${className}`;
    resultComment.style.display = 'flex';

    reportTimestamp.textContent = `진단 시각: ${new Date().toLocaleString()}`;
    
    // 최종 UI 상태 변경
    setLoadingState(false);
    previewContainer.style.display = 'none';
    reportContainer.style.display = 'block';

    document.getElementById('savePngBtn').onclick = () => saveReport('png');
    document.getElementById('savePdfBtn').onclick = () => saveReport('pdf');
}

function clearAll() {
    // UI 초기화 로직 (이전과 동일)
    uploadedFile = null;
    imageInput.value = '';
    imagePreview.src = '';
    agreeCheckbox.checked = false;
    if (gaugeChart) { gaugeChart.destroy(); gaugeChart = null; }
    analyzeBtn.disabled = true;
    clearBtn.style.display = 'none';
    reportContainer.style.display = 'none';
    agreementBox.style.display = 'none';
    previewContainer.style.display = 'none';
    progressContainer.style.display = 'none';
    uploadSection.style.display = 'block';
}

// --- 보조 함수들 (이전과 동일, 여기에 그대로 붙여넣기) ---
function setLoadingState(isLoading) { /*...*/ }
function simulateProgress() { /*...*/ }
function drawGaugeChart(value) { /*...*/ }
function createResultItem(className, probability) { /*...*/ }
function getResultComment(probability) { /*...*/ }
function saveReport(format) { /*...*/ }


// --- 이벤트 리스너 설정 ---
document.addEventListener('DOMContentLoaded', () => {
    clearAll();
    
    uploadSection.onclick = () => imageInput.click();
    imageInput.addEventListener('change', (e) => handleFile(e.target.files[0]));
    analyzeBtn.addEventListener('click', analyzeImage);
    clearBtn.addEventListener('click', clearAll);
    agreeCheckbox.addEventListener('click', () => {
        if (uploadedFile) analyzeBtn.disabled = !agreeCheckbox.checked;
    });

    // 드래그 앤 드롭 이벤트
    uploadSection.addEventListener('dragover', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--primary-color)'; });
    uploadSection.addEventListener('dragleave', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--border-color)'; });
    uploadSection.addEventListener('drop', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--border-color)'; handleFile(e.dataTransfer.files[0]); });
});