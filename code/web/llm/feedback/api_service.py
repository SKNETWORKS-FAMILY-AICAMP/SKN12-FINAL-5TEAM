import os
import json
from .process_single_qa import SingleQAProcessor
from .final_eval import run_final_evaluation_from_realtime
from .supabase_client import SupabaseManager
from .plan_eval import generate_interview_plan
from typing import Tuple, Optional
import re

class InterviewEvaluationService:
    # 클래스 변수로 모델 인스턴스 저장 (싱글톤 패턴)
    _shared_processor = None
    
    def __init__(self):
        """면접 평가 서비스 초기화"""
        self.processor = None
        self.db_manager = None
        self._initialize_processor()
        self._initialize_db()
    
    def _initialize_processor(self):
        """프로세서 초기화 (모델만 미리 로드)"""
        try:
            if InterviewEvaluationService._shared_processor is None:
                print("ML 모델과 임베딩 모델을 최초 로드 중...")
                # 모델 로딩만 미리 수행
                from .num_eval import load_model, load_encoder, MODEL_PATH, ENCODER_NAME
                ml_model = load_model(MODEL_PATH)
                encoder = load_encoder(ENCODER_NAME)
                InterviewEvaluationService._shared_processor = {
                    'ml_model': ml_model,
                    'encoder': encoder
                }
                print("모델 로드 완료! (이후 요청에서 재사용됨)")
            else:
                print("기존 로드된 모델 재사용")
            
            self.processor = InterviewEvaluationService._shared_processor
            
        except Exception as e:
            print(f"WARNING: 모델 로드 실패: {str(e)}")
            print(f"상세 에러: {type(e).__name__}: {str(e)}")
            self.processor = None
    
    def _initialize_db(self):
        """Supabase 데이터베이스 초기화"""
        try:
            self.db_manager = SupabaseManager()
            print("SUCCESS: 데이터베이스 연결 성공")
        except Exception as e:
            print(f"WARNING: 데이터베이스 연결 실패: {str(e)}")
            self.db_manager = None
    
    
    def _create_interview_session(self, user_id: int, ai_resume_id: Optional[int] = None, 
                                 user_resume_id: Optional[int] = None, posting_id: Optional[int] = None,
                                 company_id: Optional[int] = None, position_id: Optional[int] = None) -> Optional[int]:
        """새로운 면접 세션 생성"""
        if self.db_manager:
            try:
                interview_id = self.db_manager.save_interview_session(
                    user_id=user_id,
                    ai_resume_id=ai_resume_id,
                    user_resume_id=user_resume_id,
                    posting_id=posting_id,
                    company_id=company_id,
                    position_id=position_id
                )
                return interview_id
            except Exception as e:
                print(f"WARNING: 면접 세션 생성 실패: {str(e)}")
        return None
    
    def _evaluate_single_question(self, qa_pair, company_info, question_index, position_info=None, posting_info=None, resume_info=None, who='user'):
        """단일 질문 평가 (공유 모델 사용)"""
        try:
            print(f"\n--- Q{question_index} 평가 중 ---")
            
            # 동적으로 SingleQAProcessor 생성 (미리 로드된 모델 사용)
            if not self.processor:
                raise ValueError("ML 모델이 로드되지 않았습니다.")
            
            from .num_eval import evaluate_single_qa as num_evaluate_single_qa
            from .text_eval import evaluate_single_qa_with_intent_extraction
            
            # ML 점수 계산 (미리 로드된 모델 사용)
            ml_score = num_evaluate_single_qa(
                qa_pair.question, qa_pair.answer, 
                self.processor['ml_model'], self.processor['encoder']
            )
            
            # LLM 평가 수행
            llm_result = evaluate_single_qa_with_intent_extraction(
                qa_pair.question, qa_pair.answer, company_info, 
                position_info, posting_info, resume_info
            )
            
            result = {
                "question": qa_pair.question,
                "answer": qa_pair.answer,
                "intent": llm_result["extracted_intent"],
                "ml_score": ml_score,
                "llm_evaluation": llm_result["evaluation"]
            }
            
            return {
                "question_index": question_index,
                "question": qa_pair.question,
                "answer": qa_pair.answer,
                "ml_score": result.get("ml_score"),  # None일 수 있음, 하지만 이후 검증에서 처리
                "llm_evaluation": result.get("llm_evaluation", ""),
                "intent": result.get("intent", ""),
                "question_level": qa_pair.question_level if qa_pair.question_level else "unknown",
                "duration": qa_pair.duration,
                "who": who  # 사용자/AI 구분값 추가
            }
        except Exception as e:
            print(f"ERROR: Q{question_index} 평가 실패: {str(e)}")
            return {
                "question_index": question_index,
                "question": qa_pair.question,
                "answer": qa_pair.answer,
                "ml_score": 0.0,
                "llm_evaluation": f"평가 중 오류 발생: {str(e)}",
                "intent": "",
                "question_level": "unknown",
                "duration": qa_pair.duration,
                "who": who  # 사용자/AI 구분값 추가
            }
    
    def save_individual_questions_to_db(self, interview_id: int, per_question_results: list, who='user'):
        """개별 질문 평가 결과를 history_detail에 저장 (총평 생성 없음)"""
        try:
            if not self.db_manager:
                print("WARNING: DB 매니저가 없어서 개별 질문 저장을 건너뜁니다.")
                return
            
            print(f"개별 질문 평가 결과를 DB에 저장 중... ({who} 데이터)")
            for i, question_result in enumerate(per_question_results, 1):
                try:
                    qa_data = {
                        "question_index": i,
                        "question_id": i,
                        "question": question_result.get("question", ""),
                        "answer": question_result.get("answer", ""),
                        "intent": question_result.get("intent", ""),
                        "question_level": question_result.get("question_level", "unknown"),
                        "who": question_result.get("who", who),
                        "sequence": i,
                        "duration": question_result.get("duration")
                    }
                    
                    # 개별 질문 피드백 구성 (여기서는 임시 저장용이므로 기본값 허용)
                    final_feedback = {
                        "final_score": 0,  # 임시값, 실제로는 final_eval에서 덮어씀
                        "evaluation": question_result.get("llm_evaluation", ""),
                        "improvement": "개별 개선사항"
                    }
                    
                    detail_id = self.db_manager.save_qa_detail(
                        interview_id, qa_data, json.dumps(final_feedback, ensure_ascii=False)
                    )
                    
                    if detail_id:
                        print(f"SUCCESS: Q{i} 저장 완료 (ID: {detail_id}, who: {who})")
                    else:
                        print(f"WARNING: Q{i} 저장 실패 ({who})")
                        
                except Exception as detail_error:
                    print(f"ERROR: Q{i} 저장 중 오류 ({who}): {str(detail_error)}")
                    
        except Exception as e:
            print(f"ERROR: 개별 질문 저장 실패 ({who}): {str(e)}")

    def evaluate_combined_interview(self, user_id: int, user_qas: list, ai_qas: list,
                                  ai_resume_id=None, user_resume_id=None, posting_id=None, 
                                  company_id=None, position_id=None, existing_interview_id=None):
        """통합 면접 평가: 사용자와 AI 지원자 답변을 하나의 면접 레코드에 저장"""
        try:
            print(f"🔄 통합 면접 평가 시작: user_qas={len(user_qas)}개, ai_qas={len(ai_qas)}개")
            
            # 1. 면접 세션 생성 또는 기존 세션 사용
            if existing_interview_id:
                interview_id = existing_interview_id
                print(f"기존 interview_id 재사용: {interview_id}")
            else:
                interview_id = self._create_interview_session(
                    user_id=user_id, ai_resume_id=ai_resume_id, user_resume_id=user_resume_id,
                    posting_id=posting_id, company_id=company_id, position_id=position_id
                )
            
            if not interview_id:
                return {"success": False, "message": "면접 세션 생성 실패", "interview_id": None}
            
            # 2. 컨텍스트 정보 수집
            company_info = self.db_manager.get_company_info(company_id) if company_id else {}
            position_info = self.db_manager.get_position_info(position_id) if position_id else {}
            posting_info = self.db_manager.get_posting_info(posting_id) if posting_id else {}
            user_resume_info = self.db_manager.get_user_resume_info(user_resume_id) if user_resume_id else {}
            ai_resume_info = self.db_manager.get_ai_resume_info(ai_resume_id) if ai_resume_id else {}
            
            # 3. 사용자 답변 평가
            user_results = []
            for idx, qa in enumerate(user_qas):
                result = self._evaluate_single_question(
                    qa, company_info, idx+1, position_info, posting_info, user_resume_info, who='user'
                )
                user_results.append(result)
            
            # 4. AI 답변 평가  
            ai_results = []
            for idx, qa in enumerate(ai_qas):
                result = self._evaluate_single_question(
                    qa, company_info, idx+1, position_info, posting_info, ai_resume_info, who='ai_interviewer'
                )
                ai_results.append(result)
            
            # 5. 사용자 상세 평가 실행 (기존 상세 형식 유지)
            user_detailed_eval = None
            if user_results:
                print("🔄 사용자 상세 평가 실행...")
                user_detailed_eval = self.run_final_evaluation_from_memory(
                    interview_id, user_results, company_info, position_info, posting_info, user_resume_info, 'user', save_to_db=False
                )
            
            # 6. AI 지원자 상세 평가 실행 (기존 상세 형식 유지)
            ai_detailed_eval = None  
            if ai_results:
                print("🔄 AI 지원자 상세 평가 실행...")
                ai_detailed_eval = self.run_final_evaluation_from_memory(
                    interview_id, ai_results, company_info, position_info, posting_info, ai_resume_info, 'ai_interviewer', save_to_db=False
                )
            
            # 7. 통합 상세 피드백 구조 생성 (기존 형식 유지하면서 user/ai로 분리)
            combined_feedback = {}
            
            if user_detailed_eval and user_detailed_eval.get('success'):
                user_score = user_detailed_eval.get('overall_score')
                if user_score is None:
                    raise ValueError("사용자 평가에서 overall_score가 누락되었습니다.")
                combined_feedback["user"] = {
                    "overall_score": int(user_score),
                    "overall_feedback": user_detailed_eval.get('overall_feedback'),
                    "summary": user_detailed_eval.get('summary')
                }
            
            if ai_detailed_eval and ai_detailed_eval.get('success'):
                ai_score = ai_detailed_eval.get('overall_score')
                if ai_score is None:
                    raise ValueError("AI 지원자 평가에서 overall_score가 누락되었습니다.")
                combined_feedback["ai_interviewer"] = {
                    "overall_score": int(ai_score),
                    "overall_feedback": ai_detailed_eval.get('overall_feedback'), 
                    "summary": ai_detailed_eval.get('summary')
                }
            
            # 8. 개별 질문들을 history_detail에 저장 (상세 평가 결과 포함)
            if user_detailed_eval and user_detailed_eval.get('success'):
                per_question_data = user_detailed_eval.get("per_question", [])
                for i, question_eval in enumerate(per_question_data, 1):
                    try:
                        original_data = user_results[i-1]
                        qa_data = {
                            "question_index": i,
                            "question_id": i,
                            "question": question_eval.get("question", ""),
                            "answer": question_eval.get("answer", ""),
                            "intent": question_eval.get("intent", ""),
                            "question_level": original_data.get("question_level", "unknown"),
                            "who": "user",
                            "sequence": i,
                            "duration": original_data.get("duration")
                        }
                        question_score = question_eval.get("final_score")
                        if question_score is None:
                            raise ValueError(f"사용자 Q{i} 평가에서 final_score가 누락되었습니다.")
                        final_feedback = {
                            "final_score": int(question_score),
                            "evaluation": question_eval.get("evaluation", ""),
                            "improvement": question_eval.get("improvement", "")
                        }
                        self.db_manager.save_qa_detail(interview_id, qa_data, json.dumps(final_feedback, ensure_ascii=False))
                        print(f"✅ 사용자 Q{i} 상세 평가 저장 완료")
                    except Exception as e:
                        print(f"WARNING: 사용자 Q{i} 저장 실패: {str(e)}")
                        
            if ai_detailed_eval and ai_detailed_eval.get('success'):
                per_question_data = ai_detailed_eval.get("per_question", [])
                for i, question_eval in enumerate(per_question_data, 1):
                    try:
                        original_data = ai_results[i-1]
                        qa_data = {
                            "question_index": i,
                            "question_id": i,
                            "question": question_eval.get("question", ""),
                            "answer": question_eval.get("answer", ""),
                            "intent": question_eval.get("intent", ""),
                            "question_level": original_data.get("question_level", "unknown"),
                            "who": "ai_interviewer",
                            "sequence": i,
                            "duration": original_data.get("duration")
                        }
                        question_score = question_eval.get("final_score")
                        if question_score is None:
                            raise ValueError(f"AI 지원자 Q{i} 평가에서 final_score가 누락되었습니다.")
                        final_feedback = {
                            "final_score": int(question_score),
                            "evaluation": question_eval.get("evaluation", ""),
                            "improvement": question_eval.get("improvement", "")
                        }
                        self.db_manager.save_qa_detail(interview_id, qa_data, json.dumps(final_feedback, ensure_ascii=False))
                        print(f"✅ AI 지원자 Q{i} 상세 평가 저장 완료")
                    except Exception as e:
                        print(f"WARNING: AI 지원자 Q{i} 저장 실패: {str(e)}")
            
            # 9. 통합 피드백을 interview 테이블에 저장
            if combined_feedback:
                self.db_manager.update_interview_feedback(interview_id, json.dumps(combined_feedback, ensure_ascii=False))
                print("✅ 통합 상세 피드백 저장 완료")
            
            # 10. 통합 개선 계획 생성 및 저장
            combined_plans = {}
            
            # 사용자 계획 생성 (기존 방식 활용)
            if user_detailed_eval and user_detailed_eval.get('success'):
                try:
                    # 임시로 사용자 피드백만으로 계획 생성
                    user_feedback_only = {
                        "overall_score": user_detailed_eval.get('overall_score'),
                        "overall_feedback": user_detailed_eval.get('overall_feedback'),
                        "summary": user_detailed_eval.get('summary')
                    }
                    # 임시 interview 레코드로 계획 생성 로직 호출
                    from .plan_eval import generate_interview_plan
                    user_plan_result = generate_interview_plan(user_feedback_only)
                    if user_plan_result.get("success"):
                        combined_plans["user"] = {
                            "shortly_plan": user_plan_result.get("shortly_plan"),
                            "long_plan": user_plan_result.get("long_plan")
                        }
                    else:
                        combined_plans["user"] = {
                            "답변_스킬_개선": ["구체적인 예시와 STAR 기법을 활용한 답변 연습"],
                            "의사소통_능력_향상": ["면접 상황에서의 명확한 의사전달 연습"],
                            "기술_지식_보강": ["관련 분야 최신 기술 트렌드 학습"],
                            "면접_태도_개선": ["자신감 있는 태도와 적극적인 면접 참여"]
                        }
                except Exception as e:
                    print(f"WARNING: 사용자 계획 생성 실패: {str(e)}")
                    combined_plans["user"] = {
                        "답변_스킬_개선": ["구체적인 예시와 STAR 기법을 활용한 답변 연습"],
                        "의사소통_능력_향상": ["면접 상황에서의 명확한 의사전달 연습"],
                        "기술_지식_보강": ["관련 분야 최신 기술 트렌드 학습"],
                        "면접_태도_개선": ["자신감 있는 태도와 적극적인 면접 참여"]
                    }
            
            # AI 지원자 계획 생성 (기존 방식 활용)
            if ai_detailed_eval and ai_detailed_eval.get('success'):
                try:
                    ai_feedback_only = {
                        "overall_score": ai_detailed_eval.get('overall_score'),
                        "overall_feedback": ai_detailed_eval.get('overall_feedback'),
                        "summary": ai_detailed_eval.get('summary')
                    }
                    from .plan_eval import generate_interview_plan
                    ai_plan_result = generate_interview_plan(ai_feedback_only)
                    if ai_plan_result.get("success"):
                        combined_plans["ai_interviewer"] = {
                            "shortly_plan": ai_plan_result.get("shortly_plan"),
                            "long_plan": ai_plan_result.get("long_plan")
                        }
                    else:
                        combined_plans["ai_interviewer"] = {
                            "답변_스킬_개선": ["더 구체적인 기술적 경험과 프로젝트 사례 준비"],
                            "의사소통_능력_향상": ["기술적 내용을 비전문가도 이해할 수 있게 설명하는 연습"],
                            "기술_지식_보강": ["해당 회사 기술 스택과 관련된 심화 학습"],
                            "면접_태도_개선": ["AI 지원자로서 차별화된 강점 어필 방법 연구"]
                        }
                except Exception as e:
                    print(f"WARNING: AI 계획 생성 실패: {str(e)}")
                    combined_plans["ai_interviewer"] = {
                        "답변_스킬_개선": ["더 구체적인 기술적 경험과 프로젝트 사례 준비"],
                        "의사소통_능력_향상": ["기술적 내용을 비전문가도 이해할 수 있게 설명하는 연습"],
                        "기술_지식_보강": ["해당 회사 기술 스택과 관련된 심화 학습"],
                        "면접_태도_개선": ["AI 지원자로서 차별화된 강점 어필 방법 연구"]
                    }
            
            # plans 테이블에 통합 계획 저장
            if combined_plans:
                self.db_manager.save_improvement_plans(interview_id, json.dumps(combined_plans, ensure_ascii=False))
                print("✅ 통합 개선 계획 저장 완료")
            
            return {
                "success": True,
                "message": "통합 면접 평가 완료",
                "interview_id": interview_id,
                "total_questions": len(user_results) + len(ai_results),
                "user_score": combined_feedback.get("user", {}).get("overall_score"),  # 위에서 이미 검증됨
                "ai_score": combined_feedback.get("ai_interviewer", {}).get("overall_score")  # 위에서 이미 검증됨
            }
            
        except Exception as e:
            print(f"❌ 통합 면접 평가 실패: {str(e)}")
            return {"success": False, "message": f"평가 실패: {str(e)}", "interview_id": None}

    def evaluate_multiple_questions(self, user_id: int, qa_pairs: list, 
                                   ai_resume_id: Optional[int] = None, user_resume_id: Optional[int] = None,
                                   posting_id: Optional[int] = None, company_id: Optional[int] = None,
                                   position_id: Optional[int] = None, who: str = 'user',
                                   existing_interview_id: Optional[int] = None) -> dict:
        """
        여러 질문-답변 일괄 평가 후 자동으로 최종 평가 수행
        
        Args:
            user_id: 사용자 ID
            qa_pairs: 질문-답변 쌍 리스트
            기타 외래키 ID들
            
        Returns:
            dict: 전체 평가 결과 (개별 평가 + 최종 평가 + 계획)
        """
        try:
            if not self.processor:
                return {
                    "success": False,
                    "message": "ML 모델이 로드되지 않았습니다.",
                    "interview_id": None,
                    "total_questions": 0
                }
            
            # 1. 면접 세션 처리 (기존 ID 재사용 또는 새로 생성)
            if existing_interview_id:
                interview_id = existing_interview_id
                print(f"기존 interview_id 재사용: {interview_id}")
            else:
                # 새 면접 세션 생성
                interview_id = self._create_interview_session(
                    user_id=user_id,
                    ai_resume_id=ai_resume_id,
                    user_resume_id=user_resume_id,
                    posting_id=posting_id,
                    company_id=company_id,
                    position_id=position_id
                )
                
                if not interview_id:
                    print("WARNING: 면접 세션 생성 실패, 필수 필드만으로 재시도")
                    try:
                        interview_id = self._create_interview_session(user_id=user_id)
                        print(f"재시도 결과: interview_id = {interview_id}")
                    except Exception as e:
                        print(f"재시도 중 오류: {str(e)}")
            
            if not interview_id:
                error_msg = f"면접 세션 생성 실패 - user_id: {user_id}"
                print(f"CRITICAL ERROR: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "interview_id": None,
                    "total_questions": 0
                }
            
            # 2. 추가 정보 조회 (회사, 직군, 공고, 이력서)
            # 모든 정보 조회는 필수이며, 하나라도 실패하면 오류를 발생시킵니다.
            if not self.db_manager:
                raise RuntimeError("데이터베이스 연결이 설정되지 않았습니다.")

            # 회사 정보 조회 (필수)
            if not company_id:
                raise ValueError("company_id는 필수 파라미터입니다.")
            company_info = self.db_manager.get_company_info(company_id)
            if not company_info:
                raise ValueError(f"Company ID {company_id}에 해당하는 회사 정보를 찾을 수 없습니다.")
            print(f"SUCCESS: Company 정보 조회 완료 - {company_info.get('name')}")

            # 직군 정보 조회 (선택적이지만 없으면 경고)
            position_info = None
            if position_id:
                position_info = self.db_manager.get_position_info(position_id)
                if position_info:
                    print(f"SUCCESS: Position 정보 조회 완료 - {position_info.get('position_name')}")
                else:
                    print(f"WARNING: Position ID {position_id} 정보를 찾을 수 없습니다. 일반 평가로 진행됩니다.")

            # 공고 정보 조회 (선택적이지만 없으면 경고)
            posting_info = None
            if posting_id:
                posting_info = self.db_manager.get_posting_info(posting_id)
                if posting_info:
                    print(f"SUCCESS: Posting 정보 조회 완료")
                else:
                    print(f"WARNING: Posting ID {posting_id} 정보를 찾을 수 없습니다. 일반 평가로 진행됩니다.")

            # 이력서 정보 조회 (선택적이지만 없으면 경고)
            resume_info = None
            if ai_resume_id:
                resume_info = self.db_manager.get_ai_resume_info(ai_resume_id)
                if resume_info:
                    print(f"SUCCESS: AI Resume 정보 조회 완료")
                else:
                    print(f"WARNING: AI Resume ID {ai_resume_id} 정보를 찾을 수 없습니다. 일반 평가로 진행됩니다.")
            elif user_resume_id:
                resume_info = self.db_manager.get_user_resume_info(user_resume_id)
                if resume_info:
                    print(f"SUCCESS: User Resume 정보 조회 완료")
                else:
                    print(f"WARNING: User Resume ID {user_resume_id} 정보를 찾을 수 없습니다. 일반 평가로 진행됩니다.")
            
            # 3. 모든 필수 정보 조회 완료. 평가를 시작합니다.
            
            # 4. 각 질문-답변 쌍을 순차적으로 평가 (모델 재사용으로 빠른 처리)
            print(f"총 {len(qa_pairs)}개 질문 순차 평가 시작 (모델 재사용)...")
            
            per_question_results = []
            for i, qa_pair in enumerate(qa_pairs, 1):
                result = self._evaluate_single_question(qa_pair, company_info, i, position_info, posting_info, resume_info, who)
                per_question_results.append(result)
            
            print(f"SUCCESS: {len(per_question_results)}개 질문 평가 완료")
            
            # 5. 메모리 데이터 기반 최종 평가 수행 (사용자 평가일 때만)
            final_result = None
            if who == 'user':
                print(f"\n--- 사용자 최종 평가 시작 ---")
                final_result = self.run_final_evaluation_from_memory(interview_id, per_question_results, company_info, position_info, posting_info, resume_info, who)
            else:
                print(f"\n--- AI 평가: 개별 질문만 저장 (최종 총평 생성 생략) ---")
                # AI 평가는 개별 질문만 저장
                self.save_individual_questions_to_db(interview_id, per_question_results, who)
            
            # 최종 평가 결과를 API 응답 형식에 맞게 재구성
            if final_result and final_result.get("success", False):
                # 사용자 평가 성공 시
                response = {
                    "success": True,
                    "interview_id": interview_id,
                    "message": final_result.get("message", f"전체 면접 평가 완료 ({len(qa_pairs)}개 질문)"),
                    "total_questions": len(qa_pairs),
                    "overall_score": final_result.get("overall_score"),  # final_result에서 이미 검증됨
                    "overall_feedback": final_result.get("overall_feedback"),
                    "per_question_results": final_result.get("per_question", []),
                    "interview_plan": None
                }
            else:
                # AI 평가이거나 사용자 평가 실패 시 - 개별 평가 결과만 반환
                response = {
                    "success": True,
                    "interview_id": interview_id,
                    "message": f"개별 {len(qa_pairs)}개 질문 평가 완료 ({who} 평가)",
                    "total_questions": len(qa_pairs),
                    "overall_score": None,
                    "overall_feedback": None,
                    "per_question_results": [
                        {
                            "question": result["question"],
                            "answer": result["answer"],
                            "intent": result["intent"],
                            "final_score": 0,  # 임시값, 실제 평가는 별도로 수행됨
                            "evaluation": result["llm_evaluation"],
                            "improvement": "개별 개선사항 없음"
                        }
                        for result in per_question_results
                    ],
                    "interview_plan": None
                }
            
            return response
            
        except ValueError as e:
            # 잘못된 파라미터나 데이터 문제
            print(f"PARAMETER ERROR: {str(e)}")
            return {
                "success": False,
                "message": f"파라미터 오류: {str(e)}",
                "interview_id": None,
                "total_questions": 0
            }
        except RuntimeError as e:
            # 시스템 리소스 문제
            print(f"SYSTEM ERROR: {str(e)}")
            return {
                "success": False,
                "message": f"시스템 오류: {str(e)}",
                "interview_id": None,
                "total_questions": 0
            }
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"UNEXPECTED ERROR: {error_details}")
            return {
                "success": False,
                "message": f"예상치 못한 오류 발생: {str(e)}",
                "interview_id": None,
                "total_questions": 0
            }
    

    def run_final_evaluation_from_memory(self, interview_id: int, per_question_results: list, company_info: dict, position_info=None, posting_info=None, resume_info=None, who='user', save_to_db=True) -> dict:
        """
        메모리 데이터를 기반으로 최종 평가 실행 후 DB에 저장
        
        Args:
            interview_id: 면접 세션 ID
            per_question_results: 개별 질문 평가 결과 리스트
            company_info: 회사 정보
            position_info: 직군 정보
            posting_info: 공고 정보
            resume_info: 이력서 정보
            
        Returns:
            dict: 최종 평가 결과
        """
        try:
            if not self.db_manager:
                return {
                    "success": False,
                    "message": "데이터베이스 연결이 없습니다.",
                    "overall_score": None,
                    "overall_feedback": None
                }
            
            # 1. realtime_data 형태로 변환
            realtime_data = []
            for item in per_question_results:
                realtime_data.append({
                    "question": item["question"],
                    "answer": item["answer"],
                    "intent": item["intent"],
                    "ml_score": item["ml_score"],
                    "llm_evaluation": item["llm_evaluation"]
                })
            
            # 2. 최종 평가 로직 실행 (메모리에서 처리)
            print("DEBUG: Calling final_eval.run_final_evaluation_from_realtime...")
            try:
                final_results = run_final_evaluation_from_realtime(
                    realtime_data=realtime_data, 
                    company_info=company_info,
                    position_info=position_info,
                    posting_info=posting_info,
                    resume_info=resume_info,
                    output_file=None  # 파일 저장 하지 않음
                )
            except Exception as e:
                import traceback
                print(f"CRITICAL_ERROR: Failed to run or import from final_eval.py: {traceback.format_exc()}")
                final_results = {"success": False, "message": str(e), "per_question": [], "overall_score": None, "overall_feedback": None}
            
            if not final_results:
                return {
                    "success": False,
                    "message": "최종 평가 실행 실패",
                    "overall_score": None,
                    "overall_feedback": None
                }
            
            # 3. 각 질문별 최종 평가 결과를 history_detail에 저장 (옵션)
            per_question_data = final_results.get("per_question", [])
            if per_question_data and save_to_db:
                print("개별 질문 최종 평가 결과를 DB에 저장 중...")
                for i, question_eval in enumerate(per_question_data, 1):
                    try:
                        # 원본 데이터에서 추가 정보 가져오기
                        original_data = per_question_results[i-1]
                        
                        qa_data = {
                            "question_index": i,
                            "question_id": i,
                            "question": question_eval.get("question", ""),
                            "answer": question_eval.get("answer", ""),
                            "intent": question_eval.get("intent", ""),
                            "question_level": original_data.get("question_level", "unknown"),
                            "who": original_data.get("who", who),  # 전달받은 who 값 사용
                            "sequence": i,
                            "duration": original_data.get("duration")
                        }
                        
                        # 최종 정제된 피드백 저장 (final_eval.py에서 계산된 정수 점수 사용)
                        question_score = question_eval.get("final_score")
                        if question_score is None:
                            raise ValueError(f"Q{i} 최종 평가에서 final_score가 누락되었습니다.")
                        final_feedback = {
                            "final_score": int(question_score),
                            "evaluation": question_eval.get("evaluation", ""),
                            "improvement": question_eval.get("improvement", "")
                        }
                        
                        detail_id = self.db_manager.save_qa_detail(
                            interview_id, 
                            qa_data, 
                            json.dumps(final_feedback, ensure_ascii=False)
                        )
                        print(f"SUCCESS: Q{i} 최종 평가 DB 저장 완료 (Detail ID: {detail_id})")
                        
                    except Exception as e:
                        print(f"WARNING: Q{i} 최종 평가 저장 실패: {str(e)}")
            
            # 4. 전체 평가 결과를 interview 테이블에 저장 (통합 평가에서는 건너뜀)
            if save_to_db:
                try:
                    overall_data = {
                        "overall_score": final_results.get("overall_score"),
                        "overall_feedback": final_results.get("overall_feedback"),
                        "summary": final_results.get("summary")
                    }
                    self.db_manager.update_total_feedback(interview_id, overall_data)
                    print("SUCCESS: 전체 평가 결과 DB 저장 완료")
                    
                except Exception as e:
                    print(f"WARNING: 전체 평가 결과 저장 실패: {str(e)}")
            
            final_score = final_results.get("overall_score")
            if final_score is None:
                raise ValueError("최종 평가에서 overall_score가 누락되었습니다.")
                
            return {
                "success": True,
                "overall_score": int(final_score),
                "overall_feedback": final_results.get("overall_feedback"),
                "summary": final_results.get("summary"),
                "per_question": final_results.get("per_question"),
                "message": "최종 평가 완료",
                "interview_id": interview_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"최종 평가 중 오류 발생: {str(e)}",
                "overall_score": None,
                "overall_feedback": None
            }

    def generate_interview_plans(self, interview_id: int) -> dict:
        """
        면접 준비 계획 생성 (DB 기반)
        
        Args:
            interview_id: 면접 세션 ID
            
        Returns:
            dict: 면접 준비 계획 결과
        """
        try:
            if not self.db_manager:
                return {
                    "success": False,
                    "message": "데이터베이스 연결이 없습니다.",
                    "interview_plan": None,
                    "plan_id": None,
                    "interview_id": interview_id
                }
            
            # 1. 면접 데이터 조회 (총평 포함)
            interview_details = self.db_manager.get_interview_details(interview_id)
            
            if not interview_details or not interview_details['interview']:
                return {
                    "success": False,
                    "message": "면접 데이터를 찾을 수 없습니다.",
                    "interview_plan": None,
                    "plan_id": None,
                    "interview_id": interview_id
                }
            
            # 2. total_feedback에서 전체 평가 결과 추출 및 유효성 검사
            total_feedback = interview_details['interview'].get('total_feedback')
            if not total_feedback:
                return {
                    "success": False,
                    "message": f"Interview ID {interview_id}에 대한 최종 평가 결과(total_feedback)가 없습니다.",
                    "interview_plan": None,
                    "plan_id": None,
                    "interview_id": interview_id
                }
            
            if isinstance(total_feedback, str):
                try:
                    total_feedback = json.loads(total_feedback)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "message": "total_feedback 필드의 JSON 형식이 잘못되었습니다.",
                        "interview_plan": None,
                        "plan_id": None,
                        "interview_id": interview_id
                    }
            
            # 3. 면접 준비 계획 생성
            from .plan_eval import generate_interview_plan
            plan_data = generate_interview_plan(total_feedback)
            
            if not plan_data["success"]:
                return {
                    "success": False,
                    "message": f"면접 계획 생성 실패: {plan_data.get('error', 'Unknown error')}",
                    "interview_plan": None,
                    "plan_id": None,
                    "interview_id": interview_id
                }
            
            # 4. plans 테이블에 저장
            plan_id = self.db_manager.save_interview_plan(
                interview_id=interview_id,
                shortly_plan=plan_data["shortly_plan"],
                long_plan=plan_data["long_plan"]
            )
            
            plan_result = {
                "shortly_plan": plan_data["shortly_plan"],
                "long_plan": plan_data["long_plan"],
                "plan_id": plan_id
            }
            
            return {
                "success": True,
                "interview_plan": plan_result,
                "plan_id": plan_id,
                "message": "면접 준비 계획 생성 완료",
                "interview_id": interview_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"면접 계획 생성 중 오류 발생: {str(e)}",
                "interview_plan": None,
                "plan_id": None,
                "interview_id": interview_id
            }

