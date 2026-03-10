/**
 * Grad-CAM Heatmap Viewer Component (Phase D)
 *
 * 역할:
 *   - 백엔드 API 응답의 `gradcam` 필드를 받아 히트맵 UI를 렌더링
 *   - 3가지 탭 제공: "오버레이" / "히트맵 단독" / "원본 vs 히트맵 비교"
 *   - PyTorch 미설치 등 gradcam.available=false 시 안내 메시지 표시
 *   - 신뢰도 배지 (HIGH / MEDIUM / LOW)
 *   - 주목도(attention_score) 바 렌더링
 *
 * 사용법:
 *   const viewer = new GradCAMViewer('gradcamViewer');
 *   viewer.render(gradcamData, originalImageSrc);
 *   viewer.hide();
 */

class GradCAMViewer {
    /**
     * @param {string} containerId - 원하는 컨테이너 DOM id
     */
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.warn(`[GradCAMViewer] #${containerId} 요소를 찾지 못했습니다.`);
        }
        this._activeTab = 'overlay';
    }

    // ------------------------------------------------------------------ //
    //  Public API                                                         //
    // ------------------------------------------------------------------ //

    /**
     * Grad-CAM 데이터를 받아 전체 컴포넌트를 렌더링
     *
     * @param {Object}  gradcam           - 백엔드 `response.gradcam` 필드
     * @param {string}  originalImageSrc  - 레포트에 표시된 원본 이미지 src
     */
    render(gradcam, originalImageSrc) {
        if (!this.container) return;

        this.container.classList.remove('heatmap-viewer--hidden');
        this.container.innerHTML = this._buildHTML(gradcam, originalImageSrc);
        this._bindTabEvents();
        this._animateScoreBar(gradcam);
    }

    /** 컴포넌트 숨기기 */
    hide() {
        if (!this.container) return;
        this.container.classList.add('heatmap-viewer--hidden');
        this.container.innerHTML = '';
    }

    // ------------------------------------------------------------------ //
    //  Private: HTML 빌더                                              //
    // ------------------------------------------------------------------ //

    _buildHTML(gradcam, originalImageSrc) {
        const available = gradcam?.available === true;

        return `
            ${this._buildHeader(gradcam)}
            ${available ? this._buildTabs() : ''}
            <div class="heatmap-panels">
                ${available
                    ? this._buildActivePanels(gradcam, originalImageSrc)
                    : this._buildUnavailablePanel(gradcam)
                }
            </div>
        `;
    }

    _buildHeader(gradcam) {
        const available = gradcam?.available === true;
        const reliability = gradcam?.reliability || 'UNAVAILABLE';
        const badgeClass = this._reliabilityBadgeClass(reliability);
        const badgeIcon = this._reliabilityIcon(reliability);
        const badgeLabel = available ? reliability : 'UNAVAILABLE';

        return `
            <div class="heatmap-viewer__header">
                <span class="heatmap-viewer__title">
                    <i class="fa-solid fa-eye"></i>
                    Grad-CAM XAI 히트맵
                </span>
                <span class="heatmap-badge heatmap-badge--${badgeClass}">
                    <i class="fa-solid ${badgeIcon}"></i>
                    ${badgeLabel}
                </span>
            </div>
        `;
    }

    _buildTabs() {
        return `
            <div class="heatmap-tabs" role="tablist">
                <button class="heatmap-tab heatmap-tab--active"
                        role="tab" data-tab="overlay"
                        aria-selected="true">
                    <i class="fa-solid fa-layer-group"></i> 오버레이
                </button>
                <button class="heatmap-tab"
                        role="tab" data-tab="heatmap"
                        aria-selected="false">
                    <i class="fa-solid fa-fire"></i> 히트맵
                </button>
                <button class="heatmap-tab"
                        role="tab" data-tab="compare"
                        aria-selected="false">
                    <i class="fa-solid fa-code-compare"></i> 비교
                </button>
            </div>
        `;
    }

    _buildActivePanels(gradcam, originalImageSrc) {
        const overlayB64  = gradcam.heatmap_overlay_base64 || '';
        const heatmapB64  = gradcam.heatmap_only_base64    || '';
        const targetClass = gradcam.target_class            || '-';
        const score       = gradcam.attention_score         ?? null;
        const reliability = gradcam.reliability             || '';

        return `
            <!-- 탭 1: 오버레이 -->
            <div class="heatmap-panel heatmap-panel--active" data-panel="overlay">
                <div class="heatmap-img-wrap">
                    <img class="heatmap-img" src="data:image/png;base64,${overlayB64}"
                         alt="Grad-CAM 오버레이 히트맵" />
                    <div class="heatmap-img-label">✨ AI 주목 영역 오버레이</div>
                </div>
                ${score !== null ? this._buildScoreBar(score) : ''}
                ${this._buildLegend()}
                <p class="heatmap-desc">
                    <strong>빨강</strong>에 가까울수록 AI는 해당 영역을 강하게 주목했습니다.
                    진단 대상 클래스: <strong>${targetClass}</strong>
                </p>
                ${reliability === 'LOW' ? this._buildReliabilityWarning() : ''}
                ${this._buildDisclaimer()}
            </div>

            <!-- 탭 2: 히트맵만 -->
            <div class="heatmap-panel" data-panel="heatmap">
                <div class="heatmap-img-wrap">
                    <img class="heatmap-img" src="data:image/png;base64,${heatmapB64}"
                         alt="Grad-CAM 순수 히트맵" />
                    <div class="heatmap-img-label">JET 콌러맵 적용 히트맵</div>
                </div>
                ${this._buildLegend()}
                <p class="heatmap-desc">
                    원본 이미지 없이 주목도만 시각화한 진단 히트맵입니다.
                    교육적 목적의 XAI 시각화에 활용하세요.
                </p>
                ${this._buildDisclaimer()}
            </div>

            <!-- 탭 3: 나란히 비교 -->
            <div class="heatmap-panel heatmap-panel--compare" data-panel="compare">
                <div>
                    <div class="heatmap-img-wrap">
                        <img class="heatmap-img" src="${originalImageSrc}" alt="원본 X-ray" />
                        <div class="heatmap-img-label">원본 영상</div>
                    </div>
                </div>
                <div>
                    <div class="heatmap-img-wrap">
                        <img class="heatmap-img" src="data:image/png;base64,${overlayB64}"
                             alt="Grad-CAM 오버레이" />
                        <div class="heatmap-img-label">AI 주목 영역</div>
                    </div>
                </div>
            </div>
        `;
    }

    _buildUnavailablePanel(gradcam) {
        const reason = gradcam?.error
            ? `오류: ${gradcam.error}`
            : 'PyTorch가 서버에 설치되지 않았거나 가중치 파일이 없습니다.';
        return `
            <div class="heatmap-unavailable">
                <i class="fa-solid fa-flask-vial"></i>
                <p>Grad-CAM 히트맵을 생성할 수 없습니다.<br>
                <span style="font-size:0.65rem;opacity:0.6;">${reason}</span></p>
                <p style="margin-top:0.5rem;">ONNX 예측 결과는 정상적으로 제공됩니다.</p>
            </div>
        `;
    }

    _buildLegend() {
        return `
            <div class="heatmap-legend">
                <div class="heatmap-legend__bar" aria-hidden="true"></div>
                <div class="heatmap-legend__labels">
                    <span class="heatmap-legend__label">낙은 주목</span>
                    <span class="heatmap-legend__label">중간</span>
                    <span class="heatmap-legend__label">높은 주목</span>
                </div>
            </div>
        `;
    }

    _buildScoreBar(score) {
        const pct = Math.round(score * 100);
        return `
            <div class="heatmap-score" id="heatmapScoreBar">
                <span class="heatmap-score__label">주목도</span>
                <div class="heatmap-score__bar-wrap">
                    <div class="heatmap-score__bar" style="width: 0%"
                         data-target="${pct}"></div>
                </div>
                <span class="heatmap-score__value">${pct}%</span>
            </div>
        `;
    }

    _buildReliabilityWarning() {
        return `
            <div class="heatmap-warning">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <span>예측 확률이 50% 미만으로 히트맵 신뢰도가 낙습니다.
                보조 참고 용도로만 활용하세요.</span>
            </div>
        `;
    }

    _buildDisclaimer() {
        return `
            <p class="heatmap-desc" style="opacity:0.5; font-size:0.65rem; margin-top:0.4rem;">
                ⚠️ 특징 지도 영역은 모델의 내부 표현을 시각화한 것으로,
                의학적 진단을 대체하지 않습니다.
            </p>
        `;
    }

    // ------------------------------------------------------------------ //
    //  Private: 이벤트 바인딩                                     //
    // ------------------------------------------------------------------ //

    _bindTabEvents() {
        const tabs   = this.container.querySelectorAll('.heatmap-tab');
        const panels = this.container.querySelectorAll('.heatmap-panel');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const target = tab.dataset.tab;

                tabs.forEach(t => {
                    t.classList.remove('heatmap-tab--active');
                    t.setAttribute('aria-selected', 'false');
                });
                panels.forEach(p => p.classList.remove('heatmap-panel--active'));

                tab.classList.add('heatmap-tab--active');
                tab.setAttribute('aria-selected', 'true');

                const panel = this.container.querySelector(`[data-panel="${target}"]`);
                if (panel) panel.classList.add('heatmap-panel--active');

                this._activeTab = target;
            });
        });
    }

    _animateScoreBar(gradcam) {
        if (!gradcam?.available) return;
        const bar = this.container.querySelector('.heatmap-score__bar');
        if (!bar) return;
        const target = parseInt(bar.dataset.target, 10) || 0;
        // 다음 프레임에서 애니메이션 시작 (CSS transition 활용)
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                bar.style.width = `${target}%`;
            });
        });
    }

    // ------------------------------------------------------------------ //
    //  Private: 헬퍼                                                    //
    // ------------------------------------------------------------------ //

    _reliabilityBadgeClass(reliability) {
        const map = { HIGH: 'high', MEDIUM: 'medium', LOW: 'low' };
        return map[reliability] || 'unavailable';
    }

    _reliabilityIcon(reliability) {
        const map = {
            HIGH:   'fa-circle-check',
            MEDIUM: 'fa-circle-exclamation',
            LOW:    'fa-circle-xmark',
        };
        return map[reliability] || 'fa-circle-question';
    }
}

export default GradCAMViewer;
