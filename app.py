import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import numpy as np

app = Flask(__name__)
CORS(app) # 모든 경로에 대해 CORS 허용. 실제 서비스에서는 특정 Origin만 허용하도록 설정하는 것이 안전합니다.

# 모델 로드 (앱 시작 시 한 번만 로드)
MODEL_PATH = 'keras_model.h5' 

try:
    model = tf.keras.models.load_model(MODEL_PATH)
    # Teachable Machine 모델은 일반적으로 input_shape이 (1, width, height, 3) 또는 (width, height, 3)
    # 이며, input_shape을 알면 더 정확하게 로드할 수 있습니다.
    # 만약 모델 로드에 문제가 있다면, Teachable Machine에서 내보낸 코드 예제를 확인하세요.
    print(f"모델 '{MODEL_PATH}'이(가) 성공적으로 로드되었습니다.")
except Exception as e:
    print(f"모델 로드 실패: {e}")
    model = None # 모델 로드 실패 시, predict 함수에서 오류를 방지하기 위함

# 이미지 전처리 함수 (Teachable Machine 모델의 입력 요구사항에 맞춰야 합니다)
def preprocess_image(img_path, target_size=(224, 224)): # Teachable Machine 기본 입력 사이즈 224x224
    img = image.load_img(img_path, target_size=target_size)
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) # 배치 차원 추가 (1, 224, 224, 3)
    # 모델에 따라 0-1 스케일링이 필요할 수 있습니다. Teachable Machine의 경우 일반적으로 255로 나눕니다.
    img_array = img_array / 255.0
    return img_array

@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({'error': 'AI 모델이 로드되지 않았습니다.'}), 500

    if 'file' not in request.files:
        return jsonify({'error': '이미지 파일이 없습니다.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '선택된 파일이 없습니다.'}), 400

    if file:
        try:
            # 파일을 임시로 저장하거나 바로 처리
            # Teachable Machine 모델에 따라 이미지 전처리 방식이 다를 수 있습니다.
            # 여기서는 파일 시스템에 임시 저장 후 로드하는 방식을 사용
            filepath = os.path.join("uploads", file.filename) # 'uploads' 폴더 미리 생성
            os.makedirs("uploads", exist_ok=True)
            file.save(filepath)

            processed_image = preprocess_image(filepath)
            predictions = model.predict(processed_image)

            # Teachable Machine metadata.json에서 클래스 이름 가져오기 (선택 사항)
            # metadata.json 파일에서 직접 클래스 이름을 파싱하여 사용하는 것이 가장 정확합니다.
            # 예시: Teachable Machine 모델은 보통 0: Normal, 1: Pneumonia 이런 식으로 클래스를 예측합니다.
            class_names = ["Normal", "Pneumonia"] # 실제 모델의 클래스 이름으로 대체하세요

            # 예측 결과 처리
            results = []
            for i, p in enumerate(predictions[0]):
                results.append({
                    'className': class_names[i] if i < len(class_names) else f'Class {i}',
                    'probability': float(p)
                })

            # 임시 파일 삭제 (선택 사항)
            os.remove(filepath)

            return jsonify({'predictions': results})

        except Exception as e:
            print(f"예측 중 에러 발생: {e}")
            return jsonify({'error': f'이미지 처리 및 예측 중 오류 발생: {str(e)}'}), 500

if __name__ == '__main__':
    # Flask 서버 실행
    # debug=True는 개발 중 편의를 위함이며, 실제 배포 시에는 False로 설정해야 합니다.
    # host='0.0.0.0'은 외부 접속을 허용합니다 (필요에 따라 localhost만 허용할 수 있습니다).
    app.run(debug=True, host='0.0.0.0', port=5000) # 포트 번호는 자유롭게 설정 가능