/**
 * File Validator Module
 * 
 * 파일 검증 로직
 */

import CONFIG from '../config.js';
import ErrorHandler from './errorHandler.js';

/**
 * FileValidator 클래스
 */
export class FileValidator {
    /**
     * 파일 검증
     * @param {File} file - 검증할 파일
     * @returns {Object} { isValid: boolean, error: string|null }
     */
    static validate(file) {
        if (!file) {
            return {
                isValid: false,
                error: '파일이 선택되지 않았습니다.'
            };
        }

        // 파일 타입 검증
        if (!CONFIG.FILE.ALLOWED_TYPES.includes(file.type)) {
            return {
                isValid: false,
                error: `지원하지 않는 파일 형식입니다. ${CONFIG.FILE.ALLOWED_EXTENSIONS.join(', ')} 파일만 가능합니다.`
            };
        }

        // 파일 크기 검증
        if (file.size > CONFIG.FILE.MAX_SIZE) {
            const maxSizeMB = CONFIG.FILE.MAX_SIZE / (1024 * 1024);
            return {
                isValid: false,
                error: `파일 크기가 너무 큽니다. 최대 ${maxSizeMB}MB까지 허용됩니다.`
            };
        }

        // 파일 이름 검증 (확장자 확인)
        const fileName = file.name.toLowerCase();
        const hasValidExtension = CONFIG.FILE.ALLOWED_EXTENSIONS.some(ext => 
            fileName.endsWith(ext)
        );

        if (!hasValidExtension) {
            return {
                isValid: false,
                error: `잘못된 파일 확장자입니다. ${CONFIG.FILE.ALLOWED_EXTENSIONS.join(', ')} 파일만 가능합니다.`
            };
        }

        return {
            isValid: true,
            error: null
        };
    }

    /**
     * 이미지 파일인지 확인
     * @param {File} file - 확인할 파일
     * @returns {boolean}
     */
    static isImageFile(file) {
        return file && file.type.startsWith('image/');
    }
}

export default FileValidator;
