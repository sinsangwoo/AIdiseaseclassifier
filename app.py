from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
# 가장 기본적인 CORS 설정
CORS(app)

@app.route('/')
def home():
    return "백엔드 서버가 정상적으로 작동 중입니다."

@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    # 실제 분석 대신, 항상 똑같은 성공 메시지를 반환
    print("'/predict' 경로로 요청이 성공적으로 들어왔습니다.")
    
    # 실제 Teachable Machine 모델의 출력과 유사한 가짜 데이터
    dummy_predictions = [
        {'className': '정상', 'probability': 0.3},
        {'className': '폐렴', 'probability': 0.7}
    ]
    return jsonify({'predictions': dummy_predictions})

if __name__ == '__main__':
    app.run()