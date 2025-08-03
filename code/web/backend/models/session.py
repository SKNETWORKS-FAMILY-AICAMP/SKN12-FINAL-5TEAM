#!/usr/bin/env python3
"""
호환성을 위한 InterviewSession 클래스
기존 llm/session/models.py의 InterviewSession과 동일한 인터페이스 제공
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from llm.shared.models import QuestionAnswer, QuestionType


class InterviewSession:
    """
    호환성을 위한 InterviewSession 클래스
    기존 llm/session/models.py의 InterviewSession과 동일한 인터페이스 제공
    """
    
    def __init__(self, company_id: str, position: str, candidate_name: str, session_type: str = "individual"):
        self.company_id = company_id
        self.position = position
        self.candidate_name = candidate_name
        self.session_type = session_type
        self.conversation_history: List[QuestionAnswer] = []
        self.current_question_count = 0
        self.session_id = f"{company_id}_{position.replace(' ', '_')}_{int(time.time())}"
        self.created_at = datetime.now()
        self.state = "CREATED"  # SessionState enum 대신 문자열 사용
        
        # 고정된 질문 순서 (총 20개 질문)
        self.question_plan = [
            # 기본 질문 (2개)
            {"type": QuestionType.INTRO, "fixed": True},
            {"type": QuestionType.MOTIVATION, "fixed": True},
            
            # 인사 영역 (6개)
            {"type": QuestionType.HR, "fixed": False},
            {"type": QuestionType.HR, "fixed": False},
            {"type": QuestionType.HR, "fixed": False},
            {"type": QuestionType.HR, "fixed": False},
            {"type": QuestionType.HR, "fixed": False},
            {"type": QuestionType.HR, "fixed": False},
            
            # 기술 영역 (8개)
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            
            # 협업 영역 (3개)
            {"type": QuestionType.COLLABORATION, "fixed": False},
            {"type": QuestionType.COLLABORATION, "fixed": False},
            {"type": QuestionType.COLLABORATION, "fixed": False},
            
            # 심화 질문 (1개)
            {"type": QuestionType.FOLLOWUP, "fixed": False}
        ]
        
    def start_session(self):
        """세션 시작"""
        self.state = "ACTIVE"
        
    def pause_session(self):
        """세션 일시정지"""
        self.state = "PAUSED"
        
    def complete_session(self):
        """세션 완료"""
        self.state = "COMPLETED"
        
    def add_qa_pair(self, qa_pair: QuestionAnswer):
        """질문-답변 쌍 추가"""
        self.conversation_history.append(qa_pair)
        self.current_question_count += 1
        
    def get_next_question_plan(self) -> Optional[Dict]:
        """다음 질문 계획 가져오기"""
        if self.current_question_count < len(self.question_plan):
            return self.question_plan[self.current_question_count]
        return None
        
    def is_complete(self) -> bool:
        """세션 완료 여부 확인"""
        return self.current_question_count >= len(self.question_plan)
        
    @property
    def question_answers(self) -> List[QuestionAnswer]:
        """FeedbackService 호환성을 위한 question_answers property"""
        return self.conversation_history
    
    def get_conversation_context(self) -> str:
        """대화 컨텍스트 생성"""
        context = f"면접 진행 상황: {self.current_question_count}/{len(self.question_plan)}\n"
        context += f"지원자: {self.candidate_name}님\n"
        context += f"지원 직군: {self.position}\n\n"
        
        if self.conversation_history:
            context += "이전 대화 내용:\n"
            for i, qa in enumerate(self.conversation_history, 1):
                context += f"{i}. [{qa.question_type.value}] {qa.question_content}\n"
                context += f"   답변: {qa.answer_content[:100]}...\n\n"
        
        return context