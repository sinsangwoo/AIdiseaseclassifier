"""
Frontend JS 상태 머신 계약 검증 (Python 정적 분석)

실제 브라우저 없이 JS 파일을 텍스트로 분석하여
상태 머신 계약 착오를 CI 에서 조기 발견합니다.

보증 항목:
  1. AppState 스키마 (status / uploadedImageUrl / result 필드)
  2. setUploadedImage 비동기 타이밍 (미리보기 즉시 표시 여부)
  3. UIController import 스타일 (default import 여부)
  4. GradCAMViewer export 방식 (default export 여부)
  5. app.js 워크플로우 계약
"""

import re
import os
import pytest

FRONTEND_JS = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'frontend', 'js')
)


def read_js(rel_path: str) -> str:
    """
    FRONTEND_JS 기준 상대경로로 JS 파일 읽기.
    app.js  → frontend/js/app.js   : read_js('app.js')
    state   → frontend/js/state/.. : read_js('state/appState.js')
    """
    path = os.path.join(FRONTEND_JS, rel_path)
    assert os.path.exists(path), (
        f"JS 파일 없음: {path}\n"
        f"FRONTEND_JS = {FRONTEND_JS}"
    )
    with open(path, encoding='utf-8') as f:
        return f.read()


def extract_method_src(src: str, method_name: str, max_lines: int = 60) -> str:
    """
    JS 소스에서 `method_name(` 으로 시작하는 실제 메서드 블록을 추출합니다.

    전략:
      1. 줄 단위로 분리
      2. 주석(//, /* */)이 아닌 줄에서 `method_name(` 패턴 탐색
      3. 해당 줄부터 max_lines 줄을 반환

    이 방식은 JSDoc 주석 블록 안에 같은 이름이 등장해도 무시합니다.
    (기존 re.DOTALL 정규식은 주석 블록을 함수 본문으로 오인했음)
    """
    lines = src.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 주석 줄 제외: // 또는 * 으로 시작하는 줄
        if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
            continue
        # 실제 메서드 정의 줄: `methodName(` 또는 `methodName (` 패턴
        if re.search(rf'\b{re.escape(method_name)}\s*\(', stripped):
            # 해당 줄부터 max_lines 줄 반환
            return '\n'.join(lines[i:i + max_lines])
    return ''


# ── 1. AppState 스키마 ──────────────────────────────────────────────────────
class TestAppStateSchema:

    @pytest.mark.frontend
    def test_has_status_field(self):
        """AppState 에 status 필드가 있어야 한다"""
        src = read_js('state/appState.js')
        assert 'status:' in src, "AppState._state 에 status 필드 없음"
        assert "'idle'" in src or '"idle"' in src, "초기 status 가 idle 이 아님"

    @pytest.mark.frontend
    def test_has_uploadedImageUrl_field(self):
        src = read_js('state/appState.js')
        assert 'uploadedImageUrl' in src, "uploadedImageUrl 필드 없음"

    @pytest.mark.frontend
    def test_has_result_not_analysisResult(self):
        src = read_js('state/appState.js')
        assert 'result:' in src, "result 필드 없음"
        assert 'analysisResult' not in src, "analysisResult 구필드명 남아있음"

    @pytest.mark.frontend
    def test_preview_set_before_filereader_onload(self):
        """
        setUploadedImage 는 FileReader.onload 완료 전에 status=preview 를 설정해야 한다.

        기존 버그:
          reader.onload 안에서 _setState → render 실행 시 uploadedImageUrl == null
          → 미리보기 이미지 안 보임

        올바른 구조:
          _setState({status:'preview'}) 를 먼저 호출 (동기)
          reader.onload 에서 uploadedImageUrl 만 업데이트 (비동기)

        탐색 전략:
          extract_method_src() 로 주석이 아닌 실제 메서드 블록만 추출.
          (기존 re.DOTALL 방식은 JSDoc 주석 안의 패턴을 함수로 오인하는 버그 있음)
        """
        src = read_js('state/appState.js')

        # 주석 제외하고 실제 메서드 블록만 추출
        func_src = extract_method_src(src, 'setUploadedImage', max_lines=80)

        assert func_src, (
            "setUploadedImage 메서드를 소스에서 찾을 수 없음\n"
            "(주석이 아닌 실제 메서드 정의가 없거나 이름이 변경됨)"
        )

        # status='preview' 위치 탐색 — 여러 공백 패턴 지원
        preview_patterns = [
            "status:           'preview'",  # 공백 6자 (기존 코드 스타일)
            "status: 'preview'",            # 공백 1자
            'status: "preview"',
        ]
        idx_preview = -1
        matched_pat = ''
        for pat in preview_patterns:
            idx = func_src.find(pat)
            if idx != -1:
                idx_preview = idx
                matched_pat = pat
                break

        idx_onload = func_src.find('reader.onload')

        assert idx_preview != -1, (
            "setUploadedImage 메서드 안에 status='preview' 즉시 설정 없음\n"
            "올바른 구조: _setState({status:'preview',...}) 를 reader.onload 보다 먼저 호출해야 함\n"
            f"추출된 메서드 블록 (앞 300자):\n{func_src[:300]}"
        )
        assert idx_onload != -1, (
            "setUploadedImage 메서드 안에 reader.onload 없음\n"
            "FileReader 로 DataURL 을 로드하는 코드가 있어야 함"
        )
        assert idx_preview < idx_onload, (
            f"status='preview' 설정(pos {idx_preview})이 "
            f"reader.onload(pos {idx_onload}) 보다 뒤에 있음\n"
            "FileReader 비동기 지연 버그: preview 전환이 DataURL 로드 완료를 기다리고 있음\n"
            f"추출된 메서드 블록 (앞 500자):\n{func_src[:500]}"
        )

    @pytest.mark.frontend
    def test_required_methods_exist(self):
        src = read_js('state/appState.js')
        for m in ('startAnalysis', 'completeAnalysis', 'setError', 'reset', 'setAgreement'):
            assert m in src, f"AppState.{m}() 메서드 없음"


# ── 2. UIController ──────────────────────────────────────────────────────────
class TestUIControllerContract:

    @pytest.mark.frontend
    def test_render_handles_all_statuses(self):
        src = read_js('ui/uiController.js')
        for s in ('idle', 'preview', 'analyzing', 'complete', 'error'):
            assert f"'{s}'" in src or f'"{s}"' in src, f"render() 에 '{s}' case 없음"

    @pytest.mark.frontend
    def test_gradcam_is_default_import(self):
        """GradCAMViewer 는 default export 이므로 named import 하면 SyntaxError"""
        src = read_js('ui/uiController.js')
        assert 'import { GradCAMViewer }' not in src, (
            "GradCAMViewer named import 발견 - default import 으로 변경 필요"
        )
        assert re.search(r'import GradCAMViewer from', src), "GradCAMViewer default import 없음"

    @pytest.mark.frontend
    def test_uses_uploadedImageUrl_from_state(self):
        src = read_js('ui/uiController.js')
        assert 'uploadedImageUrl' in src, "uiController 가 state.uploadedImageUrl 사용 안 함"

    @pytest.mark.frontend
    def test_no_filereader_in_uicontroller(self):
        src = read_js('ui/uiController.js')
        assert 'new FileReader' not in src, (
            "uiController 에 FileReader 직접 사용 - appState 에서만 허용"
        )

    @pytest.mark.frontend
    def test_uses_hide_not_reset_for_gradcam(self):
        src = read_js('ui/uiController.js')
        assert ('gradcamViewer?.hide()' in src or 'gradcamViewer.hide()' in src), (
            "gradcamViewer.hide() 호출 없음"
        )
        assert 'gradcamViewer?.reset()' not in src and 'gradcamViewer.reset()' not in src, (
            "gradcamViewer.reset() 호출 - GradCAMViewer.reset() 메서드 없음"
        )


# ── 3. GradCAMViewer ─────────────────────────────────────────────────────────
class TestGradCAMViewerExport:

    @pytest.mark.frontend
    def test_is_default_export(self):
        src = read_js('ui/gradcam_viewer.js')
        assert 'export default GradCAMViewer' in src, (
            "gradcam_viewer.js 가 default export 가 아님"
        )

    @pytest.mark.frontend
    def test_has_render_and_hide_no_reset(self):
        src = read_js('ui/gradcam_viewer.js')
        assert 'render(' in src, "GradCAMViewer.render() 없음"
        assert 'hide('   in src, "GradCAMViewer.hide() 없음"
        assert 'reset('  not in src, (
            "GradCAMViewer.reset() 발견 - uiController 호출 시 TypeError 발생"
        )


# ── 4. app.js ─────────────────────────────────────────────────────────────────
class TestAppJsContract:

    @pytest.mark.frontend
    def test_warmup_failure_does_not_block_predict(self):
        """
        웜업 실패 시 predict 를 throw 로 차단하지 않아야 한다.
        '서버가 아직 준비' 메시지로 throw 하면 안 됨.

        경로 주의: app.js 는 frontend/js/app.js → read_js('app.js')
        """
        src = read_js('app.js')
        # 차단 패턴: throw new Error 와 '서버 준비' 문자열이 함께 있으면 버그
        has_block = (
            'throw new Error' in src and
            ('\uc11c\ubc84\uac00 \uc544\uc9c1 \uc900\ube44' in src or '\uc11c\ubc84 \uc900\ube44' in src)
        )
        assert not has_block, (
            "웜업 실패 시 predict 를 throw 로 차단하고 있음 "
            "(서버가 살아있어도 접근 불가한 버그)"
        )

    @pytest.mark.frontend
    def test_subscribes_to_appstate(self):
        """app.js 가 appState.subscribe() 를 호출해야 한다"""
        src = read_js('app.js')
        assert 'appState.subscribe' in src, "app.js 에서 appState 구독 없음"

    @pytest.mark.frontend
    def test_calls_warmup(self):
        """app.js 가 warmUpServer() 를 호출해야 한다"""
        src = read_js('app.js')
        assert 'warmUpServer()' in src, "app.js 에서 warmUpServer() 호출 없음"
