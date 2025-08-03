#!/usr/bin/env python3
"""
🗑️ DEPRECATED - 더 이상 사용하지 않음

이 파일의 모든 기능은 backend/services/interview_service.py로 이관되었습니다.
새로운 Backend 중앙 관제 시스템을 사용하세요.

기존 설명:
지능형 턴제 면접관 패널 시스템

핵심 특징:
- 3명의 면접관(HR, TECH, COLLABORATION)이 턴제로 질문 진행
- 각 면접관은 메인 질문 1개 + 동적 꼬리 질문 1~2개로 주제 심층 탐구
- 15개 주제 풀에서 다양한 메인 질문 선택
- 지원자 답변을 실시간 분석하여 맞춤형 꼬리 질문 생성
- DB 기반 참조질문과 LLM 기반 생성질문의 전략적 혼합
"""

# 🗑️ DEPRECATED - 모든 기능이 backend/services/interview_service.py로 이관됨
# import json
# import random
# import os
# import sys
# from typing import Dict, List, Any, Optional
# import openai
# from dotenv import load_dotenv

# 🚫 이 파일은 더 이상 사용되지 않습니다!
# 모든 기능이 backend/services/interview_service.py로 이관되었습니다.
# 새로운 중앙 관제 시스템을 사용하세요.

# # .env 파일에서 환경변수 로드
# load_dotenv()

# # 프로젝트 루트 경로 추가
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# from backend.services.supabase_client import get_supabase_client
# from llm.shared.constants import GPT_MODEL, MAX_TOKENS, TEMPERATURE
# from llm.candidate.model import CandidatePersona
# from .prompt import InterviewerPromptBuilder

class InterviewerService:
    """
    🚫 DEPRECATED - 더 이상 사용하지 않음
    
    이 클래스의 모든 기능은 backend/services/interview_service.py의 
    SessionState 및 중앙 관제 시스템으로 이관되었습니다.
    
    기존 설명: 지능형 턴제 기반 면접관 패널 시스템
    """
    
    def __init__(self, total_question_limit: int = 15):
        """
        🚫 DEPRECATED - 사용하지 마세요!
        backend/services/interview_service.py의 start_ai_competition()을 사용하세요.
        """
        raise DeprecationWarning(
            "🚫 InterviewerService는 더 이상 사용되지 않습니다. "
            "backend/services/interview_service.py의 새로운 중앙 관제 시스템을 사용하세요."
        )
        
        # 🗑️ 기존 코드 주석 처리
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
        
        # 턴제 시스템 관리 변수
        self.total_question_limit = total_question_limit
        self.questions_asked_count = 0
        self.current_interviewer_index = 0
        self.interviewer_turn_state = {
            'HR': {'main_question_asked': False, 'follow_up_count': 0},
            'TECH': {'main_question_asked': False, 'follow_up_count': 0}, 
            'COLLABORATION': {'main_question_asked': False, 'follow_up_count': 0}
        }
        
        # 면접관별 주제 풀 정의
        self.topic_pools = {
            'HR': ['인성_가치관', '성장_동기', '갈등_해결', '스트레스_관리', '팀워크_리더십'],
            'TECH': ['기술_역량', '문제_해결', '성능_최적화', '코드_품질', '새로운_기술_학습'],
            'COLLABORATION': ['소통_능력', '프로젝트_협업', '의견_조율', '크로스_팀_협업', '조직_문화_적응']
        }
    
    def _load_companies_data(self) -> Dict[str, Any]:
        """회사 데이터 로딩 및 캐싱 (CompanyDataLoader와 동일한 매핑 방식 사용)"""
        try:
            result = self.client.table('company').select('*').execute()
            companies_dict = {}
            
            # CompanyDataLoader와 동일한 매핑 테이블 사용
            company_id_mapping = {
                '네이버': 'naver',
                '카카오': 'kakao', 
                '라인': 'line',
                '라인플러스': '라인플러스',  # Supabase DB 호환성
                '쿠팡': 'coupang',
                '배달의민족': 'baemin',
                '당근마켓': 'daangn',
                '토스': 'toss'
            }
            
            if result.data:
                for company in result.data:
                    # 한글 이름을 영문 ID로 매핑
                    company_name = company.get('name', '')
                    english_id = company_id_mapping.get(company_name, company_name.lower())
                    companies_dict[english_id] = company
                    
            print(f"✅ 회사 데이터 로딩 완료: {len(companies_dict)}개, 키: {list(companies_dict.keys())}")
            return companies_dict
        except Exception as e:
            print(f"❌ 회사 데이터 로딩 실패: {e}")
            return {}
    
    def _load_fixed_questions(self) -> List[Dict[str, Any]]:
        """고정 질문 데이터 로딩 및 캐싱"""
        try:
            result = self.client.table('fix_question').select('*').execute()
            questions = result.data if result.data else []
            print(f"✅ 고정 질문 데이터 로딩 완료: {len(questions)}개")
            return questions
        except Exception as e:
            print(f"❌ 고정 질문 데이터 로딩 실패: {e}")
            return []
    
    def generate_next_question(self, user_resume: Dict, chun_sik_persona: CandidatePersona, 
                              company_id: str, previous_qa_pairs: List[Dict] = None,
                              user_answer: str = None, chun_sik_answer: str = None) -> Dict:
        """턴제 기반 면접 컨트롤 타워 - 질문 수 한도 관리 및 면접관 턴 제어"""
        
        print(f"🎯 [InterviewerService] generate_next_question 호출: questions_asked_count={self.questions_asked_count}, total_limit={self.total_question_limit}")
        
        # 질문 수 한도 확인
        if self.questions_asked_count >= self.total_question_limit:
            print(f"🏁 [InterviewerService] 질문 한도 도달, 면접 종료: {self.questions_asked_count}/{self.total_question_limit}")
            return {
                'question': '면접이 종료되었습니다. 수고하셨습니다.',
                'intent': '면접 종료',
                'interviewer_type': 'SYSTEM',
                'is_final': True
            }
        
        # 첫 2개 질문은 고정 (기존 로직 유지)
        if self.questions_asked_count == 0:
            self.questions_asked_count += 1
            print(f"📝 [InterviewerService] 1번째 질문 생성: 자기소개")
            # 자기소개는 이름을 모르는 상황이므로 이름 호명 없이 진행
            return {
                'question': '자기소개를 부탁드립니다.',
                'intent': '지원자의 기본 정보와 성격, 역량을 파악',
                'interviewer_type': 'HR'
            }
        
        elif self.questions_asked_count == 1:
            company_info = self.companies_data.get(company_id, {})
            company_name = company_info.get('name', '저희 회사')
            self.questions_asked_count += 1
            print(f"📝 [InterviewerService] 2번째 질문 생성: 지원동기 ({company_name})")
            
            # 지원동기 질문에 이름 호명 추가 (자기소개 후이므로 이름을 알고 있음)
            base_question = f'저희 {company_name}에 지원하신 동기를 말씀해 주세요.'
            candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
            question_with_name = self._add_candidate_name_to_question(base_question, candidate_name)
            
            return {
                'question': question_with_name,
                'intent': '회사에 대한 관심도와 지원 동기 파악',
                'interviewer_type': 'HR'
            }
        
        # 턴제 시스템 시작 (question_index >= 2)
        else:
            print(f"🎭 [InterviewerService] {self.questions_asked_count + 1}번째 질문 생성 (턴제 시스템)")
            company_info = self.companies_data.get(company_id, {})
            if not company_info:
                raise ValueError(f"회사 정보를 찾을 수 없습니다: {company_id}")
            
            # 현재 면접관 결정
            current_interviewer = self._get_current_interviewer()
            print(f"👔 [InterviewerService] 현재 면접관: {current_interviewer}")
            
            # 면접관의 턴 수행
            question_result = self._conduct_interview_turn(
                user_resume, chun_sik_persona, company_info, current_interviewer,
                user_answer, chun_sik_answer, previous_qa_pairs
            )
            
            # 질문 수 증가
            self.questions_asked_count += 1
            print(f"📈 [InterviewerService] 질문 수 증가: {self.questions_asked_count}/{self.total_question_limit}")
            
            # 면접관 턴 상태 업데이트
            self._update_turn_state(current_interviewer, question_result)
            
            return question_result
    
    def _get_current_interviewer(self) -> str:
        """현재 턴을 진행할 면접관 결정"""
        return self.interviewer_roles[self.current_interviewer_index]
    
    def _update_turn_state(self, interviewer_role: str, question_result: Dict):
        """면접관 턴 상태 업데이트 및 다음 면접관으로 전환 여부 결정"""
        turn_state = self.interviewer_turn_state[interviewer_role]
        
        # 강제 턴 전환인 경우 (빈 질문) 상태 업데이트 없이 바로 전환
        if question_result.get('force_turn_switch', False):
            self._switch_to_next_interviewer()
            return
        
        # 메인 질문이었는지 꼬리 질문이었는지 확인
        if question_result.get('question_type') == 'follow_up':
            turn_state['follow_up_count'] += 1
        else:
            # 메인 질문인 경우
            turn_state['main_question_asked'] = True
        
        # 턴 전환 조건 확인 (메인 질문 + 최대 2개 꼬리 질문 또는 남은 질문 수 부족)
        remaining_questions = self.total_question_limit - self.questions_asked_count
        should_switch_turn = (
            turn_state['follow_up_count'] >= 2 or  # 최대 꼬리 질문 수 도달
            remaining_questions <= 3  # 남은 질문이 적어 다른 면접관에게 기회 제공
        )
        
        if should_switch_turn:
            self._switch_to_next_interviewer()
    
    def _switch_to_next_interviewer(self):
        """다음 면접관으로 턴 전환"""
        # 현재 면접관의 턴 상태 초기화
        current_interviewer = self.interviewer_roles[self.current_interviewer_index]
        self.interviewer_turn_state[current_interviewer] = {
            'main_question_asked': False, 
            'follow_up_count': 0
        }
        
        # 다음 면접관으로 전환
        self.current_interviewer_index = (self.current_interviewer_index + 1) % 3
    
    def _conduct_interview_turn(self, user_resume: Dict, chun_sik_persona: CandidatePersona,
                               company_info: Dict, interviewer_role: str, 
                               user_answer: str = None, chun_sik_answer: str = None,
                               previous_qa_pairs: List[Dict] = None) -> Dict:
        """면접관의 턴 수행 - 메인 질문 또는 꼬리 질문 생성"""
        
        turn_state = self.interviewer_turn_state[interviewer_role]
        remaining_budget = self.total_question_limit - self.questions_asked_count
        
        # 메인 질문이 아직 안 나왔다면 메인 질문 생성
        if not turn_state['main_question_asked']:
            return self._generate_main_question(
                user_resume, chun_sik_persona, company_info, interviewer_role
            )
        
        # 메인 질문이 나왔다면 꼬리 질문 생성 조건 확인
        else:
            # 꼬리 질문 생성 조건 체크
            should_generate_follow_up = self._should_generate_follow_up_question(
                turn_state, remaining_budget, user_answer, chun_sik_answer
            )
            
            if should_generate_follow_up and user_answer and chun_sik_answer:
                # 이전 질문 정보 가져오기
                previous_question = self._get_last_question_from_history(previous_qa_pairs)
                
                return self._generate_follow_up_question(
                    previous_question, user_answer, chun_sik_answer, 
                    company_info, interviewer_role, user_resume
                )
            else:
                # 꼬리 질문을 생성하지 않고 턴 종료, 다음 면접관으로 넘김
                return {
                    'question': '',
                    'intent': '',
                    'interviewer_type': interviewer_role,
                    'force_turn_switch': True
                }
    
    def _should_generate_follow_up_question(self, turn_state: Dict, remaining_budget: int,
                                          user_answer: str, chun_sik_answer: str) -> bool:
        """꼬리 질문 생성 여부 결정"""
        
        # 기본 조건 체크
        if turn_state['follow_up_count'] >= 2:  # 최대 꼬리 질문 수 도달
            return False
        
        if remaining_budget <= 3:  # 남은 질문 수가 적어 다른 면접관에게 기회 제공
            return False
        
        if not user_answer or not chun_sik_answer:  # 이전 답변이 없으면 꼬리 질문 불가
            return False
        
        # 동적 결정 (답변 길이 기반)
        answer_quality_score = len(user_answer.split()) + len(chun_sik_answer.split())
        
        # 답변이 충분히 길거나 내용이 있으면 꼬리 질문 생성
        return answer_quality_score >= 20
    
    def _get_last_question_from_history(self, previous_qa_pairs: List[Dict]) -> str:
        """이전 질문 기록에서 마지막 질문 추출"""
        if not previous_qa_pairs:
            return "이전 질문 정보를 찾을 수 없습니다."
        
        last_qa = previous_qa_pairs[-1] if previous_qa_pairs else {}
        return last_qa.get('question', '이전 질문 정보를 찾을 수 없습니다.')
    
    def _generate_main_question(self, user_resume: Dict, chun_sik_persona: CandidatePersona,
                               company_info: Dict, interviewer_role: str) -> Dict:
        """메인 질문 생성 - 다양한 주제 풀에서 선택하여 참조/생성 혼합 (폴백 방지)"""
        
        # 면접관 역할에 맞는 주제 목록 선택
        topic_pool = self.topic_pools.get(interviewer_role, [])
        if not topic_pool:
            print(f"⚠️ [InterviewerService] {interviewer_role} 주제 풀이 비어있음. 일반 주제로 시도")
            topic_pool = ['일반']
        
        # 랜덤하게 주제 선택
        selected_topic = random.choice(topic_pool)
        
        # 50% 확률로 DB 템플릿 또는 LLM 생성 방식 선택
        use_db_first = random.choice([True, False])
        
        question_result = None
        
        if use_db_first:
            print(f"🎯 [InterviewerService] DB 템플릿 우선 시도: {selected_topic}")
            # 1차: DB 템플릿 기반 생성 시도
            question_result = self._try_generate_from_db_template(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
            
            print(f"❌ [InterviewerService] DB 템플릿 실패. LLM 생성으로 전환")
            # 2차: DB 실패 시 LLM 생성 시도 
            question_result = self._try_generate_from_llm(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
                
        else:
            print(f"🤖 [InterviewerService] LLM 생성 우선 시도: {selected_topic}")
            # 1차: LLM 기반 생성 시도
            question_result = self._try_generate_from_llm(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
            
            print(f"❌ [InterviewerService] LLM 생성 실패. DB 템플릿으로 전환")
            # 2차: LLM 실패 시 DB 템플릿 시도
            question_result = self._try_generate_from_db_template(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
        
        # 최종 폴백: 둘 다 실패 시 일반적인 질문 (장점/단점 아님)
        print(f"🚨 [InterviewerService] 모든 질문 생성 실패. 일반 질문으로 폴백")
        candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
        return self._get_generic_question(interviewer_role, selected_topic, candidate_name)
    
    def _try_generate_from_db_template(self, user_resume: Dict, company_info: Dict, 
                                     interviewer_role: str, topic: str) -> Optional[Dict]:
        """DB 템플릿 기반 질문 생성 시도 (실패 시 None 반환)"""
        try:
            return self._generate_from_db_template_with_topic(
                user_resume, company_info, interviewer_role, topic
            )
        except Exception as e:
            print(f"❌ [InterviewerService] DB 템플릿 생성 중 예외: {e}")
            return None
    
    def _try_generate_from_llm(self, user_resume: Dict, company_info: Dict, 
                             interviewer_role: str, topic: str) -> Optional[Dict]:
        """LLM 기반 질문 생성 시도 (실패 시 None 반환)"""
        try:
            return self._generate_from_llm_with_topic(
                user_resume, company_info, interviewer_role, topic
            )
        except Exception as e:
            print(f"❌ [InterviewerService] LLM 생성 중 예외: {e}")
            return None
    
    def _get_generic_question(self, interviewer_role: str, topic: str, candidate_name: str = None) -> Dict:
        """최종 폴백: 일반적인 질문 (장점/단점 아님)"""
        generic_questions = {
            'HR': {
                'question': f'{topic} 관련해서 본인의 경험을 자유롭게 말씀해 주세요.',
                'intent': '지원자의 경험과 역량 파악'
            },
            'TECH': {
                'question': f'{topic} 분야에서 본인이 해결한 문제나 경험을 설명해 주세요.',
                'intent': '기술적 문제 해결 능력 평가'
            },
            'COLLABORATION': {
                'question': f'{topic}과 관련된 팀 협업 경험을 말씀해 주세요.',
                'intent': '협업 능력과 소통 역량 평가'
            }
        }
        
        fallback = generic_questions.get(interviewer_role, generic_questions['HR'])
        
        # 이름 호명 추가
        question_with_name = self._add_candidate_name_to_question(
            fallback['question'], candidate_name
        )
        
        return {
            'question': question_with_name,
            'intent': fallback['intent'],
            'interviewer_type': interviewer_role,
            'topic': topic,
            'question_source': 'generic_fallback'
        }
    
    def _generate_from_db_template_with_topic(self, user_resume: Dict, company_info: Dict, 
                                            interviewer_role: str, topic: str) -> Dict:
        """주제 특화 DB 템플릿 기반 질문 생성"""
        
        # 면접관 역할에 해당하는 question_type ID 가져오기
        question_type_id = self.question_type_mapping.get(interviewer_role, 1)
        
        # 해당 타입의 질문 템플릿 필터링
        filtered_questions = [
            q for q in self.fixed_questions 
            if q.get('question_type') == question_type_id
        ]
        
        if not filtered_questions:
            raise ValueError(f"DB에 {interviewer_role} 역할(question_type={question_type_id})의 질문이 없습니다.")
        
        # 랜덤 템플릿 선택
        selected_template = random.choice(filtered_questions)
        
        # 템플릿에 데이터 주입
        question_content = self._inject_data_to_template(
            selected_template.get('question_content', ''),
            user_resume, 
            company_info
        )
        
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
            print(f"❌ LLM 메인 질문 생성 실패: {e}")
            raise  # 예외를 다시 발생시켜 상위 함수에서 처리하도록 함
    
    def _generate_follow_up_question(self, previous_question: str, user_answer: str, 
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
            
            # JSON 블록 추출 (```json 블록 또는 { } 블록)
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
            print(f"❌ 꼬리 질문 생성 실패: {e}")
            # 폴백 꼬리 질문
            return self._get_fallback_follow_up_question(interviewer_role, previous_question, user_resume)
    
    def _get_fallback_follow_up_question(self, interviewer_role: str, previous_question: str, user_resume: Dict = None) -> Dict:
        """꼬리 질문 생성 실패 시 폴백 질문"""
        
        fallback_follow_ups = {
            'HR': {
                'question': '방금 말씀해주신 내용에서 가장 어려웠던 점은 무엇이었나요?',
                'intent': '어려움 극복 과정과 성장 경험 확인'
            },
            'TECH': {
                'question': '해당 기술이나 방법을 선택한 구체적인 이유가 있다면 설명해주세요.',
                'intent': '기술적 판단 근거와 의사결정 과정 평가'
            },
            'COLLABORATION': {
                'question': '그 상황에서 다른 팀원들의 반응은 어땠나요?',
                'intent': '팀 동료와의 상호작용과 영향력 평가'
            }
        }
        
        fallback = fallback_follow_ups.get(interviewer_role, fallback_follow_ups['HR'])
        
        # 이름 호명 추가
        candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
        fallback['question'] = self._add_candidate_name_to_question(fallback['question'], candidate_name)
        
        fallback['interviewer_type'] = interviewer_role
        fallback['question_type'] = 'follow_up'
        fallback['question_source'] = 'fallback'
        
        return fallback
    
    def _add_candidate_name_to_question(self, question: str, candidate_name: str, is_intro_question: bool = False) -> str:
        """질문에 지원자 이름 호명 추가"""
        if not candidate_name or candidate_name == '지원자':
            return question
        
        # 자기소개 질문인 경우 특별 처리 (이미 이름을 모르는 상황)
        if is_intro_question:
            return question
        
        # 이름 호명 패턴들 (자연스러운 다양성 확보)
        name_patterns = [
            f"{candidate_name}님, {question}",
            f"{candidate_name}님께서는 {question}",
            f"{candidate_name}님, {question}",
            f"그렇다면 {candidate_name}님, {question}",
            f"{candidate_name}님의 경우 {question}"
        ]
        
        # 랜덤하게 패턴 선택 (80% 확률로 이름 호명)
        if random.random() < 0.8:
            selected_pattern = random.choice(name_patterns[:3])  # 기본 패턴 우선 사용
            return selected_pattern
        else:
            return question  # 20%는 이름 없이 (자연스러운 다양성)
    
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
    

def main():
    """턴제 면접 시스템 테스트"""
    print("🎯 지능형 턴제 면접관 패널 시스템 테스트")
    
    try:
        # 서비스 초기화
        service = InterviewerService(total_question_limit=10)
        
        # 샘플 데이터
        user_resume = {
            'name': '김개발',
            'position': '백엔드 개발자',  # 직군 정보 추가
            'career_years': '3',
            'technical_skills': ['Python', 'Django', 'PostgreSQL', 'AWS']
        }
        
        persona = CandidatePersona(
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
        
        qa_history = []
        total_topics = sum(len(topics) for topics in service.topic_pools.values())
        
        print(f"💼 질문 한도: {service.total_question_limit}개")
        print(f"👥 면접관: {', '.join(service.interviewer_roles)}")
        print(f"🎲 주제 풀: {total_topics}개")
        
        # 면접 시뮬레이션
        while service.questions_asked_count < service.total_question_limit:
            question = service.generate_next_question(
                user_resume, persona, '1', qa_history,
                user_answer="API 응답 시간을 50% 개선한 경험이 있습니다." if qa_history else None,
                chun_sik_answer="코드 리뷰와 테스트 코드 작성을 중시합니다." if qa_history else None
            )
            
            if question.get('is_final'):
                print(f"\n✅ {question['question']}")
                break
                
            if question.get('force_turn_switch'):
                print(f"🔄 {question['interviewer_type']} 면접관 턴 종료")
                continue
            
            # 질문 출력
            num = service.questions_asked_count
            interviewer = service._get_current_interviewer()
            state = service.interviewer_turn_state[interviewer]
            
            print(f"\n📝 질문 {num}번 - {question['interviewer_type']}")
            if question.get('topic'):
                print(f"🎯 주제: {question['topic']}")
            print(f"❓ {question['question']}")
            print(f"📈 턴 상태: 메인 {'✓' if state['main_question_asked'] else '✗'}, 꼬리 {state['follow_up_count']}개")
            
            qa_history.append({'question': question['question'], 'interviewer_type': question['interviewer_type']})
            
            if num >= 8:  # 테스트 제한
                break
        
        # 최종 통계
        print(f"\n📊 총 질문 수: {service.questions_asked_count}개")
        for role in service.interviewer_roles:
            state = service.interviewer_turn_state[role]
            print(f"   {role}: 메인 {'✓' if state['main_question_asked'] else '✗'}, 꼬리 {state['follow_up_count']}개")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()