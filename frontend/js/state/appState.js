/**
 * Application State Management
 *
 * 상태 스키마 (uiController.render(state)와 일치 필수)
 *
 * state.status: 'idle' | 'preview' | 'analyzing' | 'complete' | 'error'
 * state.uploadedImage:    File | null
 * state.uploadedImageUrl: string | null   (예시리보기 DataURL)
 * state.result:           Object | null   (API 응답)
 * state.error:            string | null
 * state.agreeChecked:     boolean
 */

class AppState {
    constructor() {
        this._state = {
            status:           'idle',   // UI 렌더링 기준
            uploadedImage:    null,
            uploadedImageUrl: null,
            result:           null,
            error:            null,
            agreeChecked:     false,
        };
        this._listeners = [];
        this._log('AppState 초기화 완료');
    }

    // ── 구독 ─────────────────────────────────────────────────────────────────
    subscribe(listener) {
        this._listeners.push(listener);
        return () => {
            this._listeners = this._listeners.filter(l => l !== listener);
        };
    }

    getState() {
        return { ...this._state };
    }

    // ── 상태 전환 메서드 ────────────────────────────────────────────────

    /** 이미지 선택 시 → 'preview' 상태로 전환 */
    setUploadedImage(file) {
        // File → DataURL 변환
        const reader = new FileReader();
        reader.onload = (e) => {
            this._setState({
                status:           'preview',
                uploadedImage:    file,
                uploadedImageUrl: e.target.result,
                result:           null,
                error:            null,
                agreeChecked:     false,
            });
            this._log(`이미지 선택: ${file.name} (${(file.size/1024).toFixed(1)} KB)`);
        };
        reader.onerror = (e) => {
            this._error(`FileReader 실패: ${e.target.error}`);
            this.setError('이미지를 읽는 중 오류가 발생했습니다.');
        };
        reader.readAsDataURL(file);
    }

    setAgreement(checked) {
        this._setState({ agreeChecked: checked });
        this._log(`동의 체크박스: ${checked}`);
    }

    /** 분석 버튼 클릭 시 → 'analyzing' */
    startAnalysis() {
        this._setState({ status: 'analyzing', error: null, result: null });
        this._log('분석 시작');
    }

    /** 서버 웹 업 대기 중에도 'analyzing' 유지 */
    analyzing() {
        if (this._state.status !== 'analyzing') {
            this._setState({ status: 'analyzing' });
        }
    }

    /** 분석 완료 → 'complete' */
    completeAnalysis(result) {
        this._setState({ status: 'complete', result, error: null });
        this._log('분석 완료', result);
    }

    /** 오류 → 'error' */
    setError(error) {
        const msg = (error instanceof Error) ? error.message : String(error);
        this._setState({ status: 'error', error: msg });
        this._error('상태 오류:', msg);
    }

    /** 리셋 → 'idle' */
    reset() {
        this._setState({
            status:           'idle',
            uploadedImage:    null,
            uploadedImageUrl: null,
            result:           null,
            error:            null,
            agreeChecked:     false,
        });
        this._log('상태 초기화');
    }

    // ── 내부 도우미 ─────────────────────────────────────────────────────
    _setState(updates) {
        const prev = this._state.status;
        this._state = { ...this._state, ...updates };
        if (prev !== this._state.status) {
            this._log(`상태 전환: ${prev} → ${this._state.status}`);
        }
        this._listeners.forEach(fn => {
            try { fn(this._state); }
            catch (e) { this._error('리스너 오류:', e); }
        });
    }

    _log(...args)  { console.log ('[AppState]', ...args); }
    _error(...args){ console.error('[AppState]', ...args); }
}

export const appState = new AppState();
export default appState;
