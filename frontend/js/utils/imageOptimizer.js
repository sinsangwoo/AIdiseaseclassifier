/**
 * 이미지 최적화 모듈 (Phase 4)
 * 
 * 클라이언트 사이드에서 이미지를 업로드 전에 압축하여
 * 서버 부하를 줄이고 업로드 속도를 향상시킵니다.
 */

/**
 * 이미지 최적화 설정
 */
const IMAGE_OPTIMIZER_CONFIG = {
    maxWidth: 1024,           // 최대 너비
    maxHeight: 1024,          // 최대 높이
    quality: 0.85,            // JPEG 품질 (0.0 ~ 1.0)
    maxFileSizeMB: 2,         // 최대 파일 크기 (MB)
    targetFormat: 'image/jpeg' // 출력 포맷
};

/**
 * 이미지 최적화 클래스
 */
class ImageOptimizer {
    constructor(config = IMAGE_OPTIMIZER_CONFIG) {
        this.config = { ...IMAGE_OPTIMIZER_CONFIG, ...config };
        this.logger = console;
    }

    /**
     * 파일을 최적화된 이미지로 변환
     * 
     * @param {File} file - 원본 이미지 파일
     * @returns {Promise<File>} 최적화된 이미지 파일
     */
    async optimizeImage(file) {
        try {
            // 이미지 파일인지 확인
            if (!file.type.startsWith('image/')) {
                throw new Error('이미지 파일만 업로드할 수 있습니다');
            }

            this.logger.log(`🔧 이미지 최적화 시작: ${file.name} (${this._formatFileSize(file.size)})`);

            // 이미지가 이미 충분히 작으면 최적화 스킵
            const maxBytes = this.config.maxFileSizeMB * 1024 * 1024;
            if (file.size <= maxBytes && file.type === this.config.targetFormat) {
                this.logger.log('✓ 이미지 크기가 적절하여 최적화 스킵');
                return file;
            }

            // 이미지 로드
            const img = await this._loadImage(file);
            
            // 리사이즈 비율 계산
            const scale = this._calculateScale(img.width, img.height);
            
            // Canvas에 그리기
            const canvas = this._createCanvas(img, scale);
            
            // 최적화된 Blob 생성
            const optimizedBlob = await this._canvasToBlob(canvas);
            
            // File 객체 생성
            const optimizedFile = new File(
                [optimizedBlob],
                this._generateOptimizedFileName(file.name),
                { type: this.config.targetFormat }
            );

            const compressionRatio = ((1 - optimizedFile.size / file.size) * 100).toFixed(1);
            this.logger.log(
                `✅ 최적화 완료: ${this._formatFileSize(file.size)} → ${this._formatFileSize(optimizedFile.size)} (${compressionRatio}% 압축)`
            );

            return optimizedFile;

        } catch (error) {
            this.logger.error('이미지 최적화 실패:', error);
            // 최적화 실패 시 원본 반환
            return file;
        }
    }

    /**
     * 이미지 파일을 로드하여 Image 객체로 변환
     * 
     * @private
     * @param {File} file - 이미지 파일
     * @returns {Promise<HTMLImageElement>} 로드된 이미지
     */
    _loadImage(file) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            const url = URL.createObjectURL(file);

            img.onload = () => {
                URL.revokeObjectURL(url);
                resolve(img);
            };

            img.onerror = () => {
                URL.revokeObjectURL(url);
                reject(new Error('이미지 로드 실패'));
            };

            img.src = url;
        });
    }

    /**
     * 리사이즈 스케일 계산
     * 
     * @private
     * @param {number} width - 원본 너비
     * @param {number} height - 원본 높이
     * @returns {number} 스케일 비율 (0.0 ~ 1.0)
     */
    _calculateScale(width, height) {
        const { maxWidth, maxHeight } = this.config;

        if (width <= maxWidth && height <= maxHeight) {
            return 1.0; // 리사이즈 불필요
        }

        const widthScale = maxWidth / width;
        const heightScale = maxHeight / height;

        return Math.min(widthScale, heightScale);
    }

    /**
     * Canvas에 이미지 그리기
     * 
     * @private
     * @param {HTMLImageElement} img - 원본 이미지
     * @param {number} scale - 스케일 비율
     * @returns {HTMLCanvasElement} Canvas 요소
     */
    _createCanvas(img, scale) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        const newWidth = Math.floor(img.width * scale);
        const newHeight = Math.floor(img.height * scale);

        canvas.width = newWidth;
        canvas.height = newHeight;

        // 고품질 리사이징 설정
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        // 이미지 그리기
        ctx.drawImage(img, 0, 0, newWidth, newHeight);

        return canvas;
    }

    /**
     * Canvas를 Blob으로 변환
     * 
     * @private
     * @param {HTMLCanvasElement} canvas - Canvas 요소
     * @returns {Promise<Blob>} 이미지 Blob
     */
    _canvasToBlob(canvas) {
        return new Promise((resolve, reject) => {
            canvas.toBlob(
                (blob) => {
                    if (blob) {
                        resolve(blob);
                    } else {
                        reject(new Error('Blob 생성 실패'));
                    }
                },
                this.config.targetFormat,
                this.config.quality
            );
        });
    }

    /**
     * 최적화된 파일명 생성
     * 
     * @private
     * @param {string} originalName - 원본 파일명
     * @returns {string} 새 파일명
     */
    _generateOptimizedFileName(originalName) {
        const nameWithoutExt = originalName.replace(/\.[^/.]+$/, '');
        const ext = this.config.targetFormat === 'image/jpeg' ? 'jpg' : 'png';
        return `${nameWithoutExt}_optimized.${ext}`;
    }

    /**
     * 파일 크기를 읽기 쉬운 형태로 포맷
     * 
     * @private
     * @param {number} bytes - 바이트 크기
     * @returns {string} 포맷된 문자열
     */
    _formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * 여러 이미지를 동시에 최적화
     * 
     * @param {FileList|File[]} files - 이미지 파일 배열
     * @returns {Promise<File[]>} 최적화된 파일 배열
     */
    async optimizeBatch(files) {
        const fileArray = Array.from(files);
        const promises = fileArray.map(file => this.optimizeImage(file));
        return Promise.all(promises);
    }
}

// 싱글톤 인스턴스 생성
const imageOptimizer = new ImageOptimizer();

// 전역 스코프에 노출
if (typeof window !== 'undefined') {
    window.ImageOptimizer = ImageOptimizer;
    window.imageOptimizer = imageOptimizer;
}

// ES6 모듈로도 export
export { ImageOptimizer, imageOptimizer };
export default imageOptimizer;
