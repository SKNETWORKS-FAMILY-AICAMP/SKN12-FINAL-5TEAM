#!/usr/bin/env python3
"""
텍스트 기반 AI 경쟁 면접 서비스 (임시)
InterviewerService + AI 페르소나를 활용한 고품질 텍스트 면접 시스템
기존 interview_service.py를 건드리지 않는 병렬 개발용
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

# 새로운 아키텍처: TurnManager와 AI 관련 모듈
from .turn_manager import TurnManager
from llm.candidate.model import AICandidateModel, CandidatePersona, AnswerRequest
from llm.candidate.quality_controller import QualityLevel
from llm.shared.models import QuestionType, QuestionAnswer
from llm.shared.logging_config import interview_logger


class InterviewServiceTemp:
    """
    텍스트 기반 AI 경쟁 면접 서비스
    
    주요 특징:
    - 새로운 아키텍처: TurnManager + QuestionGenerator 활용
    - AI 페르소나와의 텍스트 기반 경쟁
    - 기존 시스템과 독립적으로 운영
    - 관심사 분리: 턴제 관리와 질문 생성 분리
    """
    
    def __init__(self):
        """서비스 초기화"""
        # 새로운 아키텍처: 턴제 관리자 (15개 질문 한도)
        self.turn_manager = TurnManager(total_question_limit=15)
        
        # AI 페르소나 생성 및 답변 생성
        self.ai_candidate_model = AICandidateModel()
        
        # 활성 세션 관리 (메모리 기반)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # 회사 이름 매핑 (기존 interview_service.py와 동일)
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
    
    async def start_text_interview(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 기반 AI 경쟁 면접 시작"""
        try:
            # 필수 파라미터 검증
            required_fields = ['company', 'position', 'candidate_name']
            for field in required_fields:
                if field not in settings or not settings[field]:
                    raise ValueError(f"필수 필드가 누락되었습니다: {field}")
            
            company_id = self.get_company_id(settings['company'])
            
            interview_logger.info(f"🎯 텍스트 기반 면접 시작: {company_id} - {settings['position']}")
            print(settings)
            # 이력서 데이터 검증 및 로깅
            if 'resume' in settings and settings['resume']:
                resume_data = settings['resume']
                interview_logger.info(f"📄 이력서 정보: {resume_data.get('name', 'N/A')} - {resume_data.get('tech', 'N/A')[:50]}...")
            else:
                interview_logger.warning("⚠️ 이력서 데이터가 제공되지 않았습니다. 기본 정보만 사용합니다.")
            
            # 1. AI 페르소나 생성 (실시간 LLM 기반)
            ai_persona = self.ai_candidate_model.create_persona_for_interview(
                company_id, settings['position']
            )
            
            if not ai_persona:
                interview_logger.warning("AI 페르소나 생성 실패, 기본 페르소나 사용")
                ai_persona = self._create_fallback_persona(company_id, settings['position'])
            
            # 2. 세션 데이터 구성
            session_id = f"text_comp_{uuid.uuid4().hex[:8]}"
            print(settings)
            # 이력서 데이터 처리
            user_resume = {}
            if 'resume' in settings and settings['resume']:
                # 프론트엔드에서 전달받은 이력서 데이터 사용
                resume_data = settings['resume']
                user_resume = {
                    'name': resume_data.get('name', settings['candidate_name']),
                    'email': resume_data.get('email', ''),
                    'phone': resume_data.get('phone', ''),
                    'position': settings['position'],
                    'academic_record': resume_data.get('academic_record', ''),
                    'career': resume_data.get('career', ''),
                    'tech': resume_data.get('tech', ''),
                    'activities': resume_data.get('activities', ''),
                    'certificate': resume_data.get('certificate', ''),
                    'awards': resume_data.get('awards', ''),
                    'created_at': resume_data.get('created_at', ''),
                    'updated_at': resume_data.get('updated_at', '')
                }
                print(f"✅ 이력서 데이터 사용: {user_resume['name']}, 기술스택: {user_resume['tech'][:50]}...")
            else:
                # 이력서 데이터가 없는 경우 기본값 사용
                user_resume = {
                    'name': settings['candidate_name'],
                    'position': settings['position'],
                    'academic_record': '',
                    'career': '',
                    'tech': '',
                    'activities': '',
                    'certificate': '',
                    'awards': ''
                }
                print(f"⚠️ 이력서 데이터 없음 - 기본값 사용: {user_resume['name']}")
            
            # 🆕 난이도 변환 및 저장
            difficulty_map = {
                '초급': QualityLevel.INADEQUATE,
                '중급': QualityLevel.AVERAGE,
                '고급': QualityLevel.EXCELLENT
            }
            quality_level = difficulty_map.get(settings.get('difficulty', '중급'), QualityLevel.AVERAGE)
            interview_logger.info(f"🔡 텍스트 면접 난이도 설정: {settings.get('difficulty')} -> {quality_level.name}")

            session_data = {
                'session_id': session_id,
                'company_id': company_id,
                'position': settings['position'],
                'candidate_name': settings['candidate_name'],
                'user_resume': user_resume,
                'ai_persona': ai_persona,
                'ai_quality_level': quality_level,  # 🆕 세션에 난이도 저장
                'qa_history': [],
                'user_answers': [],
                'ai_answers': [],
                'created_at': datetime.now(),
                'current_question': None
            }
            
            # 3. 첫 질문 생성 (TurnManager 활용)
            first_question = self.turn_manager.generate_next_question(
                user_resume=session_data['user_resume'],
                chun_sik_persona=ai_persona,
                company_id=company_id
            )
            
            session_data['current_question'] = first_question
            self.active_sessions[session_id] = session_data
            
            interview_logger.info(f"✅ 텍스트 면접 세션 생성 완료: {session_id}")
            
            return {
                "session_id": session_id,
                "question": first_question,
                "ai_persona": {
                    "name": ai_persona.name,
                    "summary": ai_persona.summary,
                    "background": ai_persona.background
                },
                "interview_type": "text_based_competition",
                "progress": {
                    "current": 0,
                    "total": 15,
                    "percentage": 0
                },
                "message": f"텍스트 기반 AI 경쟁 면접이 시작되었습니다. AI 지원자 '{ai_persona.name}'와 경쟁합니다."
            }
            
        except Exception as e:
            interview_logger.error(f"텍스트 면접 시작 오류: {str(e)}")
            raise Exception(f"텍스트 면접 시작 중 오류가 발생했습니다: {str(e)}")
    
    async def submit_answer_and_get_next(self, session_id: str, user_answer: str) -> Dict[str, Any]:
        """사용자 답변 제출 + AI 답변 생성 + 다음 질문 = 원스톱 처리"""
        try:
            session_data = self.active_sessions.get(session_id)
            if not session_data:
                raise ValueError("세션을 찾을 수 없습니다")
            
            current_question = session_data.get('current_question')
            if not current_question:
                raise ValueError("현재 질문 정보가 없습니다")
            
            interview_logger.info(f"🔄 답변 처리 시작: {session_id}")
            
            # 1. 사용자 답변 저장
            session_data['user_answers'].append(user_answer)
            
            # 2. AI 답변 생성 (현재 질문에 대해)
            question_content = current_question.get('question', '질문 내용을 찾을 수 없습니다')
            
            # 질문 타입 결정
            interviewer_type = current_question.get('interviewer_type', 'HR')
            question_type = self._map_interviewer_type_to_question_type(interviewer_type)
            
            ai_answer_request = AnswerRequest(
                question_content=question_content,
                question_type=question_type,
                question_intent=current_question.get('intent', '면접 평가'),
                company_id=session_data['company_id'],
                position=session_data['position'],
                quality_level=session_data.get('ai_quality_level', QualityLevel.AVERAGE),  # 🆕 세션 난이도 사용
                llm_provider="openai_gpt4o_mini"
            )
            
            # AI 답변 생성 (비동기 처리)
            ai_response = await asyncio.to_thread(
                self.ai_candidate_model.generate_answer,
                ai_answer_request, 
                session_data['ai_persona']
            )
            
            if ai_response.error:
                interview_logger.warning(f"AI 답변 생성 실패: {ai_response.error}")
                ai_answer_content = "죄송합니다. 답변을 생성하는 중 문제가 발생했습니다."
            else:
                ai_answer_content = ai_response.answer_content
            
            session_data['ai_answers'].append(ai_answer_content)
            
            # 3. 다음 질문 생성 (TurnManager의 턴제 시스템)
            next_question = self.turn_manager.generate_next_question(
                user_resume=session_data['user_resume'],
                chun_sik_persona=session_data['ai_persona'],
                company_id=session_data['company_id'], 
                previous_qa_pairs=session_data['qa_history'],
                user_answer=user_answer,
                chun_sik_answer=ai_answer_content
            )
            
            # 4. 히스토리 업데이트 - 사용자와 AI 답변을 각각 별도 엔트리로 저장
            timestamp = datetime.now().isoformat()
            sequence_base = len(session_data['qa_history'])
            
            # 사용자 답변 저장
            session_data['qa_history'].append({
                'question': question_content,
                'answerer': 'user',
                'answer': user_answer,
                'interviewer_type': interviewer_type,
                'timestamp': timestamp,
                'sequence': sequence_base + 1
            })
            
            # AI 답변 저장
            session_data['qa_history'].append({
                'question': question_content,
                'answerer': 'ai',
                'answer': ai_answer_content,
                'interviewer_type': interviewer_type,
                'timestamp': timestamp,
                'sequence': sequence_base + 2
            })
            
            # 5. 현재 질문 업데이트
            session_data['current_question'] = next_question
            
            # 6. 면접 완료 여부 확인
            if next_question.get('is_final'):
                interview_logger.info(f"🏁 텍스트 면접 완료: {session_id}")
                return {
                    "status": "completed",
                    "message": "텍스트 기반 면접이 완료되었습니다.",
                    "ai_answer": {"content": ai_answer_content},
                    "final_stats": {
                        "total_questions": len(session_data['qa_history']),
                        "user_answers": len(session_data['user_answers']),
                        "ai_answers": len(session_data['ai_answers'])
                    },
                    "session_id": session_id
                }
            
            # 7. 진행률 계산 (TurnManager에서)
            progress_info = self.turn_manager.get_interview_progress()
            current_progress = progress_info['questions_asked']
            progress_percentage = progress_info['percentage']
            
            return {
                "status": "continue",
                "ai_answer": {"content": ai_answer_content},
                "next_question": next_question,
                "progress": {
                    "current": current_progress,
                    "total": 15,
                    "percentage": progress_percentage
                },
                "message": f"AI '{session_data['ai_persona'].name}' 답변 완료. 다음 질문을 준비했습니다."
            }
            
        except Exception as e:
            interview_logger.error(f"답변 처리 오류: {str(e)}")
            raise Exception(f"답변 처리 중 오류가 발생했습니다: {str(e)}")
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """세션 정보 조회"""
        try:
            session_data = self.active_sessions.get(session_id)
            if not session_data:
                return {"error": "세션을 찾을 수 없습니다"}
            
            return {
                "session_id": session_id,
                "company_id": session_data['company_id'],
                "position": session_data['position'],
                "candidate_name": session_data['candidate_name'],
                "ai_persona": {
                    "name": session_data['ai_persona'].name,
                    "summary": session_data['ai_persona'].summary
                },
                "progress": {
                    "current": len(session_data['qa_history']),
                    "total": 15,
                    "percentage": (len(session_data['qa_history']) / 15) * 100
                },
                "created_at": session_data['created_at'].isoformat()
            }
            
        except Exception as e:
            interview_logger.error(f"세션 정보 조회 오류: {str(e)}")
            return {"error": str(e)}
    
    async def get_interview_results(self, session_id: str) -> Dict[str, Any]:
        """면접 결과 생성 (간단한 버전)"""
        try:
            session_data = self.active_sessions.get(session_id)
            if not session_data:
                return {"error": "세션을 찾을 수 없습니다"}
            
            qa_history = session_data['qa_history']
            ai_persona = session_data['ai_persona']
            
            # 간단한 결과 생성
            results = {
                "session_id": session_id,
                "company": session_data['company_id'],
                "position": session_data['position'],
                "candidate": session_data['candidate_name'],
                "ai_competitor": ai_persona.name,
                "interview_type": "text_based_competition",
                "total_questions": len(qa_history),
                "qa_pairs": qa_history,
                "summary": {
                    "message": f"텍스트 기반 면접이 완료되었습니다. AI 경쟁자 '{ai_persona.name}'와 총 {len(qa_history)}개의 질문에 답변하셨습니다.",
                    "user_answers_count": len(session_data['user_answers']),
                    "ai_answers_count": len(session_data['ai_answers'])
                },
                "completed_at": datetime.now().isoformat()
            }
            
            return results
            
        except Exception as e:
            interview_logger.error(f"결과 생성 오류: {str(e)}")
            return {"error": str(e)}
    
    def _create_fallback_persona(self, company_id: str, position: str) -> CandidatePersona:
        """AI 페르소나 생성 실패 시 기본 페르소나 생성"""
        try:
            fallback_persona = CandidatePersona(
                name="김개발",
                summary=f"{position} 경력 3년차 개발자",
                background={
                    "career_years": "3",
                    "current_position": f"{position}",
                    "education": ["대학교 컴퓨터공학과 졸업"],
                    "total_experience": "3년"
                },
                technical_skills=["Python", "Java", "React", "Node.js"],
                projects=[
                    {
                        "name": "웹 서비스 개발",
                        "description": "사용자 중심의 웹 서비스 개발 경험"
                    }
                ],
                experiences=[
                    {
                        "company": "이전 회사",
                        "position": f"{position}",
                        "period": "3년",
                        "achievements": ["프로젝트 리딩", "성능 개선"]
                    }
                ],
                strengths=["문제 해결 능력", "팀워크", "빠른 학습"],
                weaknesses=["완벽주의 성향"],
                motivation=f"{company_id}에서 더 큰 도전을 하고 싶어서",
                inferred_personal_experiences=[
                    {
                        "experience": "프로젝트 성공",
                        "lesson": "팀워크의 중요성"
                    }
                ],
                career_goal="시니어 개발자로 성장",
                personality_traits=["성실함", "협력적"],
                interview_style="친근하고 전문적",
                resume_id=1
            )
            
            return fallback_persona
            
        except Exception as e:
            interview_logger.error(f"기본 페르소나 생성 오류: {str(e)}")
            # 최소한의 페르소나라도 반환
            return CandidatePersona(
                name="AI 지원자",
                summary="경험 있는 개발자",
                background={"career_years": "3"},
                technical_skills=["개발"],
                projects=[],
                experiences=[],
                strengths=["개발 능력"],
                weaknesses=[],
                motivation="도전",
                inferred_personal_experiences=[],
                career_goal="성장",
                personality_traits=["전문적"],
                interview_style="정중함",
                resume_id=1
            )
    
    def _map_interviewer_type_to_question_type(self, interviewer_type: str) -> QuestionType:
        """면접관 타입을 QuestionType으로 매핑"""
        mapping = {
            'HR': QuestionType.HR,
            'TECH': QuestionType.TECH,
            'COLLABORATION': QuestionType.COLLABORATION,
            'SYSTEM': QuestionType.FOLLOWUP,
            'INTRO': QuestionType.INTRO,
            'MOTIVATION': QuestionType.MOTIVATION,
        }
        return mapping.get(interviewer_type, QuestionType.HR)
    
    def cleanup_session(self, session_id: str) -> bool:
        """세션 정리"""
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                interview_logger.info(f"🧹 세션 정리 완료: {session_id}")
                return True
            return False
        except Exception as e:
            interview_logger.error(f"세션 정리 오류: {str(e)}")
            return False
    
    def get_active_sessions_count(self) -> int:
        """활성 세션 수 조회"""
        return len(self.active_sessions)