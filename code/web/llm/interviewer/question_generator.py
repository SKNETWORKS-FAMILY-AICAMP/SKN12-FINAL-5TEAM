#!/usr/bin/env python3
"""
순수 질문 생성기 - InterviewerService에서 분리
턴제 관리 로직 없이 오직 질문 생성만 담당
"""

import os
import sys
import json
import random
import openai
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.supabase_client import get_supabase_client
from llm.shared.constants import GPT_MODEL, MAX_TOKENS, TEMPERATURE
from llm.candidate.model import CandidatePersona
from .prompt import InterviewerPromptBuilder


class QuestionGenerator:
    """순수 질문 생성기 - 턴제 관리 없이 질문 생성만 담당"""
    
    def __init__(self):
        # Supabase 클라이언트 초기화
        self.client = get_supabase_client()
        
        # OpenAI 클라이언트 초기화
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        self.openai_client = openai.OpenAI(api_key=api_key)
        
        # 프롬프트 빌더 초기화
        self.prompt_builder = InterviewerPromptBuilder()
        
        # DB 데이터 로딩 및 캐싱
        self.companies_data = self._load_companies_data()
        self.fixed_questions = self._load_fixed_questions()
        
        # 면접관 역할 정의
        self.interviewer_roles = ['HR', 'TECH', 'COLLABORATION']
        self.question_type_mapping = {
            'HR': 1,
            'TECH': 2, 
            'COLLABORATION': 3
        }
        
        # 면접관별 주제 풀 정의
        self.topic_pools = {
            'HR': ['인성_가치관', '성장_동기', '갈등_해결', '스트레스_관리', '팀워크_리더십'],
            'TECH': ['기술_역량', '문제_해결', '성능_최적화', '코드_품질', '새로운_기술_학습'],
            'COLLABORATION': ['소통_능력', '프로젝트_협업', '의견_조율', '크로스_팀_협업', '조직_문화_적응']
        }
    
    def _load_companies_data(self) -> Dict[str, Any]:
        """회사 데이터 로딩 및 캐싱"""
        try:
            result = self.client.table('company').select('*').execute()
            companies_dict = {}
            
            # CompanyDataLoader와 동일한 매핑 테이블 사용
            company_id_mapping = {
                '네이버': 'naver',
                '카카오': 'kakao', 
                '라인': 'line',
                '라인플러스': '라인플러스',
                '쿠팡': 'coupang',
                '배달의민족': 'baemin',
                '당근마켓': 'daangn',
                '토스': 'toss'
            }
            
            if result.data:
                for company in result.data:
                    company_name = company.get('name', '')
                    english_id = company_id_mapping.get(company_name, company_name.lower())
                    companies_dict[english_id] = company
                    
            print(f"[SUCCESS] 회사 데이터 로딩 완료: {len(companies_dict)}개")
            return companies_dict
        except Exception as e:
            print(f"[ERROR] 회사 데이터 로딩 실패: {e}")
            return {}
    
    def _load_fixed_questions(self) -> List[Dict[str, Any]]:
        """고정 질문 데이터 로딩 및 캐싱"""
        try:
            result = self.client.table('fix_question').select('*').execute()
            questions = result.data if result.data else []
            print(f"[SUCCESS] 고정 질문 데이터 로딩 완료: {len(questions)}개")
            return questions
        except Exception as e:
            print(f"[ERROR] 고정 질문 데이터 로딩 실패: {e}")
            return []
    
    def generate_fixed_question(self, question_index: int, company_id: str, user_resume: Dict = None) -> Dict:
        """고정 질문 생성 (자기소개, 지원동기)"""
        if question_index == 0:
            # 첫 번째 질문: 자기소개
            return {
                'question': '자기소개를 부탁드립니다.',
                'intent': '지원자의 기본 정보와 성격, 역량을 파악',
                'interviewer_type': 'HR'
            }
        
        elif question_index == 1:
            # 두 번째 질문: 지원동기
            company_info = self.companies_data.get(company_id, {})
            company_name = company_info.get('name', '저희 회사')
            
            base_question = f'저희 {company_name}에 지원하신 동기를 말씀해 주세요.'
            candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
            question_with_name = self._add_candidate_name_to_question(base_question, candidate_name)
            
            return {
                'question': question_with_name,
                'intent': '회사에 대한 관심도와 지원 동기 파악',
                'interviewer_type': 'HR'
            }
        
        else:
            raise ValueError(f"고정 질문은 0, 1번만 지원됩니다. 입력: {question_index}")
    
    def generate_question_by_role(self, interviewer_role: str, company_id: str, 
                                 user_resume: Dict, user_answer: str = None, 
                                 chun_sik_answer: str = None, previous_qa_pairs: List[Dict] = None) -> Dict:
        """면접관 역할별 질문 생성"""
        company_info = self.companies_data.get(company_id, {})
        if not company_info:
            raise ValueError(f"회사 정보를 찾을 수 없습니다: {company_id}")
        
        # 주제 선택
        topic_pool = self.topic_pools.get(interviewer_role, [])
        if not topic_pool:
            raise ValueError(f"지원되지 않는 면접관 역할: {interviewer_role}")
        
        selected_topic = random.choice(topic_pool)
        
        # 50% 확률로 DB 템플릿 또는 LLM 생성 방식 선택
        use_db_first = random.choice([True, False])
        
        question_result = None
        
        if use_db_first:
            # 1차: DB 템플릿 기반 생성 시도
            question_result = self._try_generate_from_db_template(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
            
            # 2차: DB 실패 시 LLM 생성 시도 
            question_result = self._try_generate_from_llm(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
        else:
            # 1차: LLM 기반 생성 시도
            question_result = self._try_generate_from_llm(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
            
            # 2차: LLM 실패 시 DB 템플릿 시도
            question_result = self._try_generate_from_db_template(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
        
        # 최종 폴백: 일반적인 질문
        return self._get_generic_question(interviewer_role, selected_topic, 
                                        user_resume.get('name', '지원자') if user_resume else '지원자')
    
    def generate_follow_up_question(self, previous_question: str, user_answer: str, 
                                   chun_sik_answer: str, company_info: Dict, 
                                   interviewer_role: str, user_resume: Dict = None) -> Dict:
        """동적 꼬리 질문 생성 - 답변 기반 실시간 심층 탐구"""
        
        # 프롬프트 빌더를 사용하여 프롬프트 생성
        position = user_resume.get('position', '개발자') if user_resume else '개발자'
        prompt = self.prompt_builder.build_follow_up_question_prompt(
            previous_question, user_answer, chun_sik_answer, company_info, interviewer_role, position
        )
        system_prompt = self.prompt_builder.build_system_prompt_for_follow_up()
        
        # LLM 호출
        try:
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.7  # 창의적인 꼬리 질문을 위해 조금 높임
            )
            
            # JSON 파싱 개선 (꼬리 질문용)
            result_text = response.choices[0].message.content.strip()
            
            if not result_text:
                raise ValueError("LLM이 빈 응답을 반환했습니다")
            
            # JSON 블록 추출
            if '```json' in result_text:
                json_start = result_text.find('```json') + 7
                json_end = result_text.find('```', json_start)
                result_text = result_text[json_start:json_end].strip()
            elif '{' in result_text and '}' in result_text:
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1
                result_text = result_text[json_start:json_end]
            
            result = json.loads(result_text)
            
            # 결과 검증 및 보정
            if not result.get('question'):
                raise ValueError("question 필드가 비어있습니다")
            
            # 이름 호명 추가
            candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
            result['question'] = self._add_candidate_name_to_question(result['question'], candidate_name)
            
            result['interviewer_type'] = interviewer_role
            result['question_type'] = 'follow_up'
            result['question_source'] = 'llm_follow_up'
            return result
            
        except Exception as e:
            print(f"[ERROR] 꼬리 질문 생성 실패: {e}")
            # 폴백 꼬리 질문
            return self._get_fallback_follow_up_question(interviewer_role, previous_question, user_resume)
    
    def _try_generate_from_db_template(self, user_resume: Dict, company_info: Dict, 
                                     interviewer_role: str, topic: str) -> Optional[Dict]:
        """DB 템플릿 기반 질문 생성 시도"""
        try:
            return self._generate_from_db_template_with_topic(
                user_resume, company_info, interviewer_role, topic
            )
        except Exception as e:
            print(f"[ERROR] DB 템플릿 생성 중 예외: {e}")
            return None
    
    def _try_generate_from_llm(self, user_resume: Dict, company_info: Dict, 
                             interviewer_role: str, topic: str) -> Optional[Dict]:
        """LLM 기반 질문 생성 시도"""
        try:
            return self._generate_from_llm_with_topic(
                user_resume, company_info, interviewer_role, topic
            )
        except Exception as e:
            print(f"[ERROR] LLM 생성 중 예외: {e}")
            return None
    
    def _generate_from_db_template_with_topic(self, user_resume: Dict, company_info: Dict, 
                                            interviewer_role: str, topic: str) -> Dict:
        """주제 특화 DB 템플릿 기반 질문 생성"""
        question_type_id = self.question_type_mapping.get(interviewer_role)
        if not question_type_id:
            raise ValueError(f"지원되지 않는 면접관 역할: {interviewer_role}")
        
        # 해당 면접관 유형의 질문들 필터링
        role_questions = [
            q for q in self.fixed_questions 
            if q.get('question_type_id') == question_type_id
        ]
        
        if not role_questions:
            raise ValueError(f"{interviewer_role} 유형의 질문이 DB에 없습니다")
        
        # 랜덤 선택
        selected_template = random.choice(role_questions)
        question_content = selected_template.get('question_content', '질문을 생성할 수 없습니다.')
        
        # 이름 호명 추가
        candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
        question_with_name = self._add_candidate_name_to_question(question_content, candidate_name)
        
        return {
            'question': question_with_name,
            'intent': f"{topic} 관련 {selected_template.get('question_intent', f'{interviewer_role} 역량 평가')}",
            'interviewer_type': interviewer_role,
            'topic': topic,
            'question_source': 'db_template'
        }
    
    def _generate_from_llm_with_topic(self, user_resume: Dict, company_info: Dict, 
                                     interviewer_role: str, topic: str) -> Dict:
        """주제 특화 LLM 기반 질문 생성"""
        
        # 프롬프트 빌더를 사용하여 프롬프트 생성
        prompt = self.prompt_builder.build_main_question_prompt(
            user_resume, company_info, interviewer_role, topic
        )
        system_prompt = self.prompt_builder.build_system_prompt_for_question_generation()
        
        # LLM 호출
        try:
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            # JSON 파싱
            result_text = response.choices[0].message.content.strip()
            
            if not result_text:
                raise ValueError("LLM이 빈 응답을 반환했습니다")
            
            result = json.loads(result_text)
            
            # 결과 검증 및 보정
            if not result.get('question'):
                raise ValueError("question 필드가 비어있습니다")
            
            # 이름 호명 추가
            candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
            result['question'] = self._add_candidate_name_to_question(result['question'], candidate_name)
            
            result['interviewer_type'] = interviewer_role
            result['topic'] = topic
            result['question_source'] = 'llm_generated'
            return result
            
        except Exception as e:
            print(f"[ERROR] LLM 메인 질문 생성 실패: {e}")
            raise
    
    def _get_generic_question(self, interviewer_role: str, topic: str, candidate_name: str = None) -> Dict:
        """최종 폴백: 일반적인 질문"""
        generic_questions = {
            'HR': {
                'question': f'{topic} 관련해서 본인의 경험을 자유롭게 말씀해 주세요.',
                'intent': '지원자의 경험과 역량 파악'
            },
            'TECH': {
                'question': f'{topic}와 관련된 기술적 경험이나 학습한 내용을 설명해 주세요.',
                'intent': '기술적 역량과 학습 능력 평가'
            },
            'COLLABORATION': {
                'question': f'{topic} 상황에서 어떻게 대처하셨는지 구체적인 사례를 말씀해 주세요.',
                'intent': '협업 능력과 문제 해결 역량 평가'
            }
        }
        
        template = generic_questions.get(interviewer_role, generic_questions['HR'])
        question_text = template['question']
        
        if candidate_name:
            question_text = self._add_candidate_name_to_question(question_text, candidate_name)
        
        return {
            'question': question_text,
            'intent': template['intent'],
            'interviewer_type': interviewer_role,
            'topic': topic,
            'question_source': 'generic_fallback'
        }
    
    def _get_fallback_follow_up_question(self, interviewer_role: str, previous_question: str, user_resume: Dict = None) -> Dict:
        """꼬리 질문 생성 실패 시 폴백 질문"""
        
        fallback_follow_ups = {
            'HR': {
                'question': '그런 경험을 통해 어떤 점을 배우셨나요?',
                'intent': '경험을 통한 학습과 성장 확인'
            },
            'TECH': {
                'question': '그 과정에서 가장 어려웠던 기술적 문제는 무엇이었나요?',
                'intent': '기술적 문제 해결 능력 평가'
            },
            'COLLABORATION': {
                'question': '그 상황에서 팀원들과는 어떻게 소통하셨나요?',
                'intent': '팀 내 소통 및 협업 능력 평가'
            }
        }
        
        template = fallback_follow_ups.get(interviewer_role, fallback_follow_ups['HR'])
        question_text = template['question']
        
        # 이름 호명 추가
        candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
        question_text = self._add_candidate_name_to_question(question_text, candidate_name)
        
        return {
            'question': question_text,
            'intent': template['intent'],
            'interviewer_type': interviewer_role,
            'question_type': 'follow_up',
            'question_source': 'fallback_follow_up'
        }
    
    def _add_candidate_name_to_question(self, question: str, candidate_name: str) -> str:
        """질문에 지원자 이름 호명 추가"""
        if not candidate_name or candidate_name == '지원자':
            return question
        
        # 이미 이름이 포함되어 있으면 그대로 반환
        if candidate_name in question:
            return question
        
        # 질문 끝에 이름 추가
        if question.endswith('.') or question.endswith('?'):
            return f"{candidate_name}님, {question}"
        else:
            return f"{candidate_name}님, {question}."