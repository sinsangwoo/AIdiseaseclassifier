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

[주요 버그 수정 이력]
  - 계약 데플:  uiController.render(state) 가 status 필드로 분기
  - named import SyntaxError: { GradCAMViewer } 대신 GradCAMViewer
  - FileReader 비동기 지연: preview 전환이 reader.onload 후로 미루어짐
  - 웼업 실패 차단: warmUpFailed 시 throw 로 predict 차단 대신 직접 시도
"""

import re
import os
import pytest

# FRONTEND_JS = .../frontend/js
FRONTEND_JS = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'frontend', 'js')
)


def read_js(rel_path: str) -> str:
    """
    FRONTEND_JS 기준 상대경로로 JS 파일 읽기.
    app.js = frontend/js/app.js 이므로 read_js('app.js') 로 호출.
    """
    path = os.path.join(FRONTEND_JS, rel_path)
    assert os.path.exists(path), (
        f"JS 파일 없음: {path}\n"
        f"FRONTEND_JS = {FRONTEND_JS}"
    )
    with open(path, encoding='utf-8') as f:
        return f.read()


# ── 1. AppState 스키마 ──────────────────────────────────────────────────────────────────
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

        기존 버그: reader.onload 안에서 _setState → render 실행 시 uploadedImageUrl == null
        올바른 구조: _setState(preview) 먼저 호출, reader.onload 는 나중에 uploadedImageUrl 만 업데이트

        검증 방식:
          setUploadedImage 함수 안에서
          1) status='preview' 를 포함한 _setState 호출 위치(idx_preview)
          2) reader.onload 정의 위치(idx_onload)
          idx_preview < idx_onload 이어야 함

          주의: src.find(pattern) 은 파일 전체에서 첫 번째 매치를 반환하므로
          setUploadedImage 함수 블록 내에서만 타겟하도록 함수 범위를 켜냅니다.
        """
        src = read_js('state/appState.js')

        # setUploadedImage 함수 블록만 추출
        func_match = re.search(r'setUploadedImage\s*\(.*?\}\s*\n', src, re.DOTALL)
        if func_match is None:
            # 함수 블록 주미 기반 추출: 'setUploadedImage' 부터 다음 메서드/클래스 시작 전까지
            start = src.find('setUploadedImage')
            assert start != -1, "setUploadedImage 메서드 없음"
            # 다음 메서드 시그니처 위치를 추정 (최대 3000자 기준)
            func_src = src[start:start + 3000]
        else:
            start    = func_match.start()
            func_src = func_match.group()

        # 'preview' 스키마 설정 위치 - 여러 공백 패턴 지원
        preview_patterns = [
            "status:           'preview'",   # 공백 6자
            "status: 'preview'",             # 공백 1자
            'status: "preview"',
        ]
        idx_preview = -1
        for pat in preview_patterns:
            idx = func_src.find(pat)
            if idx != -1:
                idx_preview = idx
                break

        idx_onload = func_src.find('reader.onload')

        assert idx_preview != -1, (
            "setUploadedImage 안에 status=\'preview\' 설정 없음\n"
            f"func_src[:500]:\n{func_src[:500]}"
        )
        assert idx_onload != -1, (
            "setUploadedImage 안에 reader.onload 없음"
        )
        assert idx_preview < idx_onload, (
            f"status='preview' (pos {idx_preview}) 가 reader.onload (pos {idx_onload}) 후에 있음\n"
            "FileReader 비동기 지연 버그: preview 전환이 DataURL 로드 완료를 기다리고 있음"
        )

    @pytest.mark.frontend
    def test_required_methods_exist(self):
        src = read_js('state/appState.js')
        for m in ('startAnalysis', 'completeAnalysis', 'setError', 'reset', 'setAgreement'):
            assert m in src, f"AppState.{m}() 메서드 없음"


# ── 2. UIController ────────────────────────────────────────────────────────────────
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
        assert 'new FileReader' not in src, "uiController 에 FileReader 직접 사용 - appState 에서만 허용"

    @pytest.mark.frontend
    def test_uses_hide_not_reset_for_gradcam(self):
        src = read_js('ui/uiController.js')
        assert ('gradcamViewer?.hide()' in src or 'gradcamViewer.hide()' in src), "gradcamViewer.hide() 호출 없음"
        assert 'gradcamViewer?.reset()' not in src and 'gradcamViewer.reset()' not in src, (
            "gradcamViewer.reset() 호출 - GradCAMViewer.reset() 메서드 없음"
        )


# ── 3. GradCAMViewer ─────────────────────────────────────────────────────────────────
class TestGradCAMViewerExport:

    @pytest.mark.frontend
    def test_is_default_export(self):
        src = read_js('ui/gradcam_viewer.js')
        assert 'export default GradCAMViewer' in src, "gradcam_viewer.js 가 default export 가 아님"

    @pytest.mark.frontend
    def test_has_render_and_hide_no_reset(self):
        src = read_js('ui/gradcam_viewer.js')
        assert 'render(' in src, "GradCAMViewer.render() 없음"
        assert 'hide('   in src, "GradCAMViewer.hide() 없음"
        assert 'reset('  not in src, "GradCAMViewer.reset() 발견 - uiController 호출 시 TypeError"


# ── 4. app.js ───────────────────────────────────────────────────────────────────────
class TestAppJsContract:

    @pytest.mark.frontend
    def test_warmup_failure_does_not_block_predict(self):
        """
        웼업 실패 시 predict 를 throw 로 차단하지 않아야 한다.
        '서버가 아직 준비' 메시지로 throw 하면 안 됨.

        경로 주의: app.js 는 frontend/js/app.js 이므로 read_js('app.js')
        """
        src = read_js('app.js')  # frontend/js/app.js
        has_block = ('throw new Error' in src and
                     ('\uc11c버가 아직 준비' in src or '\uc11c버 준비' in src))
        assert not has_block, (
            "웼업 실패 시 predict 를 throw 로 차단 (서버가 살아있어도 접근 불가 버그)"
        )

    @pytest.mark.frontend
    def test_subscribes_to_appstate(self):
        """app.js 가 appState.subscribe() 를 호출해야 한다"""
        src = read_js('app.js')  # frontend/js/app.js
        assert 'appState.subscribe' in src, "app.js 에서 appState 구독 없음"

    @pytest.mark.frontend
    def test_calls_warmup(self):
        """app.js 가 warmUpServer() 를 호출해야 한다"""
        src = read_js('app.js')  # frontend/js/app.js
        assert 'warmUpServer()' in src, "app.js 에서 warmUpServer() 호출 없음"
