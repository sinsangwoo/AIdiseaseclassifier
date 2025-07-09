import os
import io
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import numpy as np

# Flask 앱 초기화
app = Flask(__name__)
# CORS 설정: 모든 출처에서의 요청을 허용합니다.
CORS(app, resources={r"/predict": {"origins": "*"}})

# --- 설정 ---
MODEL_PATH = 'keras_model.h5'
LABELS_PATH = 'labels.txt'

# --- 모델 및 레이블 로드 (앱 실행 시 한 번만) ---
model = None
class_names = []
try:
    # Teachable Machine 모델은 compile=False 옵션으로 로드하는 것이 안전합니다.
    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    with open(LABELS_PATH, 'r', encoding='utf-8') as f:
        # labels.txt 파일 형식("0 정상", "1 폐렴")을 파싱합니다.
        class_names = [line.strip().split(' ', 1)[1] for line in f.readlines()]
    print("AI 모델과 레이블이 성공적으로 로드되었습니다.")
    print(f"인식 가능한 클래스: {class_names}")
except Exception as e:
    print(f"모델 또는 레이블 로드 실패: {e}")

# 이미지 전처리 함수
def preprocess_image(img_bytes, target_size=(224, 224)):
    # 파일 경로가 아닌 바이트 데이터에서 직접 이미지를 엽니다.
    img = image.load_img(io.BytesIO(img_bytes), target_size=target_size)
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) # 배치 차원 추가
    img_array /= 255.0 # 0-1 스케일링
    return img_array

# --- API 엔드포인트 정의 ---

# 루트 URL ('/') 접속 시 index.html 파일을 렌더링
@app.route('/')
def home():
    return render_template('index.html')

# '/predict' URL로 POST 요청이 오면 이미지 분석 수행
@app.route('/predict', methods=['POST'])
def predict():
    if model is None or not class_names:
        return jsonify({'error': '서버에 모델이 로드되지 않았습니다.'}), 500

    if 'file' not in request.files:
        return jsonify({'error': '요청에서 파일을 찾을 수 없습니다.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

    try:
        # 파일을 디스크에 저장하지 않고 메모리에서 바로 처리하여 효율성 증대
        img_bytes = file.read()
        processed_image = preprocess_image(img_bytes)
        
        # 모델 예측
        predictions = model.predict(processed_image)

        # 예측 결과를 JSON 형식으로 가공
        results = []
        for i, probability in enumerate(predictions[0]):
            results.append({
                'className': class_names[i],
                'probability': float(probability)
            })

        return jsonify({'predictions': results})

    except Exception as e:
        print(f"예측 중 에러 발생: {e}")
        return jsonify({'error': f'이미지 처리 중 서버 오류 발생: {str(e)}'}), 500

# 파이썬 스크립트를 직접 실행했을 때 Flask 서버 구동
if __name__ == '__main__':
    # host='0.0.0.0'은 외부에서도 접속 가능하게 합니다.
    # debug=True는 개발 중 코드 변경 시 서버를 자동 재시작해주는 편리한 기능입니다.
    app.run(host='0.0.0.0', port=5000, debug=True)