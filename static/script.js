// --- 전역 변수 ---
const API_URL = "https://pneumonia-api-j3t8.onrender.com/predict"; // 새로운 URL로 변경
const SERVER_BASE_URL = "https://pneumonia-api-j3t8.onrender.com"; // 서버 기본 URL

// HTML 요소 가져오기 (기존과 동일)
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

// 개선된 analyzeImage 함수
async function analyzeImage() {
    if (!uploadedFile) {
        alert("분석할 이미지가 없습니다.");
        return;
    }

    setLoadingState(true);
    
    // 서버 상태 먼저 확인
    try {
        console.log("🔍 서버 상태 확인 중...");
        const healthCheck = await fetch(SERVER_BASE_URL + "/", {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
            }
        });
        
        if (!healthCheck.ok) {
            throw new Error(`서버가 응답하지 않습니다. 상태 코드: ${healthCheck.status}`);
        }
        
        const healthData = await healthCheck.json();
        console.log("✅ 서버 상태:", healthData);
        
        if (!healthData.model_loaded) {
            throw new Error("서버에 AI 모델이 로드되지 않았습니다.");
        }
        
    } catch (error) {
        console.error("❌ 서버 상태 확인 실패:", error);
        alert(`서버 연결 실패: ${error.message}\n\n서버가 시작 중이거나 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.`);
        setLoadingState(false);
        return;
    }

    // 이미지 분석 요청
    const formData = new FormData();
    formData.append('file', uploadedFile);
    
    console.log("📤 이미지 분석 요청 시작...");
    console.log("📁 파일 정보:", {
        name: uploadedFile.name,
        size: uploadedFile.size,
        type: uploadedFile.type
    });

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData,
            // Content-Type 헤더는 FormData 사용 시 설정하지 않음
        });

        console.log("📥 서버 응답 상태:", response.status);
        console.log("📥 서버 응답 헤더:", [...response.headers.entries()]);

        if (!response.ok) {
            let errorMessage = `서버 응답 오류: ${response.status}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch {
                errorMessage = await response.text() || errorMessage;
            }
            throw new Error(errorMessage);
        }

        const data = await response.json();
        console.log("✅ 분석 결과:", data);
        
        if (!data.predictions || !Array.isArray(data.predictions)) {
            throw new Error("서버에서 올바른 예측 결과를 받지 못했습니다.");
        }

        setTimeout(() => {
            displayResults(data.predictions);
        }, 500);

    } catch (error) {
        console.error("❌ 분석 요청 중 오류 발생:", error);
        
        let userMessage = "분석 중 오류가 발생했습니다.";
        
        if (error.message.includes("Failed to fetch")) {
            userMessage = "네트워크 연결 오류입니다. 인터넷 연결을 확인하고 다시 시도해주세요.";
        } else if (error.message.includes("404")) {
            userMessage = "서버의 분석 기능을 찾을 수 없습니다. 서버 설정을 확인해주세요.";
        } else if (error.message.includes("CORS")) {
            userMessage = "서버 접근 권한 오류입니다. 서버 설정을 확인해주세요.";
        } else {
            userMessage = `오류 상세: ${error.message}`;
        }
        
        alert(userMessage);
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
    gaugeChart = new Chart(ctx, { type: 'gauge', data: { datasets: [{ value: value, data: [50, 75, 90, 100], backgroundColor: ['#28a745', '#ffc107', '#dc3545'], borderWidth: 0, }] }, options: { responsive: true, maintainAspectRatio: false, needle: { radiusPercentage: 2, widthPercentage: 3.2, lengthPercentage: 80, color: needleColor, }, valueLabel: { display: true, formatter: (value) => value.toFixed(1) + '%', color: 'rgba(0, 0, 0, 0.8)', backgroundColor: 'rgba(255,255,255,0.7)', borderRadius: 5, padding: { top: 5, bottom: 5 } } } });
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
    const filename = `AI_폐렴_진단_리포트_${Date.now()}`;
    html2canvas(reportCard, { scale: 2, useCORS: true }).then(canvas => {
        if (format === 'png') { const link = document.createElement('a'); link.download = `${filename}.png`; link.href = canvas.toDataURL('image/png'); link.click(); }
        else if (format === 'pdf') { const { jsPDF } = window.jspdf; const imgData = canvas.toDataURL('image/png'); const pdf = new jsPDF({ orientation: 'p', unit: 'mm', format: 'a4' }); const imgProps = pdf.getImageProperties(imgData); const pdfWidth = pdf.internal.pageSize.getWidth() - 20; const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width; pdf.addImage(imgData, 'PNG', 10, 10, pdfWidth, pdfHeight); pdf.save(`${filename}.pdf`); }
    });
}

// 추가: 서버 상태 확인 함수
async function checkServerStatus() {
    try {
        const response = await fetch(SERVER_BASE_URL + "/", {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log("서버 상태:", data);
            return data;
        } else {
            console.error("서버 상태 확인 실패:", response.status);
            return null;
        }
    } catch (error) {
        console.error("서버 연결 실패:", error);
        return null;
    }
}

// --- 이벤트 리스너 설정 ---
document.addEventListener('DOMContentLoaded', async () => {
    clearAll();
    
    console.log("🔄 서버 상태 확인 중...");
    const serverStatus = await checkServerStatus();
    
    if (serverStatus) {
        console.log("✅ 서버 연결 성공:", serverStatus);
    } else {
        console.log("⚠️ 서버 연결 실패 - 서버가 시작 중일 수 있습니다.");
    }

    // 이벤트 리스너 설정
    if (uploadSection) {
        uploadSection.onclick = () => imageInput.click();
        
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