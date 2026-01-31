/**
 * Error Handler Module
 * 
 * 통합 에러 처리 및 사용자 친화적 메시지 생성
 */

import { APIError } from '../api/client.js';

/**
 * 에러 타입별 사용자 메시지 매핑
 */
const ERROR_MESSAGES = {
    // 네트워크 에러
    0: '서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.',
    
    // 클라이언트 에러
    400: '잘못된 요청입니다. 파일을 다시 확인해주세요.',
    401: '인증이 필요합니다.',
    403: '접근 권한이 없습니다.',
    404: 'API 엔드포인트를 찾을 수 없습니다.',
    408: '요청 시간이 초과되었습니다. 다시 시도해주세요.',
    413: '파일 크기가 너무 큽니다. 10MB 이하의 파일을 사용해주세요.',
    415: '지원하지 않는 파일 형식입니다. JPG, PNG 파일만 가능합니다.',
    422: '이미지 처리 중 오류가 발생했습니다.',
    429: '요청이 너무 많습니다. 잠시 후 다시 시도해주세요.',
    
    // 서버 에러
    500: '서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
    502: '게이트웨이 오류가 발생했습니다.',
    503: '서버가 일시적으로 사용 불가능합니다. 잠시 후 다시 시도해주세요.',
    504: '게이트웨이 시간 초과가 발생했습니다.'
};

/**
 * ErrorHandler 클래스
 */
export class ErrorHandler {
    /**
     * 에러를 사용자 친화적 메시지로 변환
     * @param {Error} error - 발생한 에러
     * @returns {string} 사용자 메시지
     */
    static getUserMessage(error) {
        // APIError인 경우
        if (error instanceof APIError) {
            const defaultMessage = ERROR_MESSAGES[error.statusCode] || '알 수 없는 오류가 발생했습니다.';
            
            // 서버가 제공한 에러 메시지가 있으면 사용
            if (error.response && error.response.error) {
                return error.response.error;
            }
            
            return error.message || defaultMessage;
        }
        
        // 일반 Error인 경우
        if (error instanceof Error) {
            // TypeError: Failed to fetch
            if (error.message.includes('Failed to fetch')) {
                return ERROR_MESSAGES[0];
            }
            
            // AbortError
            if (error.name === 'AbortError') {
                return ERROR_MESSAGES[408];
            }
            
            return error.message;
        }
        
        // 기타
        return '알 수 없는 오류가 발생했습니다.';
    }

    /**
     * 에러 타입 분류
     * @param {Error} error - 발생한 에러
     * @returns {string} 에러 타입 ('network', 'client', 'server', 'unknown')
     */
    static getErrorType(error) {
        if (error instanceof APIError) {
            if (error.statusCode === 0) return 'network';
            if (error.statusCode >= 400 && error.statusCode < 500) return 'client';
            if (error.statusCode >= 500) return 'server';
        }
        
        if (error instanceof Error) {
            if (error.message.includes('Failed to fetch') || error.name === 'AbortError') {
                return 'network';
            }
        }
        
        return 'unknown';
    }

    /**
     * 에러를 콘솔에 로깅
     * @param {Error} error - 발생한 에러
     * @param {string} context - 에러 발생 컨텍스트
     */
    static logError(error, context = '') {
        const errorType = this.getErrorType(error);
        const message = this.getUserMessage(error);
        
        console.error(`[ErrorHandler] ${context}`, {
            type: errorType,
            message: message,
            error: error,
            statusCode: error instanceof APIError ? error.statusCode : null,
            response: error instanceof APIError ? error.response : null
        });
    }

    /**
     * 에러를 사용자에게 표시
     * @param {Error} error - 발생한 에러
     * @param {string} context - 에러 발생 컨텍스트
     */
    static handleError(error, context = '') {
        this.logError(error, context);
        
        const message = this.getUserMessage(error);
        alert(message);
    }

    /**
     * 파일 검증 에러 생성
     * @param {string} message - 에러 메시지
     * @returns {Error}
     */
    static createFileValidationError(message) {
        return new Error(message);
    }
}

export default ErrorHandler;
