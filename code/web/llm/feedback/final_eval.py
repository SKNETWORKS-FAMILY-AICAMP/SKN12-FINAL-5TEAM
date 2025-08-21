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
from .num_eval import score_interview_data, load_interview_data, load_encoder, load_model
from .text_eval import evaluate_all

client = OpenAI()

# 최종 평가용 모델 설정 (개별 평가와 다른 모델 사용 가능)
FINAL_EVAL_MODEL = "gpt-4o"  # 또는 "gpt-4", "gpt-3.5-turbo", "claude-3-sonnet" 등
OVERALL_EVAL_MODEL = "gpt-4o"  # 전체 종합 평가용 모델 (다시 다른 모델 가능)

# === 핸수 정의 섹션 ===

def build_final_prompt(q, a, ml_score, llm_feedback, existing_intent, company_info=None, position_info=None, posting_info=None, resume_info=None):
    """
    개별 질문에 대한 최종 통합 평가 프롬프트 생성
    
    Args:
        q (str): 면접 질문
        a (str): 지원자 답변
        ml_score (float): ML 모델 예측 점수
        llm_feedback (str): LLM에서 생성된 상세 평가 결과
        existing_intent (str): text_eval.py에서 이미 추출된 질문 의도
        company_info (dict): 회사 정보
        position_info (dict): 직군 정보
        posting_info (dict): 공고 정보
        resume_info (dict): 이력서 정보
        
    Returns:
        str: GPT-4o에게 전달할 프롬프트
    """
    # 추가 정보 섹션들 구성
    additional_context = ""
    
    if company_info:
        additional_context += f"""
[회사 정보]:
- 회사명: {company_info.get('name', 'N/A')}
- 인재상: {company_info.get('talent_profile', 'N/A')}
- 핵심역량: {', '.join(company_info.get('core_competencies', []))}
- 기술 중점: {', '.join(company_info.get('tech_focus', []))}
"""
    
    if position_info:
        additional_context += f"""
[💼 지원 직군 정보]:
지원자가 지원한 직군: "{position_info.get('position_name', 'N/A')}"
→ 해당 직군의 전문성과 요구사항을 고려하여 평가하세요.
"""
    
    if posting_info:
        content = posting_info.get('content', 'N/A')
        if len(content) > 250:
            content = content[:250] + "..."
        additional_context += f"""
[📢 채용 공고 정보]:
공고 주요 내용: {content}
→ 공고 요구사항과 지원자 답변의 적합성을 평가하세요.
"""
    
    if resume_info:
        resume_type = "AI 생성 이력서" if 'ai_resume_id' in resume_info else "지원자 제출 이력서"
        career = resume_info.get('career', 'N/A')
        if len(career) > 150:
            career = career[:150] + "..."
        additional_context += f"""
[📄 {resume_type} 정보]:
- 학력: {resume_info.get('academic_record', 'N/A')}
- 경력: {career}
- 기술: {resume_info.get('tech', 'N/A')}
→ 이력서 내용과 답변의 일관성을 평가하세요.
"""

    return fr"""
[질문]: {q}
[답변]: {a}
[질문 의도]: {existing_intent}
[머신러닝 점수]: {ml_score:.1f} (ML 모델 예측 점수, 일반적 범위: 10~50점)
[LLM 평가결과]: {llm_feedback}
{additional_context}

위 정보를 바탕으로 회사, 직군, 공고, 이력서 정보를 종합적으로 고려하여 아래 항목을 작성해주세요.

**중요 지침**: 
- LLM 평가결과에 이미 반말 감지 및 적절한 감점이 적용되었습니다
- 독자적으로 언어 사용이나 예의 관련 판단을 하지 마세요
- 제공된 LLM 평가결과를 신뢰하고 이를 바탕으로 종합 평가하세요

1. 💬 평가: 답변의 강점과 약점을 구체적으로 분석해주세요. 핵심 요소가 누락되었거나 부족한 경우 분명히 지적해주세요. 평가는 전문적이면서도 일관된 어조로 작성해주세요.

2. 🔧 개선 방법: 면접자가 답변을 어떻게 보완하면 좋을지 구체적이고 실용적인 방법을 제시해주세요. 개선 제안은 건설적이고 실행 가능한 조언으로 작성해주세요.

3. [최종 점수]: 100점 만점 기준으로 정수 점수를 부여해주세요. 점수를 후하게 주지 말고 냉정하게 판단해주세요.
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
            {"role": "system", "content": "당신은 전문적인 인사 담당자입니다. 제공된 정보를 바탕으로 객관적이고 일관된 평가를 수행해주세요. 반드시 출력 형식(1. 💬 평가, 2. 🔧 개선 방법, 3. [최종 점수])을 지켜주세요. 독자적으로 언어 사용이나 예의를 판단하지 말고, 이미 처리된 LLM 평가결과를 신뢰하고 이를 바탕으로 종합 평가만 수행하세요."},
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
            
            # 점수 추출 (강화된 패턴 - 더 많은 경우의 수 처리)
            score_match = (
                # 기본 형식들
                re.search(r'3\.\s*\[최종\s*점수\]:\s*(\d+)', result, re.IGNORECASE) or
                re.search(r'\[최종\s*점수\]:\s*(\d+)', result, re.IGNORECASE) or
                re.search(r'최종\s*점수\s*:\s*(\d+)', result, re.IGNORECASE) or
                re.search(r'final\s*score\s*:\s*(\d+)', result, re.IGNORECASE) or
                # 숫자만 있는 경우들
                re.search(r'점수:\s*(\d+)', result) or
                re.search(r'총점:\s*(\d+)', result) or
                re.search(r'점\s*:\s*(\d+)', result) or
                re.search(r'(\d+)\s*점', result) or
                # 마지막 폴백: 0-100 사이 숫자
                re.search(r'\b([0-9]{1,2}|100)\b(?=\s*[점분/]|$)', result)
            )
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
        # 점수 추출 실패 시 오류 발생
        print("❌ 점수 추출 완전 실패")
        raise ValueError(f"점수 추출 실패: 모든 평가에서 점수를 추출할 수 없습니다. 평가 결과: {evaluations[:100] if evaluations else 'None'}...")
    
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
    eval_match = re.search(r"1\. 💬 평가:\s*(.+?)(?:\n2\.|$)", llm_result, re.DOTALL)
    improve_match = re.search(r"2\. 🔧 개선 방법:\s*(.+?)(?:\n3\.|$)", llm_result, re.DOTALL)
    # 점수 추출 (강화된 패턴)
    score_match = (
        re.search(r"3\.\s*\[최종\s*점수\]:\s*(\d+)", llm_result, re.IGNORECASE) or
        re.search(r"\[최종\s*점수\]:\s*(\d+)", llm_result, re.IGNORECASE) or
        re.search(r"최종\s*점수\s*:\s*(\d+)", llm_result, re.IGNORECASE) or
        re.search(r"(\d+)\s*점", llm_result) or
        re.search(r"\b([0-9]{1,2}|100)\b(?=\s*[점분/]|$)", llm_result)
    )

    evaluation = eval_match.group(1).strip() if eval_match else "평가 내용을 추출할 수 없습니다."
    improvement = improve_match.group(1).strip() if improve_match else "개선 방법을 추출할 수 없습니다."
    
    # 점수 추출 실패 시 오류 발생
    if not score_match:
        raise ValueError(f"점수 추출 실패: LLM 응답에서 점수를 찾을 수 없습니다. 응답 내용: {llm_result[:200]}...")
    
    score = int(score_match.group(1))

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
    # 점수 추출 (강화된 패턴)
    score_match = (
        re.search(r"\[최종\s*점수\]:\s*(\d+)", llm_result, re.IGNORECASE) or
        re.search(r"최종\s*점수\s*:\s*(\d+)", llm_result, re.IGNORECASE) or
        re.search(r"총점\s*:\s*(\d+)", llm_result) or
        re.search(r"(\d+)\s*점", llm_result) or
        re.search(r"\b([0-9]{1,2}|100)\b(?=\s*[점분/]|$)", llm_result)
    )
    feedback_match = re.search(r"\[전체\s*피드백\]:\s*(.+?)(?:\n\[|$)", llm_result, re.DOTALL | re.IGNORECASE)
    summary_match = re.search(r"\[1줄\s*요약\]:\s*(.+)", llm_result, re.IGNORECASE)
    score = int(score_match.group(1)) if score_match else None
    feedback = feedback_match.group(1).strip() if feedback_match else ""
    summary = summary_match.group(1).strip() if summary_match else ""
    return score, feedback, summary


def process_realtime_results(realtime_data, company_info, position_info=None, posting_info=None, resume_info=None):
    """
    실시간 평가 결과를 최종 평가 형태로 변환
    
    Args:
        realtime_data (list): 실시간 결과 데이터
        company_info (dict): DB에서 가져온 회사 정보
        position_info (dict): 직군 정보
        posting_info (dict): 공고 정보
        resume_info (dict): 이력서 정보
        
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
        final_prompt = build_final_prompt(question, answer, ml_score, llm_evaluation, intent, company_info, position_info, posting_info, resume_info)
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

def run_final_evaluation_from_realtime(realtime_data=None, company_info=None, position_info=None, posting_info=None, resume_info=None, realtime_file="realtime_result.json", output_file="final_evaluation_results.json"):
    """
    실시간 결과를 바탕으로 최종 평가 실행
    
    Args:
        realtime_data (list): 실시간 결과 데이터 (우선순위)
        company_info (dict): DB에서 가져온 회사 정보 (우선순위)
        position_info (dict): 직군 정보
        posting_info (dict): 공고 정보
        resume_info (dict): 이력서 정보
        realtime_file (str): 실시간 결과 파일 경로 (폴백)
        output_file (str): 최종 결과 저장 파일 경로
        
    Returns:
        dict: 최종 평가 결과 (개별+전체)
    """
    print("최종 평가를 시작합니다!")
    
    # 1. 데이터 검증 (필수 데이터)
    if realtime_data is None:
        raise ValueError("realtime_data는 필수 파라미터입니다. 메모리에서 전달되어야 합니다.")
    
    if company_info is None:
        raise ValueError("company_info는 필수 파라미터입니다. DB에서 조회된 데이터를 전달해야 합니다.")
    
    # 2. 실시간 결과를 최종 평가 형태로 변환
    #    (ML점수 + LLM평가 → 통합점수 + 상세평가)
    per_question = process_realtime_results(realtime_data, company_info, position_info, posting_info, resume_info)
    
    # 3. 전체 면접에 대한 종합 평가 수행 (앙상블 적용)
    overall_prompt = build_overall_prompt(per_question)
    overall_ensemble_result = call_llm_with_ensemble(overall_prompt)
    overall_score, overall_feedback, summary = parse_overall_llm_result(overall_ensemble_result["result"])
    
    # 4. 최종 결과 구성 (기존 포맷과 동일)
    final_results = {
        "success": True,                   # 성공 플래그 추가
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

# 모듈 파일 - API를 통해 run_final_evaluation_from_realtime() 함수를 호출하여 사용하세요