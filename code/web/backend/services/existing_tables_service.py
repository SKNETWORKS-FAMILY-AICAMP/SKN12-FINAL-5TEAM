"""
기존 Supabase 테이블과 연동하는 서비스
기존 테이블 구조를 건드리지 않고 현재 시스템과 연결
"""

from .supabase_client import get_supabase_client
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ExistingTablesService:
    """기존 Supabase 테이블과 연동하는 서비스"""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    # ===================
    # 사용자 관련 함수
    # ===================
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """사용자 정보 조회"""
        try:
            result = self.client.table('User').select('*').eq('user_id', user_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"사용자 조회 실패 (ID: {user_id}): {str(e)}")
            return None
    
    async def create_user(self, name: str, email: str, pw: str) -> Optional[Dict[str, Any]]:
        """새 사용자 생성"""
        try:
            user_data = {
                'name': name,
                'email': email,
                'pw': pw
            }
            result = self.client.table('User').insert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"사용자 생성 실패: {str(e)}")
            return None
    
    # ===================
    # 회사 및 포지션 관련 함수
    # ===================
    
    async def get_companies(self) -> List[Dict[str, Any]]:
        """모든 회사 정보 조회"""
        try:
            result = self.client.table('company').select('*').execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"회사 목록 조회 실패: {str(e)}")
            return []
    
    async def get_positions_by_company(self, company_id: int) -> List[Dict[str, Any]]:
        """특정 회사의 포지션 목록 조회"""
        try:
            result = self.client.table('position').select('*').eq('company_id', company_id).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"포지션 목록 조회 실패 (회사 ID: {company_id}): {str(e)}")
            return []
    
    # ===================
    # 면접 관련 함수
    # ===================
    
    async def create_interview(self, user_id: int, company_id: int, position_id: int, 
                              posting_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """새 면접 세션 생성"""
        try:
            interview_data = {
                'user_id': user_id,
                'company_id': company_id,
                'position_id': position_id,
                'posting_id': posting_id,
                'date': datetime.now().isoformat()
            }
            result = self.client.table('interview').insert(interview_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"면접 세션 생성 실패: {str(e)}")
            return None
    
    async def get_interview_by_id(self, interview_id: int) -> Optional[Dict[str, Any]]:
        """면접 세션 조회"""
        try:
            result = self.client.table('interview').select(
                '*, company(name), position(position_name), User(name, email)'
            ).eq('interview_id', interview_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"면접 세션 조회 실패 (ID: {interview_id}): {str(e)}")
            return None
    
    # ===================
    # 고정 질문 관련 함수
    # ===================
    
    async def get_fixed_questions(self) -> List[Dict[str, Any]]:
        """모든 고정 질문 조회"""
        try:
            result = self.client.table('fix_question').select('*').execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"고정 질문 조회 실패: {str(e)}")
            return []
    
    async def get_fixed_questions_by_level(self, question_level: str) -> List[Dict[str, Any]]:
        """난이도별 고정 질문 조회"""
        try:
            result = self.client.table('fix_question').select('*').eq('question_level', question_level).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"난이도별 고정 질문 조회 실패 (레벨: {question_level}): {str(e)}")
            return []
    
    # ===================
    # 면접 기록 관련 함수
    # ===================
    
    async def save_interview_detail(self, interview_id: int, who: str, question_index: int,
                                   question_id: int, question_content: str, question_intent: str,
                                   question_level: str, answer: str, feedback: str,
                                   sequence: int, duration: int) -> Optional[Dict[str, Any]]:
        """면접 상세 기록 저장"""
        try:
            detail_data = {
                'interview_id': interview_id,
                'who': who,  # 'user' 또는 'ai'
                'question_index': question_index,
                'question_id': question_id,
                'question_content': question_content,
                'question_intent': question_intent,
                'question_level': question_level,
                'answer': answer,
                'feedback': feedback,
                'sequence': sequence,
                'duration': duration
            }
            result = self.client.table('history_detail').insert(detail_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"면접 기록 저장 실패: {str(e)}")
            return None
    
    async def get_interview_history(self, interview_id: int) -> List[Dict[str, Any]]:
        """면접 기록 조회"""
        try:
            result = self.client.table('history_detail').select('*').eq('interview_id', interview_id).order('sequence').execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"면접 기록 조회 실패 (면접 ID: {interview_id}): {str(e)}")
            return []
    
    # ===================
    # 이력서 관련 함수
    # ===================
    
    async def save_user_resume(self, user_id: int, title: str, content: str) -> Optional[Dict[str, Any]]:
        """사용자 이력서 저장"""
        try:
            resume_data = {
                'user_id': user_id,
                'title': title,
                'content': content,
                'created_date': datetime.now().isoformat(),
                'updated_date': datetime.now().isoformat()
            }
            result = self.client.table('user_resume').insert(resume_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"사용자 이력서 저장 실패: {str(e)}")
            return None
    
    async def get_user_resumes(self, user_id: int) -> List[Dict[str, Any]]:
        """사용자의 모든 이력서 조회"""
        try:
            result = self.client.table('user_resume').select('*').eq('user_id', user_id).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"사용자 이력서 조회 실패 (사용자 ID: {user_id}): {str(e)}")
            return []
    
    async def save_ai_resume(self, title: str, content: str, position_id: int) -> Optional[Dict[str, Any]]:
        """AI 이력서 저장"""
        try:
            ai_resume_data = {
                'title': title,
                'content': content,
                'position_id': position_id
            }
            result = self.client.table('ai_resume').insert(ai_resume_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"AI 이력서 저장 실패: {str(e)}")
            return None
    
    async def get_ai_resumes_by_position(self, position_id: int) -> List[Dict[str, Any]]:
        """포지션별 AI 이력서 조회"""
        try:
            result = self.client.table('ai_resume').select('*').eq('position_id', position_id).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"AI 이력서 조회 실패 (포지션 ID: {position_id}): {str(e)}")
            return []
    
    # ===================
    # 채용공고 관련 함수
    # ===================
    
    async def get_posting_by_id(self, posting_id: int) -> Optional[Dict[str, Any]]:
        """채용공고 정보 조회 (회사, 직무 정보 포함)"""
        try:
            result = self.client.table('posting').select(
                '*, company(company_id, name), position(position_id, position_name)'
            ).eq('posting_id', posting_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"채용공고 조회 실패 (ID: {posting_id}): {str(e)}")
            return None
    
    async def get_postings_by_company(self, company_id: int) -> List[Dict[str, Any]]:
        """특정 회사의 모든 채용공고 조회"""
        try:
            result = self.client.table('posting').select(
                '*, position(position_name)'
            ).eq('company_id', company_id).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"회사별 채용공고 조회 실패 (회사 ID: {company_id}): {str(e)}")
            return []
    
    async def find_posting_by_company_position(self, company_name: str, position_name: str) -> Optional[Dict[str, Any]]:
        """회사명과 직무명으로 채용공고 찾기"""
        try:
            # 1단계: 회사명으로 company_id 찾기
            company_result = self.client.table('company').select('company_id').ilike('name', f'%{company_name}%').execute()
            if not company_result.data:
                logger.warning(f"회사를 찾을 수 없음: {company_name}")
                return None
            
            company_id = company_result.data[0]['company_id']
            logger.info(f"✅ 회사 매핑 성공: {company_name} -> company_id={company_id}")
            
            # 2단계: 직무명으로 position_id 찾기 (⚠️ company_id 제약 조건 제거)
            position_result = self.client.table('position').select('position_id').ilike('position_name', f'%{position_name}%').execute()
            if not position_result.data:
                logger.warning(f"직무를 찾을 수 없음: {position_name}")
                return None
            
            position_id = position_result.data[0]['position_id']
            logger.info(f"✅ 직무 매핑 성공: {position_name} -> position_id={position_id}")
            
            # 3단계: posting 테이블에서 company_id + position_id로 채용공고 찾기
            posting_result = self.client.table('posting').select(
                '*, company(company_id, name), position(position_id, position_name)'
            ).eq('company_id', company_id).eq('position_id', position_id).execute()
            
            if posting_result.data:
                logger.info(f"✅ 채용공고 매칭 성공: {company_name} - {position_name}")
                return posting_result.data[0]  # 첫 번째 매칭되는 채용공고 반환
            else:
                logger.warning(f"채용공고를 찾을 수 없음: {company_name} - {position_name} (company_id={company_id}, position_id={position_id})")
                return None
                
        except Exception as e:
            logger.error(f"채용공고 검색 실패 ({company_name}, {position_name}): {str(e)}")
            return None
    
    async def get_all_postings(self) -> List[Dict[str, Any]]:
        """모든 채용공고 조회 (회사, 직무 정보 포함)"""
        try:
            result = self.client.table('posting').select(
                '*, company(name), position(position_name)'
            ).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"전체 채용공고 조회 실패: {str(e)}")
            return []
    
    # ===================
    # 유틸리티 함수
    # ===================
    
    async def get_interview_count_by_user(self, user_id: int) -> int:
        """사용자의 총 면접 횟수 조회"""
        try:
            result = self.client.table('interview').select('interview_id').eq('user_id', user_id).execute()
            return len(result.data) if result.data else 0
        except Exception as e:
            logger.error(f"면접 횟수 조회 실패 (사용자 ID: {user_id}): {str(e)}")
            return 0
    
    async def get_recent_interviews(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 면접 목록 조회"""
        try:
            result = self.client.table('interview').select(
                '*, company(name), position(position_name)'
            ).eq('user_id', user_id).order('date', desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"최근 면접 목록 조회 실패 (사용자 ID: {user_id}): {str(e)}")
            return []

# 전역 서비스 인스턴스
existing_tables_service = ExistingTablesService()