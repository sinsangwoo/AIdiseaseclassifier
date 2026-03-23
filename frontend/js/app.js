/**
 * Main Application Entry Point
 *
 * [웹업 전략 v2]
 *   - /health 대신 /health/ready 사용
 *     Render Readiness probe와 동일한 엔드포인트 →
 *     웹업 성공 = 실제 서버가 predict 요청을 받을 준비가 된 상태 보장
 *
 * [CORS ERR_FAILED 대응 전략]
 *   - apiClient 안에서 RETRY_ATTEMPTS=5로 자동 재시도
 *   - ERR_FAILED 후 웹업 상태 리셋 수행
 */

import CONFIG from './config.js';
import apiClient from './api/client.js';
import appState from './state/appState.js';
import UIController from './ui/uiController.js';
import ErrorHandler from './utils/errorHandler.js';

let warmUpPromise = null;
let serverReady   = false;
let warmUpFailed  = false;

async function tryHealthCheck(timeoutMs) {
    const ctrl = new AbortController();
    const tid  = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
        // /health/ready: Render Readiness probe와 동일한 엔드포인트
        // 예전 /health GET은 Render 로드밸런서가 캐시해 실제 서버 준비와 뉔리질 수 있음
        const res = await fetch(
            `${CONFIG.API_BASE_URL}/health/ready`,
            { method: 'GET', signal: ctrl.signal }
        );
        clearTimeout(tid);
        return res.ok;
    } catch { clearTimeout(tid); return false; }
}

function warmUpServer() {
    if (CONFIG.ENVIRONMENT !== 'production') { serverReady = true; return Promise.resolve(); }
    if (warmUpPromise) return warmUpPromise;
    warmUpPromise = (async () => {
        const MAX = 12, TIMEOUT = 15000, DELAY = 8000;
        for (let i = 1; i <= MAX; i++) {
            console.log(`[WarmUp] 시도 ${i}/${MAX}...`);
            if (await tryHealthCheck(TIMEOUT)) {
                serverReady = true;
                console.log(`[WarmUp] ✅ 서버 준비 (시도 ${i})`);
                return;
            }
            console.warn(`[WarmUp] ❌ 실패 (${i}) - ${DELAY / 1000}s 후 재시도`);
            if (i < MAX) await new Promise(r => setTimeout(r, DELAY));
        }
        warmUpFailed = true;
        console.warn('[WarmUp] ⚠️ 웹업 실패 - predict 직접 시도 허용');
    })();
    return warmUpPromise;
}

function resetWarmUp() {
    warmUpPromise = null;
    serverReady   = false;
    warmUpFailed  = false;
}

class Application {
    constructor() { this.ui = null; this._init(); }

    async _init() {
        console.log('[App] 초기화 시작 - 환경:', CONFIG.ENVIRONMENT, '- API:', CONFIG.API_BASE_URL);
        try {
            this.ui = new UIController();
            console.log('[App] UIController 생성 완료');
        } catch (e) {
            console.error('[App] UIController 생성 실패:', e);
            return;
        }

        appState.subscribe((state) => {
            console.log(`[App] 상태 -> ${state.status}`);
            try { this.ui.render(state); }
            catch (e) { console.error('[App] UI 렌더링 실패:', e); }
        });

        this.ui.onAnalyze         = () => this._handleAnalysis();
        this.ui.onFileSelect      = (f) => { console.log('[App] 파일:', f.name); appState.setUploadedImage(f); };
        this.ui.onClear           = () => { console.log('[App] 리셋'); appState.reset(); };
        this.ui.onAgreementChange = (c) => { console.log('[App] 동의:', c); appState.setAgreement(c); };

        this.ui.resetUI();
        console.log('[App] 초기화 완료 - 웹업 시작');
        warmUpServer();
    }

    async _handleAnalysis() {
        const state = appState.getState();
        console.log('[App] 분석 요청, status:', state.status);

        if (!state.uploadedImage) {
            console.warn('[App] 이미지 없음');
            ErrorHandler.handleError(new Error('분석할 이미지가 없습니다.'), 'Analysis');
            return;
        }
        if (!state.agreeChecked) {
            console.warn('[App] 동의 미체크');
            ErrorHandler.handleError(new Error('주의사항에 동의해주세요.'), 'Analysis');
            return;
        }

        appState.startAnalysis();

        try {
            if (!serverReady && !warmUpFailed) {
                console.log('[App] 웹업 대기...');
                appState.analyzing();
                await warmUpServer();
            }
            if (warmUpFailed) console.warn('[App] 웹업 실패 - predict 직접 시도');

            appState.analyzing();
            console.log('[App] predict:', state.uploadedImage.name);

            const result = await apiClient.predict(state.uploadedImage);
            console.log('[App] predict 성공');
            appState.completeAnalysis(result);

        } catch (error) {
            const code = error.statusCode ?? 0;
            console.error(
                `[App] 분석 실패 [HTTP ${code}]:`,
                error.message,
                '\n실제 를 원인:', _diagnoseError(error)
            );

            if (code === 0) {
                console.log('[App] ERR_FAILED - 웹업 상태 리셋');
                resetWarmUp();
                warmUpServer();
            }

            appState.setError(error);
            ErrorHandler.handleError(error, 'Image Analysis');
        }
    }
}

/**
 * 에러 원인을 정확하게 진단하여 콘솔에 추가 정보를 남깁니다.
 *
 * [다각화된 실패 원인 분류]
 *   0 / ERR_FAILED
 *     (A) OPTIONS preflight 차단: CORS 설정 오류
 *     (B) Render 재시작 과도기: 서버가 엄다다 들어옵니다
 *     (C) 네트워크 단절 or DNS 실패
 *   502 Bad Gateway
 *     Render 로드밸런서가 덮다운스트림에 연결 실패
 *     = gunicorn 워커가 시작되지 않았거나 재시작 중
 *   503 Service Unavailable
 *     Render 무료 플랜 슬립 후 콜드 스타트 반환
 *     = 세션 주인 엄다 뒤 수 있는 시간대
 *   408 타임아웃
 *     서버가 떠 있는데 predict가 180초 안에 응답하지 못함
 *     = 모델 추론 시간 초과 또는 서버 과부하
 */
function _diagnoseError(error) {
    const code = error.statusCode ?? 0;
    if (code === 0) {
        return [
            '❌ ERR_FAILED 세부 진단:',
            '  (A) CORS preflight 실패 → /predict OPTIONS 응답에 Access-Control-Allow-Origin 없음',
            '      확인: Render 대시보드에서 최신 backend/routes/predict.py (OPTIONS 핑등) 배포 확인',
            '  (B) Render 서버 재시작 과도기 → 다음 엀도에 성공할 수 있음',
            '  (C) 네트워크 단절 → 브라우저/OS 수준 차단',
        ].join('\n');
    }
    if (code === 502) {
        return [
            '❌ 502 Bad Gateway 세부 진단:',
            '  gunicorn 워커 처리 불가 또는 재시작 중',
            '  Render 배포 진행 중에 자주 발생 → Render 대시보드에서 Auto-Deploy OFF 확인',
        ].join('\n');
    }
    if (code === 503) {
        return [
            '❌ 503 Service Unavailable 세부 진단:',
            '  Render 무료 플랜 슬립 유황 또는 콜드 스타트 중',
            '  /health/ready 웹업 성공 후 참시 후 재요청하면 동작할 수 있음',
        ].join('\n');
    }
    if (code === 408) {
        return [
            '❌ 408 Timeout 세부 진단:',
            '  모델 추론 시간이 180초를 넘었거나 서버가 과부하 상태',
        ].join('\n');
    }
    return `HTTP ${code}: ${error.message}`;
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('[App] DOMContentLoaded');
    new Application();
});
