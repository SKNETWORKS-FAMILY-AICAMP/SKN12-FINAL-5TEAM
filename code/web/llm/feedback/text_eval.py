#!/usr/bin/env python3
"""
GPT-4o 기반 텍스트 평가 시스템
반말/존댓말 감지를 GPT-4o로 수행하는 버전
"""

import re
import time
from typing import List, Dict
from openai import OpenAI

# OpenAI 클라이언트 초기화
client = OpenAI()  # 자동으로 .env의 OPENAI_API_KEY 로드

def detect_stuttering(text: str) -> int:
    """더듬는 말 감지 및 감점 계산"""
    stuttering_patterns = [
        r'음\.{2,}',     # 음...
        r'어\.{2,}',     # 어...  
        r'그\.{2,}',     # 그...
        r'흠\.{2,}',     # 흠...
        r'아\.{2,}',     # 아...
        r'저\.{2,}',     # 저...
        r'뭐\.{2,}',     # 뭐...
        r'에\.{2,}',     # 에...
        r'으\.{2,}',     # 으...
    ]
    
    stuttering_count = 0
    for pattern in stuttering_patterns:
        matches = re.findall(pattern, text)
        stuttering_count += len(matches)
    
    # 더듬는 말 감점 계산 (최대 10점 감점)
    deduction = min(stuttering_count * 2, 10)
    return deduction

def detect_stuttering_enhanced(text: str) -> int:
    """강화된 습관어 감지 시스템 (더 정교한 패턴)"""
    
    # 강화된 습관어 패턴들
    enhanced_patterns = [
        r'음{1,}\\.{2,}',      # 음..., 음음...
        r'어{1,}\\.{2,}',      # 어..., 어어...
        r'흠{1,}\\.{2,}',      # 흠..., 흠흠...
        r'아{1,}\\.{2,}',      # 아..., 아아...
        r'그{1,}\\.{2,}',      # 그..., 그그...
        r'저{1,}\\.{2,}',      # 저..., 저저...
        r'뭐{1,}\\.{2,}',      # 뭐..., 뭐뭐...
        r'에{1,}\\.{2,}',      # 에..., 에에...
        r'으{1,}\\.{2,}',      # 으..., 으으...
        r'저기{1,}\\.{2,}',    # 저기...
        r'그러니까{1,}\\.{2,}', # 그러니까...
        r'그게{1,}\\.{2,}',    # 그게...
        r'그냥{1,}\\.{2,}',    # 그냥...
        r'막{1,}\\.{2,}',      # 막...
    ]
    
    total_count = 0
    found_patterns = []
    
    for pattern in enhanced_patterns:
        matches = re.findall(pattern, text)
        count = len(matches)
        if count > 0:
            total_count += count
            found_patterns.append(f"{pattern}: {count}회")
    
    if found_patterns:
        print(f"강화된 습관어 감지: {', '.join(found_patterns)}")
    
    # 감점 계산 (점진적 감점, 최대 10점)
    if total_count == 0:
        return 0
    elif total_count <= 3:
        return 2
    elif total_count <= 6:
        return 4
    elif total_count <= 10:
        return 6
    elif total_count <= 15:
        return 8
    else:
        return 10

def calculate_stuttering_penalty(text: str) -> int:
    """
    이중 검증 습관어 감지: 기존 방식 + 강화된 패턴 결합
    놓치는 사례를 최소화하기 위해 두 방식 중 높은 값 선택
    
    Args:
        text: 평가할 텍스트
        
    Returns:
        int: 감점 점수 (0~10점)
    """
    # 1단계: 기존 방식 (단순 문자열 매칭)
    basic_patterns = [
        "음...", "어...", "흠...", "아...", "그...",  # 기존 패턴
        "저기...", "뭐...", "그러니까...", "에...", "으...", "그게...",  # 추가된 더듬는 말
        "음음...", "어어...", "그냥...", "막..."  # 자주 사용되는 더듬는 말
    ]
    basic_count = 0
    
    for pattern in basic_patterns:
        basic_count += text.count(pattern)
    
    # 기존 방식 감점 계산
    if basic_count == 0:
        basic_penalty = 0
    elif basic_count <= 3:
        basic_penalty = 2
    elif basic_count <= 6:
        basic_penalty = 4
    elif basic_count <= 10:
        basic_penalty = 6
    elif basic_count <= 15:
        basic_penalty = 8
    else:
        basic_penalty = 10
    
    # 2단계: 강화된 패턴 방식
    enhanced_penalty = detect_stuttering_enhanced(text)
    
    # 3단계: 더 높은 감점 선택 (놓치는 것 최소화)
    final_penalty = max(basic_penalty, enhanced_penalty)
    
    # 4단계: 차이가 나는 경우 로깅
    if basic_penalty != enhanced_penalty:
        print(f"🔍 습관어 이중검증 - 기존: {basic_penalty}점, 강화: {enhanced_penalty}점 → 최종: {final_penalty}점")
    else:
        print(f"✅ 습관어 일치 감지: {final_penalty}점")
    
    return final_penalty

def detect_casual_speech_count_gpt_only(text: str) -> int:
    """
    GPT-4o를 사용한 부적절한 반말 횟수 계산 (강화된 페널티 시스템)
    
    Returns:
        int: 면접관에게 직접 사용된 부적절한 반말의 횟수
    """
    try:
        # 빈 텍스트나 너무 짧은 텍스트는 패턴 기반 방식 사용
        if not text or len(text.strip()) < 2:
            print(f"텍스트가 너무 짧음, 패턴 기반 분석 사용: '{text}'")
            return detect_casual_speech_count_pattern_fallback(text)
        
        prompt = f"""다음 면접 답변을 정밀하게 분석하여 면접관에게 직접 사용된 부적절한 반말의 횟수를 정확히 세어주세요.

면접 답변: "{text}"

🎯 **분석 단계**:

1단계: 문장을 나누어 각 부분 분석
- 따옴표("", '', "", '') 안의 내용 = 인용문 → 제외
- '예를 들어', '~라는', '~라고' 다음의 반말 = 예시/설명 → 제외  
- '마음속으로', '생각으로' 다음의 반말 = 내적 독백 → 제외
- 문법적 표현: ~다면, ~다고, ~다는, ~다가 = 문법 표현 → 제외

2단계: 면접관에게 직접 말하는 반말만 카운트
✅ **카운트 대상**: 면접관에게 직접 하는 말에서 반말 어미 (마침표나 문장 끝)
- "...해." "...야." "...지." "...어." "...아." (문장 끝에서 끝나는 반말)
- "...좋아." "...싫어." "...많아." "...빨라." "...재미있어." (형용사 반말)
- "...했어." "...갔어." "...왔어." (과거형 반말)

**반말 vs 존댓말 구분 예시**:
- 반말: "이 기술이 좋아." "코딩이 재미있어." "개발했어."
- 존댓말: "이 기술이 좋아요." "코딩이 재미있어요." "개발했어요."

❌ **제외 대상**: 
- 인용문: "팀장이 '빨리해'라고 했습니다" → '빨리해'는 제외
- 예시: "예를 들어 '느려'라는 문제가..." → '느려'는 제외
- 문법: "제가 담당한다면 좋겠습니다" → '담당한다면'은 문법 표현이므로 제외
- 존댓말 (절대 카운트하지 말 것):
  * "...해요" (생각해요, 개발해요, 공부해요)
  * "...어요" (했어요, 갔어요, 왔어, 좋아요)
  * "...아요" (많아요, 예뻐요)
  * "...습니다" (했습니다, 갑습니다)
  * "...입니다" (학생입니다, 개발자입니다)

**핵심 규칙**: 
1. "~요"로 끝나면 = 존댓말 → 절대 카운트하지 않음
2. "~습니다", "~입니다"로 끝나면 = 존댓말 → 절대 카운트하지 않음  
3. 인용문("", '', "", '') 안은 = 제외 → 카운트하지 않음
4. "예를 들어" 다음은 = 예시 → 카운트하지 않음

**최종 확인**: 면접관에게 직접 말하는 반말(마침표로 끝나는)만 세어주세요.

**출력**: 숫자만 (예: 0, 1, 2, 3...)"""

        print(f"GPT-4o 반말 횟수 계산 시작: '{text[:50]}...'")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 한국어 언어학 전문가입니다. 면접 상황에서 면접관에게 직접 사용된 부적절한 반말을 정확히 식별하고 개수를 세는 것이 당신의 역할입니다. 인용문, 예시, 내적 독백은 제외하고 직접적인 면접 답변에서의 반말만 카운트해주세요."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # 일관성을 위해 낮은 temperature
            max_tokens=10,    # 짧은 응답만 필요
            timeout=30        # 30초 타임아웃
        )
        
        result = response.choices[0].message.content.strip()
        
        try:
            casual_count = int(result)
            # 디버깅용 로그
            print(f"GPT-4o 반말 횟수 계산 성공: '{text[:50]}...' → {casual_count}회")
            return casual_count
        except ValueError:
            print(f"GPT-4o 응답 파싱 실패: '{result}' → 패턴 기반 분석으로 전환")
            return detect_casual_speech_count_pattern_fallback(text)
        
    except Exception as e:
        print(f"GPT-4o 호출 오류 (패턴 기반 분석으로 전환): {e}")
        print(f"오류 유형: {type(e).__name__}")
        # 오류 시 패턴 기반 백업 방식 사용
        return detect_casual_speech_count_pattern_fallback(text)

def detect_casual_speech_count(text: str) -> int:
    """
    이중 검증 하이브리드 시스템: GPT-4o + 패턴 기반 결합
    놓치는 사례를 최소화하기 위해 두 방식 중 높은 값 선택
    
    Returns:
        int: 감지된 반말 횟수 (두 방식 중 최댓값)
    """
    # 1단계: GPT-4o로 1차 감지
    gpt_count = detect_casual_speech_count_gpt_only(text)
    
    # 2단계: 패턴으로 2차 검증 (놓친 것 찾기)
    pattern_count = detect_casual_speech_count_pattern_fallback(text)
    
    # 3단계: 더 높은 값 선택 (False Negative 최소화)
    final_count = max(gpt_count, pattern_count)
    
    # 4단계: 차이가 나는 경우 로깅 (모니터링용)
    if gpt_count != pattern_count:
        print(f"🔍 이중검증 결과 - GPT: {gpt_count}회, 패턴: {pattern_count}회 → 최종: {final_count}회")
        print(f"   대상 텍스트: '{text[:80]}...'")
    else:
        print(f"✅ 일치 감지: {final_count}회 - '{text[:50]}...'")
    
    return final_count

def detect_casual_speech(text: str) -> bool:
    """
    기존 호환성을 위한 래퍼 함수 (반말이 1회 이상이면 True)
    """
    casual_count = detect_casual_speech_count(text)
    return casual_count > 0

def detect_casual_speech_count_pattern_fallback(text: str) -> int:
    """패턴 기반 반말 감지 시스템 (GPT-4o 백업용)"""
    print(f"패턴 기반 시스템 사용: '{text[:50]}...'")
    
    if not text:
        return 0
    
    # 정규식 패턴 기반 반말 탐지
    casual_patterns = [
        r'[가-힣]+아\.',      # "좋아.", "많아."
        r'[가-힣]+어\.',      # "했어.", "있어."
        r'[가-힣]+해\.',      # "생각해.", "공부해."
        r'[가-힣]+야\.',      # "해야.", "가야."
        r'[가-힣]+지\.',      # "했지.", "좋지."
        r'[가-힣]+네\.',      # "좋네.", "예쁘네."
        r'빨라\.', r'많아\.', r'좋아\.', r'싫어\.',
        r'\b그래\b', r'\b맞아\b', r'\b응\b', r'\b했지\b'
    ]
    
    # 존댓말 패턴 (반말 패턴 전에 확인해서 제외)
    polite_patterns = [
        r'습니다\.', r'해요\.', r'어요\.', r'죠\.', r'데요\.', r'세요\.'
    ]
    
    # 존댓말이 포함된 문장은 전체적으로 존댓말로 간주
    for pattern in polite_patterns:
        if re.search(pattern, text):
            print(f"패턴 분석: 존댓말 패턴 발견 → 0회")
            return 0
    
    # 반말 횟수 계산
    casual_count = 0
    for pattern in casual_patterns:
        matches = re.findall(pattern, text)
        casual_count += len(matches)
        if matches:
            print(f"패턴 분석: 반말 패턴 발견 - {pattern} ({len(matches)}회)")
    
    print(f"패턴 분석: 총 반말 횟수 → {casual_count}회")
    return casual_count

def detect_casual_speech_fallback(text: str) -> bool:
    """기존 호환성을 위한 패턴 기반 방식 (반말이 1회 이상이면 True)"""
    casual_count = detect_casual_speech_count_pattern_fallback(text)
    return casual_count > 0

def apply_stuttering_penalty(evaluation_text: str, stuttering_deduction: int) -> str:
    """더듬는 말 감점을 평가에 적용"""
    if stuttering_deduction > 0:
        stuttering_feedback = f"\n\n🗣️ **더듬는 말 감점**: -{stuttering_deduction}점 (음..., 어... 등의 더듬는 말 사용)"
        modified_evaluation = evaluation_text + stuttering_feedback
    else:
        modified_evaluation = evaluation_text
    
    return modified_evaluation

def evaluate_single_qa_with_intent_extraction(question: str, answer: str, company_info: dict, position_info: dict, posting_info: dict, resume_info: dict) -> dict:
    """
    질문 의도 자동 추출 + 단일 질문-답변 쌍의 LLM 평가 수행 (강화된 반말 페널티 적용)
    
    Returns:
        dict: {"evaluation": str, "extracted_intent": str, "casual_count": int, "casual_penalty": int}
    """
    # 강화된 반말 횟수 계산
    casual_count = detect_casual_speech_count(answer)
    casual_penalty = casual_count * 10  # 1회당 10점 감점
    
    print(f"반말 감지 결과: {casual_count}회 → 감점 {casual_penalty}점")
    
    prompt = build_prompt_with_intent_extraction(question, answer, company_info, position_info, posting_info, resume_info, casual_count, casual_penalty)
    evaluation = evaluate_with_gpt(prompt)
    
    # 더듬는 말 감점 계산
    stuttering_penalty = calculate_stuttering_penalty(answer)
    
    # 기존 점수에서 더듬는 말 감점 적용
    if stuttering_penalty > 0:
        # 평가 결과에서 총점 추출 및 감점 적용
        evaluation = apply_stuttering_penalty(evaluation, stuttering_penalty)
    
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
        "extracted_intent": extracted_intent,
        "casual_count": casual_count,
        "casual_penalty": casual_penalty
    }

def build_prompt(question: str, answer: str, intent: str, company_info: dict) -> str:
    """
    기존 호환성을 위한 간단한 프롬프트 빌더
    """
    return f"""
면접 질문과 답변을 평가해주세요.

질문: {question}
답변: {answer}
의도: {intent}

회사 정보:
- 회사명: {company_info.get('name', 'N/A')}
- 인재상: {company_info.get('talent_profile', 'N/A')}

위 정보를 바탕으로 답변을 평가해주세요.
"""

def evaluate_single_qa(question: str, answer: str, intent: str, company_info: dict) -> str:
    """
    기존 호환성을 위한 함수 (단순한 evaluation 문자열만 반환)
    내부적으로 evaluate_single_qa_with_intent_extraction 호출
    """
    result = evaluate_single_qa_with_intent_extraction(
        question, answer, company_info,
        {"position_name": "미지정"},  # 기본 직군 정보
        {"content": "공고 정보 없음"},  # 기본 공고 정보  
        {"career": "이력서 정보 없음", "academic_record": "학력 정보 없음"}  # 기본 이력서 정보
    )
    
    # 강화된 반말 페널티 정보를 평가 결과에 추가
    if result["casual_count"] > 0:
        casual_info = f"\n\n🚨 **반말 감지 결과**: {result['casual_count']}회 감지 → {result['casual_penalty']}점 감점 적용"
        evaluation_with_penalty = result["evaluation"] + casual_info
    else:
        evaluation_with_penalty = result["evaluation"]
    
    return evaluation_with_penalty

def evaluate_all(interview_data: List[Dict[str, str]], company_info: dict) -> List[Dict[str, str]]:
    """
    전체 면접 데이터 일괄 평가 (GPT-4o 기반)
    기존 호환성을 위한 함수
    """
    results = []
    for idx, item in enumerate(interview_data):
        print(f"🎤 질문 {idx+1} 평가 중...")
        
        # GPT-4o 기반 평가 수행 (호환성을 위한 기본값 제공)
        result = evaluate_single_qa_with_intent_extraction(
            item["question"], 
            item["answer"], 
            company_info,
            {"position_name": "미지정"},  # 기본 직군 정보
            {"content": "공고 정보 없음"},  # 기본 공고 정보  
            {"career": "이력서 정보 없음", "academic_record": "학력 정보 없음"}  # 기본 이력서 정보
        )
        
        # 강화된 반말 페널티 정보를 평가 결과에 추가
        evaluation_with_penalty = result["evaluation"]
        if result["casual_count"] > 0:
            casual_info = f"\n\n🚨 **반말 감지 결과**: {result['casual_count']}회 감지 → {result['casual_penalty']}점 감점 적용"
            evaluation_with_penalty = result["evaluation"] + casual_info
        
        results.append({
            "질문": item["question"],
            "답변": item["answer"],
            "의도": result.get("extracted_intent", item.get("intent", "자동 추출됨")),
            "평가결과": evaluation_with_penalty,
            "반말횟수": result["casual_count"],
            "반말감점": result["casual_penalty"]
        })
        
        # API 호출 속도 제한을 위한 짧은 대기
        time.sleep(0.5)
        
    return results

def evaluate_with_gpt(prompt: str) -> str:
    """
    개별 평가용 LLM 호출 함수 (백업 호환성)
    
    Args:
        prompt (str): 평가용 프롬프트
        
    Returns:
        str: LLM 응답 결과
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # GPT-4o 사용
            messages=[
                {"role": "system", "content": "당신은 면접 평가 전문가입니다. 제공된 평가 기준과 시스템 분석 결과(반말 감지 결과 포함)를 정확히 따라 평가해주세요. 반말 감지는 이미 시스템에서 처리되었으므로, 독자적으로 반말을 판단하지 마세요. 제공된 정보만을 바탕으로 일관된 평가를 수행해주세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1  # 면접 평가에 적합한 설정
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ LLM 호출 에러:", e)
        return "ERROR"

def build_prompt_with_intent_extraction(question, answer, company_info, position_info: dict, posting_info: dict, resume_info: dict, casual_count=0, casual_penalty=0):
    """
    질문 의도 자동 추출 + 평가를 위한 프롬프트 구성 (백업 호환성)
    """
    # 회사 정보 동적 포맷팅 (IT 개발자 직군 전용)
    company_name = company_info.get('name', '회사')
    
    # IT 개발자 직군 평가 관점
    industry_context = "IT 개발자의 관점에서 기술적 역량, 문제해결 능력, 코딩 실력, 시스템 설계 능력을 중점적으로 평가하세요."
    
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

    # 직군 정보 섹션
    position_name = position_info.get('position_name', 'N/A')
    position_section = f"""이 지원자가 지원한 직군은 "{position_name}"입니다.
IT 개발자 직군의 핵심 역량인 프로그래밍 능력, 시스템 설계, 문제 해결, 기술 학습 능력을 중심으로 평가해주세요."""

    # 공고 정보 섹션  
    content = posting_info.get('content', 'N/A')
    if len(content) > 300:
        content = content[:300] + "..."
    posting_section = f"""이 지원자가 지원한 채용 공고의 주요 내용입니다:

{content}

위 공고의 요구사항과 지원자의 답변이 얼마나 부합하는지 평가해주세요."""

    # 이력서 정보 섹션
    resume_type = "AI 생성 이력서" if 'ai_resume_id' in resume_info else "지원자 제출 이력서"
    career = resume_info.get('career', 'N/A')
    if len(career) > 200:
        career = career[:200] + "..."
    activities = resume_info.get('activities', 'N/A')
    if len(activities) > 100:
        activities = activities[:100] + "..."
        
    resume_section = f"""다음은 {resume_type} 정보입니다:

**학력사항**: {resume_info.get('academic_record', 'N/A')}
**경력사항**: {career}
**보유 기술**: {resume_info.get('tech', 'N/A')}
**주요 활동**: {activities}
**자격증**: {resume_info.get('certificate', 'N/A')}
**수상경력**: {resume_info.get('awards', 'N/A')}

위 이력서 내용과 지원자의 면접 답변이 일치하는지, 그리고 이력서에 나타난 역량이 답변에서도 드러나는지 평가해주세요."""

    return f"""
당신은 전문 AI 면접관입니다. 다음의 구체적인 평가 기준에 따라 지원자를 정확하고 일관되게 평가해주세요.

**🎯 중요 지침 (IT 개발자 면접 - 강화된 반말 페널티):**
- **강화된 반말 페널티**: 부적절한 반말 사용 1회당 -10점 감점 (기존 -50점에서 개선)
- 인용문, 예시, 내적 독백의 반말은 제외하고 면접관에게 직접 사용한 반말만 감점 대상
- 더듬는 말("음...", "어...", "흠..." 등)이 있어도 내용 평가는 정상적으로 수행하고, 피드백에서만 의사소통 개선점으로 언급
- 기술적 깊이와 구체적인 경험을 중시하여 평가
- 프로그래밍 언어, 프레임워크, 알고리즘 등 구체적 기술 언급 시 가점
- 시스템 설계, 성능 최적화, 문제 해결 과정의 논리성 중점 평가
- 회사의 기술 스택이나 개발 문화와 관련된 언급 시 가점

**1단계: 질문 의도 분석**
질문만 보고 면접관이 무엇을 평가하려는지 분석하세요.

[질문]: {question}

**2단계: 답변 종합 평가**
이제 답변을 보고 위에서 분석한 질문 의도에 맞게 다음 항목별로 평가해주세요.

📝 **세부 평가 항목:**
- 질문 의도 일치도 (25점): 질문의 핵심 의도를 정확히 파악하고 응답했는가? (가장 중요)
- 인재상 적합성 (18점): 회사 인재상과 어느 정도 부합하는가?
- 논리성 (12점): 주장과 근거가 논리적으로 연결되었는가?
- 타당성 (12점): 제시된 경험이 신뢰 가능하고 과장되지 않았는가?
- 키워드 적합성 (10점): 면접 키워드나 질문 방향과 얼마나 관련 있는가?
- 예의/매너 (23점): 면접 상황에 적절한 존댓말과 예의를 갖추었는가?


🚨 **강화된 반말 감지 시스템 결과**: 
- 감지된 반말 횟수: {casual_count}회
- 적용 감점: -{casual_penalty}점 ({casual_count}회 × 10점)
- 평가 상태: {"반말 사용으로 감점 적용" if casual_count > 0 else "존댓말 사용으로 정상 평가"}

**중요**: 이 결과는 정밀한 GPT-4o 언어 분석 시스템에서 처리된 것입니다.
- 면접관에게 직접 사용한 부적절한 반말만 감점 대상 (인용문, 예시, 내적 독백 제외)
- 1회당 10점 감점으로 좀 더 세밀하고 합리적인 페널티 적용
- 이 시스템 결과를 절대 무시하지 말고 반드시 따라주세요

--- 🏢 회사 정보 ---
{company_section}

--- 💼 지원 직군 정보 ---
{position_section}

--- 📢 채용 공고 정보 ---
{posting_section}

--- 📄 지원자 이력서 정보 ---
{resume_section}

--- 💬 지원자 답변 ---
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
반말 페널티: -{casual_penalty}점 (감지된 반말 {casual_count}회 × 10점)
최종 총점: XX점 (기본 총점 - 반말 페널티, 최소 0점)

[💡 전체 피드백]
- 👍 좋았던 점: ...
- 👎 아쉬운 점: ...
- ✨ 개선 제안: ...
- 총평: ...
"""