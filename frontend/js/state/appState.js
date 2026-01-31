/**
 * Application State Management
 * 
 * Observer 패턴 기반 상태 관리
 * - 불변성 보장
 * - 상태 변경 구독
 */

/**
 * AppState 클래스
 */
export class AppState {
    constructor() {
        this.state = {
            uploadedFile: null,
            imagePreviewURL: null,
            isAnalyzing: false,
            analysisResult: null,
            error: null,
            agreeChecked: false
        };
        
        this.listeners = [];
    }

    /**
     * 상태 구독
     * @param {Function} listener - 상태 변경 시 호출될 콜백
     * @returns {Function} 구독 해제 함수
     */
    subscribe(listener) {
        this.listeners.push(listener);
        
        // 구독 해제 함수 반환
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    /**
     * 모든 리스너에게 상태 변경 알림
     */
    notify() {
        this.listeners.forEach(listener => listener(this.state));
    }

    /**
     * 상태 업데이트 (불변성 보장)
     * @param {Object} updates - 업데이트할 상태
     */
    setState(updates) {
        this.state = {
            ...this.state,
            ...updates
        };
        
        this.notify();
    }

    /**
     * 현재 상태 반환
     * @returns {Object} 현재 상태 (읽기 전용 복사본)
     */
    getState() {
        return { ...this.state };
    }

    /**
     * 파일 업로드 상태 설정
     */
    setUploadedFile(file, previewURL) {
        this.setState({
            uploadedFile: file,
            imagePreviewURL: previewURL,
            analysisResult: null,
            error: null
        });
    }

    /**
     * 분석 시작
     */
    startAnalysis() {
        this.setState({
            isAnalyzing: true,
            analysisResult: null,
            error: null
        });
    }

    /**
     * 분석 완료
     */
    setAnalysisResult(result) {
        this.setState({
            isAnalyzing: false,
            analysisResult: result,
            error: null
        });
    }

    /**
     * 에러 설정
     */
    setError(error) {
        this.setState({
            isAnalyzing: false,
            error: error
        });
    }

    /**
     * 동의 체크박스 상태 설정
     */
    setAgreeChecked(checked) {
        this.setState({
            agreeChecked: checked
        });
    }

    /**
     * 전체 상태 초기화
     */
    reset() {
        this.setState({
            uploadedFile: null,
            imagePreviewURL: null,
            isAnalyzing: false,
            analysisResult: null,
            error: null,
            agreeChecked: false
        });
    }
}

// 싱글톤 인스턴스
export const appState = new AppState();
export default appState;
