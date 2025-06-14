// 여기에 사용자의 Teachable Machine 모델 URL을 입력하세요.
const MODEL_URL = "https://teachablemachine.withgoogle.com/models/M5gtChz0S/";

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
const savePngBtn = document.getElementById('savePngBtn');
const savePdfBtn = document.getElementById('savePdfBtn');

let model;

// 1. 모델 초기화 함수
async function initModel() {
    try {
        const modelURL = MODEL_URL + "model.json";
        const metadataURL = MODEL_URL + "metadata.json";
        model = await tmImage.load(modelURL, metadataURL);
        console.log("AI 모델이 성공적으로 로드되었습니다.");
    } catch (error) {
        console.error("모델 로드 실패:", error);
        alert("AI 모델을 로드하는 데 실패했습니다. 인터넷 연결을 확인해주세요.");
    }
}

// 2. 파일 처리 함수
function handleFile(file) {
    if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            imagePreview.style.display = 'block';
            analyzeBtn.disabled = false;
            clearBtn.style.display = 'inline-flex';
            reportContainer.style.display = 'none';
            uploadSection.style.display = 'none';
        };
        reader.readAsDataURL(file);
    } else {
        alert("이미지 파일(JPG, PNG 등)을 선택해주세요.");
    }
}

// 3. AI 분석 시작 함수
async function analyzeImage() {
    if (!model || !imagePreview.src) {
        alert("모델이 로드되지 않았거나 분석할 이미지가 없습니다.");
        return;
    }

    // UI 상태 변경: 로딩 시작
    analyzeBtn.disabled = true;
    clearBtn.disabled = true;
    savePngBtn.disabled = true;
    savePdfBtn.disabled = true;
    progressContainer.style.display = 'block';
    simulateProgress();

    try {
        const predictions = await model.predict(imagePreview);
        // 프로그레스 바 완료 후 결과 표시
        setTimeout(() => {
            progressContainer.style.display = 'none';
            displayResults(predictions);
        }, 500); // 약간의 딜레이 후 결과 표시
    } catch (error) {
        console.error("분석 중 오류 발생:", error);
        alert("이미지 분석 중 오류가 발생했습니다.");
        progressContainer.style.display = 'none';
    } finally {
        analyzeBtn.disabled = false;
        clearBtn.disabled = false;
        savePngBtn.disabled = false;
        savePdfBtn.disabled = false;
    }
}

// 4. 프로그레스 바 시뮬레이션 함수
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

// 5. 결과 리포트 표시 함수
function displayResults(predictions) {
    resultsContent.innerHTML = '';
    const sorted = predictions.sort((a, b) => b.probability - a.probability);

    sorted.forEach(p => {
        const percentage = (p.probability * 100).toFixed(1);
        const item = document.createElement('div');
        item.className = 'result-item';
        
        const isNormal = p.className.toLowerCase().includes('정상') || p.className.toLowerCase().includes('normal');
        item.classList.add(isNormal ? 'result-normal' : 'result-pneumonia');
        
        item.innerHTML = `<span>${p.className}</span> <span class="result-percentage">${percentage}%</span>`;
        resultsContent.appendChild(item);
    });
    
    reportTimestamp.textContent = `진단 시각: ${new Date().toLocaleString()}`;
    reportContainer.style.display = 'block';
}

// 6. 리포트 저장 함수 (PNG, PDF)
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
            const pdfWidth = pdf.internal.pageSize.getWidth() - 20; // 여백 고려
            const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
            pdf.addImage(imgData, 'PNG', 10, 10, pdfWidth, pdfHeight);
            pdf.save(`${filename}.pdf`);
        }
    });
}

// 7. 초기화 함수
function clearAll() {
    imageInput.value = '';
    imagePreview.src = '';
    imagePreview.style.display = 'none';
    analyzeBtn.disabled = true;
    clearBtn.style.display = 'none';
    reportContainer.style.display = 'none';
    uploadSection.style.display = 'block';
    progressContainer.style.display = 'none';
}

// --- 이벤트 리스너 설정 ---

// 페이지 로드 시 모델 로드
window.addEventListener('load', initModel);

// 분석 및 초기화 버튼 클릭
analyzeBtn.addEventListener('click', analyzeImage);
clearBtn.addEventListener('click', clearAll);

// 리포트 저장 버튼 클릭
savePngBtn.addEventListener('click', () => saveReport('png'));
savePdfBtn.addEventListener('click', () => saveReport('pdf'));

// 파일 입력 변경 시
imageInput.addEventListener('change', (e) => handleFile(e.target.files[0]));

// 드래그 앤 드롭 이벤트
uploadSection.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadSection.style.borderColor = 'var(--primary-color)';
});
uploadSection.addEventListener('dragleave', (e) => {
    e.preventDefault();
    uploadSection.style.borderColor = 'var(--border-color)';
});
uploadSection.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadSection.style.borderColor = 'var(--border-color)';
    const file = e.dataTransfer.files[0];
    handleFile(file);
});