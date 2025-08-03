#!/usr/bin/env python3
"""
면접관 프롬프트 빌더
service.py에서 분리된 모든 프롬프트 관련 로직을 담당
"""

from typing import Dict, List, Any
from ..shared.constants import GPT_MODEL


class InterviewerPromptBuilder:
    """면접관 프롬프트 생성을 담당하는 클래스"""
    
    def __init__(self):
        pass
    
    def build_system_prompt_for_question_generation(self) -> str:
        """질문 생성용 시스템 프롬프트"""
        return """당신은 전문 면접관입니다. 

🚨 **절대 준수 사항** 🚨
- 오직 아래 JSON 형식으로만 응답하세요
- 다른 어떤 텍스트, 설명, 주석도 절대 포함하지 마세요
- JSON 앞뒤에 ```json이나 기타 텍스트 금지

**필수 응답 형식:**
{"question": "질문 내용", "intent": "질문 의도"}

**예시:**
{"question": "프로젝트에서 가장 어려웠던 기술적 도전은 무엇이었나요?", "intent": "문제 해결 능력과 기술적 역량 평가"}

위 형식만 사용하세요. 다른 형태의 응답은 시스템 오류를 발생시킵니다."""
    
    def build_main_question_prompt(self, user_resume: Dict, company_info: Dict, 
                                 interviewer_role: str, topic: str) -> str:
        """전사적 DNA 매트릭스 프롬프트 빌더 - 회사의 모든 특성과 직무 전문성을 융합한 맞춤형 질문 생성"""
        
        # 1. [회사 DNA] 정보 체계적 추출
        company_name = company_info.get('name', '회사')
        talent_profile = company_info.get('talent_profile', '정의되지 않음')
        core_competencies = ', '.join(company_info.get('core_competencies', ['정의되지 않음']))
        tech_focus = ', '.join(company_info.get('tech_focus', ['정의되지 않음']))
        question_direction = company_info.get('question_direction', '정의되지 않음')
        
        # 기업문화 정보 추출
        company_culture = company_info.get('company_culture', {})
        core_values = []
        work_style = ''
        if isinstance(company_culture, dict):
            core_values = company_culture.get('core_values', [])
            work_style = company_culture.get('work_style', '')
        
        # 2. [지원자 직무 컨텍스트] 정의
        position = user_resume.get('position', '개발자')
        position_contexts = {
            "백엔드": "대용량 트래픽 처리, 데이터베이스 설계, MSA 아키텍처, API 성능 최적화, 시스템 안정성, 분산 트랜잭션",
            "프론트엔드": "웹 성능 최적화(로딩 속도), 상태 관리, UI/UX 개선, 크로스 브라우징, 웹 접근성, Critical Rendering Path",
            "AI": "모델 성능 및 정확도, 데이터 전처리, 과적합 방지, 최신 논문 구현, MLOps, Transformer 아키텍처",
            "데이터사이언스": "A/B 테스트 설계, 통계적 가설 검증, Feature Engineering, 데이터 시각화, 예측 모델링, 불균형 데이터 처리",
            "기획": "사용자 요구사항 분석, 제품 로드맵 설정, KPI 정의, 시장 조사, 기능 우선순위 결정, RICE/ICE 프레임워크"
        }
        
        # 직군 매칭 (부분 문자열 포함 검사)
        position_context = "소프트웨어 개발 일반"
        for key, context in position_contexts.items():
            if key in position or key.lower() in position.lower():
                position_context = context
                break
        
        # 주제별 기본 가이드라인
        topic_guidelines = {
            '인성_가치관': '지원자의 핵심 가치관과 인생 철학을 파악할 수 있는 질문',
            '성장_동기': '학습 의지와 자기계발에 대한 태도를 확인하는 질문',
            '갈등_해결': '대인관계나 업무상 갈등 상황에서의 해결 능력을 평가하는 질문',
            '스트레스_관리': '압박 상황에서의 대처 능력과 회복력을 측정하는 질문',
            '팀워크_리더십': '팀 내에서의 역할과 리더십 역량을 확인하는 질문',
            '기술_역량': '전문 기술 지식과 실무 적용 능력을 검증하는 질문',
            '문제_해결': '복잡한 기술적 문제에 대한 접근 방식과 해결 과정을 평가하는 질문',
            '성능_최적화': '시스템 성능 개선과 최적화 경험을 확인하는 질문',
            '코드_품질': '코드 리뷰, 테스트, 문서화 등 품질 관리 능력을 평가하는 질문',
            '새로운_기술_학습': '기술 트렌드 파악과 새로운 기술 습득 능력을 확인하는 질문',
            '소통_능력': '의사소통과 정보 전달 능력을 평가하는 질문',
            '프로젝트_협업': '다양한 역할의 팀원들과의 협업 경험을 확인하는 질문',
            '의견_조율': '서로 다른 의견을 조율하고 합의점을 찾는 능력을 평가하는 질문',
            '크로스_팀_협업': '부서간 협업과 이해관계자 관리 능력을 확인하는 질문',
            '조직_문화_적응': '새로운 환경에 대한 적응력과 조직 문화 이해도를 평가하는 질문'
        }
        
        # 3. 안전장치: 필수 DNA 정보 부족 시 기존 방식 사용
        critical_dna_missing = (
            talent_profile == '정의되지 않음' and 
            core_competencies == '정의되지 않음' and 
            tech_focus == '정의되지 않음' and 
            question_direction == '정의되지 않음'
        )
        
        if critical_dna_missing:
            # 기존 프롬프트 구조로 폴백
            guideline = topic_guidelines.get(topic, f'{topic} 관련 전문성을 평가하는 질문')
            return f"""
당신은 {company_name}의 {interviewer_role} 담당 면접관입니다.

면접 직군: {position}
면접 주제: {topic}
질문 가이드라인: {guideline}

위 주제에 대해 두 지원자를 동시에 평가할 수 있는 메인 질문을 하나만 생성해주세요.

응답 형식:
{{"question": "질문 내용", "intent": "질문 의도"}}
"""
        
        # 4. [전사적 DNA 매트릭스 프롬프트] 구성
        prompt = f"""
### 당신의 미션 ###
당신은 '{company_name}'의 채용 철학을 완벽하게 이해한 최고 수준의 {interviewer_role} 면접관입니다.
아래에 주어진 [회사 DNA]와 [지원자 컨텍스트]를 '모두' 유기적으로 결합하여, 지원자의 역량을 다각도로 검증할 수 있는 매우 날카롭고 구체적인 질문을 '단 하나만' 생성하세요.

### [회사 DNA 분석] ###
- **인재상 (WHO):** 우리는 '{talent_profile}'인 사람을 원합니다.
- **핵심 역량 (WHAT):** 우리는 '{core_competencies}' 역량을 중요하게 생각합니다.
- **기술 중점 분야 (WHERE):** 우리의 기술은 '{tech_focus}' 분야에 집중되어 있습니다.
- **평가 방향 (HOW):** 우리는 '{question_direction}' 방식으로 지원자를 평가합니다.
{f"- **핵심가치:** {', '.join(core_values[:3])}" if core_values else ""}
{f"- **업무문화:** {work_style}" if work_style else ""}

### [지원자 컨텍스트] ###
- **직군:** {position}
- **주요 업무 영역:** {position_context}
- **면접 주제:** {topic_guidelines.get(topic, f'{topic} 관련 전문성을 평가하는 질문')}

### [질문 생성 사고 프로세스] (반드시 이 순서대로 생각하고 질문을 만드세요) ###
1. **DNA 융합:** 우리 회사의 **인재상(WHO)**과 **핵심 역량(WHAT)**을 고려했을 때, {position} 직무에서는 어떤 행동이나 기술적 결정이 가장 중요할지 정의하세요.

2. **상황 설정:** 위에서 정의한 행동/결정이 필요한 구체적인 문제 상황을 우리 회사의 **기술 중점 분야(WHERE)** 내에서 매우 현실적으로 설정하세요.

3. **질문 공식화:** 설정된 상황 속에서, 지원자가 어떻게 문제를 해결했는지 그 경험을 묻는 최종 질문을 만드세요. 이 질문은 반드시 우리 회사의 **평가 방향(HOW)**에 부합해야 하며, 지원자의 기술적 깊이와 우리 회사와의 문화적 적합성을 동시에 파악할 수 있어야 합니다.

### [질문 생성의 예시] ###
**만약 회사가 '네이버', 인재상이 '기술로 모든 것을 연결하는 플랫폼 빌더', 기술 중점이 'AI', 직군이 '백엔드'라면:**
- **사고 과정:** '기술로 모든 것을 연결'하는 '백엔드' 개발자는 기존 시스템의 한계를 넘어서는 것을 두려워하지 않아야 한다. 네이버의 'AI' 기술 중점 분야에서, 대규모 AI 모델의 데이터 서빙 파이프라인은 항상 도전적인 과제이다.
- **좋은 질문:** "네이버의 핵심 가치 중 하나는 '기술로 모든 것을 연결'하는 것입니다. 과거 대규모 AI 모델에 실시간으로 데이터를 공급하는 파이프라인에서 병목 현상을 겪고, 이를 해결하기 위해 기존 시스템의 구조에 '도전'하여 새롭게 개선했던 경험이 있다면 말씀해주세요. 어떤 기술적 근거로 새로운 아키텍처를 제안했고, 그 결과는 어땠나요?"

### [최종 출력] ###
다른 어떤 설명도 없이, 아래 JSON 형식에 맞춰서만 응답하세요.
{{
  "question": "생성된 최종 질문 내용",
  "intent": "이 질문을 통해 평가하려는 역량 (예: 데이터베이스 최적화 능력과 고객 중심 사고의 결합)",
  "related_dna": ["평가와 관련된 회사 DNA 키워드 (예: '고객 중심', '최고의 기술력')"]
}}
"""
        return prompt
    
    def build_system_prompt_for_follow_up(self) -> str:
        """꼬리 질문 생성용 시스템 프롬프트"""
        return """당신은 경험 많은 전문 면접관입니다. 지원자들의 답변을 분석하여 핵심을 파고드는 날카로운 꼬리 질문을 생성합니다.

🚨 **절대 준수 사항** 🚨
- 오직 아래 JSON 형식으로만 응답하세요
- 다른 어떤 텍스트, 설명, 주석도 절대 포함하지 마세요
- JSON 앞뒤에 ```json이나 기타 텍스트 금지

**필수 응답 형식:**
{"question": "질문 내용", "intent": "질문 의도"}

**예시:**
{"question": "방금 말씀하신 성능 최적화 방법에서 가장 효과적이었던 부분은 무엇인가요?", "intent": "구체적인 기술적 성과와 판단 근거 확인"}

위 형식만 사용하세요. 다른 형태의 응답은 시스템 오류를 발생시킵니다."""
    
    def build_follow_up_question_prompt(self, previous_question: str, user_answer: str, 
                                      chun_sik_answer: str, company_info: Dict, 
                                      interviewer_role: str) -> str:
        """동적 꼬리 질문 생성 - 답변 기반 실시간 심층 탐구"""
        
        company_name = company_info.get('name', '회사')
        
        # 꼬리 질문 생성 프롬프트
        prompt = f"""
당신은 {company_name}의 {interviewer_role} 담당 면접관입니다.

이전 질문: {previous_question}

사용자 답변: {user_answer}

춘식이 답변: {chun_sik_answer}

위 상황을 분석하여, 다음 중 하나의 목표를 달성할 수 있는 날카로운 꼬리 질문을 즉석에서 단 하나만 생성하세요:

목표 1 (심층 검증): 한 지원자의 답변에서 더 깊게 파고들 만한 부분을 찾아 구체적인 추가 설명을 요구하세요.
목표 2 (비교 분석): 두 답변의 차이점을 정확히 짚어내고, 각자의 선택에 대한 이유나 생각을 토론하도록 유도하세요.  
목표 3 (수준 조절): 한 지원자가 답변을 잘 못했다면, 그 상황을 고려하여 더 쉬운 개념 질문으로 전환하세요.

꼬리 질문 생성 가이드라인:
- 이전 답변의 구체적인 내용을 언급하며 질문하세요
- "방금 말씀하신 ~에 대해", "~라고 하셨는데" 등의 표현 활용
- 단순한 Yes/No 질문보다는 구체적인 설명을 요구하는 열린 질문
- 두 지원자 모두에게 공정하게 답변 기회 제공
- 면접관의 전문성이 드러나는 날카로운 관점

응답 형식:
{{"question": "질문 내용", "intent": "질문 의도"}}
"""
        return prompt.strip()