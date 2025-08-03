#!/usr/bin/env python3
"""
🚫 DEPRECATED - 더 이상 사용하지 않음

이 모듈의 모든 기능은 backend/services/interview_service.py로 이관되었습니다.
새로운 Backend 중앙 관제 시스템을 사용하세요.

기존 설명: AI vs Human 비교 세션 관리자
기존 unified_interview_session.py 기능을 담당
"""

# 🗑️ 모든 import 주석 처리 - 더 이상 사용하지 않음
# import uuid
# from typing import Dict, List, Any, Optional, TYPE_CHECKING
# from datetime import datetime

# from .models import ComparisonSession, SessionState, AnswerData
# # from .question_generator import question_generator_service, QuestionPlan  # 제거됨
# from ..shared.company_data_loader import get_company_loader
# from ..shared.logging_config import interview_logger

# # 순환 import 방지를 위한 TYPE_CHECKING 사용
# if TYPE_CHECKING:
#     from ..candidate.model import CandidatePersona

# ⚠️ DEPRECATED: 이 모듈을 사용하려고 하면 경고가 발생합니다.
raise DeprecationWarning(
    "🚫 llm.session.comparison_session 는 더 이상 사용되지 않습니다. "
    "backend.services.interview_service 의 새로운 중앙 관제 시스템을 사용하세요."
)

# 🗑️ 기존 코드 모두 주석 처리


# class ComparisonSessionManager:
    # """
    # AI vs Human 비교 세션 관리자
    # 기존 UnifiedInterviewSession 기능을 담당
    # """
    
    # def __init__(self):
    #     self.sessions: Dict[str, ComparisonSession] = {}
    #     self.company_loader = get_company_loader()
    #     # self.question_generator = question_generator_service  # 제거됨
    #     # 각 세션별 질문 계획 저장
    #     # self.session_question_plans: Dict[str, List[QuestionPlan]] = {}  # 제거됨
        
    #     # 🆕 페르소나 캐싱 시스템
    #     self.persona_cache: Dict[str, 'CandidatePersona'] = {}  # session_id -> persona
        
    # async def start_comparison_session(self, company_id: str, position: str, user_name: str, ai_name: str = "춘식이", posting_id: int = None, position_id: int = None) -> str:
    #     """비교 세션 시작"""
    #     company_data = self.company_loader.get_company_data(company_id)
    #     if not company_data:
    #         raise ValueError(f"회사 정보를 찾을 수 없습니다: {company_id}")
        
    #     comparison_id = f"comp_{uuid.uuid4().hex[:8]}"
    #     user_session_id = f"user_{uuid.uuid4().hex[:8]}"
    #     ai_session_id = f"ai_{uuid.uuid4().hex[:8]}"
        
    #     session = ComparisonSession(
    #         comparison_id=comparison_id,
    #         user_session_id=user_session_id,
    #         ai_session_id=ai_session_id,
    #         company_id=company_id,
    #         position=position,
    #         user_name=user_name,
    #         ai_name=ai_name,
    #         state=SessionState.ACTIVE
    #     )
        
    #     interview_logger.info(f"🚀 비교 세션 생성: {comparison_id} - {user_name} vs {ai_name}")
        
    #     # 🆕 질문 계획 생성 (고정 + 동적 질문 20개)
    #     try:
    #         interview_logger.info(f"🎯 비교 면접 질문 계획 생성 시작: {company_id} - {position}")
    #         question_plan = await self.question_generator.generate_question_plan(
    #             company_id=company_id,
    #             position=position,
    #             difficulty="중간"
    #         )
    #         self.session_question_plans[comparison_id] = question_plan
    #         interview_logger.info(f"✅ 질문 계획 생성 완료: {len(question_plan)}개 질문")
    #     except Exception as e:
    #         interview_logger.error(f"❌ 질문 계획 생성 실패: {str(e)}")
    #         # 폴백: 기본 질문 계획 사용
    #         fallback_plan = await self.question_generator._get_fallback_question_plan(company_id, position)
    #         self.session_question_plans[comparison_id] = fallback_plan
        
    #     self.sessions[comparison_id] = session
    #     interview_logger.info(f"📊 세션 등록 완료: 총 {len(self.session_question_plans[comparison_id])}개 질문으로 시작")
    #     return comparison_id
    
    # def get_session(self, comparison_id: str) -> Optional[ComparisonSession]:
    #     """비교 세션 조회"""
    #     return self.sessions.get(comparison_id)
    
    # def submit_answer(self, comparison_id: str, answer_content: str, answer_type: str) -> Dict[str, Any]:
    #     """답변 제출 (user 또는 ai) - 새로운 면접관 주도 방식"""
    #     session = self.get_session(comparison_id)
    #     if not session:
    #         raise ValueError(f"세션을 찾을 수 없습니다: {comparison_id}")
        
    #     if session.state != SessionState.ACTIVE:
    #         raise ValueError(f"활성화된 세션이 아닙니다: {session.state}")
        
    #     # 답변 데이터 생성
    #     current_q_id = f"q_{session.current_question_index + 1}"
    #     answer_data = AnswerData(
    #         question_id=current_q_id,
    #         content=answer_content,
    #         time_spent=0,  # TODO: 실제 시간 측정
    #         timestamp=datetime.now(),
    #         answer_type=answer_type
    #     )
        
    #     # 중복 답변 방지: 이미 해당 질문에 답변이 있으면 덮어쓰지 않음
    #     if answer_type == "human":
    #         if not any(a.question_id == current_q_id for a in session.user_answers):
    #             session.user_answers.append(answer_data)
    #     elif answer_type == "ai":
    #         if not any(a.question_id == current_q_id for a in session.ai_answers):
    #             session.ai_answers.append(answer_data)
    #     else:
    #         raise ValueError(f"잘못된 답변 타입: {answer_type}")
        
    #     # 🆕 새로운 로직: 면접관 주도 방식
    #     next_question = None
    #     interview_logger.info(f"📝 답변 제출 후 상태: current_question_index={session.current_question_index}, user_answers={len(session.user_answers)}, ai_answers={len(session.ai_answers)}")
        
    #     # 현재 질문에 대한 답변 카운트
    #     user_answer_count = sum(1 for a in session.user_answers if a.question_id == current_q_id)
    #     ai_answer_count = sum(1 for a in session.ai_answers if a.question_id == current_q_id)
        
    #     interview_logger.info(f"🔍 답변 카운트: user={user_answer_count}, ai={ai_answer_count}, current_q_id={current_q_id}")
        
    #     # 🆕 면접관 주도 방식: 둘 다 답변했으면 다음 질문으로 이동
    #     if user_answer_count >= 1 and ai_answer_count >= 1:
    #         interview_logger.info(f"✅ 현재 질문({session.current_question_index + 1}) 완료 - 다음 질문으로 이동")
    #         session.next_question()
            
    #         # 다음 질문 가져오기
    #         if not session.is_complete():
    #             next_question = self.get_next_question(comparison_id)
    #             interview_logger.info(f"📋 다음 질문 준비: {session.current_question_index + 1}/{session.total_questions}")
    #         else:
    #             interview_logger.info(f"🎉 모든 질문 완료: {session.current_question_index}/{session.total_questions}")
    #     else:
    #         # 아직 한쪽만 답변한 경우 - 현재 질문 정보 반환
    #         interview_logger.info(f"⏳ 아직 답변 대기 중: user={user_answer_count}, ai={ai_answer_count}")
    #         question_plans = self.session_question_plans.get(comparison_id, [])
    #         current_index = session.current_question_index
            
    #         if 0 <= current_index < len(question_plans):
    #             current_plan = question_plans[current_index]
    #             company_data = self.company_loader.get_company_data(session.company_id)
    #             next_question = {
    #                 "question_id": current_plan.question_id,
    #                 "question_number": current_index + 1,
    #                 "question_content": current_plan.question_content,
    #                 "question_type": current_plan.question_type,
    #                 "question_intent": current_plan.question_intent,
    #                 "question_level": current_plan.question_level,
    #                 "is_fixed": current_plan.is_fixed,
    #                 "source": current_plan.source,
    #                 "current_phase": "waiting",  # 답변 대기 중
    #                 "progress": session.get_progress(),
    #                 "company_name": company_data.get('name', '회사') if company_data else '회사',
    #                 "time_limit": 120
    #             }
        
    #     return {
    #         "comparison_id": comparison_id,
    #         "answer_type": answer_type,
    #         "current_phase": "waiting",  # 항상 대기 상태
    #         "progress": session.get_progress(),
    #         "is_complete": session.is_complete(),
    #         "next_question": next_question
    #     }
    
    # def get_next_question(self, comparison_id: str) -> Optional[Dict[str, Any]]:
    #     """다음 질문 가져오기 (새로운 질문 계획 시스템 사용)"""
    #     session = self.get_session(comparison_id)
    #     if not session or session.is_complete():
    #         interview_logger.info(f"🚫 세션 완료 또는 없음: {comparison_id}")
    #         return None
        
    #     # 질문 계획에서 현재 질문 가져오기
    #     question_plans = self.session_question_plans.get(comparison_id, [])
    #     if not question_plans:
    #         interview_logger.error(f"❌ 질문 계획이 없습니다: {comparison_id}")
    #         return None
        
    #     current_index = session.current_question_index
    #     if current_index >= len(question_plans):
    #         interview_logger.info(f"✅ 모든 질문 완료: {comparison_id} ({current_index}/{len(question_plans)})")
    #         session.state = SessionState.COMPLETED  # 명시적으로 완료 상태 설정
    #         return None
        
    #     current_plan = question_plans[current_index]
        
    #     # 동적 질문인 경우 실제 질문 내용이 비어있을 수 있으므로 생성해야 함
    #     question_content = current_plan.question_content
    #     if not question_content and not current_plan.is_fixed:
    #         # 동적 질문은 나중에 LLM으로 생성
    #         question_content = f"[{current_plan.question_type} 질문이 생성됩니다]"
        
    #     company_data = self.company_loader.get_company_data(session.company_id)
        
    #     result = {
    #         "question_id": current_plan.question_id,
    #         "question_number": current_index + 1,
    #         "question_content": question_content,
    #         "question_type": current_plan.question_type,
    #         "question_intent": current_plan.question_intent,
    #         "question_level": current_plan.question_level,
    #         "is_fixed": current_plan.is_fixed,
    #         "source": current_plan.source,
    #         "current_phase": "interviewer_question",  # 면접관이 질문 제시
    #         "progress": session.get_progress(),
    #         "company_name": company_data.get('name', '회사') if company_data else '회사',
    #         "time_limit": 120
    #     }
        
    #     interview_logger.info(f"📝 질문 반환: {current_index + 1}/{len(question_plans)} - {current_plan.question_type} - {current_plan.source}")
    #     return result

    # def process_interviewer_question(self, comparison_id: str) -> Dict[str, Any]:
    #     """면접관이 질문을 제시하고 AI 답변을 자동 생성"""
    #     session = self.get_session(comparison_id)
    #     if not session:
    #         raise ValueError(f"세션을 찾을 수 없습니다: {comparison_id}")
        
    #     # 현재 질문 가져오기
    #     current_question = self.get_next_question(comparison_id)
    #     if not current_question:
    #         return {
    #             "comparison_id": comparison_id,
    #             "status": "completed",
    #             "message": "모든 질문이 완료되었습니다."
    #         }
        
    #     # AI 답변 자동 생성 (비동기로 처리)
    #     import asyncio
    #     try:
    #         # AI 답변 생성을 위한 비동기 작업 예약
    #         asyncio.create_task(self._generate_ai_answer_async(comparison_id, current_question))
    #     except Exception as e:
    #         interview_logger.error(f"❌ AI 답변 생성 예약 실패: {str(e)}")
        
    #     return {
    #         "comparison_id": comparison_id,
    #         "status": "question_presented",
    #         "current_question": current_question,
    #         "message": "면접관이 질문을 제시했습니다."
    #     }
    
    # async def _generate_ai_answer_async(self, comparison_id: str, question_data: Dict[str, Any]):
    #     """AI 답변을 비동기로 생성"""
    #     try:
    #         # AI 답변 생성 로직 (기존 AI 답변 생성 코드 활용)
    #         from ..candidate.model import AICandidateModel
    #         ai_model = AICandidateModel()
            
    #         # AI 세션 ID 생성
    #         ai_session_id = f"ai_session_{comparison_id}"
            
    #         # AI 답변 생성
    #         ai_response = ai_model.generate_ai_answer_for_question(ai_session_id, question_data)
            
    #         if ai_response and ai_response.answer_content:
    #             # AI 답변을 세션에 저장
    #             self.submit_answer(comparison_id, ai_response.answer_content, "ai")
    #             interview_logger.info(f"✅ AI 답변 자동 생성 완료: {question_data['question_id']}")
    #         else:
    #             interview_logger.warning(f"⚠️ AI 답변 생성 실패: {question_data['question_id']}")
                
    #     except Exception as e:
    #         interview_logger.error(f"❌ AI 답변 생성 중 오류: {str(e)}")
    
    # def switch_turn(self, comparison_id: str) -> Dict[str, Any]:
    #     """턴 수동 전환"""
    #     session = self.get_session(comparison_id)
    #     if not session:
    #         raise ValueError(f"세션을 찾을 수 없습니다: {comparison_id}")
        
    #     session.switch_phase()
        
    #     return {
    #         "comparison_id": comparison_id,
    #         "current_phase": session.current_phase,
    #         "progress": session.get_progress()
    #     }
    
    # def get_session_summary(self, comparison_id: str) -> Dict[str, Any]:
    #     """세션 요약 정보"""
    #     session = self.get_session(comparison_id)
    #     if not session:
    #         return {}
        
    #     return {
    #         "comparison_id": session.comparison_id,
    #         "user_session_id": session.user_session_id,
    #         "ai_session_id": session.ai_session_id,
    #         "company_id": session.company_id,
    #         "position": session.position,
    #         "user_name": session.user_name,
    #         "ai_name": session.ai_name,
    #         "state": session.state.value,
    #         "created_at": session.created_at.isoformat(),
    #         "progress": session.get_progress(),
    #         "user_answers_count": len(session.user_answers),
    #         "ai_answers_count": len(session.ai_answers)
    #     }
    
    # def get_comparison_results(self, comparison_id: str) -> Dict[str, Any]:
    #     """비교 결과 생성"""
    #     session = self.get_session(comparison_id)
    #     if not session or not session.is_complete():
    #         return {}
        
    #     return {
    #         "comparison_id": comparison_id,
    #         "user_performance": {
    #             "name": session.user_name,
    #             "total_answers": len(session.user_answers),
    #             "average_score": sum(a.score for a in session.user_answers if a.score) / len(session.user_answers) if session.user_answers else 0
    #         },
    #         "ai_performance": {
    #             "name": session.ai_name,
    #             "total_answers": len(session.ai_answers),
    #             "average_score": sum(a.score for a in session.ai_answers if a.score) / len(session.ai_answers) if session.ai_answers else 0
    #         },
    #         "completed_at": datetime.now().isoformat()
    #     }
    
    # # 🆕 페르소나 캐싱 관리 메서드들
    # def set_session_persona(self, comparison_id: str, persona: 'CandidatePersona') -> None:
    #     """세션별 페르소나 저장"""
    #     session = self.get_session(comparison_id)
    #     if session:
    #         session.ai_persona = persona
    #         self.persona_cache[comparison_id] = persona
    #         interview_logger.info(f"✅ [PERSONA CACHE] 페르소나 저장: {comparison_id} -> {persona.name}")
    #     else:
    #         interview_logger.error(f"❌ [PERSONA CACHE] 세션을 찾을 수 없음: {comparison_id}")
    
    # def get_session_persona(self, comparison_id: str) -> Optional['CandidatePersona']:
    #     """세션별 페르소나 조회"""
    #     # 1순위: 세션 객체에서 조회
    #     session = self.get_session(comparison_id)
    #     if session and session.ai_persona:
    #         interview_logger.info(f"✅ [PERSONA CACHE] 세션에서 페르소나 조회: {comparison_id} -> {session.ai_persona.name}")
    #         return session.ai_persona
        
    #     # 2순위: 캐시에서 조회
    #     if comparison_id in self.persona_cache:
    #         persona = self.persona_cache[comparison_id]
    #         interview_logger.info(f"✅ [PERSONA CACHE] 캐시에서 페르소나 조회: {comparison_id} -> {persona.name}")
    #         # 세션 객체에도 동기화
    #         if session:
    #             session.ai_persona = persona
    #         return persona
        
    #     interview_logger.warning(f"⚠️ [PERSONA CACHE] 페르소나를 찾을 수 없음: {comparison_id}")
    #     return None
    
    # def clear_session_persona(self, comparison_id: str) -> None:
    #     """세션 종료 시 페르소나 캐시 정리"""
    #     if comparison_id in self.persona_cache:
    #         persona_name = self.persona_cache[comparison_id].name
    #         del self.persona_cache[comparison_id]
    #         interview_logger.info(f"🧹 [PERSONA CACHE] 페르소나 캐시 정리: {comparison_id} -> {persona_name}")
        
    #     session = self.get_session(comparison_id)
    #     if session and session.ai_persona:
    #         session.ai_persona = None
    #         interview_logger.info(f"🧹 [PERSONA CACHE] 세션 페르소나 정리: {comparison_id}")
    
    # def get_persona_cache_stats(self) -> Dict[str, Any]:
    #     """페르소나 캐시 통계"""
    #     return {
    #         "total_cached": len(self.persona_cache),
    #         "cache_sessions": list(self.persona_cache.keys()),
    #         "cache_personas": [p.name for p in self.persona_cache.values()]
    #     }