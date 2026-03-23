"""
Frontend JS 상태 머신 계약 검증 (Python 정적 분석)

실제 브라우저 없이 JS 파일을 텍스트로 분석하여
상태 머신 계약 착오를 CI 에서 조기 발견합니다.

검증 항목:
  1. AppState 스키마 (status/uploadedImageUrl/result 필드)
  2. setUploadedImage 비동기 타이밍 (preview 즉시 전환 여부)
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


def read_js(rel_path):
    path = os.path.join(FRONTEND_JS, rel_path)
    assert os.path.exists(path), f"JS 파일 없음: {path}"
    with open(path, encoding='utf-8') as f:
        return f.read()


# ────────────────────────────────────────────────────────────────────────────
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
        """result 필드가 있고 구식 analysisResult 가 없어야 한다"""
        src = read_js('state/appState.js')
        assert 'result:' in src, "result 필드 없음"
        assert 'analysisResult' not in src, "analysisResult 구필드명 남아있음"

    @pytest.mark.frontend
    def test_preview_set_before_filereader_onload(self):
        """
        setUploadedImage 는 FileReader 완료 전에 status=preview 를 설정해야 한다.
        기존 버그: reader.onload 안에서 setState → UI 지연
        올바른 구조: _setState(preview) 먼저, reader.onload 나중에
        """
        src = read_js('state/appState.js')
        idx_preview = src.find("status:           'preview'")
        if idx_preview == -1:
            idx_preview = src.find("status: 'preview'")
        idx_onload  = src.find('reader.onload')
        assert idx_preview != -1, "setUploadedImage 에 status=preview 전환 없음"
        assert idx_onload  != -1, "setUploadedImage 에 reader.onload 없음"
        assert idx_preview < idx_onload, (
            "status=preview 전환이 reader.onload 이후에 있음 "
            "(FileReader 비동기 지연 버그)"
        )

    @pytest.mark.frontend
    def test_required_methods_exist(self):
        src = read_js('state/appState.js')
        for m in ('startAnalysis', 'completeAnalysis', 'setError', 'reset', 'setAgreement'):
            assert m in src, f"AppState.{m}() 메서드 없음"


# ────────────────────────────────────────────────────────────────────────────
class TestUIControllerContract:

    @pytest.mark.frontend
    def test_render_handles_all_statuses(self):
        src = read_js('ui/uiController.js')
        for s in ('idle', 'preview', 'analyzing', 'complete', 'error'):
            assert f"'{s}'" in src or f'"{s}"' in src, (
                f"render() 에 '{s}' case 없음"
            )

    @pytest.mark.frontend
    def test_gradcam_is_default_import(self):
        """GradCAMViewer 는 default export 이므로 named import 하면 SyntaxError"""
        src = read_js('ui/uiController.js')
        assert 'import { GradCAMViewer }' not in src, (
            "GradCAMViewer named import 발견 - default import 으로 변경 필요"
        )
        assert re.search(r'import GradCAMViewer from', src), (
            "GradCAMViewer default import 없음"
        )

    @pytest.mark.frontend
    def test_uses_uploadedImageUrl_from_state(self):
        src = read_js('ui/uiController.js')
        assert 'uploadedImageUrl' in src, (
            "uiController 가 state.uploadedImageUrl 을 사용하지 않음"
        )

    @pytest.mark.frontend
    def test_no_filereader_in_uicontroller(self):
        """FileReader 는 appState 에서만 써야 한다"""
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


# ────────────────────────────────────────────────────────────────────────────
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
            "GradCAMViewer.reset() 발견 - uiController가 호출 시 TypeError 발생"
        )


# ────────────────────────────────────────────────────────────────────────────
class TestAppJsContract:

    @pytest.mark.frontend
    def test_warmup_failure_does_not_block_predict(self):
        """
        웼업 실패 시 predict 를 throw 로 차단하지 않아야 한다.
        '서버가 아직 준비' 메시지로 throw 하면 안됨.
        """
        src = read_js('../app.js')
        # 차단 패턴: throw new Error + '서버 준비' 문자열이 함께 있으면 버그
        has_block = ('throw new Error' in src and
                     ('서버가 아직 준비' in src or '서버 준비' in src))
        assert not has_block, (
            "웼업 실패 시 predict 를 throw 로 차단하고 있음 "
            "(서버가 살아있어도 접근 불가한 버그)"
        )

    @pytest.mark.frontend
    def test_subscribes_to_appstate(self):
        src = read_js('../app.js')
        assert 'appState.subscribe' in src

    @pytest.mark.frontend
    def test_calls_warmup(self):
        src = read_js('../app.js')
        assert 'warmUpServer()' in src
