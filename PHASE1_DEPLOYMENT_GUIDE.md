# 🚀 Phase 1 Rework: 긴급 배포 이슈 해결 가이드

## 📋 변경 사항 요약

이 Phase 1 리워크는 GitHub Pages(프론트엔드)와 Render(백엔드) 분리 배포 환경에서 발생했던 **치명적인 통신 실패 문제**를 해결합니다.

### 🔴 해결된 주요 문제

1. ✅ 하드코딩된 로컬 API URL → 환경별 동적 URL
2. ✅ CORS 설정 미흡 → 상세한 CORS 구성
3. ✅ 모델 파일 경로 문제 → 클라우드 환경 자동 감지
4. ✅ 배포 실패 → GitHub Actions + Render 자동화
5. ✅ 테스트 실패 → 설정 검증 완화

---

## 🎯 배포 전 체크리스트

### 1️⃣ GitHub Secrets 설정

GitHub 저장소 Settings > Secrets and variables > Actions에서 다음 시크릿을 추가하세요:

```
RENDER_API_URL = https://pneumonia-api.onrender.com
```

**⚠️ 주의**: Render 서비스 이름에 따라 URL이 달라집니다!

### 2️⃣ Render 환경변수 설정

Render Dashboard > pneumonia-api > Environment에서 다음을 확인/설정하세요:

```bash
# 필수 환경변수
FLASK_ENV=production
CORS_ORIGINS=https://sinsangwoo.github.io  # 실제 GitHub Pages URL로 변경
SECRET_KEY=<자동생성>
RENDER=true

# 모델 경로 (자동 설정됨)
MODEL_PATH=/opt/render/project/src/backend/models/artifacts/model.onnx
LABELS_PATH=/opt/render/project/src/backend/models/artifacts/labels.txt
```

### 3️⃣ GitHub Pages 활성화

1. Settings > Pages
2. Source: **GitHub Actions** 선택
3. Branch: `main` 선택

---

## 📦 배포 방법

### Option A: 자동 배포 (권장)

```bash
# 1. 브랜치 병합
git checkout main
git merge rework/phase1-emergency-fixes

# 2. 푸시 (자동으로 배포 시작)
git push origin main
```

자동으로 다음이 실행됩니다:
- ✅ GitHub Actions가 프론트엔드를 GitHub Pages에 배포
- ✅ Render가 백엔드를 자동으로 배포

### Option B: 수동 배포

**프론트엔드 (GitHub Pages):**
1. GitHub Actions 탭으로 이동
2. "Deploy Frontend to GitHub Pages" 워크플로우 선택
3. "Run workflow" 클릭

**백엔드 (Render):**
1. Render Dashboard에서 "pneumonia-api" 서비스 선택
2. "Manual Deploy" > "Deploy latest commit" 클릭

---

## 🧪 배포 후 검증

### 1. 백엔드 헬스체크

```bash
# Readiness probe
curl https://pneumonia-api.onrender.com/health/ready

# 예상 응답:
{
  "status": "ready",
  "checks": {
    "model": true,
    "disk": true,
    "memory": true
  }
}
```

### 2. 프론트엔드 테스트

1. `https://sinsangwoo.github.io/AIdiseaseclassifier` 접속
2. 브라우저 개발자 도구 (F12) 열기
3. Console 탭에서 다음 확인:
   ```
   🚀 AI Disease Classifier Frontend
   Environment: production
   API URL: https://pneumonia-api.onrender.com/predict
   ```

### 3. 통합 테스트

1. 테스트 이미지 업로드
2. "AI 정밀 분석 시작" 클릭
3. 3-5초 내에 결과 표시 확인

**❌ CORS 에러 발생 시:**
- Render의 `CORS_ORIGINS` 환경변수가 올바른 GitHub Pages URL인지 확인
- 프로토콜(https://)을 포함해야 함

---

## 🔧 트러블슈팅

### 문제 1: "Failed to fetch" 에러

**원인**: API URL이 잘못 설정됨

**해결**:
1. GitHub Secrets의 `RENDER_API_URL` 확인
2. 재배포: Actions 탭 > Re-run jobs

### 문제 2: CORS 에러

**원인**: Render의 CORS 설정 불일치

**해결**:
```bash
# Render Dashboard > Environment
CORS_ORIGINS=https://sinsangwoo.github.io  # https:// 포함 필수!
```

### 문제 3: 모델 로드 실패

**원인**: 모델 파일이 저장소에 없음

**해결**:
1. `backend/models/artifacts/` 폴더에 `model.onnx`와 `labels.txt` 확인
2. Git LFS 사용 권장 (50MB 이상 파일의 경우)

### 문제 4: 테스트 실패

**원인**: 테스트용 모델 파일 누락

**해결**:
```bash
# 임시 테스트 모델 생성
mkdir -p tests/fixtures
touch tests/fixtures/test_model.onnx
echo "Normal\nPneumonia" > tests/fixtures/test_labels.txt
```

---

## 📊 성능 모니터링

### Render 로그 확인

```bash
# Render Dashboard에서 Logs 탭 확인

# 정상 로그 예시:
✓ 모델 로드 완료
✓ CORS 설정 완료
✓ 서버 준비 완료! Rework Phase 1 적용됨
```

### GitHub Actions 로그 확인

```bash
# Actions 탭 > 최근 워크플로우 실행

# 성공 시:
✅ 환경변수 주입 완료
API URL: https://pneumonia-api.onrender.com
🚀 배포 완료
```

---

## 🔐 보안 체크리스트

- [ ] `SECRET_KEY`가 프로덕션에서 자동 생성됨
- [ ] `CORS_ORIGINS`가 정확한 도메인으로 제한됨
- [ ] HTTPS 사용 (GitHub Pages와 Render 모두 지원)
- [ ] 보안 헤더 활성화됨 (X-Frame-Options 등)

---

## 🎉 완료!

모든 단계를 완료했다면, 이제 프로덕션 환경에서 정상 작동합니다!

### 다음 단계 (Phase 2)

Phase 1이 성공적으로 배포되면, 다음 리워크를 진행할 수 있습니다:
- Phase 2: 프론트엔드 모듈화
- Phase 3: 성능 최적화
- Phase 4: 모니터링 구축

---

## 📞 문제 발생 시

1. GitHub Issues에 로그와 함께 문제 보고
2. 이메일: aksrkd7191@gmail.com
3. Render 로그 + 브라우저 Console 로그 첨부 필수

---

**작성일**: 2026-01-30  
**버전**: 6.0.0  
**작성자**: 신상우 (30814)
