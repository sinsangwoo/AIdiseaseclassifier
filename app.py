"""
Root-level Flask application wrapper.

Render 대시보드가 render.yaml을 무시하고 이 파일을 직접 실행합니다.
→ 여기서 환경변수를 설정한 뒤 backend.app을 호출하면 모든 환경에서 CORS가 보장됩니다.
"""

import os

# Render 환경변수를 몍지리 강제 주입
# render.yaml의 envVars가 적용되기 전에 이 모듈이 실행되므로
# 코드 레벨에서 직접 설정합니다.
if not os.environ.get('FLASK_ENV'):
    # RENDER 환경변수가 있으면 프로덕션, 없으면 개발
    if (
        os.environ.get('RENDER')
        or os.environ.get('RENDER_SERVICE_ID')
        or os.environ.get('RENDER_EXTERNAL_URL')
        or os.environ.get('IS_RENDER')  # 추가 fallback
    ):
        os.environ['FLASK_ENV'] = 'production'
    # RENDER 환경변수도 없으면: 코드 내에서는 판단 불가 → CORS_ORIGINS가 * 이므로 무관

# CORS_ORIGINS를 코드 레벨에서 '*' 로 강제 설정
# (render.yaml envVars 가 적용안 될 수 있으므로 코드에서 보장)
os.environ.setdefault('CORS_ORIGINS', '*')

from backend.app import app  # noqa: E402  (import 순서 유지를 위해 환경변수 설정 후 import)

if __name__ == '__main__':
    app.run()
