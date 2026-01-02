# convert_to_onnx.py
import tensorflow as tf
import tf2onnx

# 로드할 Keras 모델 경로
keras_model_path = "keras_model.h5"
# 저장할 ONNX 모델 경로
onnx_model_path = "model.onnx"

# Keras 모델 로드
try:
    model = tf.keras.models.load_model(keras_model_path, compile=False)
    print("Keras 모델을 성공적으로 로드했습니다.")
    
    # ONNX로 변환 (opset=13은 안정적인 버전)
    # input_signature는 모델의 입력 형태를 명시해줌
    input_signature = [tf.TensorSpec(model.inputs[0].shape, model.inputs[0].dtype, name="input_1")]
    onnx_model, _ = tf2onnx.convert.from_keras(model, input_signature, opset=13)
    
    # ONNX 모델 파일로 저장
    with open(onnx_model_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
        
    print(f"모델이 성공적으로 '{onnx_model_path}'로 변환 및 저장되었습니다.")

except Exception as e:
    print(f"모델 변환 중 오류 발생: {e}")