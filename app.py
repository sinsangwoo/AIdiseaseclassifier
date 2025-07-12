import os
import io
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from PIL import Image
import onnxruntime as rt

# -----------------
# 1. Flask 앱 및 CORS 설정
# -----------------
app = Flask(__name__)
# 모든 출처('*')에서 모든 경로('/')로의 요청을 허용하는 가장 확실한 CORS 설정
CORS(app, resources={r"/*": {"origins": "*"}})

# -----------------
# 2. 모델 및 레이블 로드
# -----------------
MODEL_PATH = 'model.onnx'
LABELS_PATH = 'labels.txt'
sess = None
input_name = None
output_name = None
class_names = []

try:
    # ONNX 런타임 세션 생성
    sess = rt.InferenceSession(MODEL_PATH)
    input_name = sess.get_inputs()[0].name
    output_name = sess.get_outputs()[0].name

    with open(LABELS_PATH, 'r', encoding='utf-8') as f:
        class_names = [line.strip().split(' ', 1)[1] for line in f.readlines()]
    
    print("✅ ONNX 모델과 레이블이 성공적으로 로드되었습니다.")
    print(f"   - 모델 입력 이름: {input_name}")
    print(f"   - 모델 출력 이름: {output_name}")
    print(f"   - 인식 가능한 클래스: {class_names}")

except Exception as e:
    print(f"❌ 모델 또는 레이블 로드 중 치명적인 오류 발생: {e}")
    sess = None # 로드 실패 시 sess를 None으로 설정

# -----------------
# 3. 이미지 전처리 함수 (독립적인 위치에 올바른 들여쓰기로 정의)
# -----------------
def preprocess_image(img_bytes_stream, target_size=(224, 224)):
    try:
        img = Image.open(img_bytes_stream)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img = img.resize(target_size, Image.LANCZOS)
        img_array = np.array(img).astype('float32')
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0
        return img_array
    except Exception as e:
        raise IOError(f"Pillow 라이브러리가 이미지를 열 수 없습니다: {e}")

# -----------------
# 4. API 엔드포인트 정의
# -----------------

# 서버 상태 확인을 위한 루트 경로
@app.route('/')
def home():
    return "AI 진단 백엔드 서버가 정상적으로 작동 중입니다."

# 실제 예측을 수행하는 경로
@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    # OPTIONS 요청은 CORS 사전 확인(preflight)을 위한 것이므로, 바로 성공 응답을 보냅니다.
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    # 모델이 로드되지 않았을 경우 에러 응답
    if sess is None:
        print("❌ 요청이 들어왔으나, 서버 모델이 로드되지 않은 상태입니다.")
        return jsonify({'error': '서버의 AI 모델이 준비되지 않았습니다.'}), 503

    # 파일이 없는 경우 에러 응답
    if 'file' not in request.files:
        return jsonify({'error': '요청에 이미지 파일이 없습니다.'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': '선택된 파일이 없거나 파일 이름이 없습니다.'}), 400

    try:
        # 파일 데이터를 메모리 내 스트림으로 복사하고 포인터를 처음으로 되돌립니다.
        in_memory_file = io.BytesIO()
        file.save(in_memory_file)
        in_memory_file.seek(0)
        
        # 이미지 전처리
        processed_image = preprocess_image(in_memory_file)
        
        # ONNX 모델로 예측 실행
        predictions = sess.run([output_name], {input_name: processed_image})[0]

        # 결과 가공
        results = []
        for i, probability in enumerate(predictions[0]):
            results.append({
                'className': class_names[i],
                'probability': float(probability)
            })
        
        print(f"✅ 예측 성공: {results}")
        return jsonify({'predictions': results})

    except Exception as e:
        # 예측 과정에서 발생하는 모든 예외를 잡아서 로그로 남기고 클라이언트에 에러 메시지를 보냅니다.
        print(f"❌ 예측 중 심각한 에러 발생: {e}")
        traceback.print_exc() # 터미널에 상세한 에러 내역 출력
        return jsonify({'error': f'이미지 처리 중 예측 불가능한 서버 오류가 발생했습니다.'}), 500

# -----------------
# 5. 서버 실행 (Gunicorn이 이 파일을 직접 실행하지는 않음)
# -----------------
if __name__ == '__main__':
    # Render에서는 gunicorn을 사용하므로 이 부분은 로컬 테스트 시에만 사용됩니다.
    # 포트를 5000 대신 다른 번호(예: 8080)로 변경하여 충돌을 피할 수 있습니다.
    app.run(host='0.0.0.0', port=8080, debug=True)