## 🧠 AI 폐렴 진단 시스템 (AI Pneumonia Diagnosis System)
## 📌 프로젝트 개요
“기술로 생명을 구할 수 있을까?”
이 프로젝트는 흉부 X-ray 이미지를 분석해 폐렴 여부를 예측하는 AI 기반 웹 서비스 프로토타입입니다.

Teachable Machine으로 학습한 모델을 .h5 형식으로 저장하고, Python Flask 백엔드와 연결하여 웹 인터페이스 상에서 이미지 업로드 → 분석 → 결과 확인 → 저장까지 한 번에 이뤄지는 진단 흐름을 구현했습니다.

단순한 기술 구현을 넘어, AI의 실제 응용 가능성, 사용자 경험(UX), 그리고 기술 윤리까지 고려하며 개발한 프로젝트입니다.

## 🔍 주요 기능
🖼 X-ray 이미지 업로드 – 클릭/드래그로 손쉽게 이미지 업로드

🤖 AI 기반 폐렴 분석 – Flask 백엔드를 통해 실시간 예측 수행

📊 게이지 차트 시각화 – Chart.js로 예측 확률을 직관적으로 시각화

💬 동적 분석 코멘트 – 신뢰도에 따라 위험도 안내 메시지 자동 출력

📥 진단 리포트 저장 – 결과를 PNG 또는 PDF로 저장 가능 (html2canvas, jsPDF)

⚠️ 윤리적 책임 고지 – '분석 동의 체크박스'를 통해 사용자의 명시적 동의 확보

## 🛠 사용 기술 스택
분야	기술
AI 모델링	Teachable Machine, TensorFlow, Keras
백엔드	Python, Flask, Flask-CORS
프론트엔드	HTML5, CSS3, JavaScript
시각화 & 저장	Chart.js, html2canvas, jsPDF
환경 구성	Python venv, VS Code

## 🧗 개발 여정과 문제 해결
1️⃣ 환경 설정 – 가상 환경과 버전 충돌 해결
문제: TensorFlow 등 주요 라이브러리의 버전 충돌 발생

해결: venv로 격리된 개발 환경 구성 + requirements.txt로 의존성 고정

배운 점: 환경 격리와 버전 관리의 중요성, 실무형 개발 습관 형성

2️⃣ 백엔드 연동 – Flask의 폴더 구조와 템플릿 규칙 학습
문제: TemplateNotFound 오류 발생

해결: templates/index.html로 파일 위치 수정

배운 점: Flask 웹 프레임워크의 구조적 규칙과 MVC 개념 이해

3️⃣ UI/UX 개선 – 코드보다 사용자를 생각한 설계
기능 추가:

게이지 차트 시각화

분석 신뢰도별 안내 문구 자동 출력

분석 시작 전 체크박스 동의 UI 추가

배운 점: 기술은 사용자에게 전달되어야 의미 있다는 점을 실감

4️⃣ 디버깅 – 코드보다 중요한 '타이밍'과 구조 이해
문제: 버튼 요소 null, 이미지 미표시 등 다양한 버그

해결:

DOMContentLoaded 이벤트로 스크립트 실행 시점 제어

HTML 구조 재정비 + CSS display 속성 명확화

배운 점:

DOM 제어는 구조와 타이밍의 예술

개발자 도구(Console)는 최고의 스승

## 📂 프로젝트 실행 방법
bash
복사
편집
# 1. 저장소 복제
git clone https://github.com/YourUsername/YourRepository.git
cd YourRepository

# 2. 가상 환경 생성 및 활성화
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 3. 필수 패키지 설치
pip install -r requirements.txt

# 4. 서버 실행
python app.py

# 5. 접속
http://127.0.0.1:5000


## 💡 향후 발전 방향
🧪 모델 성능 개선: 데이터 증강 및 클래스 불균형 보정으로 일반화 능력 향상

📱 반응형 UI: 모바일 환경에서도 진단이 가능한 레이아웃 추가

🔐 사용자 인증 기능: 진단 기록 저장을 위한 계정 시스템 도입

☁️ 클라우드 배포: Heroku, Render, AWS 등 클라우드 플랫폼을 통한 실 서비스 구현

📚 진단 이력 리포지토리: 사용자 개인별 진단 이력 저장 및 통계 기능

## 🔎 이 프로젝트가 특별한 이유
단순히 AI 모델을 만든 것이 아닌, 사용자 중심의 실용 가능한 서비스로 연결

버그를 “참고 넘긴 것”이 아닌, 문제의 본질을 분석하고 개선한 경험

Flask의 구조, 가상 환경 구성, 시각화 도구 연동 등 풀스택 사고 훈련

마지막으로, 기술 윤리에 대한 고민과 사용자 고지 절차를 UX에 자연스럽게 녹여냄

## ✍️ 개발자 한마디
이 프로젝트는 단지 코드 몇 줄이 아닌,
“기술은 현실 문제 해결을 위한 도구이며, 사용자를 고려할 때 완성된다”는 교훈을 남겼습니다.

프로그래머는 코드를 넘어, 사회를 설계하는 사람이라는 생각으로 계속 발전해 나가겠습니다.

오늘보다 더 나은 내일을 만들어가도록