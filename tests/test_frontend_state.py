"""
Frontend JS 상태 머신 계약 검증 (Python 정적 분석)

보증 항목:
  1. AppState 스키마
  2. setUploadedImage 비동기 타이밍
  3. UIController 화면 전환 계약
  4. GradCAMViewer export
  5. app.js 워크플로우
"""

import re
import os
import pytest

FRONTEND_JS = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'frontend', 'js')
)


def read_js(rel_path: str) -> str:
    path = os.path.join(FRONTEND_JS, rel_path)
    assert os.path.exists(path), f"JS 파일 없음: {path}\nFRONTEND_JS = {FRONTEND_JS}"
    with open(path, encoding='utf-8') as f:
        return f.read()


def extract_method_src(src: str, method_name: str, max_lines: int = 80) -> str:
    """
    주석이 아닌 실제 메서드 정의 블록만 추출
    (JSDoc 주석 안의 같은 이름 타맨트 무시)
    """
    lines = src.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('//') or s.startswith('*') or s.startswith('/*'):
            continue
        if re.search(rf'\b{re.escape(method_name)}\s*\(', s):
            return '\n'.join(lines[i:i + max_lines])
    return ''


# ── 1. AppState 스키마 ──────────────────────────────────────────────────────────────
class TestAppStateSchema:

    @pytest.mark.frontend
    def test_has_status_field(self):
        src = read_js('state/appState.js')
        assert 'status:' in src
        assert "'idle'" in src or '"idle"' in src

    @pytest.mark.frontend
    def test_has_uploadedImageUrl_field(self):
        assert 'uploadedImageUrl' in read_js('state/appState.js')

    @pytest.mark.frontend
    def test_has_result_not_analysisResult(self):
        src = read_js('state/appState.js')
        assert 'result:' in src
        assert 'analysisResult' not in src

    @pytest.mark.frontend
    def test_preview_set_before_filereader_onload(self):
        """
        setUploadedImage 는 FileReader.onload 완료 전에 status=preview 를 설정해야 한다.
        extract_method_src 로 주석 제외 후 실제 메서드 블록만 타겟.
        """
        src = read_js('state/appState.js')
        func_src = extract_method_src(src, 'setUploadedImage', max_lines=80)
        assert func_src, "setUploadedImage 메서드 없음"

        preview_patterns = ["status:           'preview'", "status: 'preview'", 'status: "preview"']
        idx_preview = next((func_src.find(p) for p in preview_patterns if func_src.find(p) != -1), -1)
        idx_onload  = func_src.find('reader.onload')

        assert idx_preview != -1, (
            "setUploadedImage 안에 status=preview 우선 설정 없음\n"
            f"func_src:\\ n{func_src[:300]}"
        )
        assert idx_onload != -1, "setUploadedImage 안에 reader.onload 없음"
        assert idx_preview < idx_onload, (
            f"preview 설정(pos {idx_preview}) 이 reader.onload(pos {idx_onload}) 후에 있음"
        )

    @pytest.mark.frontend
    def test_required_methods_exist(self):
        src = read_js('state/appState.js')
        for m in ('startAnalysis', 'completeAnalysis', 'setError', 'reset', 'setAgreement'):
            assert m in src, f"AppState.{m}() 없음"


# ── 2. UIController 화면 전환 계약 ──────────────────────────────────────────────
class TestUIControllerContract:

    @pytest.mark.frontend
    def test_render_handles_all_statuses(self):
        src = read_js('ui/uiController.js')
        for s in ('idle', 'preview', 'analyzing', 'complete', 'error'):
            assert f"'{s}'" in src or f'"{s}"' in src, f"render() 에 '{s}' case 없음"

    @pytest.mark.frontend
    def test_preview_hides_upload_wrapper(self):
        """
        _renderPreview 는 uploadWrapper(01.영상업로드 헤딩 포함 부모 section) 를 hide 해야 한다.

        수정 이력:
          - 기존: uploadSection(드롭존 div만) hide → h3 헤딩이 남아있는 버그
          - 현재: uploadWrapper(부모 section 전체) hide → 헤딩 포함 완전히 숨겨짐

        uploadWrapper = index.html 의 <section id="uploadWrapper">
        """
        src = read_js('ui/uiController.js')
        func_src = extract_method_src(src, '_renderPreview', max_lines=20)
        assert func_src, "_renderPreview 메서드 없음"
        assert '_hide(this.uploadWrapper)' in func_src, (
            "_renderPreview 에서 uploadWrapper 를 hide 안 함 — "
            "uploadWrapper 는 01.영상업로드 h3 헤딩을 포함한 부모 section. "
            "uploadSection(드롭존만) 을 숨기면 헤딩이 남아있는 버그 발생."
        )

    @pytest.mark.frontend
    def test_error_hides_upload_wrapper(self):
        """
        _renderError 도 uploadWrapper 를 hide 해야 한다.
        에러 시 01. 영상 업로드 영역이 다시 나타나면 안 됨.
        """
        src = read_js('ui/uiController.js')
        func_src = extract_method_src(src, '_renderError', max_lines=20)
        assert func_src, "_renderError 메서드 없음"
        assert '_hide(this.uploadWrapper)' in func_src, (
            "_renderError 에서 uploadWrapper 를 hide 안 함 — "
            "에러 시 01. 업로드 영역이 다시 나타나는 버그"
        )

    @pytest.mark.frontend
    def test_gradcam_is_default_import(self):
        src = read_js('ui/uiController.js')
        assert 'import { GradCAMViewer }' not in src, "named import 발견"
        assert re.search(r'import GradCAMViewer from', src), "default import 없음"

    @pytest.mark.frontend
    def test_uses_uploadedImageUrl_from_state(self):
        assert 'uploadedImageUrl' in read_js('ui/uiController.js')

    @pytest.mark.frontend
    def test_no_filereader_in_uicontroller(self):
        assert 'new FileReader' not in read_js('ui/uiController.js'), "FileReader 직접 사용"

    @pytest.mark.frontend
    def test_uses_hide_not_reset_for_gradcam(self):
        src = read_js('ui/uiController.js')
        assert 'gradcamViewer?.hide()' in src or 'gradcamViewer.hide()' in src
        assert 'gradcamViewer?.reset()' not in src and 'gradcamViewer.reset()' not in src


# ── 3. GradCAMViewer ──────────────────────────────────────────────────────────────
class TestGradCAMViewerExport:

    @pytest.mark.frontend
    def test_is_default_export(self):
        assert 'export default GradCAMViewer' in read_js('ui/gradcam_viewer.js')

    @pytest.mark.frontend
    def test_has_render_and_hide_no_reset(self):
        src = read_js('ui/gradcam_viewer.js')
        assert 'render(' in src
        assert 'hide('   in src
        assert 'reset('  not in src, "GradCAMViewer.reset() 발견"


# ── 4. app.js ─────────────────────────────────────────────────────────────────────
class TestAppJsContract:

    @pytest.mark.frontend
    def test_warmup_failure_does_not_block_predict(self):
        src = read_js('app.js')
        has_block = (
            'throw new Error' in src and
            ('\uc11c\ubc84\uac00 \uc544\uc9c1 \uc900\ube44' in src or '\uc11c\ubc84 \uc900\ube44' in src)
        )
        assert not has_block

    @pytest.mark.frontend
    def test_subscribes_to_appstate(self):
        assert 'appState.subscribe' in read_js('app.js')

    @pytest.mark.frontend
    def test_calls_warmup(self):
        assert 'warmUpServer()' in read_js('app.js')
