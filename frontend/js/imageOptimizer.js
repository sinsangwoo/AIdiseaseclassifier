/**
 * Image Optimizer Module (Phase 4)
 * 
 * 클라이언트측 이미지 압축 및 최적화
 * 서버 업로드 전 브라우저에서 이미지를 적정 크기로 압축
 */

export class ImageOptimizer {
    /**
     * 이미지 최적화 설정
     * @param {Object} options - 설정 옵션
     * @param {number} options.maxWidth - 최대 넓이 (기본: 1024px)
     * @param {number} options.maxHeight - 최대 높이 (기본: 1024px)
     * @param {number} options.quality - 품질 (0.0-1.0, 기본: 0.8)
     * @param {string} options.format - 출력 포맷 ('image/jpeg' or 'image/webp')
     */
    constructor(options = {}) {
        this.maxWidth = options.maxWidth || 1024;
        this.maxHeight = options.maxHeight || 1024;
        this.quality = options.quality || 0.8;
        this.format = options.format || 'image/jpeg';
    }

    /**
     * File 객체를 최적화된 이미지로 변환
     * @param {File} file - 원본 이미지 파일
     * @returns {Promise<Blob>} - 최적화된 이미지 Blob
     */
    async optimize(file) {
        return new Promise((resolve, reject) => {
            // 이미지가 아니면 원본 반환
            if (!file.type.startsWith('image/')) {
                resolve(file);
                return;
            }

            const reader = new FileReader();

            reader.onload = (e) => {
                const img = new Image();

                img.onload = () => {
                    // 이미 작은 이미지는 압축하지 않음
                    if (img.width <= this.maxWidth && img.height <= this.maxHeight) {
                        resolve(file);
                        return;
                    }

                    // 비율 유지하면서 크기 조정
                    const { width, height } = this._calculateDimensions(
                        img.width,
                        img.height
                    );

                    // Canvas에 그리기
                    const canvas = document.createElement('canvas');
                    canvas.width = width;
                    canvas.height = height;

                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);

                    // Blob으로 변환
                    canvas.toBlob(
                        (blob) => {
                            if (blob) {
                                console.log(
                                    `📊 이미지 최적화: ${this._formatBytes(file.size)} → ${this._formatBytes(blob.size)} ` +
                                    `(압축률: ${((1 - blob.size / file.size) * 100).toFixed(1)}%)`
                                );
                                resolve(blob);
                            } else {
                                reject(new Error('이미지 블롭 생성 실패'));
                            }
                        },
                        this.format,
                        this.quality
                    );
                };

                img.onerror = () => {
                    reject(new Error('이미지 로드 실패'));
                };

                img.src = e.target.result;
            };

            reader.onerror = () => {
                reject(new Error('파일 읽기 실패'));
            };

            reader.readAsDataURL(file);
        });
    }

    /**
     * 비율을 유지하면서 크기 계산
     * @private
     */
    _calculateDimensions(originalWidth, originalHeight) {
        let width = originalWidth;
        let height = originalHeight;

        if (width > this.maxWidth) {
            height = (height * this.maxWidth) / width;
            width = this.maxWidth;
        }

        if (height > this.maxHeight) {
            width = (width * this.maxHeight) / height;
            height = this.maxHeight;
        }

        return {
            width: Math.round(width),
            height: Math.round(height)
        };
    }

    /**
     * 바이트를 사람이 읽기 쉬운 형식으로 변환
     * @private
     */
    _formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
}

/**
 * 기본 인스턴스 생성
 */
export const imageOptimizer = new ImageOptimizer({
    maxWidth: 1024,
    maxHeight: 1024,
    quality: 0.85,
    format: 'image/jpeg'
});

export default imageOptimizer;
