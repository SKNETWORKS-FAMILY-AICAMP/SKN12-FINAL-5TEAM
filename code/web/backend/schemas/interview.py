from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# Pydantic 모델 정의
class InterviewSettings(BaseModel):
    """면접 설정 모델"""
    company: str
    position: str
    mode: str
    difficulty: str = "중간"
    candidate_name: str
    documents: Optional[List[str]] = None
    resume: Optional[Dict] = None
    posting_id: Optional[int] = None
    user_resume_id: Optional[int] = None
    use_interviewer_service: Optional[bool] = False
    calibration_data: Optional[Dict] = None

class QuestionRequest(BaseModel):
    """질문 요청 모델"""
    session_id: str
    question_index: int

class AnswerSubmission(BaseModel):
    """답변 제출 모델"""
    session_id: str
    question_id: str
    answer: str
    time_spent: int

class AICompetitionAnswerSubmission(BaseModel):
    """AI 경쟁 면접 답변 제출 모델 - question_id가 선택적"""
    session_id: str
    answer: str
    time_spent: int
    question_id: Optional[str] = None  # AI 경쟁 면접에서는 선택적

class InterviewResult(BaseModel):
    """면접 결과 모델"""
    session_id: str
    total_score: int
    category_scores: Dict[str, int]
    detailed_feedback: List[Dict]
    recommendations: List[str]

class ComparisonAnswerSubmission(BaseModel):
    """비교 면접 답변 제출 모델"""
    comparison_session_id: str
    answer: str

class AITurnRequest(BaseModel):
    """AI 턴 처리 요청 모델"""
    comparison_session_id: str
    step: str = "question"  # "question" 또는 "answer"
    
class CompetitionTurnSubmission(BaseModel):
    """경쟁 면접 통합 턴 제출 모델"""
    comparison_session_id: str
    answer: str

class InterviewHistoryResponse(BaseModel):
    detail_id: int
    interview_id: int
    who: str
    question_index: int
    question_id: int
    question_content: str
    question_intent: str
    question_level: int
    answer: str
    feedback: str
    sequence: int
    duration: int

class InterviewResponse(BaseModel):
    """면접 응답 모델"""
    interview_id: int
    user_id: int
    ai_resume_id: Optional[int] = None  # ✅ AI 면접에서만 사용
    user_resume_id: Optional[int] = None  # ✅ 사용자 면접에서만 사용
    posting_id: int
    company_id: int
    position_id: int
    total_feedback: str  # ✅ 필수 필드로 복원
    date: datetime
    company: Optional[Dict[str, str]] = None  # 회사 정보
    position: Optional[Dict[str, str]] = None  # 직무 정보

# TTS 요청: 텍스트 -> 음성
class TTSRequest(BaseModel):
    text: str
    voice_id: str

# TTS 응답
class TTSBase64Response(BaseModel):
    success: bool
    audio_base64: str

# STT 응답
class STTResponse(BaseModel):
    success: bool
    text: str
    language: str = "ko"
    duration: float = 0.0

class MemoUpdateRequest(BaseModel):
    interview_id: int
    question_index: int
    who: str
    memo: str
