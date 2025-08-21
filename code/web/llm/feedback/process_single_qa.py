"""
실시간 면접 평가 시스템 - 개별 질문 처리 모듈

이 모듈은 면접 질문이 하나씩 들어올 때마다 num_eval.py와 text_eval.py만을 사용하여
개별 평가를 수행하고, 조건 달성시 최종 평가 트리거 신호를 보냅니다.

주요 기능:
1. 개별 질문-답변 쌍에 대해 ML 점수와 LLM 평가 수행
2. 결과를 realtime_result.json에 누적 저장
3. 12개 질문 완료 또는 클로징 질문 감지시 최종 평가 신호 반환

작성자: AI Assistant
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", module="sklearn")

import json
import os
from .num_eval import evaluate_single_qa as num_evaluate_single_qa
from .text_eval import evaluate_single_qa as text_evaluate_single_qa, evaluate_single_qa_with_intent_extraction

class SingleQAProcessor:
    def __init__(self, company_info=None):
        """
        SingleQAProcessor 초기화 (파일 저장 없이 메모리에서만 처리)
        
        Args:
            company_info (dict): 회사 정보 (DB에서 조회된 데이터)
        """
        # ML 모델과 임베딩 모델을 한 번만 로드하여 성능 최적화
        from .num_eval import load_model, load_encoder, MODEL_PATH, ENCODER_NAME
        print("ML 모델과 임베딩 모델을 로드 중...")
        try:
            self.ml_model = load_model(MODEL_PATH)
            self.encoder = load_encoder(ENCODER_NAME)
            print("모델 로드 완료!")
        except Exception as e:
            print(f"ERROR: 모델 로드 실패 - {type(e).__name__}: {str(e)}")
            self.ml_model = None
            self.encoder = None
        
        # 회사 정보 설정 (필수)
        if not company_info:
            raise ValueError("SingleQAProcessor를 초기화하려면 company_info가 반드시 필요합니다.")
        self.company_info = company_info
        print(f"회사 정보로 프로세서 초기화 완료: {company_info.get('name', 'Unknown')}")
    
    def process_qa_with_intent_extraction(self, question: str, answer: str, company_info: dict = None, position_info=None, posting_info=None, resume_info=None):
        """
        질문 의도 자동 추출 + 단일 질문-답변 쌍을 처리하는 함수 (파일 저장 없음)
        
        Args:
            question (str): 면접 질문
            answer (str): 지원자 답변
            company_info (dict): 회사 정보 (동적으로 전달)
            position_info (dict): 직군 정보
            posting_info (dict): 공고 정보
            resume_info (dict): 이력서 정보
            
        Returns:
            dict: 평가결과딕셔너리 (ML점수 + LLM평가 + 의도)
        """
        print(f"질문 평가 중: {question[:50]}...")
        
        # 회사 정보가 전달되면 사용, 없으면 기존 self.company_info 사용
        eval_company_info = company_info if company_info else self.company_info
        
        # 1. 머신러닝 점수 계산 (이미 로드된 모델 사용)
        ml_score = num_evaluate_single_qa(question, answer, self.ml_model, self.encoder)
        
        # 2. LLM 평가 수행 (질문 의도 자동 추출 포함, 추가 정보 전달)
        llm_result = evaluate_single_qa_with_intent_extraction(question, answer, eval_company_info, position_info, posting_info, resume_info)
        
        # 3. 결과 구성 (메모리에서만 처리)
        result = {
            "question": question,
            "answer": answer,
            "intent": llm_result["extracted_intent"],  # 자동 추출된 의도
            "ml_score": ml_score,
            "llm_evaluation": llm_result["evaluation"]
        }
        
        print(f"평가 완료! ML 점수: {ml_score:.2f}")
        print(f"추출된 의도: {llm_result['extracted_intent'][:100]}...")
        
        return result

def process_single_question_with_intent_extraction(question: str, answer: str, company_info=None):
    """
    외부에서 호출하는 단일 질문 처리 함수 (질문 의도 자동 추출 버전)
    
    이 함수는 API에서 호출되며, 회사 정보에 따라 processor를 생성합니다.
    
    Args:
        question (str): 면접 질문
        answer (str): 지원자 답변
        company_info (dict): 회사 정보 (DB에서 조회된 데이터)
        
    Returns:
        tuple: (False, result_dict) - 최종평가는 별도 로직에서 처리
    """
    # 회사 정보는 필수
    if not company_info:
        raise ValueError("company_info는 필수 파라미터입니다. API 호출 시 반드시 전달해야 합니다.")
    
    # 회사 정보로 processor 생성
    processor = SingleQAProcessor(company_info)
    
    # 실제 처리는 processor 인스턴스에 위임 (의도 자동 추출)
    result = processor.process_qa_with_intent_extraction(question, answer)
    
    # 더 이상 최종 평가 트리거를 체크하지 않음 (새로운 구조에서는 API에서 직접 처리)
    return False, result

# 모듈 파일 - API를 통해 SingleQAProcessor 클래스를 사용하세요