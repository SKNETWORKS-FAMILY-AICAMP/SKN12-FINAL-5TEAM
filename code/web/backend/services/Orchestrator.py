import asyncio
import json
import random
import re
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from llm.candidate.quality_controller import QualityLevel
from llm.shared.logging_config import interview_logger
from llm.shared.models import AnswerRequest, LLMProvider, QuestionType

# TTS는 이제 프론트엔드에서 처리하므로 세마포어 제거

@dataclass
class Metadata:
    interview_id: str
    step: int
    task: str
    from_agent: str 
    next_agent: str
    status_code: int

@dataclass
class Content:
    type: str
    content: str

@dataclass
class Metrics:
    total_time: Optional[float] = None
    duration: Optional[float] = None

@dataclass
class AgentMessage:
    metadata: Metadata
    content: Content
    metrics: Metrics = field(default_factory=Metrics)

class Orchestrator:
    def __init__(self, session_id: str, session_state: Dict[str, Any], 
                 question_generator=None, ai_candidate_model=None):
        """
        Orchestrator: 모든 면접 비즈니스 로직 담당
        - 플로우 제어
        - 에이전트 조율
        - 메시지 처리
        - 상태 업데이트
        """
        self.session_id = session_id
        self.session_state = session_state  # InterviewService의 session_state 참조
        self.question_generator = question_generator
        self.ai_candidate_model = ai_candidate_model
        
        # TTS는 프론트엔드에서 처리하므로 이력 추적 불필요

    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """메시지를 받아서 상태를 업데이트하고 다음 액션을 결정 (🆕 즉시 TTS 처리 포함)"""
        from_agent = message.get("metadata", {}).get("from_agent", "unknown")
        print(f"[TRACE] {from_agent} -> Orchestrator")
        # 오디오 데이터 제외하고 로그 출력
        message_log = {k: v for k, v in message.items() if not k.endswith('_audio')}
        print(json.dumps(message_log, indent=2, ensure_ascii=False))

        task = message.get("metadata", {}).get("task")
        content = message.get("content", {}).get("content")

        # TTS 생성 로직 제거 - 텍스트만 처리하고 프론트엔드에서 TTS 처리

        # 상태 업데이트
        self._update_state_from_message(task, content, from_agent)

        # 다음 메시지 결정
        next_message = self._decide_next_message()
        next_agent = next_message.get("metadata", {}).get("next_agent", "unknown")
        print(f"[TRACE] Orchestrator -> {next_agent}")
        # 오디오 데이터 제외하고 로그 출력
        next_message_log = {k: v for k, v in next_message.items() if not k.endswith('_audio')}
        print(json.dumps(next_message_log, indent=2, ensure_ascii=False))
        return next_message

    def _update_state_from_message(self, task: str, content: str, from_agent: str) -> None:
        """메시지로부터 세션 상태 업데이트"""
        if task == "intro_generated":
            # 인트로 메시지 생성 완료 - 세션에 저장
            self.session_state['intro_message'] = content
            # 답변 없이 바로 턴 증가
            self.session_state['turn_count'] += 1  # 턴 0 완료, 턴 1로 이동
            # current_question은 설정하지 않음 (답변 요청하지 않음)
            
        elif task == "question_generated":
            # 턴 0에서 받은 메시지는 인트로 메시지로 처리
            current_turn = self.session_state.get('turn_count', 0)
            if current_turn == 0:
                self.session_state['intro_message'] = content
                self.session_state['turn_count'] += 1  # 턴 0 완료, 턴 1로 이동
                print(f"[DEBUG] 인트로 메시지 처리 완료: 턴 {current_turn} -> {self.session_state['turn_count']}")
            else:
                # 일반 질문 처리
                self.session_state['current_question'] = content
                print(f"[DEBUG] 일반 질문 처리: 턴 {current_turn}")
            
            # 🆕 질문 타입 추출 로직 제거 - QuestionGenerator에서 결정한 면접관 사용
            # current_interviewer는 QuestionGenerator에서 이미 설정됨
            # 여기서는 질문 내용만 저장하고 면접관 추측하지 않음
            
        elif task == "individual_questions_generated":
            # 🆕 개별 꼬리질문 생성 완료 - content는 dict 형태
            if isinstance(content, str):
                questions_data = json.loads(content)
            else:
                questions_data = content
                
            self.session_state['current_questions'] = {
                'user_question': questions_data.get('user_question', {}),
                'ai_question': questions_data.get('ai_question', {}),
                'is_individual': questions_data.get('is_individual_questions', True),
                'interviewer_type': questions_data.get('interviewer_type', 'HR')
            }
            
            print(f"[DEBUG] 개별 꼬리질문 상태 저장 완료")
            print(f"[DEBUG] 사용자 질문: {questions_data.get('user_question', {}).get('question', 'N/A')[:30]}...")
            print(f"[DEBUG] AI 질문: {questions_data.get('ai_question', {}).get('question', 'N/A')[:30]}...")
            
        elif task == "individual_answer_generated":
            # 🆕 개별 질문에 대한 답변 처리
            current_questions = self.session_state.get('current_questions', {})
            if current_questions.get('is_individual', False):
                # 개별 질문의 경우 answerer에 따라 해당하는 질문 매핑
                if from_agent == 'user':
                    question_text = current_questions.get('user_question', {}).get('question', '')
                elif from_agent == 'ai':
                    question_text = current_questions.get('ai_question', {}).get('question', '')
                else:
                    question_text = self.session_state.get('current_question', '')
            else:
                question_text = self.session_state.get('current_question', '')
            
            # 🆕 개별 답변 처리에서 질문은 TTS 큐에 추가하지 않음
            # 사용자 질문: create_user_waiting_message에서 이미 추가됨
            # AI 질문: _process_ai_task에서 추가됨 (ai_question 타입으로)
            print(f"[DEBUG] 개별 답변 처리: answerer={from_agent}, question='{question_text[:50]}...'")
            print(f"[DEBUG] TTS 큐 추가는 별도 로직에서 처리됨 (중복 방지)")
            
            # qa_history에 답변 저장
            qa_entry = {
                "question": question_text,
                "answerer": from_agent,
                "answer": content
            }
            self.session_state['qa_history'].append(qa_entry)
            print(f"[DEBUG] QA 저장: answerer={from_agent}, question='{question_text[:50]}...', answer='{content[:30]}...'")
            
            # 개별 답변 완료 체크 (사용자와 AI 모두 답변했는지)
            if current_questions.get('is_individual', False):
                # 현재 턴의 개별 답변 수 계산
                individual_answers = len([qa for qa in self.session_state['qa_history'] 
                                        if qa['question'] in [
                                            current_questions.get('user_question', {}).get('question', ''),
                                            current_questions.get('ai_question', {}).get('question', '')
                                        ]])
                
                if individual_answers >= 2:
                    self._handle_turn_completion_for_individual_questions()
            else:
                # 기존 로직 유지 (공통 질문인 경우)
                self._handle_turn_completion_for_common_question()
                
        elif task == "answer_generated":
            # 기존 답변 처리 (메인 질문 또는 공통 꼬리질문)
            # AI가 실제로 받은 질문이 사용자 질문과 다를 수 있으므로 보정
            if from_agent == 'ai' and '_ai_actual_question' in self.session_state:
                question_text = self.session_state.pop('_ai_actual_question')
            else:
                question_text = self.session_state['current_question']

            qa_entry = {
                "question": question_text,
                "answerer": from_agent,
                "answer": content
            }
            self.session_state['qa_history'].append(qa_entry)
            print(f"[DEBUG] QA 저장 (async): answerer={from_agent}, question='{question_text[:50]}...', answer='{content[:30]}...'")

            # 두 답변이 모두 완료되면 턴 증가 및 꼬리 질문 상태 업데이트
            # 현재 질문(사용자용)과 AI용 변환 텍스트 둘 다에 대해 답변이 존재하는지 확인
            try:
                user_question = self.session_state['current_question']
                ai_question_variant = self._format_question_for_ai(user_question)
                answers_for_pair = [qa for qa in self.session_state['qa_history']
                                    if qa['question'] in (user_question, ai_question_variant)]
                answerers = {qa['answerer'] for qa in answers_for_pair}
                if {'user', 'ai'}.issubset(answerers):
                    self._handle_turn_completion_for_common_question()
            except Exception:
                # 폴백: 기존 방식으로 현재 질문 텍스트 기준 카운트
                current_answers = len([qa for qa in self.session_state['qa_history']
                                      if qa['question'] == self.session_state['current_question']])
                if current_answers >= 2:
                    self._handle_turn_completion_for_common_question()

    def _handle_turn_completion_for_common_question(self):
        """공통 질문 완료 시 처리"""
        # 🆕 꼬리 질문 카운트 증가 (수정된 로직)
        current_interviewer = self.session_state.get('current_interviewer')
        current_turn = self.session_state.get('turn_count', 0)
        
        if current_interviewer and current_interviewer in ['HR', 'TECH', 'COLLABORATION']:
            turn_state = self.session_state.get('interviewer_turn_state', {})
            
            if current_interviewer in turn_state:
                # 현재 질문이 메인 질문인지 꼬리 질문인지 판단
                current_state = turn_state[current_interviewer]
                
                # 턴 1, 2는 고정 질문이므로 카운트하지 않음
                if current_turn > 2:
                    # 메인 질문 완료 표시
                    if not current_state['main_question_asked']:
                        turn_state[current_interviewer]['main_question_asked'] = True
                    else:
                        # 꼬리 질문 카운트 증가
                        turn_state[current_interviewer]['follow_up_count'] += 1
        
        self.session_state['turn_count'] += 1
        self.session_state['current_question'] = None
    
    def _handle_turn_completion_for_individual_questions(self):
        """개별 질문 완료 시 처리 (메인 질문 또는 꼬리 질문)"""
        current_interviewer = self.session_state.get('current_interviewer')
        current_turn = self.session_state.get('turn_count', 0)
        
        if current_interviewer and current_interviewer in ['HR', 'TECH', 'COLLABORATION']:
            turn_state = self.session_state.get('interviewer_turn_state', {})
            
            if current_interviewer in turn_state:
                current_state = turn_state[current_interviewer]
                
                # 턴 1, 2는 고정 질문이므로 카운트하지 않음
                if current_turn > 2:
                    # 메인 질문 vs 꼬리 질문 구분
                    if not current_state['main_question_asked']:
                        # 메인 질문 완료 처리
                        turn_state[current_interviewer]['main_question_asked'] = True
                    else:
                        # 꼬리 질문 완료 처리
                        turn_state[current_interviewer]['follow_up_count'] += 1
        
        self.session_state['turn_count'] += 1
        self.session_state['current_questions'] = None

    def _decide_next_message(self) -> Dict[str, Any]:
        """다음 메시지 결정 - 실제 플로우 제어 로직"""
        current_turn = self.session_state.get('turn_count', 0)
        start_time = self.session_state.get('start_time')
        
        # 턴 0: 인트로 처리
        if current_turn == 0:
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_intro",
                from_agent="orchestrator",
                content_text="인트로 메시지를 생성해주세요.",
                turn_count=current_turn,
                content_type="INTRO",
                start_time=start_time
            )
            message["metadata"]["next_agent"] = "interviewer"
            return message
        
        # 완료 조건 체크 (턴 0: 인트로 제외)
        if current_turn > self.session_state.get('total_question_limit', 15):
            # 🆕 현재 질문에 대한 모든 답변(사용자+AI)이 완료되었는지 확인
            current_question = self.session_state.get('current_question')
            if current_question:
                qa_history = self.session_state.get('qa_history', [])
                ai_question_variant = self._format_question_for_ai(current_question)
                current_answers = len([qa for qa in qa_history 
                                     if qa.get('question') == current_question or qa.get('question') == ai_question_variant])
                
                print(f"[DEBUG] 면접 종료 조건 체크: turn={current_turn}, current_answers={current_answers}, current_question='{current_question[:50]}...'")
                
                # 현재 질문에 대해 사용자와 AI 모두 답변했거나, 질문이 없으면 종료
                if current_answers < 2:
                    print(f"[DEBUG] 마지막 질문 답변 미완료 - 면접 계속 진행 (answers: {current_answers}/2)")
                    # 아직 답변이 완료되지 않았으면 아래 로직으로 계속 진행
                else:
                    print(f"[DEBUG] 마지막 질문 답변 완료 - 면접 종료")
                    self.session_state['is_completed'] = True
                    
                    # 🆕 면접 종료 메시지를 TTS 큐에 추가
                    end_message = "이것으로 면접을 마치겠습니다. 수고하셨습니다.."
                    tts_queue = self.session_state.get('tts_queue', [])
                    tts_queue.append({
                        'type': 'OUTRO',
                        'content': end_message
                    })
                    print(f"[DEBUG] 면접 종료 메시지 TTS 큐 추가: {end_message}")
                    
                    message = self.create_agent_message(
                        session_id=self.session_id,
                        task="end_interview",
                        from_agent="orchestrator",
                        content_text=end_message,
                        turn_count=current_turn,
                        content_type="OUTTRO",
                        start_time=start_time
                    )
                    message["metadata"]["next_agent"] = "orchestrator"
                    return message
            else:
                # 현재 질문이 없으면 즉시 종료
                print(f"[DEBUG] 현재 질문 없음 - 면접 종료")
                self.session_state['is_completed'] = True
                
                # 🆕 면접 종료 메시지를 TTS 큐에 추가
                end_message = "이것으로 면접을 마치겠습니다. 수고하셨습니다.."
                tts_queue = self.session_state.get('tts_queue', [])
                tts_queue.append({
                    'type': 'OUTRO',
                    'content': end_message
                })
                print(f"[DEBUG] 면접 종료 메시지 TTS 큐 추가: {end_message}")
                
                message = self.create_agent_message(
                    session_id=self.session_id,
                    task="end_interview",
                    from_agent="orchestrator",
                    content_text=end_message,
                    turn_count=current_turn,
                    content_type="OUTTRO",
                    start_time=start_time
                )
                message["metadata"]["next_agent"] = "orchestrator"
                return message

        # 🆕 개별 꼬리질문 처리 로직
        current_questions = self.session_state.get('current_questions')
        if current_questions and current_questions.get('is_individual', False):
            return self._handle_individual_questions_flow(current_questions, current_turn, start_time)
        
        # 현재 질문이 없으면 새 질문 생성 (메인 질문 또는 꼬리질문 결정)
        if not self.session_state.get('current_question'):
            # 🆕 꼬리질문 생성 조건 체크
            if self._should_generate_individual_follow_up():
                print(f"[DEBUG] 개별 꼬리질문 생성 조건 만족")
                message = self.create_agent_message(
                    session_id=self.session_id,
                    task="generate_individual_follow_up",
                    from_agent="orchestrator",
                    content_text="개별 꼬리질문을 생성해주세요.",
                    turn_count=current_turn,
                    start_time=start_time
                )
                message["metadata"]["next_agent"] = "interviewer_individual"
                return message
            else:
                # 일반 메인 질문 생성
                message = self.create_agent_message(
                    session_id=self.session_id,
                    task="generate_question",
                    from_agent="orchestrator",
                    content_text="다음 질문을 생성해주세요.",
                    turn_count=current_turn,
                    start_time=start_time
                )
                message["metadata"]["next_agent"] = "interviewer"
                return message
        
        # 현재 메인 질문에 대한 답변 수 확인 (AI용 변형 포함)
        user_question = self.session_state['current_question']
        ai_question_variant = self._format_question_for_ai(user_question) if user_question else None
        current_answers = len([qa for qa in self.session_state['qa_history']
                             if qa['question'] == user_question or (ai_question_variant and qa['question'] == ai_question_variant)])
        
        # 첫 번째 답변: 마지막 질문 고려 선택
        if current_answers == 0:
            current_turn = self.session_state.get('turn_count', 0)
            total_limit = self.session_state.get('total_question_limit', 15)
            is_final_question = current_turn >= total_limit
            
            print(f"[DEBUG] ===== 마지막 질문 감지 상세 로그 =====")
            print(f"[DEBUG] current_turn: {current_turn}")
            print(f"[DEBUG] total_limit: {total_limit}")
            print(f"[DEBUG] is_final_question: {is_final_question}")
            print(f"[DEBUG] current_turn >= total_limit: {current_turn >= total_limit}")
            print(f"[DEBUG] current_turn == total_limit: {current_turn == total_limit}")
            print(f"[DEBUG] 답변 선택 로직: turn={current_turn}, limit={total_limit}, is_final={is_final_question}")
            
            if current_turn == 1:
                selected_agent = 'user'  # 첫 질문은 항상 사용자가 먼저
                print(f"[DEBUG] 첫 질문 - 사용자 우선")
            elif is_final_question or current_turn == total_limit:
                selected_agent = 'ai'    # 🆕 마지막 질문은 AI가 먼저 (조건 강화)
                print(f"[DEBUG] ✅ 마지막 질문 감지 - AI 우선 실행 확정! (turn: {current_turn}, limit: {total_limit})")
                print(f"[DEBUG] ✅ selected_agent = 'ai' 설정됨")
            else:
                selected_agent = 'user' if self._random_select() == -1 else 'ai'  # 일반 질문은 랜덤
                print(f"[DEBUG] 일반 질문 - 랜덤 선택: {selected_agent}")
            # 에이전트별로 전달할 질문 텍스트 결정
            if selected_agent == 'ai':
                question_text = self._format_question_for_ai(self.session_state['current_question'])
                # QA 기록을 위해 임시 저장
                self.session_state['_ai_actual_question'] = question_text
            else:
                question_text = self.session_state['current_question']
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_answer",
                from_agent="orchestrator",
                content_text=question_text,
                turn_count=current_turn,
                start_time=start_time
            )
            message["metadata"]["next_agent"] = selected_agent
            return message
        
        # 두 번째 답변: 반대 에이전트
        elif current_answers == 1:
            # 🆕 실제 답변 존재 확인
            qa_history = self.session_state.get('qa_history', [])
            if not qa_history:
                print(f"[ERROR] current_answers=1이지만 qa_history가 비어있음")
                # 사용자 답변 대기로 처리
                selected_agent = 'user'
                question_text = self.session_state['current_question']
                message = self.create_agent_message(
                    session_id=self.session_id,
                    task="generate_answer", 
                    from_agent="orchestrator",
                    content_text=question_text,
                    turn_count=current_turn,
                    start_time=start_time
                )
                message["metadata"]["next_agent"] = selected_agent
                return message
            
            # 첫 번째 답변자 확인
            first_answerer = qa_history[-1]['answerer']
            print(f"[DEBUG] 첫 번째 답변자: {first_answerer}")
            
            # 🆕 사용자 답변이 실제로 제출되었는지 확인
            if first_answerer == 'user':
                # 🆕 실제 답변 내용이 있는지 확인
                user_answer = qa_history[-1].get('answer', '').strip()
                if not user_answer:
                    print(f"[DEBUG] 사용자 답변이 비어있음 - 사용자 대기 상태 유지")
                    selected_agent = 'user'
                    question_text = self.session_state['current_question']
                else:
                    # 🆕 마지막 질문이어도 AI에게 답변 기회 제공
                    print(f"[DEBUG] 사용자 답변 확인됨 - AI 처리 진행 (마지막 질문 포함)")
                    selected_agent = 'ai'
                    question_text = self._format_question_for_ai(self.session_state['current_question'])
                    self.session_state['_ai_actual_question'] = question_text
            else:
                # AI가 먼저 답변했으므로 사용자 차례  
                selected_agent = 'user'
                question_text = self.session_state['current_question']
                print(f"[DEBUG] AI 답변 확인됨 - 사용자 처리 진행")
                
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_answer",
                from_agent="orchestrator",
                content_text=question_text,
                turn_count=current_turn,
                start_time=start_time
            )
            message["metadata"]["next_agent"] = selected_agent
            return message
        
        # 모든 답변 완료: 다음 질문으로
        else:
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_question",
                from_agent="orchestrator",
                content_text="다음 질문을 생성해주세요.",
                turn_count=current_turn,
                start_time=start_time
            )
            message["metadata"]["next_agent"] = "interviewer"
            return message

   

    def _random_select(self) -> int:
        """사용자와 AI 중 랜덤으로 선택"""
        return random.choice([-1, 1])

    def _should_generate_individual_follow_up(self) -> bool:
        """개별 꼬리질문을 생성할 조건인지 체크 - 단순한 current_questions 존재 여부 체크"""
        # 🆕 간단한 current_questions 존재 여부 체크
        current_questions = self.session_state.get('current_questions')
        
        # current_questions가 없으면 개별 질문 생성 가능
        if current_questions is None:
            current_turn = self.session_state.get('turn_count', 0)
            current_interviewer = self.session_state.get('current_interviewer')
            turn_state = self.session_state.get('interviewer_turn_state', {})
            
            # 턴 3 이후 && 현재 면접관이 설정되어 있는 경우
            if (current_turn > 2 and 
                current_interviewer and 
                current_interviewer in turn_state):
                
                interviewer_state = turn_state[current_interviewer]
                main_asked = interviewer_state.get('main_question_asked', False)
                follow_up_count = interviewer_state.get('follow_up_count', 0)
                
                # 메인 질문은 완료했고, 꼬리질문이 2개 미만인 경우
                if main_asked and follow_up_count < 2:
                    print(f"[DEBUG] 개별 꼬리질문 조건 만족: {current_interviewer}, follow_up={follow_up_count}/2")
                    return True
        
        return False

    def _handle_individual_questions_flow(self, current_questions: Dict, current_turn: int, start_time: float) -> Dict[str, Any]:
        """개별 꼬리질문 플로우 처리"""
        user_question = current_questions.get('user_question', {}).get('question', '')
        ai_question = current_questions.get('ai_question', {}).get('question', '')
        
        # 개별 질문들에 대한 답변 수 확인
        qa_history = self.session_state.get('qa_history', [])
        individual_answers = len([qa for qa in qa_history 
                                if qa['question'] in [user_question, ai_question]])
        
        print(f"[DEBUG] 개별 질문 플로우: 답변 수 {individual_answers}/2")
        
        # 첫 번째 답변: 조건별 선택 (마지막 질문=AI 우선, 나머지=랜덤)
        if individual_answers == 0:
            total_limit = self.session_state.get('total_question_limit', 15)
            is_final_question = current_turn >= total_limit
            
            if is_final_question or current_turn == total_limit:
                selected_agent = 'ai'    # 마지막 질문은 AI 우선
                print(f"[DEBUG] 개별 질문 플로우: 마지막 질문 감지 - AI 우선 (turn: {current_turn}, limit: {total_limit})")
            else:
                selected_agent = 'user' if self._random_select() == -1 else 'ai'  # 일반 질문은 랜덤
                print(f"[DEBUG] 개별 질문 플로우: 일반 질문 - 랜덤 선택: {selected_agent}")
                
            question_text = user_question if selected_agent == 'user' else ai_question
            
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_individual_answer",
                from_agent="orchestrator",
                content_text=question_text,
                turn_count=current_turn,
                start_time=start_time
            )
            message["metadata"]["next_agent"] = selected_agent
            return message
        
        # 두 번째 답변: 반대 에이전트
        elif individual_answers == 1:
            # 첫 번째 답변자 확인
            first_answerer = qa_history[-1]['answerer']
            selected_agent = 'ai' if first_answerer == 'user' else 'user'
            question_text = user_question if selected_agent == 'user' else ai_question
            
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_individual_answer",
                from_agent="orchestrator",
                content_text=question_text,
                turn_count=current_turn,
                start_time=start_time
            )
            message["metadata"]["next_agent"] = selected_agent
            return message
        
        # 두 답변 모두 완료: 다음 단계로 (이 경우는 이미 _update_state_from_message에서 처리됨)
        else:
            return self._decide_next_message()  # 재귀 호출로 다음 단계 결정

    # 에이전트 조율 메서드들 (내부 처리용)
    async def _request_question_from_interviewer(self) -> str:
        """면접관(QuestionGenerator)에게 질문 생성을 요청하고, 텍스트 결과만 반환"""
        try:
            interview_logger.info(f"📤 면접관에게 질문 생성 요청: {self.session_id}")
            
            # QuestionGenerator에게 상태 객체(state)를 전달하여 질문 생성
            question_data = await asyncio.to_thread(
                self.question_generator.generate_question_with_orchestrator_state,
                self.session_state
            )
            
            # 🆕 턴 전환 처리
            if question_data.get('turn_switch'):
                # 🆕 턴 전환 시 바로 다음 질문을 요청 (재귀 호출)
                print(f"[DEBUG] 턴 전환 감지: {question_data.get('message', '')}")
                # 상태 업데이트 후 다시 질문 요청
                return await self._request_question_from_interviewer()
            
            # 🆕 개별 질문 데이터 체크 - 직접 반환
            if 'user_question' in question_data and 'ai_question' in question_data:
                print(f"[DEBUG] 개별 질문 감지됨 - 개별 질문 데이터 반환")
                return question_data  # Dict 형태로 반환
            
            # 일반 질문 반환
            return question_data.get('question', '다음 질문이 무엇인가요?')
            
        except Exception as e:
            interview_logger.error(f"면접관 질문 요청 오류: {e}", exc_info=True)
            return "죄송합니다, 질문을 생성하는 데 문제가 발생했습니다."

    async def _request_individual_follow_up_questions(self) -> Dict[str, Any]:
        """면접관에게 개별 꼬리질문 2개 생성 요청"""
        try:
            interview_logger.info(f"📤 면접관에게 개별 꼬리질문 생성 요청: {self.session_id}")
            
            # qa_history에서 최신 답변들 추출
            qa_history = self.session_state.get('qa_history', [])
            if len(qa_history) < 2:
                raise ValueError("개별 꼬리질문을 생성하려면 최소 2개의 답변이 필요합니다")
            
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
            
            if not user_answer or not ai_answer:
                raise ValueError("사용자와 AI 답변이 모두 필요합니다")
            
            # 회사 정보 가져오기
            company_info = self.question_generator.companies_data.get(
                self.session_state.get('company_id'), {}
            )
            
            # 현재 면접관 정보
            current_interviewer = self.session_state.get('current_interviewer', 'HR')
            
            # 사용자 이력서 정보
            user_resume = {
                'name': self.session_state.get('user_name', '지원자'),
                'position': self.session_state.get('position', '개발자')
            }
            
            print(f"[DEBUG] 개별 꼬리질문 생성 - 면접관: {current_interviewer}")
            print(f"[DEBUG] 이전 질문: {previous_question[:50]}...")
            print(f"[DEBUG] 사용자 답변: {user_answer[:50]}...")
            print(f"[DEBUG] AI 답변: {ai_answer[:50]}...")
            
            # 개별 꼬리질문 생성 요청
            follow_up_data = await asyncio.to_thread(
                self.question_generator.generate_follow_up_questions_for_both,
                previous_question=previous_question,
                user_answer=user_answer,
                ai_answer=ai_answer,
                company_info=company_info,
                interviewer_role=current_interviewer,
                user_resume=user_resume
            )
            
            return follow_up_data
            
        except Exception as e:
            interview_logger.error(f"개별 꼬리질문 요청 오류: {e}", exc_info=True)
            
            # 폴백: 공통 꼬리질문 사용
            try:
                common_question = await self._request_question_from_interviewer()
                return {
                    'user_question': {'question': common_question},
                    'ai_question': {'question': common_question},
                    'interviewer_type': self.session_state.get('current_interviewer', 'HR'),
                    'question_type': 'follow_up',
                    'is_individual_questions': False,
                    'fallback_reason': 'individual_request_failed'
                }
            except Exception as fallback_error:
                interview_logger.error(f"폴백 질문 생성도 실패: {fallback_error}")
                return {
                    'user_question': {'question': '추가로 설명해 주실 수 있나요?'},
                    'ai_question': {'question': '더 자세한 내용을 말씀해 주세요.'},
                    'interviewer_type': 'HR',
                    'question_type': 'follow_up',
                    'is_individual_questions': False,
                    'fallback_reason': 'complete_fallback'
                }

    async def _request_answer_from_ai_candidate(self, question: str) -> str:
        """AI 지원자에게 답변 생성을 요청하고, 텍스트 결과만 반환"""
        try:
            interview_logger.info(f"📤 AI 지원자에게 답변 요청: {self.session_id}")
            
            ai_persona = self.session_state.get('ai_persona')
            
            answer_request = AnswerRequest(
                question_content=question,
                question_type=QuestionType.HR, # TODO: 질문 유형을 state에서 가져오도록 개선
                question_intent="면접관의 질문",
                company_id=self.session_state.get('company_id'),
                position=self.session_state.get('position'),
                quality_level=QualityLevel.AVERAGE,
                llm_provider=LLMProvider.OPENAI_GPT4O
            )
            
            response = await asyncio.to_thread(
                self.ai_candidate_model.generate_answer,
                request=answer_request,
                persona=ai_persona
            )
            return response.answer_content
            
        except Exception as e:
            interview_logger.error(f"AI 지원자 답변 요청 오류: {e}", exc_info=True)
            return "죄송합니다, 답변을 생성하는 데 문제가 발생했습니다."

    # TTS 생성 메서드 제거 - 프론트엔드에서 TTS 처리

    # TTS 처리 메서드들 제거 - 프론트엔드에서 처리

    # TTS 재생 메서드들 제거 - 프론트엔드에서 TTS 처리

    # 실시간 TTS 메서드 제거 - 프론트엔드에서 TTS 처리
    
    # TTS 저장 메서드 제거 - 프론트엔드에서 TTS 처리

    # TTS 판단 메서드 제거 - 프론트엔드에서 TTS 처리

    # TTS 에이전트 타입 결정 메서드 제거 - 프론트엔드에서 TTS 처리

    # 개별 질문 TTS 생성 메서드 제거 - 프론트엔드에서 TTS 처리

    @staticmethod
    def create_agent_message(session_id: str, task: str, from_agent: str, content_text: str, 
                             turn_count: int, duration: float = 0, content_type: str = "text", 
                             start_time: float = None) -> Dict[str, Any]:
        """외부(Agent)에서 Orchestrator로 보낼 메시지를 생성하는 정적 메서드"""
        # 🆕 total_time 계산
        total_time = None
        if start_time:
            total_time = time.time() - start_time
        
        return {
            "metadata": {
                "interview_id": session_id,
                "step": turn_count,
                "task": task,
                "from_agent": from_agent,
                "next_agent": "orchestrator",
                "status_code": 200
            },
            "content": {
                "type": content_type,
                "content": content_text
            },
            "metrics": {
                "duration": duration,
                "total_time": total_time
            }
        }

    async def process_user_answer(self, user_answer: str, time_spent: float = None) -> Dict[str, Any]:
        """사용자 답변을 처리하고 전체 플로우를 완료하여 최종 결과 반환"""
        print(f"[TRACE] Orchestrator.process_user_answer start: session={self.session_id}")
        
        # 🆕 개별 질문 상태 체크
        current_questions = self.session_state.get('current_questions')
        is_individual_question = current_questions and current_questions.get('is_individual', False)
        
        # 1. 사용자 답변 메시지 생성 및 처리
        task = "individual_answer_generated" if is_individual_question else "answer_generated"
        
        user_message = self.create_agent_message(
            session_id=self.session_id,
            task=task,
            from_agent="user",
            content_text=user_answer,
            turn_count=self.session_state.get('turn_count', 0),
            duration=time_spent,
            start_time=self.session_state.get('start_time')
        )
        
        # 2. 사용자 답변으로 상태 업데이트 (handle_message에서 JSON 출력됨)
        await self.handle_message(user_message)
        
        # 3. 다음 액션 결정 및 전체 플로우 처리
        return await self._process_complete_flow()
    
    async def _process_complete_flow(self) -> Dict[str, Any]:
        """완전한 플로우를 처리하여 최종 결과 반환"""
        print(f"[TRACE] Orchestrator._process_complete_flow start: session={self.session_id}")
        
        loop_count = 0
        while True:
            loop_count += 1
            current_turn = self.session_state.get('turn_count', 0)
            tts_queue_size = len(self.session_state.get('tts_queue', []))
            
            print(f"[TRACE] === 루프 {loop_count} 시작 ===")
            print(f"[TRACE] turn={current_turn}, tts_queue_size={tts_queue_size}")
            
            # 다음 메시지 결정
            next_message = self._decide_next_message()
            next_agent = next_message.get("metadata", {}).get("next_agent")
            task = next_message.get("metadata", {}).get("task")
            
            print(f"[TRACE] decide_next -> next_agent={next_agent}, task={task}")
            
            # 루프 무한 방지 (디버깅용)
            if loop_count > 10:
                print(f"[ERROR] 루프 10회 초과 - 강제 중단")
                break
            
            # 완료 조건 체크
            if task == "end_interview":
                print(f"[TRACE] interview complete")
                result = {
                    "status": "completed",
                    "message": "이것으로 면접을 마치겠습니다. 수고하셨습니다..",
                    "qa_history": self.session_state.get('qa_history', []),
                    "session_id": self.session_id
                }
                # 🆕 프론트 추출용 AI 메타데이터 포함 (resume_id 전달)
                try:
                    ai_resume_id = self.session_state.get('ai_resume_id') or (
                        (self.session_state.get('ai_persona') or {}).get('resume_id') if isinstance(self.session_state.get('ai_persona'), dict) else None
                    )
                except Exception:
                    ai_resume_id = None
                result['turn_info'] = {
                    'ai_metadata': {
                        'resume_id': ai_resume_id
                    }
                }
                print(f"[TRACE] Orchestrator -> Client (complete)")
                # 오디오 데이터 제외하고 로그 출력
                result_log = {k: v for k, v in result.items() if not k.endswith('_audio')}
                print(json.dumps(result_log, indent=2, ensure_ascii=False))
                return result
            
            # 사용자 입력 대기 상태인 경우
            if next_agent == "user":
                print(f"[TRACE] wait for user input")
                
                # 🆕 현재 질문에 대한 사용자 답변이 없으면 루프 중단
                current_question = self.session_state.get('current_question')
                if current_question:
                    qa_history = self.session_state.get('qa_history', [])
                    user_answered = any(qa.get('question') == current_question and qa.get('answerer') == 'user' and qa.get('answer', '').strip()
                                      for qa in qa_history)
                    if not user_answered:
                        print(f"[DEBUG] 사용자 답변 미완료 - 루프 중단하고 대기")
                        # 사용자 대기 메시지 생성 전 TTS 큐 상태
                        tts_queue_before = len(self.session_state.get('tts_queue', []))
                        result = await self.create_user_waiting_message()
                        tts_queue_after = len(self.session_state.get('tts_queue', []))
                        
                        print(f"[TRACE] TTS 큐 변화: {tts_queue_before} -> {tts_queue_after}")
                        print(f"[TRACE] Orchestrator -> Client (wait) - 루프 종료")
                        return result
                
                # 사용자 대기 메시지 생성 전 TTS 큐 상태
                tts_queue_before = len(self.session_state.get('tts_queue', []))
                result = await self.create_user_waiting_message()
                tts_queue_after = len(self.session_state.get('tts_queue', []))
                
                print(f"[TRACE] TTS 큐 변화: {tts_queue_before} -> {tts_queue_after}")
                print(f"[TRACE] Orchestrator -> Client (wait) - 루프 종료")
                # JSON 출력은 create_user_waiting_message에서 이미 처리됨
                return result
            
            # 에이전트 작업 수행 (handle_message에서 TTS 순차 처리 포함)
            tts_queue_before_agent = len(self.session_state.get('tts_queue', []))
            
            if next_agent == "interviewer":
                print(f"[TRACE] interviewer task start")
                await self._process_interviewer_task()
            elif next_agent == "interviewer_individual":
                print(f"[TRACE] interviewer individual follow-up task start")
                await self._process_individual_interviewer_task()
            elif next_agent == "ai":
                print(f"[TRACE] ai task start")
                
                # 🆕 AI 작업 실행 전 추가 검증 (마지막 질문 예외)
                current_question = self.session_state.get('current_question')
                current_turn = self.session_state.get('turn_count', 0)
                total_limit = self.session_state.get('total_question_limit', 15)
                is_final_question = current_turn >= total_limit
                
                print(f"[DEBUG] ===== AI 작업 시작 전 마지막 질문 체크 =====")
                print(f"[DEBUG] current_turn: {current_turn}")
                print(f"[DEBUG] total_limit: {total_limit}")
                print(f"[DEBUG] is_final_question: {is_final_question}")
                print(f"[DEBUG] current_question: {current_question}")
                print(f"[DEBUG] =========================================")
                
                if current_question and not is_final_question:
                    # 일반 질문에서만 사용자 답변 확인
                    qa_history = self.session_state.get('qa_history', [])
                    user_answered = any(qa.get('question') == current_question and qa.get('answerer') == 'user' and qa.get('answer', '').strip()
                                      for qa in qa_history)
                    if not user_answered:
                        print(f"[ERROR] AI 작업 실행 중지 - 사용자 답변이 없음")
                        # 사용자 대기 상태로 강제 전환
                        result = await self.create_user_waiting_message()
                        return result
                elif is_final_question:
                    print(f"[DEBUG] ✅ 마지막 질문 - AI 작업 검증 건너뜀 (turn: {current_turn}, limit: {total_limit})")
                    print(f"[DEBUG] ✅ 마지막 질문에서 AI 작업 진행 확정!")
                
                print(f"[DEBUG] AI 작업 시작: _process_ai_task 호출")
                await self._process_ai_task(next_message.get("content", {}).get("content"))
                print(f"[DEBUG] AI 작업 완료: _process_ai_task 완료")
            
            tts_queue_after_agent = len(self.session_state.get('tts_queue', []))
            print(f"[TRACE] {next_agent} 처리 후 TTS 큐 변화: {tts_queue_before_agent} -> {tts_queue_after_agent}")
            print(f"[TRACE] === 루프 {loop_count} 완료 - 다음 루프로 ===")
            # 루프 계속

    async def _process_initial_flow(self) -> Dict[str, Any]:
        """
        ⚡ 면접 시작용 초기 플로우: INTRO + 첫 번째 질문 처리하고 즉시 응답
        - 전체 면접 플로우 대신 INTRO + 첫 질문만 생성하여 API 응답 속도 최적화
        """
        print(f"[⚡ INITIAL_FLOW] 면접 시작 초기 플로우 시작: session={self.session_id}")
        print(f"[⚡ DEBUG] 시작 시 session_state: {self.session_state}")
        
        try:
            # 1. INTRO 생성 및 TTS 처리
            current_turn = self.session_state.get('turn_count', 0)
            print(f"[⚡ DEBUG] INTRO 단계 - current_turn: {current_turn}")
            
            if current_turn == 0:
                print(f"[⚡ INITIAL_FLOW] INTRO 생성 시작 (turn={current_turn})")
                
                # 면접관에게 INTRO 요청
                intro_content = await self._request_question_from_interviewer()
                print(f"[⚡ DEBUG] INTRO content 생성됨: {intro_content[:100]}...")
                
                # INTRO 메시지 생성 및 처리
                intro_response = self.create_agent_message(
                    session_id=self.session_id,
                    task="intro_generated",
                    from_agent="interviewer", 
                    content_text=intro_content,
                    turn_count=current_turn,
                    content_type="INTRO",
                    start_time=self.session_state.get('start_time')
                )
                
                # handle_message로 TTS 생성 및 상태 업데이트
                await self.handle_message(intro_response)
                print(f"[⚡ INITIAL_FLOW] ✅ INTRO 처리 완료")
                print(f"[⚡ DEBUG] INTRO 처리 후 session_state: {self.session_state}")
            else:
                print(f"[⚡ WARNING] INTRO 단계 건너뜀 - current_turn이 0이 아님: {current_turn}")
            
            # 2. 첫 번째 질문 생성 및 TTS 처리
            current_turn = self.session_state.get('turn_count', 0)
            print(f"[⚡ DEBUG] 첫 번째 질문 단계 - current_turn: {current_turn}")
            
            if current_turn == 1:  # INTRO 처리 후 턴이 1이 됨
                print(f"[⚡ INITIAL_FLOW] 첫 번째 질문 생성 시작 (turn={current_turn})")
                
                # 면접관에게 첫 번째 질문 요청
                first_question = await self._request_question_from_interviewer()
                print(f"[⚡ DEBUG] 첫 번째 질문 content 생성됨: {first_question[:100]}...")
                
                # 첫 번째 질문 메시지 생성 및 처리
                question_response = self.create_agent_message(
                    session_id=self.session_id,
                    task="question_generated",
                    from_agent="interviewer", 
                    content_text=first_question,
                    turn_count=current_turn,
                    content_type="QUESTION",
                    start_time=self.session_state.get('start_time')
                )
                
                # handle_message로 TTS 생성 및 상태 업데이트
                await self.handle_message(question_response)
                print(f"[⚡ INITIAL_FLOW] ✅ 첫 번째 질문 처리 완료")
                print(f"[⚡ DEBUG] 첫 번째 질문 처리 후 session_state: {self.session_state}")
            else:
                print(f"[⚡ WARNING] 첫 번째 질문 단계 건너뜀 - current_turn이 1이 아님: {current_turn}")
                
            # 3. session_state 상세 분석
            print(f"[⚡ DEBUG] === 최종 session_state 분석 ===")
            print(f"[⚡ DEBUG] turn_count: {self.session_state.get('turn_count')}")
            print(f"[⚡ DEBUG] intro_message: {bool(self.session_state.get('intro_message'))}")
            print(f"[⚡ DEBUG] intro_audio: {bool(self.session_state.get('intro_audio'))}")
            print(f"[⚡ DEBUG] current_question: {bool(self.session_state.get('current_question'))}")
            print(f"[⚡ DEBUG] question_audio: {bool(self.session_state.get('question_audio'))}")
            if self.session_state.get('current_question'):
                print(f"[⚡ DEBUG] current_question 내용: {self.session_state.get('current_question')[:50]}...")
                
            # 4. INTRO + 첫 번째 질문 응답 즉시 반환 (클라이언트 호환성 보장)
            first_question = self.session_state.get('current_question')
            ai_resume_id = self.session_state.get('ai_resume_id')
            
            result = {
                "status": "interview_started",
                "message": "면접이 시작되었습니다. INTRO와 첫 번째 질문을 확인해주세요.",
                "session_id": self.session_id,
                "intro_message": self.session_state.get('intro_message'),
                "first_question": first_question,
                # 오디오 필드들 제거
                # 🆕 클라이언트가 기대하는 content 구조 추가
                "content": {
                    "question": first_question,
                    "content": first_question,  # 호환성을 위한 중복
                    "metadata": {
                        "ai_resume_id": ai_resume_id,
                        "interviewer_type": "HR",
                        "question_type": "main",
                        "turn_count": self.session_state.get('turn_count', 0)
                    }
                },
                # 🆕 최상위 레벨에도 ai_resume_id 포함 (다중 접근 경로)
                "ai_resume_id": ai_resume_id,
                "metadata": {
                    "ai_resume_id": ai_resume_id,
                    "session_id": self.session_id,
                    "interviewer_type": "HR"
                },
                # 🆕 ai_answer 구조도 추가 (클라이언트 호환성)
                "ai_answer": {
                    "metadata": {
                        "ai_resume_id": ai_resume_id
                    }
                },
                "turn_info": {
                    "current_turn": self.session_state.get('turn_count', 0),
                    "is_user_turn": True,
                    "next_action": "wait_user_answer",
                    "ai_metadata": {
                        "ai_resume_id": ai_resume_id
                    }
                }
            }
            
            print(f"[⚡ INITIAL_FLOW] === 면접 시작 응답 준비 완료 ===")
            print(f"[⚡ INITIAL_FLOW] INTRO 메시지: {bool(result.get('intro_message'))}")
            print(f"[⚡ INITIAL_FLOW] 첫 번째 질문: {bool(result.get('first_question'))}")
            print(f"[⚡ INITIAL_FLOW] 🆕 content 필드: {bool(result.get('content'))}")
            print(f"[⚡ INITIAL_FLOW] 🆕 ai_resume_id (최상위): {result.get('ai_resume_id')}")
            print(f"[⚡ INITIAL_FLOW] 🆕 ai_answer.metadata: {bool(result.get('ai_answer', {}).get('metadata'))}")
            print(f"[⚡ INITIAL_FLOW] 🆕 content.metadata.ai_resume_id: {result.get('content', {}).get('metadata', {}).get('ai_resume_id')}")
            if result.get('first_question'):
                print(f"[⚡ INITIAL_FLOW] 첫 번째 질문 내용: {result.get('first_question')[:50]}...")
            print(f"[⚡ INITIAL_FLOW] ✅ API 즉시 응답 (텍스트 전용)!")
            
            return result
            
        except Exception as e:
            print(f"[⚡ INITIAL_FLOW] ❌ 초기 플로우 처리 실패: {e}")
            print(f"[⚡ INITIAL_FLOW] 스택 트레이스: {traceback.format_exc()}")
            
            return {
                "status": "error",
                "message": f"면접 시작 중 오류가 발생했습니다: {str(e)}",
                "session_id": self.session_id
            }
    
    async def _process_interviewer_task(self):
        """면접관 작업 처리"""
        print(f"[TRACE] Orchestrator -> Interviewer (generate_question)")
        
        # 🆕 현재 상태 디버깅 (개선)
        current_interviewer = self.session_state.get('current_interviewer')
        turn_state = self.session_state.get('interviewer_turn_state', {})
        current_turn = self.session_state.get('turn_count', 0)
        
        print(f"[TRACE] interviewer_state turn={current_turn}, current_interviewer={current_interviewer}")
        for role, state in turn_state.items():
            main_done = "✓" if state['main_question_asked'] else "✗"
            follow_count = state['follow_up_count']
            print(f"[DEBUG]   {role}: 메인 {main_done}, 꼬리 {follow_count}개")
        
        question_result = await self._request_question_from_interviewer()
        
        # 🆕 반환값 타입에 따른 처리
        if isinstance(question_result, dict) and 'user_question' in question_result and 'ai_question' in question_result:
            print(f"[TRACE] individual questions generated (dict)")
            
            # 🆕 중복 방지: 개별 질문 생성 시에는 TTS 큐에 추가하지 않음
            # 실제 질문/답변 처리 시에 TTS 큐에 추가됨
            user_question_text = question_result.get('user_question', {}).get('question', '')
            ai_question_text = question_result.get('ai_question', {}).get('question', '')
            print(f"[DEBUG] 개별 질문 생성 완료 - 사용자용: {user_question_text[:50]}...")
            print(f"[DEBUG] 개별 질문 생성 완료 - AI용: {ai_question_text[:50]}...")
            print(f"[DEBUG] TTS 큐 추가는 실제 처리 시에 수행됨 (중복 방지)")
            
            # 개별 질문 메시지 생성
            questions_message = self.create_agent_message(
                session_id=self.session_id,
                task="individual_questions_generated",
                from_agent="interviewer",
                content_text=json.dumps(question_result),
                turn_count=current_turn,
                content_type=current_interviewer or "HR",
                start_time=self.session_state.get('start_time')
            )
            
            # TRACE 출력: interviewer -> orchestrator (individual_questions_generated)
            # 🆕 handle_message에서 TTS가 순차적으로 처리됨
            await self.handle_message(questions_message)
            
        else:
            # 일반 질문 처리
            question_content = question_result if isinstance(question_result, str) else str(question_result)
            
            # 🆕 content_type 결정
            content_type = "INTRO" if current_turn == 0 else current_interviewer or "HR"
            
            # 🆕 마지막 질문 감지
            total_limit = self.session_state.get('total_question_limit', 15)
            is_final_question = current_turn >= total_limit
            
            print(f"[DEBUG] 질문 생성 단계: turn={current_turn}, limit={total_limit}, is_final={is_final_question}")
            
            # 🆕 마지막 질문이 아닐 때만 즉시 TTS 큐 추가
            if not is_final_question:
                tts_queue = self.session_state.get('tts_queue', [])
                tts_queue.append({
                    'type': content_type,
                    'content': question_content
                })
                print(f"[DEBUG] 일반 질문 TTS 큐 추가 ({content_type}): {question_content[:50]}...")
            else:
                print(f"[DEBUG] 마지막 질문 - 사용자용 질문 TTS 큐 추가 연기")
            
            # 현재 턴에 따라 task 결정
            task = "intro_generated" if current_turn == 0 else "question_generated"
            
            question_message = self.create_agent_message(
                session_id=self.session_id,
                task=task,
                from_agent="interviewer",
                content_text=question_content,
                turn_count=current_turn,
                content_type=content_type,
                start_time=self.session_state.get('start_time')
            )
            
            # TRACE 출력: interviewer -> orchestrator (question_generated)  
            # 🆕 handle_message에서 TTS가 순차적으로 처리됨
            await self.handle_message(question_message)
    
    async def _process_individual_interviewer_task(self):
        """개별 꼬리질문 생성 작업 처리"""
        print(f"[TRACE] Orchestrator -> Interviewer (generate_individual_follow_up)")
        
        # 현재 상태 디버깅
        current_interviewer = self.session_state.get('current_interviewer')
        turn_state = self.session_state.get('interviewer_turn_state', {})
        current_turn = self.session_state.get('turn_count', 0)
        
        print(f"[TRACE] individual follow-up start turn={current_turn}, interviewer={current_interviewer}")
        
        try:
            # 개별 꼬리질문 생성 요청
            individual_questions = await self._request_individual_follow_up_questions()
            
            # 개별 질문 메시지 생성 및 처리
            questions_message = self.create_agent_message(
                session_id=self.session_id,
                task="individual_questions_generated",
                from_agent="interviewer",
                content_text=json.dumps(individual_questions),  # Dict를 JSON으로 변환
                turn_count=current_turn,
                content_type=current_interviewer or "HR",
                start_time=self.session_state.get('start_time')
            )
            
            # TRACE 출력: interviewer -> orchestrator (individual_questions_generated)
            # 🆕 handle_message에서 TTS가 순차적으로 처리됨  
            await self.handle_message(questions_message)
            
        except Exception as e:
            print(f"[TRACE][ERROR] individual follow-up generation failed: {e}")
            # 폴백: 일반 질문으로 대체
            await self._process_interviewer_task()

    async def _process_individual_interviewer_task_parallel(self) -> Dict[str, Any]:
        """
        🆕 병렬 처리를 적용한 개별 꼬리질문 생성 작업 처리
        """
        print(f"[TRACE] Orchestrator -> Interviewer (generate_individual_follow_up)")
        
        # 현재 상태 디버깅
        current_interviewer = self.session_state.get('current_interviewer')
        turn_state = self.session_state.get('interviewer_turn_state', {})
        current_turn = self.session_state.get('turn_count', 0)
        
        print(f"[TRACE] individual follow-up start turn={current_turn}, interviewer={current_interviewer}")
        
        try:
            # 개별 꼬리질문 생성 요청
            individual_questions = await self._request_individual_follow_up_questions()
            
            # 개별 질문 메시지 생성 및 처리
            questions_message = self.create_agent_message(
                session_id=self.session_id,
                task="individual_questions_generated",
                from_agent="interviewer",
                content_text=json.dumps(individual_questions),  # Dict를 JSON으로 변환
                turn_count=current_turn,
                content_type=current_interviewer or "HR",
                start_time=self.session_state.get('start_time')
            )
            
            # TRACE 출력: interviewer -> orchestrator (individual_questions_generated)
            # 🆕 handle_message에서 TTS가 순차적으로 처리됨
            await self.handle_message(questions_message)
            
            return questions_message
            
        except Exception as e:
            print(f"[TRACE][ERROR] individual follow-up generation failed: {e}")
            # 폴백: 일반 질문으로 대체
            return await self._process_interviewer_task_parallel()
    
    async def _process_ai_task(self, question: str):
        """AI 지원자 작업 처리"""
        print(f"[TRACE] Orchestrator -> AI (question) : {question[:50]}...")
        
        # AI에게 전달할 질문에서 사용자 이름 호칭을 AI용으로 최소 치환
        ai_question = self._format_question_for_ai(question)
        
        # 🆕 AI 질문을 TTS 큐에 추가
        tts_queue = self.session_state.get('tts_queue', [])
        tts_queue.append({
            'type': 'ai_question',
            'content': ai_question
        })
        print(f"[DEBUG] AI 질문 TTS 큐 추가: {ai_question[:50]}...")
        
        ai_answer = await self._request_answer_from_ai_candidate(ai_question)
        
        # 🆕 AI 답변을 TTS 큐에 추가
        tts_queue.append({
            'type': 'ai_answer', 
            'content': ai_answer
        })
        print(f"[DEBUG] AI 답변 TTS 큐 추가: {ai_answer[:50]}...")
        
        # 🆕 마지막 질문에서 AI 작업 완료 후 사용자용 질문 TTS 큐 추가
        current_turn = self.session_state.get('turn_count', 0)
        total_limit = self.session_state.get('total_question_limit', 15)
        is_final_question = current_turn >= total_limit
        
        if is_final_question:
            user_question = self.session_state.get('current_question', '')
            current_interviewer = self.session_state.get('current_interviewer', 'HR')
            user_content_type = current_interviewer if current_interviewer in ['HR', 'TECH', 'COLLABORATION'] else 'HR'
            
            if user_question:
                tts_queue.append({
                    'type': user_content_type,
                    'content': user_question
                })
                print(f"[DEBUG] 마지막 질문 - AI 작업 완료 후 사용자용 질문 TTS 추가: {user_question[:50]}...")
        
        # 🆕 개별 질문 상태 체크
        current_questions = self.session_state.get('current_questions')
        is_individual_question = current_questions and current_questions.get('is_individual', False)
        
        # 🆕 content_type 결정 (현재 면접관 기반)
        current_interviewer = self.session_state.get('current_interviewer', 'HR')
        content_type = current_interviewer if current_interviewer in ['HR', 'TECH', 'COLLABORATION'] else 'HR'
        
        # 개별 질문 여부에 따라 task 결정
        task = "individual_answer_generated" if is_individual_question else "answer_generated"
        
        # AI가 실제로 받은 질문을 상태에 임시 저장 (qa 기록용)
        self.session_state['_ai_actual_question'] = ai_question

        ai_message = self.create_agent_message(
            session_id=self.session_id,
            task=task,
            from_agent="ai",
            content_text=ai_answer,
            turn_count=self.session_state.get('turn_count', 0),
            content_type=content_type,
            start_time=self.session_state.get('start_time')
        )
        
        # handle_message에서 JSON 출력되고 TTS도 순차적으로 처리됨
        await self.handle_message(ai_message)

    async def create_user_waiting_message(self) -> Dict[str, Any]:
        """사용자 입력 대기 메시지 생성"""
        # 🆕 개별 질문 상태 체크
        current_questions = self.session_state.get('current_questions')
        is_individual_question = current_questions and current_questions.get('is_individual', False)
        
        # 🆕 질문 텍스트 결정
        if is_individual_question:
            question_text = current_questions.get('user_question', {}).get('question', '')
            print(f"[DEBUG] 사용자 개별 질문: {question_text[:50]}...")
        else:
            question_text = self.session_state.get('current_question', '')
        
        # 🆕 content_type 결정 (현재 면접관 기반)
        current_interviewer = self.session_state.get('current_interviewer', 'HR')
        content_type = current_interviewer if current_interviewer in ['HR', 'TECH', 'COLLABORATION'] else 'HR'
        
        # 🆕 개별 질문에서 사용자 질문을 TTS 큐에 추가
        if is_individual_question and question_text:
            tts_queue = self.session_state.get('tts_queue', [])
            
            # 중복 방지: 이미 큐에 있는지 확인
            question_already_in_queue = any(item.get('content') == question_text for item in tts_queue)
            
            if not question_already_in_queue:
                tts_queue.append({
                    'type': f'{current_interviewer}_user_question',
                    'content': question_text
                })
                print(f"[DEBUG] 사용자 대기 메시지 생성 시 사용자 질문 TTS 큐 추가: {question_text[:50]}...")
            else:
                print(f"[DEBUG] 사용자 질문이 이미 TTS 큐에 존재함 - 중복 추가 방지: {question_text[:50]}...")
        
        response = self.create_agent_message(
            session_id=self.session_id,
            task="wait_for_user_input",
            from_agent="orchestrator",
            content_text=question_text,
            turn_count=self.session_state.get('turn_count', 0),
            content_type=content_type,
            start_time=self.session_state.get('start_time')
        )
        # next_agent를 'user'로 수정하여 프론트엔드가 올바르게 인식하도록 함
        response['metadata']['next_agent'] = 'user'
        response['status'] = 'waiting_for_user'
        response['message'] = '답변을 입력해주세요.'
        response['session_id'] = self.session_id
        
        # 🆕 INTRO 메시지 포함 (첫 번째 응답에서만) - 오디오 제거
        current_turn = self.session_state.get('turn_count', 0)
        intro_message = self.session_state.get('intro_message')
        
        # INTRO는 턴 1에서만 전달 (턴 2 이후에는 불필요)
        if current_turn <= 1 and intro_message:
            response['intro_message'] = intro_message
            print(f"[📝 TEXT] INTRO 메시지 전달 (턴 {current_turn}): {intro_message[:50]}...")
            
            # 한 번 전달 후 삭제
            if 'intro_message' in self.session_state:
                del self.session_state['intro_message']
                
            print(f"[📝 TEXT] 🗑️ INTRO 데이터 삭제 완료 - 다음 턴부터는 전송 안함")
        else:
            print(f"[📝 TEXT] INTRO 전송 건너뜀 (턴 {current_turn}, intro_message 존재: {bool(intro_message)})")
        
        # AI 질문 텍스트만 처리 - 오디오 제거
        current_question = question_text
        ai_resume_id = self.session_state.get('ai_resume_id')
        
        print(f"[📝 TEXT] AI 질문 텍스트 전달: {current_question[:50] if current_question else 'N/A'}...")
        
        # 표준화된 응답 구조 추가 - 오디오 제거
        response['content'] = {
            'question': current_question,
            'content': current_question,
            'metadata': {
                'ai_resume_id': ai_resume_id,
                'interviewer_type': content_type,
                'question_type': 'main' if not is_individual_question else 'individual',
                'turn_count': self.session_state.get('turn_count', 0)
            }
        }
        
        # ai_answer 구조 추가 - 오디오 제거, 프론트엔드 호환을 위해 resume_id도 추가
        response['ai_answer'] = {
            'metadata': {
                'ai_resume_id': ai_resume_id,
                'resume_id': ai_resume_id  # 프론트엔드 호환성을 위한 필드
            }
        }
        
        # 🆕 최상위 ai_resume_id
        response['ai_resume_id'] = ai_resume_id
        response['metadata'] = {
            'ai_resume_id': ai_resume_id,
            'resume_id': ai_resume_id,  # 프론트엔드 호환성을 위한 필드
            'session_id': self.session_id,
            'interviewer_type': content_type
        }
        
        # 🆕 턴 정보 추가 (개별 질문 정보 포함) - ai_resume_id 중복 정의 제거
        response['turn_info'] = {
            'current_turn': self.session_state.get('turn_count', 0),
            'is_user_turn': True,
            'is_individual_question': is_individual_question,
            'question_type': 'individual_follow_up' if is_individual_question else 'main_question',
            'ai_metadata': {
                'resume_id': ai_resume_id
            }
        }
        
        # 🆕 개별 질문 텍스트 정보 추가 (프론트엔드 호환성)
        if is_individual_question and current_questions:
            response['turn_info']['user_question_text'] = current_questions.get('user_question', {}).get('question', '')
            response['turn_info']['ai_question_text'] = current_questions.get('ai_question', {}).get('question', '')
            print(f"[DEBUG] 턴 정보에 개별 질문 텍스트 추가: user={bool(response['turn_info'].get('user_question_text'))}, ai={bool(response['turn_info'].get('ai_question_text'))}")
        
        # 🆕 TTS 통합 큐를 클라이언트로 전달
        tts_queue = self.session_state.get('tts_queue', [])
        
        print(f"[📝 TTS_QUEUE] TTS 큐 전달 체크:")
        print(f"  - tts_queue 항목 수: {len(tts_queue)}")
        
        if tts_queue:
            response['tts_queue'] = tts_queue.copy()  # 복사본 전달
            print(f"[📝 TTS_QUEUE] TTS 큐 전달 완료 - {len(tts_queue)}개 항목:")
            for i, item in enumerate(tts_queue):
                print(f"  {i+1}. {item.get('type', 'unknown')}: {item.get('content', '')[:50]}...")
            
            # 한 번 전달 후 큐 비우기
            self.session_state['tts_queue'] = []
            print(f"[📝 TTS_QUEUE] 🗑️ TTS 큐 초기화 완료 - 다음 턴을 위해 비움")
        else:
            print(f"[📝 TTS_QUEUE] TTS 큐 없음 - 빈 큐 전달")
            response['tts_queue'] = []
        
        # 사용자 질문 텍스트 확인 - 오디오 제거
        if question_text and question_text.strip():
            print(f"[📝 TEXT] 사용자 질문 확인: {question_text[:50]}...")
        else:
            print(f"[📝 TEXT] 사용자 질문이 비어있음")
        
        # 최종 응답 상태 로그 - 오디오 제거
        print(f"[📝 REALTIME] === 텍스트 전용 처리 완료 ===")
        print(f"[📝 REALTIME] TTS 생성: 프론트엔드에서 처리")
        print(f"[📝 REALTIME] ✅ API 즉시 응답 준비 완료!")
        
        # 응답 JSON 출력
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        return response

    def _format_question_for_ai(self, question: str) -> str:
        """AI에게 보낼 때 사용자 이름 호칭을 '춘식이님'으로 최소 치환"""
        try:
            if not isinstance(question, str):
                return question

            user_name_raw = self.session_state.get('user_name', '지원자') or '지원자'
            # 공백 제거 및 '님' 제거한 두 가지 버전 준비
            user_name_compact = re.sub(r"\s+", "", user_name_raw)
            name_wo_suffix = user_name_compact[:-1] if user_name_compact.endswith('님') else user_name_compact

            # 패턴들: 맨 앞에 등장하는 이름 호칭 + 선택적 공백/콤마를 AI용으로 치환
            patterns = [
                rf"^\s*{re.escape(name_wo_suffix)}\s*님\s*[,， ]*",
                rf"^\s*{re.escape(user_name_compact)}\s*[,， ]*",
                rf"{re.escape(name_wo_suffix)}\s*님\s*[,， ]*",
                rf"{re.escape(user_name_compact)}\s*[,， ]*",
            ]

            for pat in patterns:
                if re.search(pat, question):
                    question = re.sub(pat, "춘식이님, ", question, count=1)
                    break

            # 일반적인 '지원자님' 호칭 치환 (한 번만)
            if re.search(r"지원자님\s*[,， ]*", question):
                question = re.sub(r"지원자님\s*[,， ]*", "춘식이님, ", question, count=1)

            # 선두에 중복된 'AI ' 토큰 정리: 'AI AI 지원자님' -> '춘식이님'
            question = re.sub(r"^\s*(AI\s+)+지원자님\s*[,， ]*", "춘식이님, ", question)

            # 호칭이 없으면 앞에만 붙임 (중복 방지)
            if not question.strip().startswith("춘식이님"):
                question = f"춘식이님, {question}"
            return question
        except Exception:
            return question

    # 🗑️ 기존 병렬 처리 메서드들 제거됨 - 순차 처리 방식으로 변경
    # _generate_and_play_tts_parallel, _generate_tts_async, _play_audio_async 
    # 이제 _generate_and_play_tts_sequential 메서드 사용

    async def _process_interviewer_task_parallel(self) -> Dict[str, Any]:
        """🆕 순차 처리 방식으로 변경된 면접관 태스크 처리"""
        # 기존 _process_interviewer_task와 동일하게 처리
        return await self._process_interviewer_task()

    async def _process_ai_task_parallel(self, question: str) -> Dict[str, Any]:
        """🆕 순차 처리 방식으로 변경된 AI 태스크 처리"""  
        # 기존 _process_ai_task와 동일하게 처리
        await self._process_ai_task(question)
        # AI 태스크는 반환값이 없는 void 메서드이므로 성공 메시지 반환
        return self.create_agent_message(
            session_id=self.session_id,
            task="ai_task_completed",
            content_text="AI 답변 처리 완료",
            from_agent="orchestrator", 
            turn_count=self.session_state.get('turn_count', 0)
        )

    
