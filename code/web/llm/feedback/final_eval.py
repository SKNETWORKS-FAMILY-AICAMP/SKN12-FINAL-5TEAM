"""
실시간 면접 평가 시스템 - 최종 평가 모듈

이 모듈은 realtime_result.json에 누적된 개별 평가 결과를 바탕으로
최종 통합 평가를 수행하여 final_evaluation_results.json을 생성합니다.

주요 기능:
1. 실시간 결과를 최종 평가 형태로 변환 (ML점수 + LLM평가 → 통합 점수)
2. 개별 질문별 최종 점수, 의도, 평가, 개선사항 생성
3. 전체 면접에 대한 종합 평가 및 점수 산출

작성자: AI Assistant  
"""

from openai import OpenAI
import json
import re
import os
import datetime
import statistics
from num_eval import score_interview_data, load_interview_data, load_encoder, load_model
from text_eval import evaluate_all

client = OpenAI()

# 최종 평가용 모델 설정 (개별 평가와 다른 모델 사용 가능)
FINAL_EVAL_MODEL = "gpt-4o"  # 또는 "gpt-4", "gpt-3.5-turbo", "claude-3-sonnet" 등
OVERALL_EVAL_MODEL = "gpt-4o"  # 전체 종합 평가용 모델 (다시 다른 모델 가능)

# === 핸수 정의 섹션 ===

def build_final_prompt(q, a, ml_score, llm_feedback, existing_intent):
    """
    개별 질문에 대한 최종 통합 평가 프롬프트 생성
    
    Args:
        q (str): 면접 질문
        a (str): 지원자 답변
        ml_score (float): ML 모델 예측 점수
        llm_feedback (str): LLM에서 생성된 상세 평가 결과
        existing_intent (str): text_eval.py에서 이미 추출된 질문 의도
        
    Returns:
        str: GPT-4o에게 전달할 프롬프트
    """
    return fr"""
[질문]: {q}
[답변]: {a}
[질문 의도]: {existing_intent}
[머신러닝 점수]: {ml_score:.1f} (ML 모델 예측 점수, 일반적 범위: 10~50점)
[LLM 평가결과]: {llm_feedback}

위 정보를 바탕으로 아래 항목을 작성해주세요.

1. 💬 평가: 답변의 강점과 약점을 구체적으로 분석해주세요. 핵심 요소가 누락되었거나 부족한 경우 분명히 지적해주세요. **답변에서 반말이나 예의 없는 표현을 사용했다면 이는 면접에서 절대 용납될 수 없는 중대한 문제점으로 강하게 지적해주세요.** 평가는 전문적이면서도 일관된 어조로 작성해주세요.
2. 🔧 개선 방법: 면접자가 답변을 어떻게 보완하면 좋을지 구체적이고 실용적인 방법을 제시해주세요. 개선 제안은 건설적이고 실행 가능한 조언으로 작성해주세요.
3. [최종 점수]: 100점 만점 기준으로 정수 점수를 부여해주세요. 점수를 후하게 주지 말고 냉정하게 판단해주세요. **답변에서 반말이나 예의 없는 표현(~해, ~야, ~다 등)을 사용했다면 점수를 반으로 깎되 소수점은 버리고 정수로 처리해주세요.**
"""

def call_llm(prompt):
    """
    OpenAI GPT-4o를 호출하여 평가 결과 생성
    
    Args:
        prompt (str): GPT-4o에게 전달할 프롬프트
        
    Returns:
        str: GPT-4o의 응답 텍스트
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "당신은 전문적인 인사 담당자입니다. 일관된 어조와 말투로 평가와 피드백을 제공해주세요. 반드시 출력 형식을 지켜주세요."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    return response.choices[0].message.content.strip()

def call_llm_with_ensemble(prompt, num_evaluations=3):
    """
    3번 평가 후 앙상블로 최종 결과 생성
    
    Args:
        prompt (str): GPT-4o에게 전달할 프롬프트
        num_evaluations (int): 평가 횟수 (기본 3회)
        
    Returns:
        dict: {"result": str, "confidence": float, "scores": list}
    """
    print(f"🔄 앙상블 평가 시작 ({num_evaluations}회)")
    
    evaluations = []
    scores = []
    
    # 다중 평가 실행
    for i in range(num_evaluations):
        try:
            result = call_llm(prompt)
            evaluations.append(result)
            
            # 점수 추출
            score_match = re.search(r'\[최종 점수\]:\s*(\d+)', result)
            if score_match:
                score = int(score_match.group(1))
                scores.append(score)
                print(f"  평가 {i+1}: {score}점")
            else:
                print(f"  평가 {i+1}: 점수 추출 실패")
                
        except Exception as e:
            print(f"  평가 {i+1} 실패: {e}")
            continue
    
    if not evaluations:
        print("❌ 모든 평가 실패")
        return {"result": "평가 실패", "confidence": 0.0, "scores": []}
    
    # 점수 안정화
    if scores:
        final_score = int(round(statistics.median(scores)))  # 중앙값으로 변경하고 정수 보장
        score_variance = statistics.variance(scores) if len(scores) > 1 else 0.0
        confidence = max(0.0, min(1.0, 1.0 - score_variance / 100.0))
        
        # 중앙값에 가장 가까운 평가 선택
        best_idx = min(range(len(scores)), key=lambda i: abs(scores[i] - final_score))
        best_evaluation = evaluations[best_idx]
        
        # 점수를 최종 점수로 교체
        final_result = re.sub(
            r'\[최종 점수\]:\s*\d+', 
            f'[최종 점수]: {final_score}', 
            best_evaluation
        )
        
        print(f"✅ 최종 점수: {final_score}점 (신뢰도: {confidence:.2f})")
        print(f"   점수 분포: {scores} → 중앙값: {final_score}")
        
    else:
        # 점수가 없으면 첫 번째 평가 사용
        final_result = evaluations[0]
        confidence = 0.5
        final_score = 50  # 이미 정수
        
        print(f"⚠️ 점수 추출 실패, 기본 평가 사용 (신뢰도: {confidence})")
    
    return {
        "result": final_result,
        "confidence": confidence,
        "scores": scores,
        "final_score": final_score
    }

def parse_llm_result(llm_result):
    """
    GPT-4o의 응답에서 구조화된 정보 추출
    
    Args:
        llm_result (str): GPT-4o의 원시 응답 텍스트
        
    Returns:
        tuple: (최종점수, 평가내용, 개선방안)
    """
    eval_match = re.search(r"1\. 💬 평가:\s*(.+?)\n2\.", llm_result, re.DOTALL)
    improve_match = re.search(r"2\. 🔧 개선 방법:\s*(.+?)\n3\.", llm_result, re.DOTALL)
    score_match = re.search(r"3\. \[최종 점수\]:\s*(\d+)", llm_result)

    evaluation = eval_match.group(1).strip() if eval_match else ""
    improvement = improve_match.group(1).strip() if improve_match else ""
    score = int(score_match.group(1)) if score_match else None

    return score, evaluation, improvement



def build_overall_prompt(final_results):
    per_q = ""
    for i, item in enumerate(final_results, 1):
        per_q += f"{i}. 질문: {item['question']}\n   답변: {item['answer']}\n   점수: {item['final_score']}\n   평가: {item['evaluation']}\n   개선사항: {item['improvement']}\n\n"
    return fr"""
[전체 답변 평가]
아래는 지원자의 각 문항별 답변, 점수, 평가, 개선사항입니다.

{per_q}

위 정보를 종합해 지원자에 대해
- 최종 점수(100점 만점, 정수)
- 전체 피드백(5~10문장, 구체적이고 길게, 전문적이고 일관된 어조로)
- 1줄 요약(한 문장, 임팩트 있게)
를 아래 형식으로 출력하세요.

[최종 점수]: XX
[전체 피드백]: ...
[1줄 요약]: ...
"""

def parse_overall_llm_result(llm_result):
    score_match = re.search(r"\[최종 점수\]:\s*(\d+)", llm_result)
    feedback_match = re.search(r"\[전체 피드백\]:\s*(.+?)(?:\n\[|$)", llm_result, re.DOTALL)
    summary_match = re.search(r"\[1줄 요약\]:\s*(.+)", llm_result)
    score = int(score_match.group(1)) if score_match else None
    feedback = feedback_match.group(1).strip() if feedback_match else ""
    summary = summary_match.group(1).strip() if summary_match else ""
    return score, feedback, summary


def process_realtime_results(realtime_data, company_info):
    """
    실시간 평가 결과를 최종 평가 형태로 변환
    
    Args:
        realtime_data (list): 실시간 결과 데이터
        company_info (dict): DB에서 가져온 회사 정보
        
    Returns:
        list: 최종 평가 형태로 변환된 결과 리스트
    """
    
    final_results = []
    
    # 각 질문에 대해 최종 통합 평가 수행
    for item in realtime_data:
        question = item["question"]
        answer = item["answer"]
        intent = item.get("intent", "")
        ml_score = item.get("ml_score", 0)  # num_eval.py에서 생성된 점수
        llm_evaluation = item.get("llm_evaluation", "")  # text_eval.py에서 생성된 평가
        
        # ML 점수와 LLM 평가를 결합한 최종 통합 평가 (앙상블 적용)
        final_prompt = build_final_prompt(question, answer, ml_score, llm_evaluation, intent)
        ensemble_result = call_llm_with_ensemble(final_prompt)
        
        # 결과에서 구조화된 정보 추출
        final_score, evaluation, improvement = parse_llm_result(ensemble_result["result"])
        
        # 최종 결과 형태로 구성
        final_results.append({
            "question": question,
            "answer": answer,
            "intent": intent,  # text_eval.py에서 이미 추출된 의도 사용
            "final_score": final_score,
            "evaluation": evaluation,
            "improvement": improvement
        })
    
    return final_results

def run_final_evaluation_from_realtime(realtime_data=None, company_info=None, realtime_file="realtime_result.json", output_file="final_evaluation_results.json"):
    """
    실시간 결과를 바탕으로 최종 평가 실행
    
    Args:
        realtime_data (list): 실시간 결과 데이터 (우선순위)
        company_info (dict): DB에서 가져온 회사 정보 (우선순위)
        realtime_file (str): 실시간 결과 파일 경로 (폴백)
        output_file (str): 최종 결과 저장 파일 경로
        
    Returns:
        dict: 최종 평가 결과 (개별+전체)
    """
    print("최종 평가를 시작합니다!")
    
    # 1. 데이터 준비 (메모리 데이터 우선, 파일 폴백)
    if realtime_data is None:
        # 파일에서 읽기 (기존 방식)
        with open(realtime_file, "r", encoding="utf-8") as f:
            realtime_data = json.load(f)
    
    if company_info is None:
        # 파일에서 읽기 (기존 방식)
        with open("company_info.json", "r", encoding="utf-8") as f:
            company_info = json.load(f)
    
    # 2. 실시간 결과를 최종 평가 형태로 변환
    #    (ML점수 + LLM평가 → 통합점수 + 상세평가)
    per_question = process_realtime_results(realtime_data, company_info)
    
    # 3. 전체 면접에 대한 종합 평가 수행 (앙상블 적용)
    overall_prompt = build_overall_prompt(per_question)
    overall_ensemble_result = call_llm_with_ensemble(overall_prompt)
    overall_score, overall_feedback, summary = parse_overall_llm_result(overall_ensemble_result["result"])
    
    # 4. 최종 결과 구성 (기존 포맷과 동일)
    final_results = {
        "per_question": per_question,      # 개별 질문 평가 결과
        "overall_score": overall_score,    # 전체 점수
        "overall_feedback": overall_feedback,  # 전체 피드백
        "summary": summary                 # 1줄 요약
    }
    
    # 5. JSON 파일로 저장 (output_file이 제공된 경우에만)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_results, f, ensure_ascii=False, indent=2)
        print(f"결과는 '{output_file}'에 저장되었습니다!")
    
    print(f"최종 평가 완료! 점수: {overall_score}/100")
    
    return final_results

if __name__ == "__main__":
    # 기존 batch 평가 방식
    # run_final_eval("interview_data.json")
    
    # 새로운 실시간 결과 기반 최종 평가
    if os.path.exists("realtime_result.json"):
        run_final_evaluation_from_realtime()
    else:
        print("realtime_result.json 파일이 없습니다. process_single_qa.py를 먼저 실행하세요.")