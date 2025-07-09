import os
import io
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import numpy as np
from PIL import Image # Pillow 라이브러리 직접 사용
import onnxruntime as rt # onnxruntime 임포트

app = Flask(__name__)
CORS(app)

# --- 설정 ---
MODEL_PATH = 'model.onnx' # ONNX 모델 사용
LABELS_PATH = 'labels.txt'

# --- 모델 및 레이블 로드 ---
sess = None
class_names = []
try:
    # ONNX 런타임 세션 생성
    sess = rt.InferenceSession(MODEL_PATH)
    # 모델의 입력/출력 이름 가져오기
    input_name = sess.get_inputs()[0].name
    output_name = sess.get_outputs()[0].name

    with open(LABELS_PATH, 'r', encoding='utf-8') as f:
        class_names = [line.strip().split(' ', 1)[1] for line in f.readlines()]
    print("✅ ONNX 모델과 레이블이 성공적으로 로드되었습니다.")
    print(f"🔍 인식 가능한 클래스: {class_names}")
except Exception as e:
    print(f"❌ 모델 또는 레이블 로드 실패: {e}")

# 이미지 전처리 함수
def preprocess_image(img_bytes, target_size=(224, 224)):
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    img = img.resize(target_size, Image.LANCZOS)
    img_array = np.array(img).astype('float32')
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0
    return img_array

# --- API 엔드포인트 정의 ---

# '/predict' URL로 POST 요청이 오면 이미지 분석 수행
@app.route('/predict', methods=['POST'])
def predict():
    if sess is None or not class_names:
        return jsonify({'error': '서버에 모델이 로드되지 않았습니다.'}), 500

    if 'file' not in request.files:
        return jsonify({'error': '요청에서 파일을 찾을 수 없습니다.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

    try:
        img_bytes = file.read()
        processed_image = preprocess_image(img_bytes)
        
        # ONNX 모델로 예측 실행
        predictions = sess.run([output_name], {input_name: processed_image})[0]

        # 결과 처리
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