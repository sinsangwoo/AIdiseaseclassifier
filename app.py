import os
import io
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import numpy as np
from PIL import Image
import onnxruntime as rt

app = Flask(__name__)

# CORS 설정 개선 - 모든 오리진 허용으로 테스트
CORS(app, origins=['*'], supports_credentials=True)

# --- 설정 ---
MODEL_PATH = 'model.onnx'
LABELS_PATH = 'labels.txt'

# --- 모델 및 레이블 로드 ---
sess = None
class_names = []
input_name = None
output_name = None

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

# 이미지 전처리 함수 (들여쓰기 수정)
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

# 헬스 체크 엔드포인트 추가
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Pneumonia API is running',
        'model_loaded': sess is not None,
        'classes': class_names
    })

# OPTIONS 요청 처리 (CORS preflight)
@app.route('/predict', methods=['OPTIONS'])
def handle_options():
    response = jsonify({'message': 'OK'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    return response

# '/predict' URL로 POST 요청이 오면 이미지 분석 수행
@app.route('/predict', methods=['POST'])
def predict():
    print("🔍 POST 요청 받음")
    
    if sess is None:
        print("❌ 모델이 로드되지 않음")
        return jsonify({'error': '서버에 모델이 로드되지 않았습니다.'}), 500
    
    if 'file' not in request.files:
        print("❌ 파일이 요청에 없음")
        return jsonify({'error': '요청에서 파일을 찾을 수 없습니다.'}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        print("❌ 파일이 선택되지 않음")
        return jsonify({'error': '선택된 파일이 없거나 파일 이름이 없습니다.'}), 400
    
    try:
        print(f"📁 파일 처리 시작: {file.filename}")
        
        # file.stream에서 직접 데이터를 읽어 BytesIO 객체를 생성
        in_memory_file = io.BytesIO()
        file.save(in_memory_file)
        in_memory_file.seek(0)  # 스트림의 포인터를 맨 처음으로 되돌림
        
        # 전처리 함수 호출
        processed_image = preprocess_image(in_memory_file)
        print("✅ 이미지 전처리 완료")
        
        # ONNX 모델로 예측 실행
        predictions = sess.run([output_name], {input_name: processed_image})[0]
        print("✅ 예측 완료")
        
        # 결과 처리
        results = []
        for i, probability in enumerate(predictions[0]):
            results.append({
                'className': class_names[i],
                'probability': float(probability)
            })
        
        print(f"📊 예측 결과: {results}")
        return jsonify({'predictions': results})
        
    except Exception as e:
        # 에러 로그를 더 자세하게 남김
        print(f"❌ 예측 중 심각한 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'이미지 처리 중 예측 불가능한 서버 오류 발생: {str(e)}'}), 500

# 추가 CORS 헤더 설정
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

if __name__ == '__main__':
    # Render에서는 환경변수 PORT를 사용
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)  # 프로덕션에서는 debug=False