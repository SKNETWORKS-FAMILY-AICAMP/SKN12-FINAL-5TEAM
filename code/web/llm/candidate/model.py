#!/usr/bin/env python3
"""
AI 지원자 모델 - LLM 기반 실시간 페르소나 생성
실제 이력서 데이터를 기반으로 LLM이 인간미 넘치는 페르소나를 실시간 생성
"""

import os
import json
import sys
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel

# .env 파일에서 환경변수 로드
load_dotenv()

# 상위 디렉토리의 database 모듈 접근을 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from backend.services.supabase_client import get_supabase_client
except ImportError:
    print("WARNING: Supabase 클라이언트를 가져올 수 없습니다. 파일 기반 fallback만 사용됩니다.")
    get_supabase_client = None

from ..shared.models import LLMProvider, LLMResponse
from .quality_controller import AnswerQualityController, QualityLevel
from .prompt import CandidatePromptBuilder
from ..shared.models import QuestionType, QuestionAnswer, AnswerRequest, AnswerResponse
from backend.models.session import InterviewSession  # 호환성을 위한 별도 모듈
from ..shared.utils import safe_json_load, get_fixed_questions

# 직군 매핑 (position_name -> position_id)
POSITION_MAPPING = {
    "프론트엔드 개발자": 1,
    "프론트": 1,
    "frontend": 1,
    "백엔드": 2,
    "백엔드 개발자": 2,
    "backend": 2,
    "기획": 3,
    "기획자": 3,
    "pm": 3,
    "product manager": 3,
    "AI": 4,
    "ai": 4,
    "인공지능": 4,
    "머신러닝": 4,
    "ml": 4,
    "데이터사이언스": 5,
    "데이터": 5,
    "data science": 5,
    "data scientist": 5,
    "ds": 5,
    # 🆕 모바일 개발자 매핑 추가
    "모바일": 6,
    "모바일개발자": 6,
    "모바일개발자android": 6,
    "모바일개발자ios": 6,
    "android": 6,
    "ios": 6,
    "mobile": 6,
    "앱개발자": 6,
    "앱": 6,
    # 🆕 기타 일반적인 직군들 추가
    "풀스택": 7,
    "fullstack": 7,
    "풀스택개발자": 7,
    "devops": 8,
    "데브옵스": 8,
    "인프라": 8,
    "qa": 9,
    "테스터": 9,
    "품질관리": 9
}

# 새로운 CandidatePersona 모델 (LLM 생성용)
class CandidatePersona(BaseModel):
    """LLM이 생성하는 인간미 넘치는 페르소나 모델"""
    # --- LLM 생성 정보 ---
    name: str
    summary: str  # 예: "5년차 Java 백엔드 개발자로, 대용량 트래픽 처리와 MSA 설계에 강점이 있습니다."
    background: Dict[str, Any]
    technical_skills: List[str]
    projects: List[Dict[str, Any]]  # 각 프로젝트에 'achievements'와 'challenges' 포함
    experiences: List[Dict[str, Any]]
    strengths: List[str]
    weaknesses: List[str]  # 개선하고 싶은 점
    motivation: str  # 개발자/기술에 대한 개인적 동기나 스토리
    inferred_personal_experiences: List[Dict[str, str]]  # 이력서 기반으로 추론된 개인적 교훈
    career_goal: str
    personality_traits: List[str]
    interview_style: str
    
    # --- 메타데이터 ---
    generated_by: str = "gpt-4o-mini"
    resume_id: int  # 원본 이력서 ID

# 모델별 AI 지원자 이름 매핑 (호환성을 위해 유지)
AI_CANDIDATE_NAMES = {
    LLMProvider.OPENAI_GPT4: "춘식이",
    LLMProvider.OPENAI_GPT35: "춘식이", 
    LLMProvider.OPENAI_GPT4O_MINI: "춘식이",
    LLMProvider.GOOGLE_GEMINI_PRO: "제미니",
    LLMProvider.GOOGLE_GEMINI_FLASH: "제미니",
    LLMProvider.KT_BELIEF: "믿음이"
}

class AICandidateSession(InterviewSession):
    """AI 지원자 전용 면접 세션 - 면접자와 동일한 플로우"""
    
    def __init__(self, company_id: str, position: str, persona: 'CandidatePersona'):
        super().__init__(company_id, position, persona.name)
        self.persona = persona
        self.ai_answers: List[QuestionAnswer] = []
        
        # 면접자와 동일한 20개 질문 계획 사용
        # 이미 부모 클래스에서 self.question_plan이 20개로 설정됨
        
    def add_ai_answer(self, qa_pair: QuestionAnswer):
        """AI 답변 추가"""
        self.ai_answers.append(qa_pair)
        # 부모 클래스의 add_qa_pair 메서드를 사용하여 일관성 유지
        super().add_qa_pair(qa_pair)
    
    @property
    def question_answers(self) -> List[QuestionAnswer]:
        """FeedbackService 호환성을 위한 question_answers property - conversation_history 반환"""
        return super().question_answers
        
    def get_persona_context(self) -> str:
        """페르소나 컨텍스트 구성"""
        context = f"""
=== AI 지원자 페르소나 정보 ===
이름: {self.persona.name}
경력: {self.persona.background.get('career_years', '0')}년
현재 직책: {self.persona.background.get('current_position', '지원자')}
주요 기술: {', '.join(self.persona.technical_skills[:5])}
강점: {', '.join(self.persona.strengths[:3])}
커리어 목표: {self.persona.career_goal}
성격 특성: {', '.join(self.persona.personality_traits)}
면접 스타일: {self.persona.interview_style}

=== 주요 프로젝트 ===
"""
        for i, project in enumerate(self.persona.projects[:2], 1):
            context += f"{i}. {project.get('name', '프로젝트')}: {project.get('description', '')}\n"
            context += f"   기술스택: {', '.join(project.get('tech_stack', []))}\n"
            if project.get('achievements'):
                context += f"   성과: {', '.join(project['achievements'])}\n"
        
        context += f"""
=== 업무 경험 ===
"""
        for exp in self.persona.experiences[:2]:
            context += f"- {exp.get('company', '회사')}: {exp.get('position', '개발자')} ({exp.get('period', '기간')})\n"
            if exp.get('achievements'):
                context += f"  성과: {', '.join(exp['achievements'])}\n"
        
        return context
    
    def get_previous_answers_context(self) -> str:
        """이전 답변 컨텍스트 (일관성 유지용)"""
        if not self.ai_answers:
            return ""
        
        context = "\n=== 이전 답변 내역 (일관성 유지) ===\n"
        for i, qa in enumerate(self.ai_answers[-3:], 1):  # 최근 3개만
            context += f"{i}. [{qa.question_type.value}] {qa.question_content}\n"
            context += f"   답변: {qa.answer_content[:100]}...\n\n"
        
        return context

class AICandidateModel:
    """AI 지원자 모델 메인 클래스"""
    
    def __init__(self, api_key: str = None, quality_controller: AnswerQualityController = None):
        # OpenAI 클라이언트 직접 초기화
        import openai
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.openai_client = openai.OpenAI(api_key=self.api_key)
            print("OK: OpenAI 클라이언트 초기화 완료")
        else:
            self.openai_client = None
            print("WARNING: OpenAI API 키가 설정되지 않았습니다. .env 파일에 OPENAI_API_KEY를 추가하거나 직접 전달하세요.")
        
        # 🆕 의존성 주입 패턴: quality_controller를 외부에서 주입 받거나 기본값 사용
        if quality_controller is not None:
            self.quality_controller = quality_controller
            print("OK [DI] 외부에서 주입된 QualityController 사용")
        else:
            self.quality_controller = AnswerQualityController()
            print("OK [DI] 기본 QualityController 생성")
            
        # 🆕 프롬프트 빌더 초기화
        self.prompt_builder = CandidatePromptBuilder()
        print("OK [DI] CandidatePromptBuilder 초기화 완료")
            
        self.companies_data = self._load_companies_data()
        
        # AI 지원자 세션 관리
        self.ai_sessions: Dict[str, 'AICandidateSession'] = {}
        self.fixed_questions = self._load_fixed_questions()
        
        # 새로운 LLM 기반 시스템에서는 페르소나를 동적으로 생성하므로 빈 딕셔너리로 초기화
        self.candidate_personas: Dict[str, CandidatePersona] = {}
        self.personas_data = {"personas": {}}
    
    def create_persona_for_interview(self, company_name: str, position_name: str) -> Optional[CandidatePersona]:
        """
        주어진 회사와 직군에 맞는 AI 지원자 페르소나를 LLM으로 실시간 생성
        """
        try:
            print(f"DEBUG [PERSONA DEBUG] 페르소나 생성 시작: company='{company_name}', position='{position_name}'")
            
            company_korean_name = self._get_company_korean_name(company_name)
            position_id = self._get_position_id(position_name, company_korean_name)
            
            if not position_id:
                print(f"ERROR [PERSONA DEBUG] 지원하지 않는 직군: {position_name}, 기본 페르소나 생성 시도")
                return self._create_default_persona(company_korean_name, position_name)
            
            resume_data = self._get_random_resume_from_db(position_id)
            if not resume_data:
                print(f"ERROR [PERSONA DEBUG] 이력서 없음: position_id {position_id}, 기본 페르소나 생성 시도")
                return self._create_default_persona(company_korean_name, position_name)
            
            company_info = self._get_company_info(company_name)
            
            prompt = self.prompt_builder.build_persona_generation_prompt(resume_data, company_name, position_name, company_info)
            system_prompt = self.prompt_builder.build_system_prompt_for_persona_generation()
            
            llm_response = self._generate_persona_with_extended_tokens(prompt, system_prompt)
            
            if llm_response.error:
                print(f"ERROR [PERSONA DEBUG] LLM 응답 오류: {llm_response.error}")
                return None
            
            persona = self._parse_llm_response_to_persona(llm_response.content, resume_data.get('ai_resume_id', 0))
            
            if persona:
                print(f"OK [PERSONA DEBUG] 페르소나 생성 완료: {persona.name} ({company_name} {position_name})")
                return persona
            else:
                print(f"ERROR [PERSONA DEBUG] 페르소나 파싱 실패")
                return None
                
        except Exception as e:
            print(f"ERROR [PERSONA DEBUG] 페르소나 생성 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_position_id(self, position_name: str, company_name: str = None) -> Optional[int]:
        """직군명을 position_id로 변환"""
        # ... (이하 코드는 이전과 동일)
        try:
            # 🆕 1순위: DB에서 직접 조회 (company_name이 있는 경우)
            if company_name and get_supabase_client:
                from backend.services.existing_tables_service import existing_tables_service
                import asyncio
                import concurrent.futures
                
                def run_async_safely():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            existing_tables_service.find_posting_by_company_position(company_name, position_name)
                        )
                    finally:
                        loop.close()
                
                try:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_async_safely)
                        posting_info = future.result(timeout=10)
                    
                    if posting_info and posting_info.get('position', {}).get('position_id'):
                        return posting_info['position']['position_id']
                except Exception as db_error:
                    print(f"WARNING [DB] 직군 조회 실패: {db_error}")
            
            position_lower = position_name.lower().replace(" ", "").replace("(", "").replace(")", "")
            return POSITION_MAPPING.get(position_lower)
            
        except Exception as e:
            print(f"ERROR [POSITION] 직군 ID 변환 오류: {e}")
            return None
    
    def _get_random_resume_from_db(self, position_id: int) -> Optional[Dict[str, Any]]:
        """데이터베이스에서 해당 직군의 이력서를 무작위로 선택"""
        if get_supabase_client is None:
            return None
        try:
            response = get_supabase_client().table('ai_resume').select('*').eq('position_id', position_id).execute()
            return random.choice(response.data) if response.data else None
        except Exception as e:
            print(f"ERROR 이력서 조회 오류: {e}")
            return None
    
    def _get_company_info(self, company_name: str) -> Dict[str, Any]:
        """회사 정보 가져오기"""
        for company in self.companies_data.get("companies", []):
            if company.get("name", "").lower() == company_name.lower() or company.get("id", "").lower() == company_name.lower():
                return company
        return {"name": company_name, "core_competencies": [], "tech_focus": [], "talent_profile": ""}
    
    def _generate_persona_with_extended_tokens(self, prompt: str, system_prompt: str) -> LLMResponse:
        """페르소나 생성용 확장된 토큰으로 LLM 호출"""
        if not self.openai_client:
            return LLMResponse(content="", provider=LLMProvider.OPENAI_GPT4O_MINI, model_name="gpt-4o-mini", error="OpenAI API 키가 설정되지 않았습니다.")
        try:
            import time
            start_time = time.time()
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, max_tokens=1500, temperature=0.7, timeout=60.0
            )
            response_time = time.time() - start_time
            return LLMResponse(
                content=response.choices[0].message.content.strip(),
                provider=LLMProvider.OPENAI_GPT4O_MINI,
                model_name="gpt-4o-mini",
                token_count=response.usage.total_tokens if response.usage else None,
                response_time=response_time
            )
        except Exception as e:
            return LLMResponse(content="", provider=LLMProvider.OPENAI_GPT4O_MINI, model_name="gpt-4o-mini", error=f"페르소나 생성 LLM 호출 실패: {e}")
    
    def _parse_llm_response_to_persona(self, llm_response: str, resume_id: int) -> Optional[CandidatePersona]:
        """LLM JSON 응답을 CandidatePersona 객체로 파싱"""
        try:
            response_clean = llm_response.strip()
            if response_clean.startswith('```json'):
                response_clean = response_clean.replace('```json', '').replace('```', '').strip()
            persona_data = json.loads(response_clean)
            return CandidatePersona(**persona_data, resume_id=resume_id)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"ERROR JSON 파싱 또는 페르소나 객체 생성 오류: {e}")
            return None
    
    def _load_companies_data(self) -> Dict[str, Any]:
        """회사 데이터 로드"""
        return safe_json_load("llm/data/companies_data.json", {"companies": []})
    
    def _create_default_persona(self, company_name: str, position_name: str) -> Optional[CandidatePersona]:
        """fallback: 기본 페르소나 생성"""
        # ... (이하 코드는 이전과 동일)
        try:
            print(f"INFO [DEFAULT PERSONA] 기본 페르소나 생성 시작: {company_name} - {position_name}")
            company_info = self._get_company_info(company_name)
            company_name = company_info.get("name", company_name.capitalize())
            
            default_persona = CandidatePersona(
                name=f"{company_name} 지원자",
                summary=f"{position_name} 개발자로 {company_name}에 지원하는 경력 3년차 개발자입니다.",
                background={"career_years": "3", "current_position": f"{position_name} 개발자", "education": ["대학교 컴퓨터공학과 졸업"], "total_experience": "3년"},
                technical_skills=self._get_default_tech_skills(position_name),
                projects=[{"name": f"{position_name} 프로젝트", "description": f"{position_name} 개발 프로젝트 경험", "tech_stack": self._get_default_tech_skills(position_name)[:3], "achievements": ["성공적인 프로젝트 완수", "팀워크 향상에 기여"]}],
                experiences=[{"company": "기존 회사", "position": f"{position_name} 개발자", "period": "2021 - 현재", "achievements": ["프로젝트 성공적 완수", "기술 역량 향상"]}],
                strengths=["문제 해결 능력", "팀워크", "학습 의지"],
                weaknesses=["완벽주의적 성향"],
                motivation=f"{company_name}에서 {position_name} 개발자로 성장하고 싶습니다.",
                inferred_personal_experiences=[{"category": "학습", "experience": "지속적인 기술 학습을 통해 성장해왔습니다.", "lesson": "꾸준한 학습의 중요성을 깨달았습니다."}],
                career_goal=f"{company_name}에서 {position_name} 전문가로 성장하고 싶습니다.",
                personality_traits=["성실함", "적극성", "협력적"],
                interview_style="진정성 있고 논리적으로 답변하는 스타일",
                resume_id=0
            )
            return default_persona
        except Exception as e:
            print(f"ERROR [DEFAULT PERSONA] 기본 페르소나 생성 실패: {e}")
            return None

    def _get_company_korean_name(self, company_code: str) -> str:
        """회사 코드를 한국어 회사명으로 변환"""
        company_mapping = {
            "naver": "네이버", "kakao": "카카오", "toss": "토스", "line": "라인",
            "라인플러스": "라인플러스", "coupang": "쿠팡", "baemin": "배달의민족", "daangn": "당근마켓",
            "네이버": "네이버", "카카오": "카카오", "토스": "토스", "라인": "라인", 
            "쿠팡": "쿠팡", "배달의민족": "배달의민족", "당근마켓": "당근마켓"
        }
        return company_mapping.get(company_code.lower(), company_code.capitalize())
    
    def _load_fixed_questions(self) -> Dict[str, List[Dict]]:
        """고정 질문 데이터 로드"""
        return get_fixed_questions()

    def generate_answer(self, request: AnswerRequest, persona: CandidatePersona = None) -> AnswerResponse:
        """질문에 대한 AI 지원자 답변 생성"""
        start_time = datetime.now()
        
        if not persona:
            persona = self.create_persona_for_interview(request.company_id, request.position)
            if not persona:
                persona = self._create_default_persona(request.company_id, request.position)
        
        if not persona:
            return AnswerResponse(
                answer_content="죄송합니다. 지원자 정보를 생성하는 데 실패했습니다. 다시 시도해주세요.",
                quality_level=request.quality_level, llm_provider=request.llm_provider,
                persona_name="오류", confidence_score=0.1, response_time=0.1,
                reasoning="페르소나 생성 최종 실패", error="Persona creation failed"
            )
        
        company_data = self._get_company_info(request.company_id)
        
        prompt = self.prompt_builder.build_prompt(request, persona, company_data)
        
        config = self.quality_controller.get_quality_config(request.quality_level)
        quality_prompt = self.quality_controller.generate_quality_prompt(prompt, request.quality_level, request.question_type.value)
        
        # system_prompt 생성
        system_prompt = self.prompt_builder.build_system_prompt(persona, company_data, request.question_type, request.llm_provider)
        
        llm_response = self._generate_llm_answer(quality_prompt, system_prompt, config)
        
        response_time = (datetime.now() - start_time).total_seconds()
        confidence_score = self._calculate_confidence_score(llm_response, request.quality_level)
        processed_answer = self.quality_controller.process_complete_answer(llm_response.content, request.quality_level, request.question_type.value)
        
        return AnswerResponse(
            answer_content=processed_answer,
            quality_level=request.quality_level,
            llm_provider=llm_response.provider,
            persona_name=self.get_ai_name(llm_response.provider),
            confidence_score=confidence_score,
            response_time=response_time,
            reasoning=f"{self.get_ai_name(llm_response.provider)}의 답변",
            error=llm_response.error,
            metadata={
                "token_count": llm_response.token_count,
                "company_id": request.company_id,
                "question_type": request.question_type.value,
                "original_prompt_length": len(prompt),
                "persona_name_internal": persona.name
            }
        )

    def _generate_llm_answer(self, prompt: str, system_prompt: str, config) -> LLMResponse:
        """LLM 답변 생성 로직"""
        if not self.openai_client:
            return LLMResponse(content="", provider=LLMProvider.OPENAI_GPT4O_MINI, model_name=config.model_name, error="OpenAI API 키가 설정되지 않았습니다.")
        try:
            import time
            start_time = time.time()
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
            response = self.openai_client.chat.completions.create(
                model=config.model_name, messages=messages, max_tokens=400,
                temperature=config.temperature, timeout=60.0
            )
            response_time = time.time() - start_time
            provider = LLMProvider.OPENAI_GPT4O if config.model_name == "gpt-4o" else LLMProvider.OPENAI_GPT4O_MINI
            return LLMResponse(
                content=response.choices[0].message.content.strip(),
                provider=provider, model_name=config.model_name,
                token_count=response.usage.total_tokens if response.usage else None,
                response_time=response_time
            )
        except Exception as e:
            provider = LLMProvider.OPENAI_GPT4O if config.model_name == "gpt-4o" else LLMProvider.OPENAI_GPT4O_MINI
            return LLMResponse(content="", provider=provider, model_name=config.model_name, error=f"API 호출 실패: {e}")

    def _calculate_confidence_score(self, llm_response: LLMResponse, quality_level: QualityLevel) -> float:
        """답변 신뢰도 점수 계산"""
        if llm_response.error: return 0.0
        base_score = 0.7
        quality_bonus = (quality_level.value - 5) * 0.05
        length_bonus = min(len(llm_response.content) / 1000, 0.2)
        time_bonus = 0.1 if llm_response.response_time and llm_response.response_time < 3.0 else 0.0
        confidence = min(base_score + quality_bonus + length_bonus + time_bonus, 1.0)
        return round(confidence, 2)

    def get_ai_name(self, llm_provider: LLMProvider) -> str:
        """모델에 따른 AI 지원자 이름 반환"""
        return AI_CANDIDATE_NAMES.get(llm_provider, "춘식이")

    def _get_default_tech_skills(self, position: str) -> List[str]:
        """직군별 기본 기술 스택"""
        tech_mapping = {
            "프론트엔드": ["JavaScript", "React", "HTML/CSS", "TypeScript", "Vue.js"],
            "백엔드": ["Java", "Spring Boot", "MySQL", "Python", "Node.js"],
            "풀스택": ["JavaScript", "React", "Node.js", "MySQL", "TypeScript"],
            "AI": ["Python", "TensorFlow", "PyTorch", "Machine Learning", "Data Science"],
            "데이터": ["Python", "SQL", "Pandas", "Tableau", "R"],
            "기획": ["Product Management", "기획", "분석", "Communication", "Strategy"]
        }
        return tech_mapping.get(position, tech_mapping["백엔드"])