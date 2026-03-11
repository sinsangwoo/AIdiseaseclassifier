/**
 * Grad-CAM Heatmap Viewer Component (Phase E)
 *
 * Phase E 변경사항:
 *   E-2: low_confidence=true 시 히트맵 이미지 대신 경고 패널 렌더링
 *   E-3: 모든 패널에 법적 고지 강화 (워터마크 텍스트 오버레이 포함)
 *   E-4: gradcam_time_ms 성능 수치 UI 표시
 */

class GradCAMViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.warn(`[GradCAMViewer] #${containerId} 요소를 찾지 못했습니다.`);
        }
        this._activeTab = 'overlay';
    }

    render(gradcam, originalImageSrc) {
        if (!this.container) return;
        this.container.classList.remove('heatmap-viewer--hidden');
        this.container.innerHTML = this._buildHTML(gradcam, originalImageSrc);
        this._bindTabEvents();
        this._animateScoreBar(gradcam);
    }

    hide() {
        if (!this.container) return;
        this.container.classList.add('heatmap-viewer--hidden');
        this.container.innerHTML = '';
    }

    // ------------------------------------------------------------------ //
    //  HTML 빌더                                                          //
    // ------------------------------------------------------------------ //

    _buildHTML(gradcam, originalImageSrc) {
        const available     = gradcam?.available === true;
        const lowConfidence = gradcam?.low_confidence === true;

        return `
            ${this._buildHeader(gradcam)}
            ${available && !lowConfidence ? this._buildTabs() : ''}
            <div class="heatmap-panels">
                ${
                    !available
                        ? this._buildUnavailablePanel(gradcam)
                        : lowConfidence
                            ? this._buildLowConfidencePanel(gradcam)
                            : this._buildActivePanels(gradcam, originalImageSrc)
                }
            </div>
        `;
    }

    _buildHeader(gradcam) {
        const available     = gradcam?.available === true;
        const lowConfidence = gradcam?.low_confidence === true;
        const reliability   = gradcam?.reliability || 'UNAVAILABLE';
        const timeMs        = gradcam?.gradcam_time_ms;  // E-4

        let badgeClass, badgeIcon, badgeLabel;
        if (!available) {
            badgeClass = 'unavailable'; badgeIcon = 'fa-circle-question'; badgeLabel = 'UNAVAILABLE';
        } else if (lowConfidence) {
            badgeClass = 'low'; badgeIcon = 'fa-circle-xmark'; badgeLabel = 'LOW';
        } else {
            badgeClass = this._reliabilityBadgeClass(reliability);
            badgeIcon  = this._reliabilityIcon(reliability);
            badgeLabel = reliability;
        }

        // E-4: 성능 수치
        const timeBadge = (timeMs != null)
            ? `<span class="heatmap-badge heatmap-badge--unavailable" style="font-size:0.62rem;opacity:0.6;">
                   <i class="fa-solid fa-stopwatch"></i> ${timeMs.toFixed(0)}ms
               </span>`
            : '';

        return `
            <div class="heatmap-viewer__header">
                <span class="heatmap-viewer__title">
                    <i class="fa-solid fa-eye"></i>
                    Grad-CAM XAI 히트맵
                </span>
                <div style="display:flex;gap:0.4rem;align-items:center;flex-wrap:wrap;">
                    ${timeBadge}
                    <span class="heatmap-badge heatmap-badge--${badgeClass}">
                        <i class="fa-solid ${badgeIcon}"></i>
                        ${badgeLabel}
                    </span>
                </div>
            </div>
        `;
    }

    _buildTabs() {
        return `
            <div class="heatmap-tabs" role="tablist">
                <button class="heatmap-tab heatmap-tab--active"
                        role="tab" data-tab="overlay" aria-selected="true">
                    <i class="fa-solid fa-layer-group"></i> 오버레이
                </button>
                <button class="heatmap-tab"
                        role="tab" data-tab="heatmap" aria-selected="false">
                    <i class="fa-solid fa-fire"></i> 히트맵
                </button>
                <button class="heatmap-tab"
                        role="tab" data-tab="compare" aria-selected="false">
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
                    ${this._buildWatermark()}
                    <div class="heatmap-img-label">✨ AI 주목 영역 오버레이</div>
                </div>
                ${score !== null ? this._buildScoreBar(score) : ''}
                ${this._buildLegend()}
                <p class="heatmap-desc">
                    <strong>빨강</strong>에 가까울수록 AI는 해당 영역을 강하게 주목했습니다.
                    진단 대상 클래스: <strong>${targetClass}</strong>
                </p>
                ${reliability === 'LOW' ? this._buildReliabilityWarning() : ''}
                ${this._buildStrongDisclaimer()}
            </div>

            <!-- 탭 2: 히트맵만 -->
            <div class="heatmap-panel" data-panel="heatmap">
                <div class="heatmap-img-wrap">
                    <img class="heatmap-img" src="data:image/png;base64,${heatmapB64}"
                         alt="Grad-CAM 순수 히트맵" />
                    ${this._buildWatermark()}
                    <div class="heatmap-img-label">JET 컬러맵 적용 히트맵</div>
                </div>
                ${this._buildLegend()}
                <p class="heatmap-desc">
                    원본 이미지 없이 주목도만 시각화한 히트맵입니다.
                    교육적 목적의 XAI 시각화에 활용하세요.
                </p>
                ${this._buildStrongDisclaimer()}
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
                        ${this._buildWatermark()}
                        <div class="heatmap-img-label">AI 주목 영역</div>
                    </div>
                </div>
            </div>
        `;
    }

    /** E-2: LOW 신뢰도 전용 패널 — 히트맵 이미지 대신 경고 표시 */
    _buildLowConfidencePanel(gradcam) {
        const targetClass = gradcam.target_class  || '-';
        const score       = gradcam.attention_score ?? null;
        return `
            <div class="heatmap-unavailable">
                <i class="fa-solid fa-triangle-exclamation" style="color:#f87171;"></i>
                <p style="color:#f87171;font-weight:600;margin-bottom:0.5rem;">
                    신뢰도 부족 — 히트맵 표시 억제
                </p>
                <p>
                    예측 확률이 50% 미만(<strong>${targetClass}</strong>)으로,
                    히트맵의 신뢰성이 낮아 표시하지 않습니다.
                </p>
                <p style="font-size:0.65rem;opacity:0.6;margin-top:0.5rem;">
                    더 명확한 이미지를 업로드하거나,
                    모델 파인튜닝 후 재시도하세요.
                </p>
                ${score !== null ? `<p style="font-size:0.65rem;margin-top:0.4rem;opacity:0.7;">attention_score: ${(score*100).toFixed(1)}%</p>` : ''}
            </div>
            ${this._buildStrongDisclaimer()}
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
                    <span class="heatmap-legend__label">낮은 주목</span>
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
                    <div class="heatmap-score__bar" style="width:0%" data-target="${pct}"></div>
                </div>
                <span class="heatmap-score__value">${pct}%</span>
            </div>
        `;
    }

    _buildReliabilityWarning() {
        return `
            <div class="heatmap-warning">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <span>예측 확률이 50% 미만으로 히트맵 신뢰도가 낮습니다.
                보조 참고 용도로만 활용하세요.</span>
            </div>
        `;
    }

    /** E-3: 강화된 법적 고지 — 더 눈에 띄는 스타일 */
    _buildStrongDisclaimer() {
        return `
            <div class="heatmap-warning" style="margin-top:0.75rem;background:rgba(201,169,110,0.06);border-color:rgba(201,169,110,0.2);color:#c9a96e;">
                <i class="fa-solid fa-scale-balanced"></i>
                <span>
                    <strong>[의료적 고지]</strong>
                    이 히트맵은 AI 모델의 내부 연산을 시각화한 연구용 자료입니다.
                    의학적 진단을 대체하지 않으며, 최종 판단은 반드시 전문의가 내려야 합니다.
                    <em>(Not FDA/CE approved. For research & educational use only.)</em>
                </span>
            </div>
        `;
    }

    /** E-3: 이미지 위 워터마크 오버레이 */
    _buildWatermark() {
        return `
            <div class="heatmap-watermark" aria-hidden="true">
                연구용 AI · 의료 진단 불가
            </div>
        `;
    }

    // ------------------------------------------------------------------ //
    //  이벤트 바인딩                                                       //
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
        requestAnimationFrame(() => {
            requestAnimationFrame(() => { bar.style.width = `${target}%`; });
        });
    }

    // ------------------------------------------------------------------ //
    //  헬퍼                                                               //
    // ------------------------------------------------------------------ //

    _reliabilityBadgeClass(r) {
        return { HIGH: 'high', MEDIUM: 'medium', LOW: 'low' }[r] || 'unavailable';
    }

    _reliabilityIcon(r) {
        return {
            HIGH:   'fa-circle-check',
            MEDIUM: 'fa-circle-exclamation',
            LOW:    'fa-circle-xmark',
        }[r] || 'fa-circle-question';
    }
}

export default GradCAMViewer;
