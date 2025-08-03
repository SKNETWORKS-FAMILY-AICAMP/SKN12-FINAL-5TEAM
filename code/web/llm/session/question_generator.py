#!/usr/bin/env python3
"""
🚫 DEPRECATED - 더 이상 사용하지 않음

이 모듈의 모든 기능은 backend/services/interview_service.py로 이관되었습니다.
새로운 Backend 중앙 관제 시스템의 QuestionGenerator를 사용하세요.

기존 설명: AI 경쟁 면접용 질문 생성 서비스
Supabase fix_question 테이블의 고정 질문 + LLM 동적 질문 조합
"""

# 🗑️ 모든 import 주석 처리 - 더 이상 사용하지 않음
# import sys
# import os
# from typing import Dict, List, Any, Optional
# from dataclasses import dataclass
# import random

# # 프로젝트 루트 경로 추가
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# from backend.services.existing_tables_service import existing_tables_service
# from ..shared.models import QuestionType
# from ..shared.logging_config import interview_logger

# ⚠️ DEPRECATED: 이 모듈을 사용하려고 하면 경고가 발생합니다.
raise DeprecationWarning(
    "🚫 llm.session.question_generator 는 더 이상 사용되지 않습니다. "
    "backend.services.interview_service.QuestionGenerator 를 사용하세요."
)

# 🗑️ 기존 코드 모두 주석 처리


# @dataclass
# class QuestionPlan:
#     """질문 계획 데이터 클래스"""
#     question_id: str
#     question_type: str
#     question_content: str
#     question_intent: str
#     question_level: str = "중간"
#     is_fixed: bool = False
#     source: str = "llm"  # "fixed" or "llm"


# class QuestionGeneratorService:
#     """
#     AI 경쟁 면접용 질문 생성 서비스
#     고정 질문(Supabase) + 동적 질문(LLM) 조합
#     """
    
#     def __init__(self):
#         self.db_service = existing_tables_service
#         self.total_questions = 20
        
#         # 질문 구성 계획
#         self.question_structure = {
#             "fixed": 8,      # 고정 질문 8개
#             "dynamic": 12    # 동적 질문 12개
#         }
        
#         # 동적 질문 타입별 배분
#         self.dynamic_distribution = {
#             QuestionType.HR: 4,           # HR 질문 4개
#             QuestionType.TECH: 6,         # 기술 질문 6개
#             QuestionType.COLLABORATION: 2  # 협업 질문 2개
#         }
    
#     async def generate_question_plan(self, company_id: str, position: str, difficulty: str = "중간") -> List[QuestionPlan]:
#         """
#         AI 경쟁 면접용 20개 질문 계획 생성
#         고정 질문 8개 + 동적 질문 12개
#         """
#         try:
#             interview_logger.info(f"🎯 질문 계획 생성 시작: {company_id} - {position} - {difficulty}")
            
#             question_plan = []
            
#             # 1. 고정 질문 8개 선별
#             fixed_questions = await self._get_selected_fixed_questions(company_id, position, difficulty)
#             question_plan.extend(fixed_questions)
            
#             # 2. 동적 질문 12개 계획 생성
#             dynamic_questions = self._generate_dynamic_question_plans(company_id, position)
#             question_plan.extend(dynamic_questions)
            
#             # 3. 질문 순서 최적화 (고정 질문을 앞쪽에 배치)
#             optimized_plan = self._optimize_question_order(question_plan)
            
#             interview_logger.info(f"✅ 질문 계획 생성 완료: 총 {len(optimized_plan)}개 질문")
#             interview_logger.info(f"📊 구성: 고정 {len(fixed_questions)}개, 동적 {len(dynamic_questions)}개")
            
#             return optimized_plan
            
#         except Exception as e:
#             interview_logger.error(f"❌ 질문 계획 생성 실패: {str(e)}")
#             # 폴백: 기본 질문 계획 반환
#             return self._get_fallback_question_plan(company_id, position)
    
#     async def _get_selected_fixed_questions(self, company_id: str, position: str, difficulty: str) -> List[QuestionPlan]:
#         """Supabase에서 고정 질문 8개 선별"""
#         try:
#             # 모든 고정 질문 조회
#             all_fixed_questions = await self.db_service.get_fixed_questions()
            
#             if not all_fixed_questions:
#                 interview_logger.warning("🚫 고정 질문이 없습니다. 기본 질문 사용")
#                 return self._get_default_fixed_questions()
            
#             # 필수 질문 (자기소개, 지원동기)
#             essential_questions = [q for q in all_fixed_questions 
#                                  if q.get('question_content', '').find('자기소개') != -1 or 
#                                     q.get('question_content', '').find('지원') != -1]
            
#             # 나머지 질문들에서 6개 랜덤 선택
#             other_questions = [q for q in all_fixed_questions if q not in essential_questions]
#             selected_others = random.sample(other_questions, min(6, len(other_questions)))
            
#             # 선택된 고정 질문들을 QuestionPlan으로 변환
#             fixed_plans = []
            
#             # 필수 질문 추가
#             for i, question in enumerate(essential_questions[:2]):  # 최대 2개
#                 plan = QuestionPlan(
#                     question_id=f"fixed_{i+1}",
#                     question_type="INTRO" if i == 0 else "MOTIVATION",
#                     question_content=question.get('question_content', ''),
#                     question_intent=question.get('question_intent', '기본 질문'),
#                     question_level=question.get('question_level', difficulty),
#                     is_fixed=True,
#                     source="fixed"
#                 )
#                 fixed_plans.append(plan)
            
#             # 추가 질문들
#             for i, question in enumerate(selected_others):
#                 plan = QuestionPlan(
#                     question_id=f"fixed_{len(fixed_plans)+1}",
#                     question_type=question.get('question_type', 'HR'),
#                     question_content=question.get('question_content', ''),
#                     question_intent=question.get('question_intent', '일반 질문'),
#                     question_level=question.get('question_level', difficulty),
#                     is_fixed=True,
#                     source="fixed"
#                 )
#                 fixed_plans.append(plan)
            
#             interview_logger.info(f"📋 고정 질문 선별 완료: {len(fixed_plans)}개")
#             return fixed_plans[:8]  # 최대 8개로 제한
            
#         except Exception as e:
#             interview_logger.error(f"❌ 고정 질문 선별 실패: {str(e)}")
#             return self._get_default_fixed_questions()
    
#     def _get_default_fixed_questions(self) -> List[QuestionPlan]:
#         """기본 고정 질문 (DB 조회 실패 시 폴백)"""
#         default_questions = [
#             {
#                 "type": "INTRO",
#                 "content": "간단한 자기소개를 부탁드립니다.",
#                 "intent": "지원자의 기본 배경과 성격 파악"
#             },
#             {
#                 "type": "MOTIVATION", 
#                 "content": "저희 회사에 지원하게 된 동기는 무엇인가요?",
#                 "intent": "회사에 대한 관심도와 지원 의지 평가"
#             },
#             {
#                 "type": "HR",
#                 "content": "본인의 장점과 단점은 무엇인가요?",
#                 "intent": "자기 인식 능력과 성장 의지 확인"
#             },
#             {
#                 "type": "HR",
#                 "content": "지금까지의 경력에 대해 말씀해 주세요.",
#                 "intent": "경력 사항과 성장 과정 파악"
#             },
#             {
#                 "type": "TECH",
#                 "content": "기술적으로 가장 도전적이었던 프로젝트는 무엇인가요?",
#                 "intent": "기술적 역량과 문제 해결 능력 평가"
#             },
#             {
#                 "type": "HR",
#                 "content": "스트레스를 받는 상황에서 어떻게 대처하시나요?",
#                 "intent": "스트레스 관리 능력과 회복탄력성 평가"
#             },
#             {
#                 "type": "COLLABORATION",
#                 "content": "팀 내에서 갈등이 발생했을 때 어떻게 해결하시나요?",
#                 "intent": "갈등 해결 능력과 협업 스킬 평가"
#             },
#             {
#                 "type": "HR",
#                 "content": "5년 후 본인의 모습을 어떻게 그리고 계시나요?",
#                 "intent": "비전과 목표 의식, 성장 계획 확인"
#             }
#         ]
        
#         plans = []
#         for i, q in enumerate(default_questions):
#             plan = QuestionPlan(
#                 question_id=f"default_{i+1}",
#                 question_type=q["type"],
#                 question_content=q["content"],
#                 question_intent=q["intent"],
#                 question_level="중간",
#                 is_fixed=True,
#                 source="default"
#             )
#             plans.append(plan)
        
#         return plans
    
#     def _generate_dynamic_question_plans(self, company_id: str, position: str) -> List[QuestionPlan]:
#         """동적 질문 12개 계획 생성 (실제 LLM 생성은 나중에)"""
#         dynamic_plans = []
#         question_count = 9  # 고정 질문 8개 다음부터
        
#         # HR 질문 4개
#         for i in range(self.dynamic_distribution[QuestionType.HR]):
#             plan = QuestionPlan(
#                 question_id=f"dynamic_hr_{i+1}",
#                 question_type="HR",
#                 question_content="",  # LLM이 나중에 생성
#                 question_intent="HR 역량 평가",
#                 is_fixed=False,
#                 source="llm"
#             )
#             dynamic_plans.append(plan)
        
#         # 기술 질문 6개
#         for i in range(self.dynamic_distribution[QuestionType.TECH]):
#             plan = QuestionPlan(
#                 question_id=f"dynamic_tech_{i+1}",
#                 question_type="TECH",
#                 question_content="",  # LLM이 나중에 생성
#                 question_intent="기술 역량 평가",
#                 is_fixed=False,
#                 source="llm"
#             )
#             dynamic_plans.append(plan)
        
#         # 협업 질문 2개
#         for i in range(self.dynamic_distribution[QuestionType.COLLABORATION]):
#             plan = QuestionPlan(
#                 question_id=f"dynamic_collab_{i+1}",
#                 question_type="COLLABORATION",
#                 question_content="",  # LLM이 나중에 생성
#                 question_intent="협업 역량 평가",
#                 is_fixed=False,
#                 source="llm"
#             )
#             dynamic_plans.append(plan)
        
#         return dynamic_plans
    
#     def _optimize_question_order(self, questions: List[QuestionPlan]) -> List[QuestionPlan]:
#         """질문 순서 최적화 (고정 질문을 앞쪽에, 타입별 적절한 배치)"""
#         fixed_questions = [q for q in questions if q.is_fixed]
#         dynamic_questions = [q for q in questions if not q.is_fixed]
        
#         # 고정 질문 중 필수 질문(자기소개, 지원동기)을 맨 앞에
#         essential = [q for q in fixed_questions if q.question_type in ["INTRO", "MOTIVATION"]]
#         other_fixed = [q for q in fixed_questions if q.question_type not in ["INTRO", "MOTIVATION"]]
        
#         # 최적화된 순서: 필수 → 기타 고정 → 동적 질문
#         optimized_order = essential + other_fixed + dynamic_questions
        
#         # 질문 ID 재할당
#         for i, question in enumerate(optimized_order):
#             question.question_id = f"q_{i+1}"
        
#         return optimized_order
    
#     def _get_fallback_question_plan(self, company_id: str, position: str) -> List[QuestionPlan]:
#         """폴백 질문 계획 (모든 생성이 실패했을 때)"""
#         interview_logger.warning("🚨 폴백 질문 계획 사용")
        
#         fallback_questions = [
#             "간단한 자기소개를 부탁드립니다.",
#             f"{company_id}에 지원하게 된 동기는 무엇인가요?",
#             "본인의 장점과 단점은 무엇인가요?",
#             "지금까지의 경력에 대해 말씀해 주세요.",
#             "가장 자신 있는 기술 스택은 무엇인가요?",
#             "팀 프로젝트에서 어려웠던 경험이 있다면 말씀해 주세요.",
#             "업무에서 우선순위를 어떻게 정하시나요?",
#             "새로운 기술을 학습할 때 어떤 방식을 사용하시나요?",
#             "동료와 의견이 다를 때 어떻게 조율하시나요?",
#             "실패한 프로젝트에서 배운 점이 있다면 말씀해 주세요.",
#             "현재 관심 있는 기술 트렌드는 무엇인가요?",
#             "업무 효율성을 높이기 위해 어떤 노력을 하시나요?",
#             "고객이나 사용자 관점에서 개발할 때 중요하게 생각하는 것은?",
#             "코드 리뷰 시 중점적으로 보는 부분은 무엇인가요?",
#             "프로젝트 일정이 촉박할 때 어떻게 대응하시나요?",
#             "기술 부채 해결에 대한 본인의 생각은?",
#             "개발 문서화의 중요성에 대해 어떻게 생각하시나요?",
#             "신입 개발자에게 조언한다면?",
#             "회사에서 기대하는 개발자상은 무엇이라고 생각하시나요?",
#             "마지막으로 궁금한 점이나 하고 싶은 말씀이 있으시다면?"
#         ]
        
#         plans = []
#         for i, content in enumerate(fallback_questions):
#             question_type = "INTRO" if i == 0 else "MOTIVATION" if i == 1 else "HR" if i < 8 else "TECH" if i < 16 else "COLLABORATION"
#             plan = QuestionPlan(
#                 question_id=f"fallback_{i+1}",
#                 question_type=question_type,
#                 question_content=content,
#                 question_intent="기본 평가",
#                 is_fixed=True,
#                 source="fallback"
#             )
#             plans.append(plan)
        
#         return plans[:20]  # 20개로 제한


# # 싱글톤 인스턴스
# question_generator_service = QuestionGeneratorService()