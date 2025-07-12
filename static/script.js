// --- 전역 변수 ---
// ✅ [필수 수정] Teachable Machine에서 '모델 업로드' 후 받은 자신의 공유 링크로 교체하세요!
const MODEL_URL = "https://teachablemachine.withgoogle.com/models/3wMtRD9Yg/"; 

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
let model; // AI 모델을 저장할 변수
let uploadedFile = null;
let gaugeChart = null;

// --- 핵심 함수들 ---

/**
 * 페이지 로드 시 Teachable Machine 모델을 비동기적으로 로드합니다.
 */
async function initModel() {
    const modelURL = MODEL_URL + "model.json";
    const metadataURL = MODEL_URL + "metadata.json";
    try {
        console.log("AI 모델 로드를 시작합니다...");
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 모델 로딩 중...';
        
        model = await tmImage.load(modelURL, metadataURL);
        
        console.log("✅ AI 모델이 성공적으로 로드되었습니다.");
        analyzeBtn.innerHTML = '<i class="fa-solid fa-brain"></i> AI 분석 시작';
        // 이미지가 먼저 업로드된 경우, 모델 로딩 후 버튼 활성화
        if (uploadedFile && agreeCheckbox.checked) {
            analyzeBtn.disabled = false;
        }
    } catch (error) {
        console.error("❌ 모델 로드 실패:", error);
        alert("AI 모델을 로드하는 데 실패했습니다. 인터넷 연결을 확인하거나 잠시 후 다시 시도해주세요.");
        analyzeBtn.innerHTML = '<i class="fa-solid fa-times"></i> 모델 로드 실패';
    }
}

/**
 * 파일이 업로드되었을 때 UI를 처리하는 함수
 * @param {File} file 사용자가 업로드한 파일 객체
 */
function handleFile(file) {
    if (file && file.type.startsWith('image/')) {
        uploadedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            // 모델이 로드되었고, 동의 체크박스가 선택되었다면 분석 버튼 활성화
            analyzeBtn.disabled = !(model && agreeCheckbox.checked);
            
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

/**
 * 'AI 분석 시작' 버튼 클릭 시 로드된 모델로 이미지를 분석합니다.
 */
async function analyzeImage() {
    if (!model) return alert("AI 모델이 아직 준비되지 않았습니다. 잠시 후 다시 시도해주세요.");
    if (!imagePreview.src) return alert("분석할 이미지가 없습니다.");

    setLoadingState(true);

    try {
        const predictions = await model.predict(imagePreview);
        // 서버 통신이 없으므로, 프로그레스 바를 위한 가짜 딜레이를 줍니다.
        setTimeout(() => {
            displayResults(predictions);
        }, 500);
    } catch (error) {
        console.error("분석 중 오류 발생:", error);
        alert(`분석 중 오류가 발생했습니다: ${error.message}`);
        setLoadingState(false);
    }
}

/**
 * 분석 결과를 받아 화면에 리포트를 표시하는 함수
 * @param {Array} predictions 예측 결과 배열
 */
function displayResults(predictions) {
    reportImageContainer.innerHTML = '';
    const imgClone = imagePreview.cloneNode(true);
    imgClone.style.maxWidth = '100%';
    imgClone.style.maxHeight = 'none';
    reportImageContainer.appendChild(imgClone);

    const sorted = predictions.sort((a, b) => b.probability - a.probability);
    const pneumoniaResult = sorted.find(p => !(p.className.toLowerCase().includes('정상') || p.className.toLowerCase().includes('normal')));
    
    if (!pneumoniaResult) {
        alert("결과에 '폐렴' 클래스가 없습니다. Teachable Machine 모델을 확인해주세요.");
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
    document.querySelector('.report-actions').style.display = 'flex';

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
    if (gaugeChart) { gaugeChart.destroy(); gaugeChart = null; }
    
    // 모델이 로드 중이 아닐 때만 버튼 텍스트를 변경
    if (model) {
        analyzeBtn.innerHTML = '<i class="fa-solid fa-brain"></i> AI 분석 시작';
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
    const progressBarFill = document.getElementById('progressBarFill');
    if(progressBarFill) {
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
}

/**
 * 개선된 게이지 차트 그리기 함수 (도넛 차트 기반)
 * @param {number} value 폐렴 확률 값 (0-100)
 */
function drawGaugeChart(value) {
    const ctx = document.getElementById('gaugeChart').getContext('2d');
    if (gaugeChart) gaugeChart.destroy();
    
    // 색상 결정 (단계별)
    let gaugeColor;
    if (value <= 30) gaugeColor = '#28a745'; // 초록 (안전)
    else if (value <= 50) gaugeColor = '#ffc107'; // 노랑 (주의)
    else if (value <= 70) gaugeColor = '#fd7e14'; // 주황 (경고)
    else gaugeColor = '#dc3545'; // 빨강 (위험)
    
    gaugeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [value, 100 - value],
                backgroundColor: [gaugeColor, '#e9ecef'],
                borderWidth: 0,
                circumference: 180, // 반원 형태
                rotation: 270, // 시작 각도 (하단부터)
                borderRadius: 8, // 둥근 모서리
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            },
            cutout: '75%', // 내부 구멍 크기
            animation: {
                animateRotate: true,
                duration: 1500, // 애니메이션 시간
                easing: 'easeOutCubic'
            }
        },
        plugins: [{
            afterDraw: function(chart) {
                const ctx = chart.ctx;
                const centerX = chart.chartArea.left + (chart.chartArea.right - chart.chartArea.left) / 2;
                const centerY = chart.chartArea.top + (chart.chartArea.bottom - chart.chartArea.top) / 2 + 20;
                
                // 중앙에 큰 숫자 표시
                ctx.save();
                ctx.fillStyle = '#333';
                ctx.font = 'bold 28px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(value.toFixed(1) + '%', centerX, centerY - 10);
                
                // 하단에 라벨 표시
                ctx.fillStyle = '#666';
                ctx.font = '14px Arial';
                ctx.fillText('폐렴 확률', centerX, centerY + 25);
                
                // 위험도 표시
                let riskLevel = '';
                if (value <= 30) riskLevel = '낮음';
                else if (value <= 50) riskLevel = '보통';
                else if (value <= 70) riskLevel = '높음';
                else riskLevel = '매우 높음';
                
                ctx.fillStyle = gaugeColor;
                ctx.font = 'bold 12px Arial';
                ctx.fillText(`위험도: ${riskLevel}`, centerX, centerY + 45);
                
                // 눈금 표시
                const radius = (chart.chartArea.right - chart.chartArea.left) / 2 * 0.8;
                for (let i = 0; i <= 100; i += 25) {
                    const angle = (Math.PI * i / 100) - Math.PI / 2;
                    const x1 = centerX + Math.cos(angle) * (radius - 10);
                    const y1 = centerY + Math.sin(angle) * (radius - 10);
                    const x2 = centerX + Math.cos(angle) * (radius + 5);
                    const y2 = centerY + Math.sin(angle) * (radius + 5);
                    
                    ctx.strokeStyle = '#ccc';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);
                    ctx.stroke();
                    
                    // 눈금 숫자
                    const x3 = centerX + Math.cos(angle) * (radius + 20);
                    const y3 = centerY + Math.sin(angle) * (radius + 20);
                    ctx.fillStyle = '#888';
                    ctx.font = '10px Arial';
                    ctx.fillText(i.toString(), x3, y3);
                }
                
                ctx.restore();
            }
        }]
    });
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
    }
    else if (probability > 70) { 
        text = "<strong>주의 필요:</strong> 폐렴 가능성이 있습니다. 의료 전문가와 상담하여 정확한 진단을 받는 것을 권장합니다."; 
        className = 'warning'; 
    }
    else if (probability > 50) { 
        text = "<strong>경계:</strong> 일부 비정상적인 패턴이 감지되었습니다. 상태를 지켜보거나 예방 차원에서 상담을 고려해볼 수 있습니다."; 
        className = 'privacy'; 
    }
    else { 
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
    
    html2canvas(reportCard, { 
        scale: 2, 
        useCORS: true,
        backgroundColor: '#ffffff'
    }).then(canvas => {
        if (format === 'png') { 
            const link = document.createElement('a'); 
            link.download = `${filename}.png`; 
            link.href = canvas.toDataURL('image/png'); 
            link.click(); 
        }
        else if (format === 'pdf') { 
            const { jsPDF } = window.jspdf; 
            const imgData = canvas.toDataURL('image/png'); 
            const pdf = new jsPDF({ 
                orientation: 'p', 
                unit: 'mm', 
                format: 'a4' 
            }); 
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
    clearAll(); 
    initModel(); // 페이지가 열리면 바로 모델 로딩을 시작합니다.
    
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
            // 모델이 로드되었고, 파일이 업로드 된 상태에서만 체크박스로 버튼 활성화
            if (model && uploadedFile) {
                analyzeBtn.disabled = !agreeCheckbox.checked;
            }
        });
    }
});