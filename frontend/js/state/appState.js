/**
 * Application State Management
 *
 * [FileReader 비동기 처리 전략 타임라인]
 *
 * 기존 (버그):
 *   setUploadedImage(file)
 *     ├ FileReader.onload 대기
 *     └ onload 완료 후 _setState({status:'preview', uploadedImageUrl: DataURL})
 *     → 문제: render('preview') 실행 시 uploadedImageUrl == null → 미리보기 안보임
 *
 * 수정 (핵심):
 *   setUploadedImage(file)
 *     ├ _setState({status:'preview', uploadedImage:file, uploadedImageUrl:null}) ← 즉시
 *     └ reader.onload: _setState({uploadedImageUrl: DataURL}) ← 비동기
 *   → 효과: preview 패널 즉시 표시, 미리보기는 DataURL 로드 시 업데이트
 */

class AppState {
    constructor() {
        this._state = {
            status:           'idle',
            uploadedImage:    null,
            uploadedImageUrl: null,
            result:           null,
            error:            null,
            agreeChecked:     false,
        };
        this._listeners = [];
        this._log('AppState 초기화 완료');
    }

    subscribe(listener) {
        this._listeners.push(listener);
        return () => { this._listeners = this._listeners.filter(l => l !== listener); };
    }

    getState() { return { ...this._state }; }

    // ── 상태 전환 ────────────────────────────────────────────────────────

    setUploadedImage(file) {
        // 1단계: 즉시 preview 전환 (uploadedImageUrl 는 아직 null)
        this._setState({
            status:           'preview',
            uploadedImage:    file,
            uploadedImageUrl: null,
            result:           null,
            error:            null,
            agreeChecked:     false,
        });
        this._log(`이미지 선택 (즉시 preview): ${file.name} (${(file.size/1024).toFixed(1)} KB)`);

        // 2단계: 비동기 DataURL 로드 → uploadedImageUrl 만 업데이트
        const reader = new FileReader();
        reader.onload = (e) => {
            this._setState({ uploadedImageUrl: e.target.result });
            this._log(`DataURL 로드 완료: ${file.name}`);
        };
        reader.onerror = (e) => {
            this._error(`FileReader 실패: ${e.target.error}`);
        };
        reader.readAsDataURL(file);
    }

    setAgreement(checked) {
        this._setState({ agreeChecked: checked });
        this._log(`동의: ${checked}`);
    }

    startAnalysis() {
        this._setState({ status: 'analyzing', error: null, result: null });
        this._log('분석 시작');
    }

    analyzing() {
        if (this._state.status !== 'analyzing') this._setState({ status: 'analyzing' });
    }

    completeAnalysis(result) {
        this._setState({ status: 'complete', result, error: null });
        this._log('분석 완료');
    }

    setError(error) {
        const msg = (error instanceof Error) ? error.message : String(error);
        this._setState({ status: 'error', error: msg });
        this._error('오류:', msg);
    }

    reset() {
        this._setState({
            status: 'idle', uploadedImage: null, uploadedImageUrl: null,
            result: null, error: null, agreeChecked: false,
        });
        this._log('상태 초기화');
    }

    _setState(updates) {
        const prev = this._state.status;
        this._state = { ...this._state, ...updates };
        if ('status' in updates && prev !== this._state.status) {
            this._log(`상태 전환: ${prev} -> ${this._state.status}`);
        }
        this._listeners.forEach(fn => {
            try { fn(this._state); }
            catch (e) { this._error('리스너 오류:', e); }
        });
    }

    _log(...a)   { console.log('[AppState]', ...a); }
    _error(...a) { console.error('[AppState]', ...a); }
}

export const appState = new AppState();
export default appState;
