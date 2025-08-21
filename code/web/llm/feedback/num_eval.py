import json
import numpy as np
import pandas as pd
from autogluon.tabular import TabularPredictor
from sentence_transformers import SentenceTransformer

# 모델 및 인코더 이름  
import os
MODEL_PATH = os.path.join(os.path.dirname(__file__), "automl")
ENCODER_NAME = "BM-K/KoSimCSE-roberta"
DATA_PATH = "interview_data.json"
OUTPUT_PATH = "scored_results.json"

def load_model(model_path: str):
    return TabularPredictor.load(model_path, require_version_match=False)

def load_encoder(model_name: str):
    return SentenceTransformer(model_name)

def embed_qa_pair(question: str, answer: str, encoder: SentenceTransformer) -> np.ndarray:
    q_emb = encoder.encode(question)
    a_emb = encoder.encode(answer)
    return np.concatenate([q_emb, a_emb]).reshape(1, -1)

def load_interview_data(json_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def score_interview_data(data: list, model, encoder: SentenceTransformer) -> list:
    results = []
    for item in data:
        question = item.get("question", "")
        answer = item.get("answer", "")
        vector = embed_qa_pair(question, answer, encoder)
        columns = [f'f{i}' for i in range(vector.shape[1])]
        df = pd.DataFrame(vector, columns=columns)
        score = model.predict(df)[0]
        results.append({"question": question, "answer": answer, "score": float(score)})
    return results

def save_results(results: list, output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

def evaluate_single_qa(question: str, answer: str, model=None, encoder=None) -> float:
    """단일 질문-답변 쌍의 머신러닝 점수 계산"""
    if model is None:
        model = load_model(MODEL_PATH)
    if encoder is None:
        encoder = load_encoder(ENCODER_NAME)
    
    vector = embed_qa_pair(question, answer, encoder)
    columns = [f'f{i}' for i in range(vector.shape[1])]
    df = pd.DataFrame(vector, columns=columns)
    score = model.predict(df)[0]
    return float(score)

# 이 모듈은 다른 파일에서 import하여 사용됩니다.
# 직접 실행이 필요한 경우 main.py를 사용하세요.
# 모듈 파일 - 직접 실행하지 말고 import해서 사용하세요
