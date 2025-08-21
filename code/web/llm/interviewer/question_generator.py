#!/usr/bin/env python3
"""
순수 질문 생성기 - InterviewerService에서 분리
턴제 관리 로직 없이 오직 질문 생성만 담당
"""

import os
import sys
import json
import random
import time
import openai
import logging
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
        
        # DB 질문 타입 ID 매핑 (면접관 역할 → DB ID)
        self.interviewer_role_to_db_id = {
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
                    # 한글명으로도 접근 가능하도록 추가
                    companies_dict[company_name] = company
                    
            print(f"[SUCCESS] 회사 데이터 로딩 완료: {len(companies_dict)}개")
            print(f"[DEBUG] 로딩된 회사 키들: {list(companies_dict.keys())}")
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
            candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
            base_question = '간단하게 자기소개 부탁드립니다.'
            question_with_name = self._add_candidate_name_to_question(base_question, candidate_name)
            return {
                'question': question_with_name,
                'intent': '지원자의 기본 정보와 성격, 역량을 파악',
                'interviewer_type': 'INTRO'
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
                'interviewer_type': 'INTRO'
            }
        
        else:
            raise ValueError(f"고정 질문은 0, 1번만 지원됩니다. 입력: {question_index}")
    
    def generate_intro_message(self, company_id: str, user_resume: Dict = None) -> Dict:
        """인트로 메시지 생성 (턴 0용)"""
        company_info = self.companies_data.get(company_id, {})
        company_name = company_info.get('name', '저희 회사')
        user_name = user_resume.get('name', '지원자') if user_resume else '지원자'
        user_position = user_resume.get('position', '개발자') if user_resume else '개발자'
        
        intro_message = f"""
안녕하세요.
{company_name}에 지원해주셔서 감사합니다.
{user_name}님 그리고 춘식이님 {user_position} 전형 면접을 시작하겠습니다.
"""
        
        return {
            'question': intro_message,
            'intent': '면접 시작 인사 및 면접관 소개',
            'interviewer_type': 'INTRO'
        }
    
    def generate_question_by_role(self, interviewer_role: str, company_id: str, 
                                 user_resume: Dict, user_answer: str = None, 
                                 chun_sik_answer: str = None, previous_qa_pairs: List[Dict] = None) -> Dict:
        """면접관 역할별 개별 질문 생성 (사용자/AI 동시 생성)"""
        print(f"[DEBUG] 개별 질문 생성 요청: company_id='{company_id}', role='{interviewer_role}'")
        print(f"[DEBUG] 사용 가능한 회사 키들: {list(self.companies_data.keys())}")
        
        company_info = self.companies_data.get(company_id, {})
        if not company_info:
            print(f"[WARNING] 회사 정보를 찾을 수 없음: {company_id}, 기본 회사 정보로 대체")
            # 에러 대신 기본 회사 정보 생성
            company_info = {
                "name": company_id.capitalize(),
                "id": company_id,
                "core_competencies": [],
                "tech_focus": [],
                "talent_profile": "혁신적인 기술 회사"
            }
        
        # 주제 선택
        topic_pool = self.topic_pools.get(interviewer_role, [])
        if not topic_pool:
            raise ValueError(f"지원되지 않는 면접관 역할: {interviewer_role}")
        
        selected_topic = random.choice(topic_pool)
        
        # 사용자 질문 생성
        user_main_question = self._try_generate_main_question_for_user(
            user_resume, company_info, interviewer_role, selected_topic
        )
        
        # AI 질문 생성
        ai_main_question = self._try_generate_main_question_for_ai(
            user_resume, company_info, interviewer_role, selected_topic
        )
        
        print(f"[DEBUG] 개별 질문 생성 완료 - 주제: {selected_topic}")
        print(f"[DEBUG] 사용자 질문: {user_main_question.get('question', 'N/A')[:50]}...")
        print(f"[DEBUG] AI 질문: {ai_main_question.get('question', 'N/A')[:50]}...")
        
        return {
            'user_question': user_main_question,
            'ai_question': ai_main_question,
            'interviewer_type': interviewer_role,
            'question_type': 'main',
            'is_individual_questions': True
        }
    
    def generate_question_with_orchestrator_state(self, state: Dict[str, Any]) -> Dict:
        """
        Orchestrator의 state 딕셔너리를 받아서 질문을 생성하는 메서드
        
        Args:
            state: Orchestrator의 state 객체
        """
        try:
            # Orchestrator의 state에서 직접 정보 추출
            turn_count = state.get('turn_count', 0)
            current_interviewer = state.get('current_interviewer')
            turn_state = state.get('interviewer_turn_state', {})
            
            # 턴 0: 인트로 메시지 생성
            if turn_count == 0:
                company_id = state.get('company_id')
                user_resume = {
                    'name': state.get('user_name', '지원자'),
                    'position': state.get('position', '개발자')
                }
                return self.generate_intro_message(company_id, user_resume)
            
            # 턴 1: 자기소개 (fixed)
            elif turn_count == 1:
                question_index = 0
                question = self.generate_fixed_question(question_index, state.get('company_id'), 
                                                      {"name": state.get('user_name', '지원자')})
                return question
            
            # 턴 2: 지원동기 (fixed)
            elif turn_count == 2:
                question_index = 1
                question = self.generate_fixed_question(question_index, state.get('company_id'), 
                                                      {"name": state.get('user_name', '지원자')})
                return question
            
            # 턴 3부터: 면접관별 질문 (메인 질문 + 꼬리 질문)
            else:
                # 🆕 상태 기반 면접관 결정 로직
                if not current_interviewer:
                    # 첫 번째 면접관은 HR부터 시작
                    current_interviewer = 'HR'
                
                # 🆕 결정한 면접관을 state에 설정
                state['current_interviewer'] = current_interviewer
                
                # 🆕 면접관 상태 초기화 (없으면 생성)
                if current_interviewer not in turn_state:
                    turn_state[current_interviewer] = {
                        'main_question_asked': False,
                        'follow_up_count': 0
                    }
                
                current_turn_state = turn_state.get(current_interviewer, {})
                
                # 기본 user_resume 구성
                user_resume = {
                    'name': state.get('user_name', '지원자'),
                    'position': state.get('position', '개발자')
                }
                
                # 메인 질문 안했으면 메인 질문 생성
                if not current_turn_state.get('main_question_asked', False):
                    question = self.generate_question_by_role(
                        interviewer_role=current_interviewer,
                        company_id=state.get('company_id'),
                        user_resume=user_resume,
                        previous_qa_pairs=state.get('qa_history', [])
                    )
                    return question
                
                # 꼬리 질문 생성 (최대 2개)
                elif current_turn_state.get('follow_up_count', 0) < 2:
                    # 🆕 qa_history에서 최신 데이터 추출
                    qa_history = state.get('qa_history', [])
                    if len(qa_history) >= 2:
                        # 가장 최근 질문과 답변들 추출
                        latest_qa_pairs = qa_history[-2:]  # 마지막 2개 (사용자 + AI 답변)
                        previous_question = latest_qa_pairs[0]['question'] if latest_qa_pairs else ''
                        
                        # 사용자와 AI 답변 분리
                        user_answer = ""
                        ai_answer = ""
                        for qa in latest_qa_pairs:
                            if qa['answerer'] == 'user':
                                user_answer = qa['answer']
                            elif qa['answerer'] == 'ai':
                                ai_answer = qa['answer']
                    else:
                        previous_question = ""
                        user_answer = ""
                        ai_answer = ""
                    
                    company_info = self.companies_data.get(state.get('company_id'), {})
                    
                    # 🆕 개별 꼬리질문 생성으로 변경
                    if user_answer and ai_answer:
                        print(f"[DEBUG] 개별 꼬리질문 생성 호출 - {current_interviewer}")
                        individual_questions = self.generate_follow_up_questions_for_both(
                            previous_question=previous_question,
                            user_answer=user_answer,
                            ai_answer=ai_answer,
                            company_info=company_info,
                            interviewer_role=current_interviewer,
                            user_resume=user_resume
                        )
                        return individual_questions
                    else:
                        # 폴백: 기존 단일 질문 방식
                        question = self.generate_follow_up_question(
                            previous_question=previous_question,
                            user_answer=user_answer,
                            chun_sik_answer=ai_answer,
                            company_info=company_info,
                            interviewer_role=current_interviewer,
                            user_resume=user_resume
                        )
                        return {
                            'user_question': question,
                            'ai_question': question,
                            'interviewer_type': current_interviewer,
                            'question_type': 'follow_up',
                            'is_individual_questions': False,
                            'fallback_reason': 'missing_answers'
                        }
                
                # 턴 전환 필요 (꼬리 질문 2개 완료)
                else:
                    # 다음 면접관 결정
                    roles = ['HR', 'TECH', 'COLLABORATION']
                    current_index = roles.index(current_interviewer)
                    next_index = (current_index + 1) % len(roles)
                    next_interviewer = roles[next_index]
                    
                    # 🆕 턴 전환 시 새로운 면접관의 상태 초기화
                    turn_state[next_interviewer] = {
                        'main_question_asked': False,
                        'follow_up_count': 0
                    }
                    
                    # 🆕 state의 current_interviewer도 업데이트
                    state['current_interviewer'] = next_interviewer
                    
                    return {
                        'turn_switch': True,
                        'next_interviewer': next_interviewer,
                        'message': f'{current_interviewer} 면접관 턴 완료, {next_interviewer} 면접관으로 전환'
                    }
            
        except Exception as e:
            print(f"[ERROR] state 기반 질문 생성 실패: {e}")
            user_name = state.get('user_name', '지원자')
            return {
                'question': f'{user_name}님, 자유롭게 본인에 대해 말씀해 주세요.',
                'intent': '일반적인 면접 질문',
                'interviewer_type': 'HR'
            }

   
    def generate_follow_up_question(self, previous_question: str, user_answer: str, 
                                   chun_sik_answer: str, company_info: Dict, 
                                   interviewer_role: str, user_resume: Dict = None) -> Dict:
        """동적 꼬리 질문 생성 - 답변 기반 실시간 심층 탐구"""
        
        # 프롬프트 빌더를 사용하여 프롬프트 생성
        position = user_resume.get('position', '개발자') if user_resume else '개발자'
        prompt = self.prompt_builder.build_follow_up_question_prompt(
            previous_question, user_answer, chun_sik_answer, company_info, interviewer_role, position, user_resume
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
            result['question_flow_type'] = 'follow_up'
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
        """주제 특화 DB 템플릿 기반 질문 생성 (LLM 튜닝 포함)"""
        question_type = self.interviewer_role_to_db_id.get(interviewer_role)
        if not question_type:
            raise ValueError(f"지원되지 않는 면접관 역할: {interviewer_role}")
        
        # 해당 면접관 유형의 질문들 필터링
        role_questions = [
            q for q in self.fixed_questions 
            if q.get('question_type') == question_type
        ]
        
        if not role_questions:
            raise ValueError(f"{interviewer_role} 유형의 질문이 DB에 없습니다")
        
        # 랜덤 선택
        selected_template = random.choice(role_questions)
        question_content = selected_template.get('question_content', '질문을 생성할 수 없습니다.')
        
        # 템플릿에 데이터 주입 (참조질문 커스터마이징)
        question_content = self._inject_data_to_template(question_content, user_resume, company_info)
        
        # ⭐ 새로운 LLM 튜닝 단계 추가 ⭐
        enhanced_question = self._enhance_db_template_with_llm(
            db_template=question_content,
            user_resume=user_resume,
            company_info=company_info,
            interviewer_role=interviewer_role
        )
        
        # 이름 호명 추가
        candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
        final_question = self._add_candidate_name_to_question(enhanced_question, candidate_name)
        
        return {
            'question': final_question,
            'intent': f"{topic} 관련 {selected_template.get('question_intent', f'{interviewer_role} 역량 평가')}",
            'interviewer_type': interviewer_role,
            'topic': topic,
            'question_source': 'db_template_enhanced'  # 소스 표시 변경
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
            'question_flow_type': 'follow_up',
            'question_source': 'fallback_follow_up'
        }
    
    def generate_follow_up_questions_for_both(self, previous_question: str, user_answer: str,
                                             ai_answer: str, company_info: Dict,
                                             interviewer_role: str, user_resume: Dict = None) -> Dict:
        """사용자와 AI 각각의 답변에 기반한 개별 꼬리질문 2개 생성"""
        
        try:
            print(f"[DEBUG] 개별 꼬리질문 생성 시작 - 면접관: {interviewer_role}")
            
            # 사용자용 꼬리질문 생성
            user_follow_up = self.generate_follow_up_question(
                previous_question=previous_question,
                user_answer=user_answer,
                chun_sik_answer=ai_answer,  # AI 답변도 전달 (비교 참고용)
                company_info=company_info,
                interviewer_role=interviewer_role,
                user_resume=user_resume
            )
            
            # AI용 꼬리질문 생성 (AI 답변에 더 집중)
            ai_follow_up = self._generate_ai_focused_follow_up(
                previous_question=previous_question,
                user_answer=user_answer,
                ai_answer=ai_answer,
                company_info=company_info,
                interviewer_role=interviewer_role,
                user_resume=user_resume
            )
            
            result = {
                'user_question': user_follow_up,
                'ai_question': ai_follow_up,
                'interviewer_type': interviewer_role,
                'question_type': 'follow_up',
                'is_individual_questions': True
            }
            
            print(f"[DEBUG] 개별 꼬리질문 생성 완료")
            print(f"[DEBUG] 사용자 질문: {user_follow_up.get('question', 'N/A')[:50]}...")
            print(f"[DEBUG] AI 질문: {ai_follow_up.get('question', 'N/A')[:50]}...")
            
            return result
            
        except Exception as e:
            print(f"[ERROR] 개별 꼬리질문 생성 실패: {e}")
            # 폴백: 공통 꼬리질문 사용
            common_follow_up = self.generate_follow_up_question(
                previous_question, user_answer, ai_answer, 
                company_info, interviewer_role, user_resume
            )
            
            return {
                'user_question': common_follow_up,
                'ai_question': common_follow_up,
                'interviewer_type': interviewer_role,
                'question_type': 'follow_up',
                'is_individual_questions': False,
                'fallback_reason': 'individual_generation_failed'
            }
    
    def _generate_ai_focused_follow_up(self, previous_question: str, user_answer: str,
                                     ai_answer: str, company_info: Dict,
                                     interviewer_role: str, user_resume: Dict = None) -> Dict:
        """AI 답변에 더 집중한 꼬리질문 생성"""
        
        # AI에게 더 적합한 프롬프트 구성
        position = user_resume.get('position', '개발자') if user_resume else '개발자'
        
        # AI 중심 프롬프트 빌드 (user_answer와 ai_answer 순서 바꿈)
        ai_focused_prompt = self.prompt_builder.build_follow_up_question_prompt(
            previous_question, user_answer=ai_answer, chun_sik_answer=user_answer, company_info=company_info, interviewer_role=interviewer_role, position=position, user_resume=user_resume
        )
        
        # AI 전용 시스템 프롬프트 (더 기술적/이론적 관점 강조)
        ai_system_prompt = f"""
당신은 {interviewer_role} 면접관입니다. AI 지원자의 답변에 기반하여 심층적인 꼬리 질문을 생성하세요.

AI 지원자 특성을 고려한 질문 생성 가이드라인:
- 기술적 세부사항이나 이론적 배경을 더 깊이 탐구
- 구현 방법론이나 아키텍처적 관점에서 접근
- 비교 분석이나 대안적 접근 방식에 대한 질문
- 확장성이나 최적화 관점에서의 심화 질문

응답 형식:
{{
    "question": "질문 내용",
    "intent": "질문 의도",
    "focus": "기술적 심화"
}}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": ai_system_prompt},
                    {"role": "user", "content": ai_focused_prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.7
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if not result_text:
                raise ValueError("LLM이 빈 응답을 반환했습니다")
            
            # JSON 파싱
            if '```json' in result_text:
                json_start = result_text.find('```json') + 7
                json_end = result_text.find('```', json_start)
                result_text = result_text[json_start:json_end].strip()
            elif '{' in result_text and '}' in result_text:
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1
                result_text = result_text[json_start:json_end]
            
            result = json.loads(result_text)
            
            if not result.get('question'):
                raise ValueError("question 필드가 비어있습니다")
            
            # AI용 질문이므로 "춘식이님" 호명 추가
            result['question'] = f"춘식이님, {result['question']}"
            result['interviewer_type'] = interviewer_role
            result['question_flow_type'] = 'ai_follow_up'
            result['question_source'] = 'ai_focused_llm'
            
            return result
            
        except Exception as e:
            print(f"[ERROR] AI 중심 꼬리질문 생성 실패: {e}")
            # 폴백: AI용 기본 꼬리질문
            return self._get_fallback_follow_up_question(interviewer_role, previous_question, 
                                                       {"name": "춘식이"})

    def _inject_data_to_template(self, template: str, user_resume: Dict, company_info: Dict) -> str:
        """템플릿에 실제 데이터 동적 주입"""
        result = template
        
        # 회사 정보 치환
        result = result.replace('{company_name}', company_info.get('name', '회사'))
        result = result.replace('{talent_profile}', company_info.get('talent_profile', ''))
        result = result.replace('{tech_focus}', ', '.join(company_info.get('tech_focus', [])))
        
        # 지원자 정보 치환 
        if user_resume:
            result = result.replace('{candidate_name}', user_resume.get('name', '지원자'))
            result = result.replace('{experience_years}', str(user_resume.get('career_years', '0')))
            result = result.replace('{main_skills}', ', '.join(user_resume.get('technical_skills', [])[:3]))
        
        # AI 지원자 이름 통일
        result = result.replace('{persona_name}', '춘식이')
        
        return result



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

    def _enhance_db_template_with_llm(self, db_template: str, user_resume: Dict, 
                                    company_info: Dict, interviewer_role: str) -> str:
        """DB 템플릿을 LLM으로 튜닝/개선하는 메서드"""
        try:
            # 프롬프트 빌더를 사용하여 고도화된 튜닝 프롬프트 생성
            enhancement_prompt = self.prompt_builder.build_db_template_enhancement_prompt(
                db_template=db_template,
                user_resume=user_resume,
                company_info=company_info,
                interviewer_role=interviewer_role
            )
            
            # 시스템 프롬프트
            system_prompt = self.prompt_builder.build_system_prompt_for_question_generation()
            
            # OpenAI API 호출
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhancement_prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            # 응답 파싱
            response_text = response.choices[0].message.content.strip()
            
            try:
                # JSON 파싱 시도
                import json
                result = json.loads(response_text)
                
                if 'question' in result and result['question'].strip():
                    return result['question'].strip()
                else:
                    logger.warning(f"LLM 응답에 question 필드가 없음: {result}")
                    return db_template
                    
            except json.JSONDecodeError as e:
                logger.warning(f"LLM 응답 JSON 파싱 실패: {response_text}, 에러: {e}")
                return db_template
                
        except Exception as e:
            logger.error(f"DB 템플릿 LLM 튜닝 실패: {e}")
            return db_template

    def _try_generate_main_question_for_user(self, user_resume: Dict, company_info: Dict, 
                                            interviewer_role: str, topic: str) -> Dict:
        """사용자에게 적합한 메인 질문 생성 시도 (기존 로직 재사용)"""
        use_db_first = random.choice([True, False])
        
        question_result = None
        
        if use_db_first:
            # 1차: DB 템플릿 기반 생성 시도
            question_result = self._try_generate_from_db_template(
                user_resume, company_info, interviewer_role, topic
            )
            if question_result:
                return question_result
            
            # 2차: DB 실패 시 LLM 생성 시도 
            question_result = self._try_generate_from_llm(
                user_resume, company_info, interviewer_role, topic
            )
            if question_result:
                return question_result
        else:
            # 1차: LLM 기반 생성 시도
            question_result = self._try_generate_from_llm(
                user_resume, company_info, interviewer_role, topic
            )
            if question_result:
                return question_result
            
            # 2차: LLM 실패 시 DB 템플릿 시도
            question_result = self._try_generate_from_db_template(
                user_resume, company_info, interviewer_role, topic
            )
            if question_result:
                return question_result
        
        # 최종 폴백: 일반적인 질문
        return self._get_generic_question(interviewer_role, topic, 
                                        user_resume.get('name', '지원자') if user_resume else '지원자')

    def _try_generate_main_question_for_ai(self, user_resume: Dict, company_info: Dict, 
                                          interviewer_role: str, topic: str) -> Dict:
        """AI 지원자에게 적합한 메인 질문 생성 시도"""
        use_db_first = random.choice([True, False])
        
        question_result = None
        
        if use_db_first:
            # 1차: AI용 DB 템플릿 기반 생성 시도
            try:
                question_result = self._generate_from_db_template_for_ai_with_topic(
                    user_resume, company_info, interviewer_role, topic
                )
                if question_result:
                    return question_result
            except Exception as e:
                print(f"[ERROR] AI용 DB 템플릿 생성 중 예외: {e}")
            
            # 2차: DB 실패 시 AI용 LLM 생성 시도
            try:
                question_result = self._generate_from_llm_for_ai_with_topic(
                    user_resume, company_info, interviewer_role, topic
                )
                if question_result:
                    return question_result
            except Exception as e:
                print(f"[ERROR] AI용 LLM 생성 중 예외: {e}")
        else:
            # 1차: AI용 LLM 기반 생성 시도
            try:
                question_result = self._generate_from_llm_for_ai_with_topic(
                    user_resume, company_info, interviewer_role, topic
                )
                if question_result:
                    return question_result
            except Exception as e:
                print(f"[ERROR] AI용 LLM 생성 중 예외: {e}")
            
            # 2차: LLM 실패 시 AI용 DB 템플릿 시도
            try:
                question_result = self._generate_from_db_template_for_ai_with_topic(
                    user_resume, company_info, interviewer_role, topic
                )
                if question_result:
                    return question_result
            except Exception as e:
                print(f"[ERROR] AI용 DB 템플릿 생성 중 예외: {e}")
        
        # 최종 폴백: AI용 일반적인 질문
        return self._get_generic_question(interviewer_role, topic, '춘식이')

    def _generate_from_llm_for_ai_with_topic(self, user_resume: Dict, company_info: Dict, 
                                     interviewer_role: str, topic: str) -> Dict:
        """AI 지원자에게 적합한 LLM 기반 메인 질문 생성"""
        
        # 프롬프트 빌더를 사용하여 기본 프롬프트 생성
        base_prompt = self.prompt_builder.build_main_question_prompt(
            user_resume, company_info, interviewer_role, topic
        )
        
        # AI 전용 시스템 프롬프트
        ai_system_prompt = f"""
당신은 {interviewer_role} 면접관입니다. AI 지원자에게 적합한 메인 질문을 생성하세요.

AI 지원자 특성을 고려한 질문 생성 가이드라인:
- 기술적 세부사항이나 이론적 배경을 더 깊이 탐구하는 질문
- 구현 방법론이나 아키텍처적 관점에서 접근하는 질문
- 비교 분석이나 대안적 접근 방식에 대한 질문
- 확장성이나 최적화 관점에서의 심화 질문
- AI의 학습 능력, 데이터 처리, 모델 최적화 등에 초점을 맞춘 질문

응답 형식:
{{
    "question": "질문 내용",
    "intent": "질문 의도",
    "focus": "기술적 심화"
}}
        """
        
        # LLM 호출
        try:
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": ai_system_prompt},
                    {"role": "user", "content": base_prompt}
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
            
            # AI용 질문이므로 "춘식이님" 호명 추가
            result['question'] = f"춘식이님, {result['question']}"
            result['interviewer_type'] = interviewer_role
            result['topic'] = topic
            result['question_source'] = 'llm_generated_for_ai'
            return result
            
        except Exception as e:
            print(f"[ERROR] AI 중심 메인 질문 생성 실패: {e}")
            raise

    def _generate_from_db_template_for_ai_with_topic(self, user_resume: Dict, company_info: Dict, 
                                            interviewer_role: str, topic: str) -> Dict:
        """AI 지원자에게 적합한 DB 템플릿 기반 질문 생성"""
        question_type = self.interviewer_role_to_db_id.get(interviewer_role)
        if not question_type:
            raise ValueError(f"지원되지 않는 면접관 역할: {interviewer_role}")
        
        # 해당 면접관 유형의 질문들 필터링
        role_questions = [
            q for q in self.fixed_questions 
            if q.get('question_type') == question_type
        ]
        
        if not role_questions:
            raise ValueError(f"{interviewer_role} 유형의 질문이 DB에 없습니다")
        
        # 랜덤 선택
        selected_template = random.choice(role_questions)
        question_content = selected_template.get('question_content', '질문을 생성할 수 없습니다.')
        
        # AI용 질문이므로 "춘식이님" 호명 추가
        question_with_name = f"춘식이님, {question_content}"
        
        return {
            'question': question_with_name,
            'intent': f"{topic} 관련 {selected_template.get('question_intent', f'{interviewer_role} 역량 평가')}",
            'interviewer_type': interviewer_role,
            'topic': topic,
            'question_source': 'db_template_for_ai'
        }


# 로거 초기화
logger = logging.getLogger(__name__)
