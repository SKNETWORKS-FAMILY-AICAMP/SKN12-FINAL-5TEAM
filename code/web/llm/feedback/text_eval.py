from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from typing import List, Dict
import time
import re
import statistics

load_dotenv()

# 개별 평가용 LLM 클라이언트 설정
client = OpenAI()  # 자동으로 .env의 OPENAI_API_KEY 사용됨

# 개별 평가용 모델 설정 (여기서 모델 변경 가능)
INDIVIDUAL_EVAL_MODEL = "gpt-4o"  # 또는 "gpt-4", "gpt-3.5-turbo" 등

# 반말 감지를 위한 유틸리티 함수
def detect_casual_speech(text: str) -> bool:
    """
    반말 사용 여부를 감지하는 함수
    인용문이나 예시 설명은 제외하고 실제 면접 답변에서의 반말만 감지
    """
    # 인용문 패턴 (따옴표 안의 내용 제외)
    quote_patterns = [
        r'"[^"]*"',  # 큰따옴표
        r"'[^']*'",  # 작은따옴표
        r'"[^"]*"',  # 전각 큰따옴표
        r"'[^']*'",  # 전각 작은따옴표
    ]
    
    # 인용문 제거
    cleaned_text = text
    for pattern in quote_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text)
    
    # 반말 패턴들
    casual_patterns = [
        r'\b나는\b',      # "나는"
        r'\b했어\b',      # "했어"
        r'\b있어\b',      # "있어" 
        r'\b이야\b',      # "이야"
        r'\b했지\b',      # "했지"
        r'[가-힣]+해\.?$',  # 문장 끝 "~해"
        r'[가-힣]+야\.?$',  # 문장 끝 "~야"
        r'[가-힣]+지\.?$',  # 문장 끝 "~지"
        r'[가-힣]+어\.?$',  # 문장 끝 "~어"
        r'[가-힣]+다\.?$',  # 문장 끝 "~다" (단, 존댓말 제외)
    ]
    
    # 존댓말 예외 패턴 (반말로 오인될 수 있는 존댓말들)
    polite_exceptions = [
        r'습니다\.?$',    # "~습니다"
        r'했습니다\.?$',  # "~했습니다"
        r'입니다\.?$',    # "~입니다"
        r'있습니다\.?$',  # "~있습니다"
        r'합니다\.?$',    # "~합니다"
    ]
    
    # 각 문장별로 확인
    sentences = re.split(r'[.!?]', cleaned_text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # 존댓말 예외 확인
        is_polite = any(re.search(pattern, sentence) for pattern in polite_exceptions)
        if is_polite:
            continue
            
        # 반말 패턴 확인
        has_casual = any(re.search(pattern, sentence) for pattern in casual_patterns)
        if has_casual:
            return True
    
    return False

# 🤖 프롬프트 빌더 (질문 의도 자동 추출 + 평가)
def build_prompt_with_intent_extraction(question, answer, company_info):
    # 회사 정보 동적 포맷팅 (산업별/회사별 특화)
    company_name = company_info.get('name', '회사')
    
    # 산업별 평가 관점 설정
    industry_context = ""
    if 'IT' in company_name or 'tech' in company_info.get('tech_focus', []):
        industry_context = "IT/기술 기업의 관점에서 기술적 역량과 문제해결 능력을 중점적으로 평가하세요."
    elif '금융' in company_name or 'finance' in company_info.get('name', '').lower():
        industry_context = "금융업의 관점에서 신뢰성, 정확성, 리스크 관리 능력을 중점적으로 평가하세요."
    else:
        industry_context = f"{company_name}의 사업 특성과 기업 문화를 고려하여 평가하세요."
    
    company_section = f"""
🏢 회사 정보:
- 회사명: {company_info['name']}
- 인재상: {company_info.get('talent_profile', 'N/A')}
- 핵심역량: {', '.join(company_info.get('core_competencies', []))}
- 기술 중점: {', '.join(company_info.get('tech_focus', []))}
- 면접 키워드: {', '.join(company_info.get('interview_keywords', []))}
- 질문 방향: {company_info.get('question_direction', 'N/A')}
- 기술 과제: {', '.join(company_info.get('technical_challenges', []))}

📋 조직 문화:
- 근무 방식: {company_info.get('company_culture', {}).get('work_style', 'N/A')}
- 의사결정: {company_info.get('company_culture', {}).get('decision_making', 'N/A')}
- 성장 지원: {company_info.get('company_culture', {}).get('growth_support', 'N/A')}
- 핵심 가치: {', '.join(company_info.get('company_culture', {}).get('core_values', []))}

🎯 평가 관점: {industry_context}
"""
    # 역할별 정보 (예시: ai_researcher, product_manager)
    roles = []
    for role_key in ['ai_researcher', 'product_manager']:
        if role_key in company_info:
            role = company_info[role_key]
            roles.append(f"- {role['name']} ({role['role']}): {role['experience']} / 성격: {role['personality']} / 화법: {role['speaking_style']} / 중점: {', '.join(role['focus_areas'])}")
    roles_section = '\n'.join(roles)
    if roles_section:
        company_section += f"\n주요 면접관:\n{roles_section}"

    return f"""
당신은 전문 AI 면접관입니다. 다음의 구체적인 평가 기준에 따라 지원자를 정확하고 일관되게 평가해주세요.

**📋 평가 기준 (총 100점)**
1. **답변의 구체성** (25점): 실제 경험, 수치, 사례 포함 여부
2. **전문성과 역량** (25점): 해당 직무에 필요한 기술적/전문적 지식 
3. **논리적 구성** (20점): 답변의 체계성, 일관성, 명확성
4. **회사 적합성** (20점): 회사 문화와 요구사항에 부합하는 정도
5. **의사소통 능력** (10점): 언어 사용, 예의, 표현력

**🎯 중요 지침:**
- 반말 사용 시 즉시 -50점 적용
- 모호하거나 일반적인 답변은 감점
- 구체적 사례와 수치가 있는 답변은 가점
- 회사의 기술 스택이나 문화와 관련된 언급 시 가점

**1단계: 질문 의도 분석**
질문만 보고 면접관이 무엇을 평가하려는지 분석하세요.

[질문]: {question}

**2단계: 답변 종합 평가**
이제 답변을 보고 위에서 분석한 질문 의도에 맞게 평가해주세요.

📝 평가 항목 및 가중치:
- 질문 의도 일치도 (25점): 질문의 핵심 의도를 정확히 파악하고 응답했는가? (가장 중요)
- 인재상 적합성 (18점): 회사 인재상과 어느 정도 부합하는가?
- 논리성 (12점): 주장과 근거가 논리적으로 연결되었는가?
- 타당성 (12점): 제시된 경험이 신뢰 가능하고 과장되지 않았는가?
- 키워드 적합성 (10점): 면접 키워드나 질문 방향과 얼마나 관련 있는가?
- 예의/매너 (23점): 면접 상황에 적절한 존댓말과 예의를 갖추었는가?


🚨 절대 규칙: 면접에서 반말이나 무례한 표현을 사용한 경우 무조건 50점을 차감합니다.
- 반말 패턴: 문장 끝의 "~해", "~야", "~지", "~어", "~다", "나는", "했어", "있어", "이야", "했지" 등
- 단, 인용문이나 예시 설명 중의 반말은 제외 ("그때 상사가 '괜찮다'고 했습니다" 등)
- 이는 협상 불가능한 절대 규칙이며, 내용이 아무리 좋아도 반드시 적용해야 합니다.
- 예의/매너 점수도 0~5점 이하로만 평가하세요.

--- 회사 정보 ---
{company_section}

--- 지원자 답변 ---
[답변]: {answer}

--- 출력 형식 ---
**질문 의도 분석**: [이 질문을 통해 면접관이 알고자 하는 것]

**답변 평가 결과**:
의도 일치도 점수 (25점 만점): X점 - 이유: [...]
인재상 적합성 점수 (18점 만점): X점 - 이유: [...]
논리성 점수 (12점 만점): X점 - 이유: [...]
타당성 점수 (12점 만점): X점 - 이유: [...]
키워드 적합성 점수 (10점 만점): X점 - 이유: [...]
예의/매너 점수 (23점 만점): X점 - 이유: [...]

기본 총점: XX점
예의 페널티: -X점 (예의가 부족한 경우 -50점, 없으면 -0점)
최종 총점: XX점 (최소 0점)

[💡 전체 피드백]
- 👍 좋았던 점: ...
- 👎 아쉬운 점: ...
- ✨ 개선 제안: ...
- 총평: ...
"""

# GPT 호출 함수
def evaluate_with_gpt(prompt: str) -> str:
    """
    개별 평가용 LLM 호출 함수
    
    Args:
        prompt (str): 평가용 프롬프트
        
    Returns:
        str: LLM 응답 결과
    """
    try:
        response = client.chat.completions.create(
            model=INDIVIDUAL_EVAL_MODEL,  # 개별 평가 전용 모델 사용
            messages=[
                {"role": "system", "content": "너는 매우 엄격한 면접관입니다. 반말 사용 시 반드시 50점을 차감하고, 출력 형식을 반드시 지키세요. 예의없는 답변에는 절대 관대하지 마세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1  # 면접 평가에 적합한 설정
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ 개별 평가 LLM ({INDIVIDUAL_EVAL_MODEL}) 호출 에러:", e)
        return "ERROR"

# 전체 평가 루프 (company_info를 인자로 받음)
def evaluate_all(interview_data: List[Dict[str, str]], company_info: dict) -> List[Dict[str, str]]:
    results = []
    for idx, item in enumerate(interview_data):
        print(f"🎤 질문 {idx+1} 평가 중...")
        prompt = build_prompt(item["question"], item["answer"], item["intent"], company_info)
        evaluation = evaluate_with_gpt(prompt)
        results.append({
            "질문": item["question"],
            "답변": item["answer"],
            "의도": item["intent"],
            "평가결과": evaluation
        })
        # time.sleep(1.2)
    return results

def evaluate_single_qa(question: str, answer: str, intent: str, company_info: dict) -> str:
    """단일 질문-답변 쌍의 LLM 평가 수행 (구 버전 - 호환성 유지)"""
    prompt = build_prompt(question, answer, intent, company_info)
    evaluation = evaluate_with_gpt(prompt)
    return evaluation

def evaluate_single_qa_with_intent_extraction(question: str, answer: str, company_info: dict) -> dict:
    """
    질문 의도 자동 추출 + 단일 질문-답변 쌍의 LLM 평가 수행
    
    Returns:
        dict: {"evaluation": str, "extracted_intent": str}
    """
    prompt = build_prompt_with_intent_extraction(question, answer, company_info)
    evaluation = evaluate_with_gpt(prompt)
    
    # 응답에서 질문 의도 추출
    extracted_intent = ""
    if "**질문 의도 분석**:" in evaluation:
        intent_start = evaluation.find("**질문 의도 분석**:") + len("**질문 의도 분석**:")
        intent_end = evaluation.find("**답변 평가 결과**:")
        if intent_end != -1:
            extracted_intent = evaluation[intent_start:intent_end].strip()
        else:
            # 다음 줄바꿈까지
            intent_end = evaluation.find("\n", intent_start)
            if intent_end != -1:
                extracted_intent = evaluation[intent_start:intent_end].strip()
    
    return {
        "evaluation": evaluation,
        "extracted_intent": extracted_intent
    }

# 메인 처리
if __name__ == "__main__":
    # 입력 JSON 파일명
    input_file = "interview_data.json"
    output_file = "evaluation_results.json"
    company_file = "company_info.json"

    # 입력 JSON 로딩
    with open(input_file, "r", encoding="utf-8") as f:
        interview_data = json.load(f)
    with open(company_file, "r", encoding="utf-8") as f:
        company_info = json.load(f)

    # 평가 실행
    results = evaluate_all(interview_data, company_info)

    # 출력 저장
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 평가 완료! 결과는 '{output_file}'에 저장되었습니다!")
