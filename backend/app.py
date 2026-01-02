import os
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from PIL import Image
import onnxruntime as rt

# --- Flask 앱 및 CORS 초기화 ---
app = Flask(__name__)
# 가장 광범위하고 단순한 CORS 설정
CORS(app) 

# --- 설정 및 모델 로드 ---
MODEL_PATH = 'model.onnx'
LABELS_PATH = 'labels.txt'
sess = None
class_names = []
input_name = None
output_name = None

try:
    print("서버 시작: ONNX 모델 로드를 시도합니다...")
    sess = rt.InferenceSession(MODEL_PATH)
    input_name = sess.get_inputs()[0].name
    output_name = sess.get_outputs()[0].name
    
    with open(LABELS_PATH, 'r', encoding='utf-8') as f:
        class_names = [line.strip().split(' ', 1)[1] for line in f.readlines()]
    print(f"모델과 레이블 로드 성공. 클래스: {class_names}")
except Exception as e:
    print(f"모델 또는 레이블 로드 실패: {e}")

# --- 이미지 전처리 함수 ---
def preprocess_image(img_bytes_stream, target_size=(224, 224)):
    img = Image.open(img_bytes_stream)
    if img.mode != "RGB":
        img = img.convert("RGB")
    img = img.resize(target_size, Image.LANCZOS)
    img_array = np.array(img, dtype=np.float32)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0
    return img_array

# --- API 엔드포인트 ---

@app.route("/")
def health_check():
    # 서버가 살아있는지 Render가 확인할 수 있는 간단한 응답
    return "AI 진단 서버가 작동 중입니다."

@app.route("/predict", methods=['POST'])
def predict():
    print("'/predict' 경로로 POST 요청을 받았습니다.")
    if not sess:
        return jsonify({'error': '서버에 모델이 아직 준비되지 않았습니다.'}), 500

    if 'file' not in request.files:
        return jsonify({'error': '요청에 파일이 없습니다.'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': '파일이 비어있거나 파일 이름이 없습니다.'}), 400
    
    print(f"파일 수신: {file.filename}")

    try:
        in_memory_file = io.BytesIO()
        file.save(in_memory_file)
        in_memory_file.seek(0)
        
        processed_image = preprocess_image(in_memory_file)
        predictions = sess.run([output_name], {input_name: processed_image})[0]
        
        results = []
        for i, probability in enumerate(predictions[0]):
            results.append({
                'className': class_names[i],
                'probability': float(probability)
            })
        
        print(f"예측 성공: {results}")
        return jsonify({'predictions': results})

    except Exception as e:
        print(f"❌ 예측 중 심각한 오류 발생: {e}")
        return jsonify({'error': f'서버 내부 오류: 이미지를 처리할 수 없습니다. {e}'}), 500