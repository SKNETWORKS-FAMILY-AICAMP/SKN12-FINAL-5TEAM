from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class QuestionAnswerPair(BaseModel):
    """개별 질문-답변 쌍"""
    question: str
    answer: str
    duration: Optional[int] = None  # 답변 소요 시간 (초)
    question_level: Optional[int] = None

class QuestionRequest(BaseModel):
    """전체 면접 질문-답변 평가 요청"""
    user_id: int
    ai_resume_id: Optional[int] = None
    user_resume_id: Optional[int] = None
    posting_id: Optional[int] = None
    company_id: Optional[int] = None
    position_id: Optional[int] = None
    qa_pairs: List[QuestionAnswerPair]  # 질문-답변 쌍들의 리스트

class QuestionResponse(BaseModel):
    """전체 면접 평가 응답"""
    success: bool
    interview_id: Optional[int] = None
    message: str
    total_questions: int
    overall_score: Optional[int] = None
    overall_feedback: Optional[str] = None
    per_question_results: Optional[List['PerQuestionResult']] = None
    interview_plan: Optional['InterviewPlan'] = None

# DB 테이블 구조 기반 구체적인 타입 모델들
class PerQuestionResult(BaseModel):
    """개별 질문 평가 결과 - history_detail 테이블 기반"""
    question: str
    answer: str
    intent: str
    final_score: int
    evaluation: str
    improvement: str

class InterviewPlan(BaseModel):
    """면접 준비 계획 - plans 테이블 기반"""
    shortly_plan: Dict[str, List[str]]  # 단기 계획: 카테고리별 항목 리스트
    long_plan: Dict[str, List[str]]     # 장기 계획: 카테고리별 항목 리스트
    plan_id: Optional[int] = None

class CompanyInfo(BaseModel):
    """회사 정보 - company 테이블 기반"""
    company_id: int
    name: str
    talent_profile: Optional[str] = None
    core_competencies: List[str] = []
    tech_focus: List[str] = []
    interview_keywords: List[str] = []
    question_direction: Optional[str] = None
    company_culture: Dict[str, Any] = {}
    technical_challenges: List[str] = []

class EvaluationFeedback(BaseModel):
    """평가 피드백 - history_detail.feedback JSON 구조"""
    final_score: int
    evaluation: str
    improvement: str

class InterviewSession(BaseModel):
    """면접 세션 정보 - interview 테이블 기반"""
    interview_id: int
    user_id: int
    ai_resume_id: Optional[int] = None
    user_resume_id: Optional[int] = None
    posting_id: Optional[int] = None
    company_id: Optional[int] = None
    position_id: Optional[int] = None
    total_feedback: Optional[Dict[str, Any]] = None
    date: Optional[str] = None

class PlansRequest(BaseModel):
    """면접 준비 계획 생성 요청"""
    interview_id: int

class PlansResponse(BaseModel):
    """면접 준비 계획 생성 응답"""
    success: bool
    interview_plan: Optional[InterviewPlan] = None
    plan_id: Optional[int] = None
    message: str
    interview_id: int

# Forward references 해결
QuestionResponse.model_rebuild()