/**
 * Application State Management (Phase 4 Enhanced)
 * 
 * 애플리케이션의 전체 상태를 관리하는 모듈
 * Phase 4: 비동기 처리 및 UI 업데이트 강화
 */

class AppState {
    constructor() {
        this.state = {
            isAnalyzing: false,
            uploadedImage: null,
            analysisResult: null,
            error: null,
            // Phase 4: 진행 상태 추가
            progress: {
                stage: '', // 'uploading', 'analyzing', 'complete'
                percent: 0,
                message: ''
            },
            // 캐시 통계
            cacheStats: null
        };

        this.listeners = [];
    }

    /**
     * 상태 변경 리스너 등록
     * @param {Function} listener - 상태 변경 시 호출될 함수
     */
    subscribe(listener) {
        this.listeners.push(listener);
        // 구독 해제 함수 반환
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    /**
     * 상태 업데이트
     * @param {Object} updates - 변경할 상태 값들
     */
    setState(updates) {
        this.state = { ...this.state, ...updates };
        this._notifyListeners();
    }

    /**
     * 현재 상태 조회
     * @returns {Object} - 현재 상태
     */
    getState() {
        return { ...this.state };
    }

    /**
     * Phase 4: 분석 시작
     */
    startAnalysis() {
        this.setState({
            isAnalyzing: true,
            error: null,
            analysisResult: null,
            progress: {
                stage: 'uploading',
                percent: 10,
                message: '이미지 업로드 중...'
            }
        });
    }

    /**
     * Phase 4: 분석 중 (서버 전송 완료)
     */
    analyzing() {
        this.setState({
            progress: {
                stage: 'analyzing',
                percent: 50,
                message: 'AI 모델 분석 중...'
            }
        });
    }

    /**
     * Phase 4: 분석 완료
     * @param {Object} result - 분석 결과
     */
    completeAnalysis(result) {
        this.setState({
            isAnalyzing: false,
            analysisResult: result,
            progress: {
                stage: 'complete',
                percent: 100,
                message: '분석 완료!'
            }
        });
    }

    /**
     * 분석 실패
     * @param {string|Error} error - 오류 메시지
     */
    setError(error) {
        this.setState({
            isAnalyzing: false,
            error: error.message || error,
            progress: {
                stage: '',
                percent: 0,
                message: ''
            }
        });
    }

    /**
     * 이미지 업로드
     * @param {File} file - 업로드된 파일
     */
    setUploadedImage(file) {
        this.setState({
            uploadedImage: file,
            analysisResult: null,
            error: null
        });
    }

    /**
     * 상태 초기화
     */
    reset() {
        this.setState({
            isAnalyzing: false,
            uploadedImage: null,
            analysisResult: null,
            error: null,
            progress: {
                stage: '',
                percent: 0,
                message: ''
            }
        });
    }

    /**
     * 모든 리스너에게 변경 사항 알림
     * @private
     */
    _notifyListeners() {
        this.listeners.forEach(listener => {
            try {
                listener(this.state);
            } catch (error) {
                console.error('상태 리스너 오류:', error);
            }
        });
    }
}

// 싱글턴 인스턴스 생성 및 export
export const appState = new AppState();
export default appState;
