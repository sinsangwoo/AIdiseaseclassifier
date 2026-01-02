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

# --- API 엔드포인트 정의 ---

# '/predict' URL로 POST 요청이 오면 이미지 분석 수행
@app.route('/predict', methods=['POST'])
def predict():
    if sess is None:
        return jsonify({'error': '서버에 모델이 로드되지 않았습니다.'}), 500

    if 'file' not in request.files:
        return jsonify({'error': '요청에서 파일을 찾을 수 없습니다.'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': '선택된 파일이 없거나 파일 이름이 없습니다.'}), 400

    try:
        # ✅ file.stream에서 직접 데이터를 읽어 BytesIO 객체를 생성합니다.
        # 이것이 file.read()보다 더 안정적일 수 있습니다.
        in_memory_file = io.BytesIO()
        file.save(in_memory_file)
        in_memory_file.seek(0) # 스트림의 포인터를 맨 처음으로 되돌립니다. (매우 중요!)

        # 전처리 함수 호출
        processed_image = preprocess_image(in_memory_file)
        
        # ONNX 모델로 예측 실행
        predictions = sess.run([output_name], {input_name: processed_image})[0]

        # ... (결과 처리 부분은 그대로) ...
        results = []
        for i, probability in enumerate(predictions[0]):
            results.append({
                'className': class_names[i],
                'probability': float(probability)
            })
        return jsonify({'predictions': results})
    
    except Exception as e:
        # 에러 로그를 더 자세하게 남깁니다.
        print(f"예측 중 심각한 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'이미지 처리 중 예측 불가능한 서버 오류 발생: {e}'}), 500
    
# 이미지 전처리 함수
def preprocess_image(img_bytes_stream, target_size=(224, 224)):
    try:
        img = Image.open(img_bytes_stream) # 이제 스트림 객체를 직접 받습니다.
        if img.mode != "RGB":
            img = img.convert("RGB")
        img = img.resize(target_size, Image.LANCZOS)
        img_array = np.array(img).astype('float32')
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0
        return img_array
    except Exception as e:
        raise IOError(f"Pillow 라이브러리가 이미지를 열 수 없습니다: {e}")

# 파이썬 스크립트를 직접 실행했을 때 Flask 서버 구동
if __name__ == '__main__':
    # host='0.0.0.0'은 외부에서도 접속 가능하게 합니다.
    # debug=True는 개발 중 코드 변경 시 서버를 자동 재시작해주는 편리한 기능입니다.
    app.run(host='0.0.0.0', port=5000, debug=True)