import os
import io
import logging
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import numpy as np
from PIL import Image
import onnxruntime as rt

# --- 로깅 설정 ---
# Render 로그에서 더 자세한 정보를 볼 수 있도록 로깅 레벨 설정
logging.basicConfig(level=logging.INFO)

# --- Flask 앱 및 CORS 초기화 ---
app = Flask(__name__)
# CORS를 더 정교하게 설정하여 안정성 확보
# OPTIONS 요청에 대한 사전 처리를 자동으로 수행
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# --- 설정 및 모델 로드 ---
MODEL_PATH = 'model.onnx'
LABELS_PATH = 'labels.txt'
sess = None
class_names = []
input_name = None
output_name = None

try:
    logging.info("ONNX 모델 로드를 시작합니다...")
    sess = rt.InferenceSession(MODEL_PATH)
    input_name = sess.get_inputs()[0].name
    output_name = sess.get_outputs()[0].name
    
    with open(LABELS_PATH, 'r', encoding='utf-8') as f:
        class_names = [line.strip().split(' ', 1)[1] for line in f.readlines()]
    logging.info(f"✅ ONNX 모델과 레이블 로드 성공. 클래스: {class_names}")

except Exception as e:
    logging.error(f"❌ 모델 또는 레이블 로드 실패: {e}", exc_info=True)

# --- 이미지 전처리 함수 ---
def preprocess_image(img_bytes_stream, target_size=(224, 224)):
    try:
        img = Image.open(img_bytes_stream)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img = img.resize(target_size, Image.LANCZOS)
        img_array = np.array(img, dtype=np.float32)
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0
        return img_array
    except Exception as e:
        logging.error(f"Pillow 이미지 처리 중 오류: {e}", exc_info=True)
        raise

# --- API 엔드포인트 ---

@app.route("/")
def health_check():
    """서버가 살아있는지 확인하는 헬스 체크 엔드포인트."""
    logging.info("헬스 체크 요청 수신.")
    return "백엔드 서버가 정상적으로 작동 중입니다."

@app.route("/predict", methods=['POST', 'OPTIONS'])
def predict():
    # OPTIONS 요청은 CORS 핸들러가 자동으로 처리하므로, 바로 성공 응답을 보냅니다.
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    logging.info("/predict POST 요청 수신.")
    if not sess:
        return jsonify({'error': '서버에 모델이 로드되지 않았습니다.'}), 500

    if 'file' not in request.files:
        return jsonify({'error': '요청에서 파일을 찾을 수 없습니다.'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': '파일이 없거나 파일 이름이 없습니다.'}), 400

    try:
        in_memory_file = io.BytesIO()
        file.save(in_memory_file)
        in_memory_file.seek(0)
        
        logging.info("이미지 전처리를 시작합니다...")
        processed_image = preprocess_image(in_memory_file)
        logging.info("이미지 전처리 완료.")

        logging.info("ONNX 모델 예측을 시작합니다...")
        predictions = sess.run([output_name], {input_name: processed_image})[0]
        logging.info("ONNX 모델 예측 완료.")
        
        results = []
        for i, probability in enumerate(predictions[0]):
            results.append({
                'className': class_names[i],
                'probability': float(probability)
            })
        
        logging.info(f"예측 결과 반환: {results}")
        return jsonify({'predictions': results})

    except Exception as e:
        logging.error(f"예측 중 심각한 에러 발생: {e}", exc_info=True)
        return jsonify({'error': f'서버 내부 오류 발생: {e}'}), 500

def _build_cors_preflight_response():
    """CORS 사전 요청(preflight)에 대한 응답을 생성합니다."""
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response

# --- Gunicorn을 통해 실행될 때를 위한 설정 ---
# if __name__ == '__main__' 블록은 Gunicorn 사용 시 필요 없습니다.