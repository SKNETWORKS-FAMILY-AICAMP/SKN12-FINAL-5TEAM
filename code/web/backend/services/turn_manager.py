#!/usr/bin/env python3
"""
턴제 면접 관리자 - InterviewerService에서 분리된 턴제 로직 전담
순수 질문 생성은 QuestionGenerator에 위임
"""

import sys
import os
from typing import Dict, List, Any

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from llm.interviewer.question_generator import QuestionGenerator
from llm.candidate.model import CandidatePersona


class TurnManager:
    """턴제 면접 시스템 관리자"""
    
    def __init__(self, total_question_limit: int = 15):
        # 질문 생성기 의존성 주입
        self.question_generator = QuestionGenerator()
        
        # 턴제 시스템 관리 변수
        self.total_question_limit = total_question_limit
        self.questions_asked_count = 0
        self.current_interviewer_index = 0
        
        # 면접관 역할 정의
        self.interviewer_roles = ['HR', 'TECH', 'COLLABORATION']
        
        # 면접관별 턴 상태 관리
        self.interviewer_turn_state = {
            'HR': {'main_question_asked': False, 'follow_up_count': 0},
            'TECH': {'main_question_asked': False, 'follow_up_count': 0}, 
            'COLLABORATION': {'main_question_asked': False, 'follow_up_count': 0}
        }
    
    def generate_next_question(self, user_resume: Dict, chun_sik_persona: CandidatePersona, 
                              company_id: str, previous_qa_pairs: List[Dict] = None,
                              user_answer: str = None, chun_sik_answer: str = None) -> Dict:
        """턴제 기반 면접 컨트롤 타워 - 질문 수 한도 관리 및 면접관 턴 제어"""
        
        print(f"[TARGET] [TurnManager] generate_next_question 호출: questions_asked_count={self.questions_asked_count}, total_limit={self.total_question_limit}")
        
        # 질문 수 한도 확인
        if self.questions_asked_count >= self.total_question_limit:
            print(f"[FINISH] [TurnManager] 질문 한도 도달, 면접 종료: {self.questions_asked_count}/{self.total_question_limit}")
            return {
                'question': '면접이 종료되었습니다. 수고하셨습니다.',
                'intent': '면접 종료',
                'interviewer_type': 'SYSTEM',
                'is_final': True
            }
        
        # 첫 2개 질문은 고정 (기존 로직 유지)
        if self.questions_asked_count == 0:
            self.questions_asked_count += 1
            print(f"[NOTE] [TurnManager] 1번째 질문 생성: 자기소개")
            return self.question_generator.generate_fixed_question(0, company_id, user_resume)
        
        elif self.questions_asked_count == 1:
            self.questions_asked_count += 1
            print(f"[NOTE] [TurnManager] 2번째 질문 생성: 지원동기")
            return self.question_generator.generate_fixed_question(1, company_id, user_resume)
        
        # 턴제 시스템 시작 (question_index >= 2)
        else:
            print(f"[THEATER] [TurnManager] {self.questions_asked_count + 1}번째 질문 생성 (턴제 시스템)")
            
            # 현재 면접관 결정
            current_interviewer = self._get_current_interviewer()
            print(f"[SUIT] [TurnManager] 현재 면접관: {current_interviewer}")
            
            # 면접관의 턴 수행
            question_result = self._conduct_interview_turn(
                user_resume, chun_sik_persona, company_id, current_interviewer,
                user_answer, chun_sik_answer, previous_qa_pairs
            )
            
            # 질문 수 증가
            self.questions_asked_count += 1
            print(f"[CHART] [TurnManager] 질문 수 증가: {self.questions_asked_count}/{self.total_question_limit}")
            
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
            # 꼬리 질문 카운트 증가
            turn_state['follow_up_count'] += 1
        else:
            # 메인 질문 처리
            turn_state['main_question_asked'] = True
        
        # 턴 전환 조건 확인
        remaining_questions = self.total_question_limit - self.questions_asked_count
        
        # 1) 메인+꼬리 1개씩 완료하거나
        # 2) 남은 질문이 적어서 다른 면접관에게 기회를 줘야 하는 경우
        if (turn_state['main_question_asked'] and turn_state['follow_up_count'] >= 1) or \
           (remaining_questions <= 3 and not self._all_interviewers_had_main_turn()):
            self._switch_to_next_interviewer()
    
    def _switch_to_next_interviewer(self):
        """다음 면접관으로 턴 전환"""
        
        # 현재 면접관의 턴 상태 초기화
        current_interviewer = self.interviewer_roles[self.current_interviewer_index]
        self.interviewer_turn_state[current_interviewer] = {
            'main_question_asked': False,
            'follow_up_count': 0
        }
        
        # 다음 면접관으로 전환 (순환)
        self.current_interviewer_index = (self.current_interviewer_index + 1) % 3
        
        print(f"[SWITCH] [TurnManager] 면접관 전환: {current_interviewer} → {self.interviewer_roles[self.current_interviewer_index]}")
    
    def _all_interviewers_had_main_turn(self) -> bool:
        """모든 면접관이 메인 질문을 했는지 확인"""
        return all(
            self.interviewer_turn_state[role]['main_question_asked'] 
            for role in self.interviewer_roles
        )
    
    def _conduct_interview_turn(self, user_resume: Dict, chun_sik_persona: CandidatePersona, 
                               company_id: str, interviewer_role: str,
                               user_answer: str = None, chun_sik_answer: str = None, 
                               previous_qa_pairs: List[Dict] = None) -> Dict:
        """단일 면접관 턴 수행 - 메인 질문 또는 꼬리 질문 결정"""
        
        turn_state = self.interviewer_turn_state[interviewer_role]
        remaining_budget = self.total_question_limit - self.questions_asked_count
        
        # 턴 예산 확인 (남은 질문이 1개면 메인 질문만)
        if remaining_budget <= 1:
            if not turn_state['main_question_asked']:
                # 메인 질문 생성
                return self.question_generator.generate_question_by_role(
                    interviewer_role, company_id, user_resume, user_answer, chun_sik_answer, previous_qa_pairs
                )
            else:
                # 이미 메인 질문을 했으면 턴 종료
                return {
                    'question': '',
                    'interviewer_type': interviewer_role,
                    'force_turn_switch': True
                }
        
        # 일반적인 턴 진행
        if not turn_state['main_question_asked']:
            # 메인 질문 생성
            print(f"[MAIN] [TurnManager] {interviewer_role} 메인 질문 생성")
            return self.question_generator.generate_question_by_role(
                interviewer_role, company_id, user_resume, user_answer, chun_sik_answer, previous_qa_pairs
            )
        
        elif turn_state['follow_up_count'] == 0 and user_answer and previous_qa_pairs:
            # 꼬리 질문 생성 (이전 질문과 답변이 있는 경우)
            print(f"[FOLLOW] [TurnManager] {interviewer_role} 꼬리 질문 생성")
            
            # 가장 최근 질문 찾기
            previous_question = previous_qa_pairs[-1].get('question', '') if previous_qa_pairs else ''
            
            # 회사 정보 가져오기
            company_info = self.question_generator.companies_data.get(company_id, {})
            
            return self.question_generator.generate_follow_up_question(
                previous_question, user_answer, chun_sik_answer, company_info, interviewer_role, user_resume
            )
        
        else:
            # 이 면접관의 턴 종료 (메인+꼬리 완료)
            print(f"[END] [TurnManager] {interviewer_role} 턴 완료")
            return {
                'question': '',
                'interviewer_type': interviewer_role,
                'force_turn_switch': True
            }
    
    def get_interview_progress(self) -> Dict[str, Any]:
        """현재 면접 진행 상황 반환"""
        return {
            'questions_asked': self.questions_asked_count,
            'total_questions': self.total_question_limit,
            'percentage': (self.questions_asked_count / self.total_question_limit) * 100,
            'current_interviewer': self._get_current_interviewer(),
            'interviewer_states': self.interviewer_turn_state.copy()
        }
    
    def reset_interview(self):
        """면접 상태 초기화"""
        self.questions_asked_count = 0
        self.current_interviewer_index = 0
        self.interviewer_turn_state = {
            'HR': {'main_question_asked': False, 'follow_up_count': 0},
            'TECH': {'main_question_asked': False, 'follow_up_count': 0}, 
            'COLLABORATION': {'main_question_asked': False, 'follow_up_count': 0}
        }
        print("[RESET] [TurnManager] 면접 상태 초기화 완료")
    
    def is_interview_completed(self) -> bool:
        """면접 완료 여부 확인"""
        return self.questions_asked_count >= self.total_question_limit