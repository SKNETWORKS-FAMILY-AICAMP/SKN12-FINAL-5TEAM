#!/usr/bin/env python3
"""
면접 서비스
모든 면접 관련 비즈니스 로직을 담당하는 서비스 계층
- Backend 중앙 관제 시스템: 모든 면접 상태와 흐름을 직접 관리
"""

import asyncio
import os
import json
import uuid
import random
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

# 🆕 필요한 모듈 직접 임포트
from llm.interviewer.question_generator import QuestionGenerator  # service.py 대신 question_generator.py를 직접 사용
from llm.candidate.model import AICandidateModel, CandidatePersona
from llm.shared.models import AnswerRequest, QuestionType, QuestionAnswer, LLMProvider
from llm.candidate.quality_controller import QualityLevel
from llm.shared.constants import ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE
from llm.shared.logging_config import interview_logger, performance_logger

# 호환성을 위한 InterviewSession 클래스 import
from backend.models.session import InterviewSession

# 🔥 llm/session 의존성 완전 제거 - 더 이상 사용하지 않음
# from llm.session import SessionManager, InterviewSession, ComparisonSession  # REMOVED

# 문서 처리 및 피드백 서비스
from llm.interviewer.document_processor import DocumentProcessor, UserProfile
from llm.feedback.service import FeedbackService

# 🆕 면접 세션의 모든 상태를 담는 데이터 클래스 (턴 관리 상태 포함)
@dataclass
class SessionState:
    session_id: str
    company_id: str
    position: str
    user_name: str
    
    # LLM 엔진 인스턴스
    question_generator: QuestionGenerator
    ai_candidate_model: AICandidateModel
    ai_persona: CandidatePersona
    
    # 면접 진행 상태
    qa_history: List[Dict[str, Any]] = field(default_factory=list)
    is_completed: bool = False
    total_question_limit: int = 15
    questions_asked_count: int = 0
    current_interviewer_index: int = 0
    interviewer_roles: List[str] = field(default_factory=lambda: ['HR', 'TECH', 'COLLABORATION'])
    interviewer_turn_state: Dict[str, Any] = field(default_factory=lambda: {
        'HR': {'main_question_asked': False, 'follow_up_count': 0},
        'TECH': {'main_question_asked': False, 'follow_up_count': 0},
        'COLLABORATION': {'main_question_asked': False, 'follow_up_count': 0}
    })
    
    def get_current_interviewer(self) -> str:
        return self.interviewer_roles[self.current_interviewer_index]



class InterviewService:
    """면접 서비스 - 모든 면접 관련 로직을 담당"""
    
    def __init__(self):
        """서비스 초기화. 모든 세션을 직접 관리합니다."""
        self.active_sessions: Dict[str, SessionState] = {}  # 🆕 세션 저장소
        
        # 🔥 SessionManager 완전 제거 - 모든 세션을 active_sessions에서 직접 관리
        # self.session_manager = SessionManager()  # REMOVED
        
        # 보조 서비스들
        self.document_processor = DocumentProcessor()
        self.ai_candidate_model = AICandidateModel()
        self.feedback_service = FeedbackService()
        
        # 회사 이름 매핑
        self.company_name_map = {
            "네이버": "naver",
            "카카오": "kakao", 
            "라인": "line",
            "라인플러스": "라인플러스",
            "쿠팡": "coupang",
            "배달의민족": "baemin",
            "당근마켓": "daangn", 
            "토스": "toss"
        }
    
    def get_company_id(self, company_name: str) -> str:
        """회사 이름을 ID로 변환"""
        return self.company_name_map.get(company_name, company_name.lower())
    
    async def start_interview(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """🔥 새로운 중앙 관제 방식으로 일반 면접 시작"""
        try:
            interview_logger.info("🎯 [Central Control] Regular Interview Start")
            session_id = f"reg_{uuid.uuid4().hex[:12]}"
            company_id = self.get_company_id(settings['company'])
            
            # 1. LLM 엔진 인스턴스 생성
            question_generator = QuestionGenerator()
            ai_candidate_model = AICandidateModel()
            
            # 2. AI 페르소나 생성 (일반 면접용)
            ai_persona = await asyncio.to_thread(
                ai_candidate_model.create_persona_for_interview, company_id, settings['position']
            )
            if not ai_persona:
                ai_persona = ai_candidate_model._create_default_persona(company_id, settings['position'])
            
            # 3. 새로운 세션 상태 객체 생성 및 저장 (일반 면접용 설정)
            session_state = SessionState(
                session_id=session_id, company_id=company_id, position=settings['position'],
                user_name=settings['candidate_name'], question_generator=question_generator,
                ai_candidate_model=ai_candidate_model, ai_persona=ai_persona,
                total_question_limit=20  # 일반 면접은 20개 질문
            )
            session_state.interviewer_roles = ['GENERAL']  # 일반 면접은 단일 면접관
            session_state.interviewer_turn_state = {
                'GENERAL': {'main_question_asked': False, 'follow_up_count': 0}
            }
            self.active_sessions[session_id] = session_state
            
            # 4. 첫 질문 생성 (자기소개)
            first_question = session_state.question_generator.generate_fixed_question(0, company_id)
            session_state.questions_asked_count += 1
            session_state.qa_history.append({"question": first_question, "user_answer": None, "ai_answer": None})
            
            interview_logger.info(f"✅ [Central Control] Regular interview session created: {session_id}")
            
            return {
                "session_id": session_id, "question": first_question,
                "total_questions": session_state.total_question_limit,
                "message": "면접이 시작되었습니다."
            }
            
        except Exception as e:
            interview_logger.error(f"면접 시작 오류: {e}", exc_info=True)
            raise
    
    async def upload_document(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """문서 업로드 및 분석"""
        try:
            # 파일 검증
            filename = file_data['filename']
            content = file_data['content']
            
            if not filename.lower().endswith(tuple(ALLOWED_FILE_EXTENSIONS)):
                raise ValueError("지원하지 않는 파일 형식입니다.")
            
            # 파일 저장
            upload_dir = Path("uploads")
            upload_dir.mkdir(exist_ok=True)
            
            file_path = upload_dir / f"{uuid.uuid4()}_{filename}"
            
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            # 문서 분석
            analyzed_content = await self._analyze_document_async(file_path)
            
            return {
                "file_id": str(file_path),
                "analyzed_content": analyzed_content,
                "message": "문서 업로드 및 분석이 완료되었습니다."
            }
            
        except Exception as e:
            interview_logger.error(f"문서 업로드 오류: {str(e)}")
            raise Exception(f"문서 업로드 중 오류가 발생했습니다: {str(e)}")
    
    async def get_next_question(self, session_id: str) -> Dict[str, Any]:
        """🔥 새로운 중앙 관제 방식으로 다음 질문 가져오기"""
        try:
            session_state = self.active_sessions.get(session_id)
            if not session_state:
                return {"error": "유효하지 않은 세션 ID입니다."}
            
            # 면접 완료 확인
            if session_state.is_completed or session_state.questions_asked_count >= session_state.total_question_limit:
                return {"completed": True, "message": "모든 질문이 완료되었습니다."}
            
            # 다음 질문 생성 로직
            next_question = None
            
            # 첫 번째 고정 질문 (자기소개)
            if session_state.questions_asked_count == 0:
                next_question = session_state.question_generator.generate_fixed_question(0, session_state.company_id)
            # 두 번째 고정 질문 (지원동기)
            elif session_state.questions_asked_count == 1:
                next_question = session_state.question_generator.generate_fixed_question(1, session_state.company_id, 
                                                                                        {"name": session_state.user_name})
            # 동적 질문 생성
            else:
                current_interviewer = session_state.get_current_interviewer()
                next_question = await asyncio.to_thread(
                    session_state.question_generator.generate_question_by_role,
                    interviewer_role=current_interviewer, company_id=session_state.company_id,
                    user_resume={"name": session_state.user_name, "position": session_state.position}
                )
            
            if not next_question:
                return {"error": "질문 생성에 실패했습니다."}
            
            # 진행률 계산
            progress = (session_state.questions_asked_count / session_state.total_question_limit) * 100
            
            return {
                "question": {
                    "id": f"q_{session_state.questions_asked_count + 1}",
                    "question": next_question.get("question", ""),
                    "category": next_question.get("interviewer_type", "GENERAL"),
                    "intent": next_question.get("intent", ""),
                    "time_limit": 120,
                    "keywords": []
                },
                "question_index": session_state.questions_asked_count + 1,
                "total_questions": session_state.total_question_limit,
                "progress": progress
            }
            
        except Exception as e:
            interview_logger.error(f"질문 가져오기 오류: {e}", exc_info=True)
            raise
    
    async def submit_answer(self, answer_data: Dict[str, Any]) -> Dict[str, Any]:
        """🔥 새로운 중앙 관제 방식으로 답변 제출 및 다음 질문 생성"""
        try:
            session_id = answer_data['session_id']
            user_answer = answer_data['answer']
            
            session_state = self.active_sessions.get(session_id)
            if not session_state:
                return {"error": "유효하지 않은 세션 ID입니다."}
            
            if session_state.is_completed:
                return {"error": "이미 완료된 면접입니다."}
            
            # 1. 사용자 답변 기록
            if session_state.qa_history:
                last_qa = session_state.qa_history[-1]
                last_qa["user_answer"] = user_answer
            
            # 2. 다음 질문 생성 또는 면접 종료 처리
            if session_state.questions_asked_count >= session_state.total_question_limit:
                session_state.is_completed = True
                return {
                    "status": "interview_complete",
                    "message": "면접이 완료되었습니다.",
                    "total_questions": session_state.questions_asked_count
                }
            
            # 3. 다음 질문 생성
            next_question = None
            
            # 두 번째 고정 질문 (지원동기)
            if session_state.questions_asked_count == 1:
                next_question = session_state.question_generator.generate_fixed_question(1, session_state.company_id, 
                                                                                        {"name": session_state.user_name})
            # 동적 질문 생성
            else:
                current_interviewer = session_state.get_current_interviewer()
                turn_state = session_state.interviewer_turn_state.get(current_interviewer, {})
                
                # 메인 질문 안했으면 메인 질문 생성
                if not turn_state.get('main_question_asked', False):
                    next_question = await asyncio.to_thread(
                        session_state.question_generator.generate_question_by_role,
                        interviewer_role=current_interviewer, company_id=session_state.company_id,
                        user_resume={"name": session_state.user_name, "position": session_state.position}
                    )
                    turn_state['main_question_asked'] = True
                # 꼬리 질문 생성 (최대 2개)
                elif turn_state.get('follow_up_count', 0) < 2:
                    # 이전 질문 정보 가져오기
                    if len(session_state.qa_history) >= 2:
                        prev_qa = session_state.qa_history[-2]
                        previous_question_text = prev_qa["question"].get("question", "")
                        company_info = session_state.question_generator.companies_data.get(session_state.company_id, {})
                        
                        next_question = await asyncio.to_thread(
                            session_state.question_generator.generate_follow_up_question,
                            previous_question=previous_question_text, user_answer=user_answer, chun_sik_answer="",
                            company_info=company_info, interviewer_role=current_interviewer,
                            user_resume={"name": session_state.user_name, "position": session_state.position}
                        )
                        turn_state['follow_up_count'] = turn_state.get('follow_up_count', 0) + 1
                    else:
                        # 꼬리 질문 생성 조건 부족
                        next_question = await asyncio.to_thread(
                            session_state.question_generator.generate_question_by_role,
                            interviewer_role=current_interviewer, company_id=session_state.company_id,
                            user_resume={"name": session_state.user_name, "position": session_state.position}
                        )
                # 턴 전환
                else:
                    # 다음 면접관으로 전환
                    session_state.current_interviewer_index = (session_state.current_interviewer_index + 1) % len(session_state.interviewer_roles)
                    new_interviewer = session_state.get_current_interviewer()
                    
                    next_question = await asyncio.to_thread(
                        session_state.question_generator.generate_question_by_role,
                        interviewer_role=new_interviewer, company_id=session_state.company_id,
                        user_resume={"name": session_state.user_name, "position": session_state.position}
                    )
                    session_state.interviewer_turn_state[new_interviewer]['main_question_asked'] = True
            
            # 4. 상태 업데이트
            if next_question:
                session_state.questions_asked_count += 1
                session_state.qa_history.append({"question": next_question, "user_answer": None, "ai_answer": None})
                
                return {
                    "status": "success",
                    "message": "답변이 성공적으로 제출되었습니다.",
                    "next_question": next_question,
                    "answered_count": session_state.questions_asked_count,
                    "total_questions": session_state.total_question_limit,
                    "progress": (session_state.questions_asked_count / session_state.total_question_limit) * 100
                }
            else:
                session_state.is_completed = True
                return {
                    "status": "interview_complete",
                    "message": "면접이 완료되었습니다.",
                    "total_questions": session_state.questions_asked_count
                }
            
        except Exception as e:
            interview_logger.error(f"답변 제출 오류: {e}", exc_info=True)
            raise
    
    async def get_interview_results(self, session_id: str) -> Dict[str, Any]:
        """면접 결과 조회 - 새로운 중앙 관제 시스템 및 기존 시스템 모두 지원"""
        try:
            # 새로운 중앙 관제 시스템 세션인지 확인
            if session_id in self.active_sessions:
                session_state = self.active_sessions[session_id]
                
                # 간단한 결과 생성 (실제로는 LLM 기반 평가 시스템을 사용할 수 있음)
                total_questions = len(session_state.qa_history)
                
                return {
                    "session_id": session_id,
                    "company": session_state.company_id,
                    "position": session_state.position,
                    "candidate": session_state.user_name,
                    "ai_name": session_state.ai_persona.name,
                    "total_questions": total_questions,
                    "questions_asked": session_state.questions_asked_count,
                    "is_completed": session_state.is_completed,
                    "interviewer_stats": session_state.interviewer_turn_state,
                    "qa_history": session_state.qa_history,
                    "message": "새로운 중앙 관제 시스템 결과"
                }
            
            # 🔥 SessionManager 의존성 완전 제거 - 모든 세션을 active_sessions에서 처리
            else:
                return {"error": f"세션 ID '{session_id}'를 찾을 수 없습니다. 새로운 중앙 관제 시스템만 지원됩니다."}
            
        except Exception as e:
            interview_logger.error(f"결과 조회 오류: {str(e)}")
            raise Exception(f"결과를 조회하는 중 오류가 발생했습니다: {str(e)}")
    
    # 🔄 완전히 새로운 로직으로 교체
    async def start_ai_competition(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        try:
            interview_logger.info("🎯 [New Arch] Backend-Controlling Interview Start")
            session_id = f"comp_{uuid.uuid4().hex[:12]}"
            company_id = self.get_company_id(settings['company'])
            
            # 1. LLM 엔진 인스턴스 생성
            question_generator = QuestionGenerator()
            ai_candidate_model = AICandidateModel()
            
            # 2. AI 페르소나 생성
            ai_persona = await asyncio.to_thread(
                ai_candidate_model.create_persona_for_interview, company_id, settings['position']
            )
            if not ai_persona:
                ai_persona = ai_candidate_model._create_default_persona(company_id, settings['position'])
            
            # 3. 새로운 세션 상태 객체 생성 및 저장
            session_state = SessionState(
                session_id=session_id, company_id=company_id, position=settings['position'],
                user_name=settings['candidate_name'], question_generator=question_generator,
                ai_candidate_model=ai_candidate_model, ai_persona=ai_persona
            )
            self.active_sessions[session_id] = session_state
            
            # 4. 첫 질문 생성 (자기소개)
            first_question = session_state.question_generator.generate_fixed_question(0, company_id)
            session_state.questions_asked_count += 1
            session_state.qa_history.append({"question": first_question, "user_answer": None, "ai_answer": None})
            
            interview_logger.info(f"✅ [New Arch] New session created: {session_id}")
            
            return {
                "session_id": session_id, "question": first_question,
                "ai_name": ai_persona.name, "total_questions": session_state.total_question_limit,
                "message": "새로운 AI 경쟁 면접이 시작되었습니다."
            }
        except Exception as e:
            interview_logger.error(f"AI 경쟁 면접 시작 오류: {e}", exc_info=True)
            raise
    
    
    
    async def get_ai_answer(self, session_id: str, question_id: str) -> Dict[str, Any]:
        """AI 지원자의 답변 생성"""
        try:
            # URL 디코딩
            import urllib.parse
            decoded_session_id = urllib.parse.unquote(session_id)
            
            # 세션 ID에서 회사와 포지션 파싱
            session_parts = decoded_session_id.split('_')
            company_id = session_parts[0] if len(session_parts) > 0 else "naver"
            position = "_".join(session_parts[1:-1]) if len(session_parts) > 2 else "백엔드 개발"
            
            # 🗑️ 더 이상 사용하지 않음 - 새로운 중앙 관제 시스템 사용
            # from llm.session.interviewer_session import InterviewerSession
            
            # InterviewerSession 임시 생성하여 질문 가져오기
            temp_session = InterviewerSession(company_id, position, "춘식이")
            first_question_data = temp_session.start()
            
            if first_question_data:
                question_content = first_question_data["question"]
                question_intent = first_question_data.get("intent", "일반적인 평가")
                question_type = first_question_data.get("interviewer_type", "HR")
            else:
                # 폴백 질문
                if question_id == "q_1":
                    question_content = "춘식이, 자기소개를 부탁드립니다."
                    question_intent = "지원자의 기본 정보와 성격, 역량을 파악"
                    question_type = "INTRO"
                elif question_id == "q_2":
                    question_content = f"춘식이께서 네이버에 지원하게 된 동기는 무엇인가요?"
                    question_intent = "회사에 대한 관심도와 지원 동기 파악"
                    question_type = "MOTIVATION"
                else:
                    question_content = "춘식이에 대해 더 알려주세요."
                    question_intent = "일반적인 평가"
                    question_type = "HR"
            
            # AI 답변 생성
            from llm.candidate.model import AnswerRequest
            from llm.shared.models import QuestionType
            
            # QuestionType 매핑
            question_type_map = {
                "INTRO": QuestionType.INTRO,
                "MOTIVATION": QuestionType.MOTIVATION,
                "HR": QuestionType.HR,
                "TECH": QuestionType.TECH,
                "COLLABORATION": QuestionType.COLLABORATION
            }
            
            answer_request = AnswerRequest(
                question_content=question_content,
                question_type=question_type_map.get(question_type, QuestionType.HR),
                question_intent=question_intent,
                company_id=company_id,
                position=position,
                quality_level=QualityLevel.GOOD,
                llm_provider="openai_gpt4o_mini"
            )
            
            # 🔄 단독 AI 답변 생성 (세션 없음 - 매번 새로운 페르소나)
            interview_logger.info(f"🎭 [STANDALONE AI] 단독 AI 답변 생성 (세션 무관): {company_id} - {position}")
            ai_answer = self.ai_candidate_model.generate_answer(answer_request, persona=None)
            
            if not ai_answer:
                raise Exception("AI 답변 생성에 실패했습니다.")
            
            return {
                "question": question_content,
                "questionType": question_type,
                "questionIntent": question_intent,
                "answer": ai_answer.answer_content,
                "time_spent": 60,
                "score": 85,
                "quality_level": ai_answer.quality_level.value,
                "persona_name": ai_answer.persona_name
            }
            
        except Exception as e:
            interview_logger.error(f"AI 답변 생성 오류: {str(e)}")
            raise Exception(f"AI 답변 생성 중 오류가 발생했습니다: {str(e)}")
    
    
    
    async def get_interview_history(self, user_id: str = None) -> Dict[str, Any]:
        """면접 기록 조회 - 새로운 중앙 관제 시스템 및 기존 시스템 모두 지원"""
        try:
            completed_sessions = []
            
            # 새로운 중앙 관제 시스템 세션들 추가
            for session_id, session_state in self.active_sessions.items():
                if session_state.is_completed:
                    completed_sessions.append({
                        "session_id": session_id,
                        "settings": {
                            "company": session_state.company_id,
                            "position": session_state.position,
                            "user_name": session_state.user_name
                        },
                        "completed_at": "",
                        "total_score": 85,  # 기본값
                        "type": "central_control",
                        "questions_asked": session_state.questions_asked_count,
                        "ai_name": session_state.ai_persona.name
                    })
            
            # 🔥 SessionManager 의존성 완전 제거 - 오직 active_sessions만 사용
            # 메모: 기존 SessionManager 세션들은 더 이상 지원하지 않음
            
            return {
                "total_interviews": len(completed_sessions),
                "interviews": completed_sessions
            }
            
        except Exception as e:
            interview_logger.error(f"기록 조회 오류: {str(e)}")
            raise Exception(f"기록을 조회하는 중 오류가 발생했습니다: {str(e)}")
    
    # 🔄 완전히 새로운 로직으로 교체
    async def process_competition_turn(self, session_id: str, user_answer: str) -> Dict[str, Any]:
        try:
            session_state = self.active_sessions.get(session_id)
            if not session_state or session_state.is_completed:
                raise ValueError("유효하지 않거나 이미 종료된 세션 ID입니다.")
            
            # 1. 사용자 답변 및 이전 질문 기록
            last_qa = session_state.qa_history[-1]
            last_qa["user_answer"] = user_answer
            previous_question_obj = last_qa["question"]
            previous_question_text = previous_question_obj["question"]
            
            # 2. AI 답변 생성
            answer_request = AnswerRequest(
                question_content=previous_question_text,
                question_type=QuestionType.from_string(previous_question_obj.get("interviewer_type", "HR")),
                question_intent=previous_question_obj.get("intent", ""),
                company_id=session_state.company_id,
                position=session_state.position,
                quality_level=QualityLevel.AVERAGE,
                llm_provider=LLMProvider.OPENAI_GPT4O
            )
            ai_answer_response = await asyncio.to_thread(
                session_state.ai_candidate_model.generate_answer, request=answer_request, persona=session_state.ai_persona
            )
            ai_answer_content = ai_answer_response.answer_content
            last_qa["ai_answer"] = ai_answer_content
            
            # 3. 다음 질문 생성을 위한 모든 로직을 여기서 직접 수행
            # 3-1. 면접 종료 조건 확인
            if session_state.questions_asked_count >= session_state.total_question_limit:
                session_state.is_completed = True
                next_question = {'question': '면접이 종료되었습니다. 수고하셨습니다.', 'intent': '면접 종료', 
                                'interviewer_type': 'SYSTEM', 'is_final': True}
            # 3-2. 두 번째 고정 질문 (지원동기)
            elif session_state.questions_asked_count == 1:
                next_question = session_state.question_generator.generate_fixed_question(1, session_state.company_id, 
                                                                                        {"name": session_state.user_name})
            # 3-3. 턴제 시스템에 따른 질문 생성
            else:
                current_interviewer = session_state.get_current_interviewer()
                turn_state = session_state.interviewer_turn_state[current_interviewer]
                
                # 메인 질문 안했으면 메인 질문 생성
                if not turn_state['main_question_asked']:
                    next_question = await asyncio.to_thread(
                        session_state.question_generator.generate_question_by_role,
                        interviewer_role=current_interviewer, company_id=session_state.company_id,
                        user_resume={"name": session_state.user_name, "position": session_state.position}
                    )
                    turn_state['main_question_asked'] = True
                # 꼬리 질문 생성 (최대 2개로 수정)
                elif turn_state['follow_up_count'] < 2:  # 1개에서 2개로 변경
                    company_info = session_state.question_generator.companies_data.get(session_state.company_id, {})
                    next_question = await asyncio.to_thread(
                        session_state.question_generator.generate_follow_up_question,
                        previous_question=previous_question_text, user_answer=user_answer, chun_sik_answer=ai_answer_content,
                        company_info=company_info, interviewer_role=current_interviewer,
                        user_resume={"name": session_state.user_name, "position": session_state.position}
                    )
                    turn_state['follow_up_count'] += 1
                # 턴 전환
                else:
                    # 현재 면접관 턴 초기화 및 다음 면접관으로 인덱스 변경
                    turn_state['main_question_asked'] = False
                    turn_state['follow_up_count'] = 0
                    session_state.current_interviewer_index = (session_state.current_interviewer_index + 1) % len(session_state.interviewer_roles)
                    
                    # 새로운 면접관의 메인 질문 생성
                    new_interviewer = session_state.get_current_interviewer()
                    next_question = await asyncio.to_thread(
                        session_state.question_generator.generate_question_by_role,
                        interviewer_role=new_interviewer, company_id=session_state.company_id,
                        user_resume={"name": session_state.user_name, "position": session_state.position}
                    )
                    session_state.interviewer_turn_state[new_interviewer]['main_question_asked'] = True
            
            # 4. 상태 업데이트
            if not next_question.get('is_final'):
                session_state.questions_asked_count += 1
                session_state.qa_history.append({"question": next_question, "user_answer": None, "ai_answer": None})
            
            interview_logger.info(f"🔄 [New Arch] Turn processed: {session_id}, Next question by {next_question.get('interviewer_type')}")
            
            return {
                "status": "success", "ai_answer": {"content": ai_answer_content},
                "next_question": next_question, "interview_status": "completed" if session_state.is_completed else "continue",
                "progress": {
                    "current": session_state.questions_asked_count, "total": session_state.total_question_limit,
                    "percentage": (session_state.questions_asked_count / session_state.total_question_limit) * 100
                }
            }
        except Exception as e:
            interview_logger.error(f"경쟁 면접 턴 처리 오류: {e}", exc_info=True)
            raise
    
    # 🗑️ 더 이상 사용하지 않는 메서드들 (기존 시스템 호환용으로 유지)
    
    async def start_turn_based_interview(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """턴제 면접 시작 - 더 이상 사용하지 않음, start_ai_competition 사용 권장"""
        try:
            company_id = self.get_company_id(settings['company'])
            
            # 세션 ID 생성
            session_id = f"turn_{company_id}_{settings['position']}_{uuid.uuid4().hex[:8]}"
            
            # 사용자 이력서 정보 (임시)
            user_resume = {
                'name': settings['candidate_name'],
                'career_years': '3',
                'technical_skills': ['Python', 'Django', 'PostgreSQL', 'AWS']
            }
            
            # AI 지원자 페르소나 생성
            from llm.candidate.model import CandidatePersona
            ai_persona = CandidatePersona(
                name='춘식이', summary='3년차 Python 백엔드 개발자',
                background={'career_years': '3', 'current_position': '백엔드 개발자'},
                technical_skills=['Python', 'Django', 'PostgreSQL', 'AWS'],
                projects=[{'name': '이커머스 플랫폼', 'description': '대용량 트래픽 처리'}],
                experiences=[{'company': '스타트업', 'position': '개발자', 'period': '3년'}],
                strengths=['문제 해결', '학습 능력'], weaknesses=['완벽주의'],
                motivation='좋은 서비스를 만들고 싶어서',
                inferred_personal_experiences=[{'experience': '성장', 'lesson': '끊임없는 학습'}],
                career_goal='시니어 개발자로 성장', personality_traits=['친근함', '전문성'],
                interview_style='상호작용적', resume_id=1
            )
            
            # 세션 상태 저장 (간단한 메모리 저장)
            if not hasattr(self, 'turn_based_sessions'):
                self.turn_based_sessions = {}
            
            self.turn_based_sessions[session_id] = {
                'user_resume': user_resume,
                'ai_persona': ai_persona,
                'company_id': company_id,
                'qa_history': [],
                'user_answers': [],
                'ai_answers': [],
                'created_at': time.time()
            }
            
            # 첫 질문 생성
            first_question = self.interviewer_service.generate_next_question(
                user_resume, ai_persona, company_id
            )
            
            interview_logger.info(f"턴제 면접 시작 - 세션 ID: {session_id}")
            
            return {
                "session_id": session_id,
                "question": first_question,
                "total_question_limit": self.interviewer_service.total_question_limit,
                "current_interviewer": self.interviewer_service._get_current_interviewer(),
                "questions_asked": self.interviewer_service.questions_asked_count,
                "message": "턴제 면접이 시작되었습니다."
            }
            
        except Exception as e:
            interview_logger.error(f"턴제 면접 시작 오류: {str(e)}")
            raise Exception(f"턴제 면접 시작 중 오류가 발생했습니다: {str(e)}")
    
    async def get_turn_based_question(self, session_id: str, user_answer: str = None) -> Dict[str, Any]:
        """턴제 면접 다음 질문 가져오기"""
        try:
            if not hasattr(self, 'turn_based_sessions') or session_id not in self.turn_based_sessions:
                raise ValueError("세션을 찾을 수 없습니다")
            
            session_data = self.turn_based_sessions[session_id]
            
            # 사용자 답변 저장
            if user_answer:
                session_data['user_answers'].append(user_answer)
                
                # AI 답변 생성 (간단한 구현)
                ai_answer = "저는 기술적 완성도를 중시하며, 코드 리뷰와 테스트를 통해 안정적인 서비스를 만들려고 노력합니다."
                session_data['ai_answers'].append(ai_answer)
            
            # 다음 질문 생성
            next_question = self.interviewer_service.generate_next_question(
                session_data['user_resume'],
                session_data['ai_persona'], 
                session_data['company_id'],
                session_data['qa_history'],
                user_answer,
                session_data['ai_answers'][-1] if session_data['ai_answers'] else None
            )
            
            # 면접 종료 확인
            if next_question.get('is_final'):
                return {
                    "completed": True,
                    "message": next_question['question'],
                    "final_stats": {
                        "total_questions": self.interviewer_service.questions_asked_count,
                        "interviewer_stats": self.interviewer_service.interviewer_turn_state
                    }
                }
            
            # 턴 전환 확인
            if next_question.get('force_turn_switch'):
                # 다시 질문 생성 시도
                next_question = self.interviewer_service.generate_next_question(
                    session_data['user_resume'],
                    session_data['ai_persona'], 
                    session_data['company_id'],
                    session_data['qa_history']
                )
            
            # QA 히스토리 업데이트
            session_data['qa_history'].append({
                'question': next_question['question'],
                'interviewer_type': next_question['interviewer_type']
            })
            
            return {
                "question": next_question,
                "session_stats": {
                    "questions_asked": self.interviewer_service.questions_asked_count,
                    "remaining_questions": self.interviewer_service.total_question_limit - self.interviewer_service.questions_asked_count,
                    "current_interviewer": self.interviewer_service._get_current_interviewer(),
                    "turn_states": self.interviewer_service.interviewer_turn_state
                }
            }
            
        except Exception as e:
            interview_logger.error(f"턴제 질문 가져오기 오류: {str(e)}")
            raise Exception(f"질문을 가져오는 중 오류가 발생했습니다: {str(e)}")
    
    # 헬퍼 메소드들
    
    async def _generate_personalized_profile(self, documents: List[str]) -> UserProfile:
        """문서 기반 사용자 프로필 생성 (필요시 사용)"""
        try:
            profile = None
            
            for doc_path in documents:
                if os.path.exists(doc_path):
                    profile = await asyncio.to_thread(
                        self.document_processor.process_document, 
                        doc_path
                    )
                    break
            
            if not profile:
                # 기본 프로필 생성
                profile = UserProfile(
                    name="지원자",
                    background={"career_years": "3", "education": "대학교 졸업"},
                    technical_skills=["Java", "Spring", "MySQL"],
                    projects=[{"name": "웹 서비스 개발", "description": "백엔드 API 개발"}],
                    experiences=[{"company": "이전 회사", "role": "백엔드 개발자", "duration": "2년"}],
                    strengths=["문제해결능력", "커뮤니케이션"],
                    keywords=["개발", "협업", "성장"],
                    career_goal="시니어 개발자로 성장",
                    unique_points=["빠른 학습 능력"]
                )
            
            return profile
            
        except Exception as e:
            interview_logger.error(f"프로필 생성 오류: {str(e)}")
            return None
    
    async def _analyze_document_async(self, file_path: Path) -> Dict:
        """문서 분석 (비동기)"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self.document_processor.process_document,
                str(file_path)
            )
            return result
        except Exception as e:
            interview_logger.error(f"문서 분석 오류: {str(e)}")
            return {}