"""
기존 Supabase 테이블과 현재 시스템 연동
기존 구조를 건드리지 않고 데이터베이스 기능 추가
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.existing_tables_service import existing_tables_service
from backend.schemas.database import CreateUserRequest, CreateInterviewRequest, SaveInterviewDetailRequest, SaveResumeRequest
import logging

logger = logging.getLogger(__name__)

# 라우터 생성
database_router = APIRouter(prefix="/database", tags=["Database"])

# ===================
# 사용자 관련 엔드포인트
# ===================

@database_router.get("/users/{user_id}")
async def get_user(user_id: int):
    """사용자 정보 조회"""
    try:
        user = await existing_tables_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        return {"success": True, "data": user}
    except Exception as e:
        logger.error(f"사용자 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 조회 중 오류가 발생했습니다")

@database_router.post("/users")
async def create_user(request: CreateUserRequest):
    """새 사용자 생성"""
    try:
        user = await existing_tables_service.create_user(
            name=request.name,
            email=request.email,
            pw=request.pw
        )
        if not user:
            raise HTTPException(status_code=400, detail="사용자 생성에 실패했습니다")
        return {"success": True, "data": user}
    except Exception as e:
        logger.error(f"사용자 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 생성 중 오류가 발생했습니다")

# ===================
# 회사 및 포지션 관련 엔드포인트
# ===================

@database_router.get("/companies")
async def get_companies():
    """모든 회사 목록 조회"""
    try:
        companies = await existing_tables_service.get_companies()
        return {"success": True, "data": companies}
    except Exception as e:
        logger.error(f"회사 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="회사 목록 조회 중 오류가 발생했습니다")

@database_router.get("/companies/{company_id}/positions")
async def get_positions_by_company(company_id: int):
    """특정 회사의 포지션 목록 조회"""
    try:
        positions = await existing_tables_service.get_positions_by_company(company_id)
        return {"success": True, "data": positions}
    except Exception as e:
        logger.error(f"포지션 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="포지션 목록 조회 중 오류가 발생했습니다")

# ===================
# 면접 관련 엔드포인트
# ===================

@database_router.post("/interviews")
async def create_interview(request: CreateInterviewRequest):
    """새 면접 세션 생성"""
    try:
        interview = await existing_tables_service.create_interview(
            user_id=request.user_id,
            company_id=request.company_id,
            position_id=request.position_id,
            posting_id=request.posting_id
        )
        if not interview:
            raise HTTPException(status_code=400, detail="면접 세션 생성에 실패했습니다")
        return {"success": True, "data": interview}
    except Exception as e:
        logger.error(f"면접 세션 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="면접 세션 생성 중 오류가 발생했습니다")

@database_router.get("/interviews/{interview_id}")
async def get_interview(interview_id: int):
    """면접 세션 상세 조회"""
    try:
        interview = await existing_tables_service.get_interview_by_id(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="면접 세션을 찾을 수 없습니다")
        return {"success": True, "data": interview}
    except Exception as e:
        logger.error(f"면접 세션 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="면접 세션 조회 중 오류가 발생했습니다")

@database_router.get("/interviews/{interview_id}/history")
async def get_interview_history(interview_id: int):
    """면접 기록 조회"""
    try:
        history = await existing_tables_service.get_interview_history(interview_id)
        return {"success": True, "data": history}
    except Exception as e:
        logger.error(f"면접 기록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="면접 기록 조회 중 오류가 발생했습니다")

@database_router.post("/interviews/details")
async def save_interview_detail(request: SaveInterviewDetailRequest):
    """면접 상세 기록 저장"""
    try:
        detail = await existing_tables_service.save_interview_detail(
            interview_id=request.interview_id,
            who=request.who,
            question_index=request.question_index,
            question_id=request.question_id,
            question_content=request.question_content,
            question_intent=request.question_intent,
            question_level=request.question_level,
            answer=request.answer,
            feedback=request.feedback,
            sequence=request.sequence,
            duration=request.duration
        )
        if not detail:
            raise HTTPException(status_code=400, detail="면접 기록 저장에 실패했습니다")
        return {"success": True, "data": detail}
    except Exception as e:
        logger.error(f"면접 기록 저장 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="면접 기록 저장 중 오류가 발생했습니다")

# ===================
# 고정 질문 관련 엔드포인트
# ===================

@database_router.get("/questions/fixed")
async def get_fixed_questions():
    """모든 고정 질문 조회"""
    try:
        questions = await existing_tables_service.get_fixed_questions()
        return {"success": True, "data": questions}
    except Exception as e:
        logger.error(f"고정 질문 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="고정 질문 조회 중 오류가 발생했습니다")

@database_router.get("/questions/fixed/{question_level}")
async def get_fixed_questions_by_level(question_level: str):
    """난이도별 고정 질문 조회"""
    try:
        questions = await existing_tables_service.get_fixed_questions_by_level(question_level)
        return {"success": True, "data": questions}
    except Exception as e:
        logger.error(f"난이도별 고정 질문 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="난이도별 고정 질문 조회 중 오류가 발생했습니다")

# ===================
# 이력서 관련 엔드포인트
# ===================

@database_router.post("/resumes/user")
async def save_user_resume(request: SaveResumeRequest):
    """사용자 이력서 저장"""
    try:
        resume = await existing_tables_service.save_user_resume(
            user_id=request.user_id,
            title=request.title,
            content=request.content
        )
        if not resume:
            raise HTTPException(status_code=400, detail="이력서 저장에 실패했습니다")
        return {"success": True, "data": resume}
    except Exception as e:
        logger.error(f"이력서 저장 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="이력서 저장 중 오류가 발생했습니다")

@database_router.get("/resumes/user/{user_id}")
async def get_user_resumes(user_id: int):
    """사용자의 모든 이력서 조회"""
    try:
        resumes = await existing_tables_service.get_user_resumes(user_id)
        return {"success": True, "data": resumes}
    except Exception as e:
        logger.error(f"사용자 이력서 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 이력서 조회 중 오류가 발생했습니다")

@database_router.get("/resumes/ai/{position_id}")
async def get_ai_resumes_by_position(position_id: int):
    """포지션별 AI 이력서 조회"""
    try:
        resumes = await existing_tables_service.get_ai_resumes_by_position(position_id)
        return {"success": True, "data": resumes}
    except Exception as e:
        logger.error(f"AI 이력서 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="AI 이력서 조회 중 오류가 발생했습니다")

# ===================
# 통계 관련 엔드포인트
# ===================

@database_router.get("/users/{user_id}/interview-count")
async def get_user_interview_count(user_id: int):
    """사용자의 총 면접 횟수 조회"""
    try:
        count = await existing_tables_service.get_interview_count_by_user(user_id)
        return {"success": True, "data": {"interview_count": count}}
    except Exception as e:
        logger.error(f"면접 횟수 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="면접 횟수 조회 중 오류가 발생했습니다")

@database_router.get("/users/{user_id}/recent-interviews")
async def get_recent_interviews(user_id: int, limit: int = 10):
    """최근 면접 목록 조회"""
    try:
        interviews = await existing_tables_service.get_recent_interviews(user_id, limit)
        return {"success": True, "data": interviews}
    except Exception as e:
        logger.error(f"최근 면접 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="최근 면접 목록 조회 중 오류가 발생했습니다")

# ===================
# 헬스체크
# ===================

@database_router.get("/health")
async def database_health_check():
    """데이터베이스 연결 상태 확인"""
    try:
        # 간단한 테스트 쿼리
        companies = await existing_tables_service.get_companies()
        return {
            "success": True, 
            "message": "데이터베이스 연결 정상",
            "companies_count": len(companies)
        }
    except Exception as e:
        logger.error(f"데이터베이스 헬스체크 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="데이터베이스 연결에 문제가 있습니다")