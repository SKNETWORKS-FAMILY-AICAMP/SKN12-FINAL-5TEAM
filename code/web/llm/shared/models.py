#!/usr/bin/env python3
"""
공용 데이터 모델
모든 모듈에서 사용하는 공통 데이터 클래스들
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel

# 기존 llm.core.llm_manager의 enum들은 제거되었음 - 문자열 타입 사용
from ..candidate.quality_controller import QualityLevel

# TYPE_CHECKING을 사용하여 순환 import 방지
if TYPE_CHECKING:
    from ..candidate.model import CandidatePersona

class LLMProvider(Enum):
    OPENAI_GPT4 = "openai_gpt4"
    OPENAI_GPT35 = "openai_gpt35"
    OPENAI_GPT4O_MINI = "openai_gpt4o_mini"
    OPENAI_GPT4O = "openai_gpt4o"
    GOOGLE_GEMINI_PRO = "google_gemini_pro"
    GOOGLE_GEMINI_FLASH = "google_gemini_flash"
    KT_BELIEF = "kt_belief"

class LLMResponse(BaseModel):
    """LLM 응답 표준화"""
    content: str
    provider: LLMProvider
    model_name: str
    token_count: Optional[int] = None
    response_time: Optional[float] = None
    error: Optional[str] = None

class QuestionType(Enum):
    """질문 유형"""
    INTRO = "자기소개"
    MOTIVATION = "지원동기"
    MOTIVE = "동기"
    HR = "인사"
    TECH = "기술"
    COLLABORATION = "협업"
    FOLLOWUP = "심화"
    GENERAL = "일반"
    BASIC = "기본"
    FUTURE = "미래"
    
    @classmethod
    def from_str(cls, value: str) -> 'QuestionType':
        """문자열로부터 QuestionType을 반환합니다.
        
        Args:
            value: 영어 문자열 ('HR', 'TECH', 'COLLABORATION' 등) 또는 한글 문자열
            
        Returns:
            QuestionType: 해당하는 QuestionType enum 값
            
        Raises:
            ValueError: 매핑되지 않는 값인 경우
        """
        # 영어 문자열 -> QuestionType 매핑
        english_mapping = {
            'HR': cls.HR,
            'TECH': cls.TECH,
            'COLLABORATION': cls.COLLABORATION,
            'INTRO': cls.INTRO,
            'MOTIVATION': cls.MOTIVATION,
            'MOTIVE': cls.MOTIVE,
            'FOLLOWUP': cls.FOLLOWUP,
            'GENERAL': cls.GENERAL,
            'BASIC': cls.BASIC,
            'FUTURE': cls.FUTURE
        }
        
        # 대소문자 무시하고 확인
        upper_value = value.upper()
        if upper_value in english_mapping:
            return english_mapping[upper_value]
        
        # 한글 문자열로 직접 매핑 시도
        for question_type in cls:
            if question_type.value == value:
                return question_type
        
        # 매핑되지 않으면 HR을 기본값으로 반환 (안전한 fallback)
        return cls.HR
    
    @classmethod
    def from_string(cls, value: str) -> 'QuestionType':
        """from_str의 별칭 메서드 - 호환성을 위해 추가"""
        return cls.from_str(value)

@dataclass
class QuestionAnswer:
    """질문-답변 쌍"""
    question_id: str
    question_type: QuestionType
    question_content: str
    answer_content: str
    timestamp: datetime
    question_intent: str = ""
    individual_score: int = 0
    individual_feedback: str = ""


@dataclass
class AnswerRequest:
    """답변 생성 요청"""
    question_content: str
    question_type: QuestionType
    question_intent: str
    company_id: str
    position: str
    quality_level: QualityLevel
    llm_provider: LLMProvider
    additional_context: Optional[str] = None

@dataclass
class AnswerResponse:
    """답변 생성 응답"""
    answer_content: str
    quality_level: QualityLevel
    llm_provider: LLMProvider
    persona_name: str
    confidence_score: float
    response_time: float
    reasoning: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

# 🆕 세션 관련 클래스들은 llm.session 모듈로 이동되었습니다.
# InterviewSession, ComparisonSession 등은 llm.session에서 import하여 사용하세요.

@dataclass
class AICandidatePersonaContext:
    """AI 지원자 페르소나 컨텍스트 (기존 AICandidateSession의 컨텍스트 기능만 분리)"""
    persona: 'CandidatePersona'
    
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
        for i, exp in enumerate(self.persona.experiences[:2], 1):
            context += f"{i}. {exp.get('company', '회사')}: {exp.get('position', '직책')} ({exp.get('period', '기간')})\n"
            if exp.get('achievements'):
                context += f"   주요 성과: {', '.join(exp['achievements'])}\n"
        
        return context

@dataclass
class ConversationHistoryContext:
    """대화 이력 컨텍스트 (기존 AICandidateSession의 컨텍스트 기능만 분리)"""
    question_answers: List[QuestionAnswer]
    
    def get_previous_answers_context(self) -> str:
        """이전 답변 컨텍스트 (일관성 유지용)"""
        if not self.question_answers:
            return ""
        
        context = "\n=== 이전 답변 내역 (일관성 유지) ===\n"
        for i, qa in enumerate(self.question_answers[-3:], 1):  # 최근 3개만
            context += f"{i}. [{qa.question_type.value}] {qa.question_content}\n"
            context += f"   답변: {qa.answer_content[:100]}...\n\n"
        
        return context
