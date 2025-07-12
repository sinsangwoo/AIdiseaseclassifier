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
            const errorData = await response.json();
            throw new Error(errorData.error || `서버 응답 오류: ${response.status}`);
        }

        const data = await response.json();
        displayResults(data.predictions);

    } catch (error) {
        console.error("분석 요청 중 오류 발생:", error);
        let userMessage = error.message.includes("Failed to fetch") 
            ? "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
            : `분석 실패: ${error.message}`;
        alert(userMessage);
        setLoadingState(false);
    }
}

function displayResults(predictions) {
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
    sorted.forEach(p => {
        const resultItem = createResultItem(p.className, p.probability);
        resultsContent.appendChild(resultItem);
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
    if (gaugeChart) { gaugeChart.destroy(); gaugeChart = null; }
    analyzeBtn.disabled = true;
    clearBtn.style.display = 'none';
    reportContainer.style.display = 'none';
    document.querySelector('.report-actions').style.display = 'none';
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

function simulateProgress() {
    let width = 0;
    const progressBarFill = document.getElementById('progressBarFill');
    if (!progressBarFill) return;
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

function drawGaugeChart(value) {
    const ctx = document.getElementById('gaugeChart').getContext('2d');
    if (gaugeChart) gaugeChart.destroy();
    const needleColor = value > 50 ? 'rgba(231, 76, 60, 1)' : 'rgba(40, 167, 69, 1)';
    gaugeChart = new Chart(ctx, { type: 'gauge', data: { datasets: [{ value: value, data: [50, 75, 90, 100], backgroundColor: ['#28a745', '#ffc107', '#dc3545'], borderWidth: 0, }] }, options: { responsive: true, maintainAspectRatio: false, needle: { radiusPercentage: 2, widthPercentage: 3.2, lengthPercentage: 80, color: needleColor, }, valueLabel: { display: true, formatter: (val) => val.toFixed(1) + '%', color: 'rgba(0, 0, 0, 0.8)', backgroundColor: 'rgba(255,255,255,0.7)', borderRadius: 5, padding: { top: 5, bottom: 5 } } } });
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
    if (probability > 90) { text = "<strong>높은 위험:</strong> 폐렴일 가능성이 매우 높게 예측되었습니다. 즉시 의료 전문가의 진단이 필요합니다."; className = 'warning'; }
    else if (probability > 70) { text = "<strong>주의 필요:</strong> 폐렴 가능성이 있습니다. 의료 전문가와 상담하여 정확한 진단을 받는 것을 권장합니다."; className = 'warning'; }
    else if (probability > 50) { text = "<strong>경계:</strong> 일부 비정상적인 패턴이 감지되었습니다. 상태를 지켜보거나 예방 차원에서 상담을 고려해볼 수 있습니다."; className = 'privacy'; }
    else { text = "<strong>낮은 위험:</strong> 정상 범위로 예측되었습니다. 하지만 이 결과는 참고용이며, 의심 증상이 있다면 반드시 의사와 상담하세요."; className = 'privacy'; }
    if (probability > 40 && probability < 60) { text += "<br><br><strong>참고:</strong> AI가 이미지를 판단하기 어려워하는 경계선상의 확률입니다. X-ray 이미지의 품질이나 각도에 따라 결과가 달라질 수 있습니다."; }
    return { text, className };
}

function saveReport(format) {
    const reportCard = document.getElementById('reportCard');
    html2canvas(reportCard, { scale: 2, useCORS: true }).then(canvas => {
        const filename = `AI_폐렴_진단_리포트_${Date.now()}`;
        if (format === 'png') { const link = document.createElement('a'); link.download = `${filename}.png`; link.href = canvas.toDataURL('image/png'); link.click(); }
        else if (format === 'pdf') { const { jsPDF } = window.jspdf; const imgData = canvas.toDataURL('image/png'); const pdf = new jsPDF({ orientation: 'p', unit: 'mm', format: 'a4' }); const imgProps = pdf.getImageProperties(imgData); const pdfWidth = pdf.internal.pageSize.getWidth() - 20; const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width; pdf.addImage(imgData, 'PNG', 10, 10, pdfWidth, pdfHeight); pdf.save(`${filename}.pdf`); }
    });
}

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

    uploadSection.addEventListener('dragover', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--primary-color)'; });
    uploadSection.addEventListener('dragleave', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--border-color)'; });
    uploadSection.addEventListener('drop', (e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--border-color)'; handleFile(e.dataTransfer.files[0]); });
});