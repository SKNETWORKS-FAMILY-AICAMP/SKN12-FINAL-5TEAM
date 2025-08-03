#!/usr/bin/env python3
"""
🚫 DEPRECATED - 더 이상 사용하지 않음

이 모듈의 모든 기능은 backend/services/interview_service.py로 이관되었습니다.
새로운 Backend 중앙 관제 시스템을 사용하세요.

기존 설명: 세션 관련 데이터 모델
기존 llm/core/interview_system.py와 unified_interview_session.py에서 이동
"""

# 🗑️ 모든 import 주석 처리 - 더 이상 사용하지 않음
# import time
# from datetime import datetime
# from typing import List, Dict, Any, Optional, TYPE_CHECKING
# from dataclasses import dataclass, field
# from enum import Enum

# # shared 모듈에서 공통 타입 import
# from ..shared.models import QuestionType, QuestionAnswer

# # 순환 import 방지를 위한 TYPE_CHECKING 사용
# if TYPE_CHECKING:
#     from ..candidate.model import CandidatePersona

# ⚠️ DEPRECATED: 이 모듈을 사용하려고 하면 경고가 발생합니다.
raise DeprecationWarning(
    "🚫 llm.session.models 는 더 이상 사용되지 않습니다. "
    "backend.services.interview_service.SessionState 를 사용하세요."
)

# 🗑️ 기존 코드 모두 주석 처리


# class SessionState(Enum):
#     """세션 상태"""
#     CREATED = "created"
#     ACTIVE = "active"
#     PAUSED = "paused"
#     COMPLETED = "completed"
#     CANCELLED = "cancelled"


# @dataclass
# class QuestionData:
#     """질문 데이터 클래스 (unified_interview_session.py에서 이동)"""
#     id: str
#     content: str
#     category: str
#     intent: str
#     time_limit: int = 120
#     keywords: List[str] = field(default_factory=list)


# @dataclass
# class AnswerData:
#     """답변 데이터 클래스 (unified_interview_session.py에서 이동)"""
#     question_id: str
#     content: str
#     time_spent: int
#     timestamp: datetime
#     answer_type: str  # "human" or "ai"
#     score: Optional[int] = None
#     metadata: Dict[str, Any] = field(default_factory=dict)


# class InterviewSession:
#     """
#     기본 면접 세션 클래스
#     기존 llm/core/interview_system.py에서 이동 및 개선
#     """
#     
#     def __init__(self, company_id: str, position: str, candidate_name: str, session_type: str = "individual"):
#         self.company_id = company_id
#         self.position = position
#         self.candidate_name = candidate_name
#         self.session_type = session_type
#         self.conversation_history: List[QuestionAnswer] = []
#         self.current_question_count = 0
#         self.session_id = f"{company_id}_{position.replace(' ', '_')}_{int(time.time())}"
#         self.created_at = datetime.now()
#         self.state = SessionState.CREATED
#         
#         # 고정된 질문 순서 (총 20개 질문)
#         self.question_plan = [
#             # 기본 질문 (2개)
#             {"type": QuestionType.INTRO, "fixed": True},
#             {"type": QuestionType.MOTIVATION, "fixed": True},
#             
#             # 인사 영역 (6개)
#             {"type": QuestionType.HR, "fixed": False},
#             {"type": QuestionType.HR, "fixed": False},
#             {"type": QuestionType.HR, "fixed": False},
#             {"type": QuestionType.HR, "fixed": False},
#             {"type": QuestionType.HR, "fixed": False},
#             {"type": QuestionType.HR, "fixed": False},
#             
#             # 기술 영역 (8개)
#             {"type": QuestionType.TECH, "fixed": False},
#             {"type": QuestionType.TECH, "fixed": False},
#             {"type": QuestionType.TECH, "fixed": False},
#             {"type": QuestionType.TECH, "fixed": False},
#             {"type": QuestionType.TECH, "fixed": False},
#             {"type": QuestionType.TECH, "fixed": False},
#             {"type": QuestionType.TECH, "fixed": False},
#             {"type": QuestionType.TECH, "fixed": False},
#             
#             # 협업 영역 (3개)
#             {"type": QuestionType.COLLABORATION, "fixed": False},
#             {"type": QuestionType.COLLABORATION, "fixed": False},
#             {"type": QuestionType.COLLABORATION, "fixed": False},
#             
#             # 심화 질문 (1개)
#             {"type": QuestionType.FOLLOWUP, "fixed": False}
#         ]
#         
#     def start_session(self):
#         """세션 시작"""
#         self.state = SessionState.ACTIVE
#         
#     def pause_session(self):
#         """세션 일시정지"""
#         self.state = SessionState.PAUSED
#         
#     def complete_session(self):
#         """세션 완료"""
#         self.state = SessionState.COMPLETED
#         
#     def add_qa_pair(self, qa_pair: QuestionAnswer):
#         """질문-답변 쌍 추가"""
#         self.conversation_history.append(qa_pair)
#         self.current_question_count += 1
#         
#     def get_next_question_plan(self) -> Optional[Dict]:
#         """다음 질문 계획 가져오기"""
#         if self.current_question_count < len(self.question_plan):
#             return self.question_plan[self.current_question_count]
#         return None
#         
#     def is_complete(self) -> bool:
#         """세션 완료 여부 확인"""
#         return self.current_question_count >= len(self.question_plan)
#         
#     @property
#     def question_answers(self) -> List[QuestionAnswer]:
#         """FeedbackService 호환성을 위한 question_answers property"""
#         return self.conversation_history
#     
#     def get_conversation_context(self) -> str:
#         """대화 컨텍스트 생성"""
#         context = f"면접 진행 상황: {self.current_question_count}/{len(self.question_plan)}\n"
#         context += f"지원자: {self.candidate_name}님\n"
#         context += f"지원 직군: {self.position}\n\n"
#         
#         if self.conversation_history:
#             context += "이전 대화 내용:\n"
#             for i, qa in enumerate(self.conversation_history, 1):
#                 context += f"{i}. [{qa.question_type.value}] {qa.question_content}\n"
#                 context += f"   답변: {qa.answer_content[:100]}...\n\n"
#         
#         return context


# @dataclass
# class ComparisonSession:
#     """
#     사용자 vs AI 비교 세션
#     기존 unified_interview_session.py 로직 통합
#     """
#     comparison_id: str
#     user_session_id: str
#     ai_session_id: str
#     company_id: str
#     position: str
#     current_question_index: int = 0
#     current_phase: str = "user_turn"  # "user_turn" or "ai_turn"
#     total_questions: int = 20
#     user_name: str = ""
#     ai_name: str = "춘식이"
#     user_answers: List[AnswerData] = field(default_factory=list)
#     ai_answers: List[AnswerData] = field(default_factory=list)
#     starts_with_user: bool = True
#     created_at: datetime = field(default_factory=datetime.now)
#     state: SessionState = SessionState.CREATED
#     
#     # 🆕 AI 페르소나 일관성을 위한 필드
#     ai_persona: Optional['CandidatePersona'] = None
#     
#     def switch_phase(self):
#         """턴 전환"""
#         self.current_phase = "ai_turn" if self.current_phase == "user_turn" else "user_turn"
#     
#     def next_question(self):
#         """다음 질문으로 이동 - 사용자와 AI 모두 답변한 후에만 호출되어야 함"""
#         self.current_question_index += 1
#         if self.current_question_index >= self.total_questions:
#             self.state = SessionState.COMPLETED
#     
#     def both_answered_current_question(self) -> bool:
#         """현재 질문에 대해 사용자와 AI 모두 답변했는지 확인"""
#         current_q_id = f"q_{self.current_question_index + 1}"
#         
#         user_answered = any(answer.question_id == current_q_id for answer in self.user_answers)
#         ai_answered = any(answer.question_id == current_q_id for answer in self.ai_answers)
#         
#         # 디버깅 로그 추가
#         from ..shared.logging_config import interview_logger
#         interview_logger.info(f"🔍 both_answered_current_question 디버깅:")
#         interview_logger.info(f"  - current_q_id: {current_q_id}")
#         interview_logger.info(f"  - current_question_index: {self.current_question_index}")
#         interview_logger.info(f"  - user_answers: {[a.question_id for a in self.user_answers]}")
#         interview_logger.info(f"  - ai_answers: {[a.question_id for a in self.ai_answers]}")
#         interview_logger.info(f"  - user_answered: {user_answered}")
#         interview_logger.info(f"  - ai_answered: {ai_answered}")
#         interview_logger.info(f"  - result: {user_answered and ai_answered}")
#         
#         return user_answered and ai_answered
#     
#     def should_advance_question(self) -> bool:
#         """질문을 다음으로 넘어가야 하는지 확인"""
#         return self.both_answered_current_question() and not self.is_complete()
#     
#     def is_complete(self) -> bool:
#         """비교 세션 완료 여부"""
#         return self.state == SessionState.COMPLETED or self.current_question_index >= self.total_questions
#     
#     def get_progress(self) -> Dict[str, Any]:
#         """진행 상황 반환"""
#         return {
#             "current_question": self.current_question_index + 1,
#             "total_questions": self.total_questions,
#             "current_phase": self.current_phase,
#             "progress_percentage": (self.current_question_index / self.total_questions) * 100,
#             "state": self.state.value
#         }