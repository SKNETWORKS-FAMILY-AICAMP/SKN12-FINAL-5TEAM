import os
from supabase import create_client, Client
import json
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class SupabaseManager:
    def __init__(self):
        # 환경변수에서 Supabase 설정 읽기
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL과 SUPABASE_KEY 환경변수를 설정해주세요.")
        
        self.supabase: Client = create_client(self.url, self.key)
    
    def _validate_foreign_keys(self, user_id=None, ai_resume_id=None, user_resume_id=None,
                              posting_id=None, company_id=None, position_id=None):
        """외래키 제약조건 검증"""
        validation_results = {}
        
        try:
            # user_id 검증 (필수)
            if user_id:
                try:
                    user_result = self.supabase.table('user').select('user_id').eq('user_id', user_id).execute()
                    validation_results['user_id'] = len(user_result.data) > 0
                except:
                    validation_results['user_id'] = True  # 검증 실패시 통과시킴
            
            # company_id 검증 (선택적)
            if company_id:
                try:
                    company_result = self.supabase.table('company').select('company_id').eq('company_id', company_id).execute()
                    validation_results['company_id'] = len(company_result.data) > 0
                except:
                    validation_results['company_id'] = False
            
            # ai_resume_id 검증 (선택적)
            if ai_resume_id:
                try:
                    ai_resume_result = self.supabase.table('ai_resume').select('ai_resume_id').eq('ai_resume_id', ai_resume_id).execute()
                    validation_results['ai_resume_id'] = len(ai_resume_result.data) > 0
                except:
                    validation_results['ai_resume_id'] = False
            
            # user_resume_id 검증 (선택적)
            if user_resume_id:
                try:
                    user_resume_result = self.supabase.table('user_resume').select('user_resume_id').eq('user_resume_id', user_resume_id).execute()
                    validation_results['user_resume_id'] = len(user_resume_result.data) > 0
                except:
                    validation_results['user_resume_id'] = False
            
            # posting_id 검증 (선택적)
            if posting_id:
                try:
                    posting_result = self.supabase.table('posting').select('posting_id').eq('posting_id', posting_id).execute()
                    validation_results['posting_id'] = len(posting_result.data) > 0
                except:
                    validation_results['posting_id'] = False
            
            # position_id 검증 (선택적)
            if position_id:
                try:
                    position_result = self.supabase.table('position').select('position_id').eq('position_id', position_id).execute()
                    validation_results['position_id'] = len(position_result.data) > 0
                except:
                    validation_results['position_id'] = False
                
        except Exception as e:
            print(f"WARNING: 외래키 검증 중 전체 오류: {str(e)}")
            # 전체 검증 실패시 user_id만 통과시키고 나머지는 False
            validation_results = {'user_id': True}
        
        return validation_results

    def save_interview_session(self, user_id, ai_resume_id=None, user_resume_id=None, 
                          posting_id=None, company_id=None, position_id=None):
        try:
            # 임시로 외래키 검증 비활성화하고 기존 방식 사용
            insert_data = {
                'user_id': user_id,
                'ai_resume_id': ai_resume_id,
                'user_resume_id': user_resume_id,
                'posting_id': posting_id,
                'company_id': company_id,
                'position_id': position_id,
                'date': datetime.now().isoformat()
            }
            
            print("insert_data:", insert_data)
            result = self.supabase.table('interview').insert(insert_data).execute()
            print("result.data:", result.data)
            interview_id = result.data[0]['interview_id']
            print(f"SUCCESS: 새로운 면접 세션 생성 (ID: {interview_id})")
            return interview_id
            
        except Exception as e:
            print(f"ERROR: 면접 세션 생성 실패: {str(e)}")
            print(f"ERROR 상세: {e}")
            return None
    
    def save_qa_detail(self, interview_id, question_data, feedback=None):
        """
        개별 질문-답변을 history_detail 테이블에 저장
        """
        try:
            insert_data = {
                'interview_id': interview_id,
                'who': question_data.get('who', 'interviewer'),
                'question_index': question_data.get('question_index'),
                'question_id': question_data.get('question_id'),
                'question_content': question_data.get('question'),
                'question_intent': question_data.get('intent'),
                'question_level': question_data.get('question_level'),
                'answer': question_data.get('answer'),
                'feedback': feedback,
                'sequence': question_data.get('sequence'),
                'duration': question_data.get('duration')
            }
            
            result = self.supabase.table('history_detail').insert(insert_data).execute()
            detail_id = result.data[0]['detail_id']
            print(f"SUCCESS: Q{question_data.get('question_index')} 저장 완료 (ID: {detail_id})")
            return detail_id
            
        except Exception as e:
            print(f"ERROR: 질문-답변 저장 실패: {str(e)}")
            return None
    
    
    def update_total_feedback(self, interview_id, total_feedback):
        """
        최종 평가 결과를 interview 테이블의 total_feedback에 업데이트
        """
        try:
            result = self.supabase.table('interview')\
                                  .update({'total_feedback': json.dumps(total_feedback, ensure_ascii=False)})\
                                  .eq('interview_id', interview_id)\
                                  .execute()
            
            print(f"SUCCESS: 최종 평가 저장 완료 (Interview ID: {interview_id})")
            return True
            
        except Exception as e:
            print(f"ERROR: 최종 평가 저장 실패: {str(e)}")
            return False
    
    def save_interview_plan(self, interview_id, shortly_plan, long_plan):
        """
        면접 준비 계획을 plans 테이블에 저장
        """
        try:
            insert_data = {
                'interview_id': interview_id,
                'shortly_plan': json.dumps(shortly_plan, ensure_ascii=False),
                'long_plan': json.dumps(long_plan, ensure_ascii=False)
            }
            
            result = self.supabase.table('plans').insert(insert_data).execute()
            plan_id = result.data[0]['id'] if result.data else None
            print(f"SUCCESS: 면접 준비 계획 저장 완료 (Plan ID: {plan_id})")
            return plan_id
            
        except Exception as e:
            print(f"ERROR: 면접 계획 저장 실패: {str(e)}")
            return None
    
    def get_company_info(self, company_id):
        """
        Company 테이블에서 회사 정보 조회
        
        Args:
            company_id (int): 회사 ID
            
        Returns:
            dict: 회사 정보 (company_info.json과 동일한 구조)
        """
        try:
            result = self.supabase.table('company')\
                                  .select("*")\
                                  .eq('company_id', company_id)\
                                  .execute()
            
            if not result.data:
                print(f"WARNING: Company ID {company_id}를 찾을 수 없습니다.")
                return None
            
            company_data = result.data[0]
            print(f"DEBUG: Company 데이터: {company_data}")
            
            # company_info.json 형태로 변환 (테이블 구조에 맞게 수정)
            company_info = {
                "id": company_data.get('name', '').lower().replace(' ', '_'),
                "name": company_data.get('name', ''),
                "talent_profile": company_data.get('talent_profile', ''),
                "core_competencies": self._safe_text_to_list(company_data.get('core_competencies', '')),
                "tech_focus": self._safe_text_to_list(company_data.get('tech_focus', '')),
                "interview_keywords": self._safe_text_to_list(company_data.get('interview_keywords', '')),
                "question_direction": company_data.get('question_direction', ''),
                "company_culture": self._safe_text_to_dict(company_data.get('company_culture', '')),
                "technical_challenges": self._safe_text_to_list(company_data.get('technical_challenges', ''))
            }
            
            print(f"SUCCESS: Company ID {company_id} 정보 조회 완료")
            return company_info
            
        except Exception as e:
            print(f"ERROR: 회사 정보 조회 실패: {str(e)}")
            return None

    def _safe_text_to_list(self, text):
        """
        텍스트를 리스트로 안전하게 변환
        """
        if not text:
            return []
        
        try:
            # JSON 형태인지 확인
            if text.strip().startswith('['):
                return json.loads(text)
            else:
                # 콤마나 줄바꿈으로 분리
                return [item.strip() for item in text.replace('\n', ',').split(',') if item.strip()]
        except:
            return [text] if text else []

    def _safe_text_to_dict(self, text):
        """
        텍스트를 딕셔너리로 안전하게 변환
        """
        if not text:
            return {}
        
        try:
            # JSON 형태인지 확인
            if text.strip().startswith('{'):
                return json.loads(text)
            else:
                # 기본 구조 반환
                return {
                    "work_style": text,
                    "decision_making": "",
                    "growth_support": "",
                    "core_values": []
                }
        except:
            return {"description": text} if text else {}

    def get_interview_details(self, interview_id):
        """
        특정 면접의 모든 상세 정보 조회
        """
        try:
            # interview 테이블에서 기본 정보 조회
            interview_result = self.supabase.table('interview')\
                                           .select("*")\
                                           .eq('interview_id', interview_id)\
                                           .execute()
            
            # history_detail 테이블에서 상세 정보 조회
            details_result = self.supabase.table('history_detail')\
                                         .select("*")\
                                         .eq('interview_id', interview_id)\
                                         .order('sequence')\
                                         .execute()
            
            return {
                'interview': interview_result.data[0] if interview_result.data else None,
                'details': details_result.data
            }
            
        except Exception as e:
            print(f"ERROR: 면접 정보 조회 실패: {str(e)}")
            return None