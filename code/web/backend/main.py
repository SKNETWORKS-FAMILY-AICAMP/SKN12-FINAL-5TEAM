#!/usr/bin/env python3
"""
FastAPI 기반 AI 면접 시스템
새로운 서비스 계층 구조 적용
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 데이터베이스 확장 임포트
try:
    from routers.user import user_router
    from routers.resume import resume_router
    from routers.auth import auth_router
    from routers.company import company_router
    from routers.posting import posting_router
    from routers.position import position_router
    from routers.interview import interview_router
    # from routers.migration import migration_router
    # from routers.database import database_router

    DATABASE_ENABLED = True
    print("데이터베이스 확장 로드 성공")
    print("마이그레이션 API 로드 성공")
    print("인증 라우터 로드 성공")
except ImportError as e:
    DATABASE_ENABLED = False
    print(f"데이터베이스 확장 로드 실패: {e}")
    print("메모리 기반 모드로 실행됩니다.")

# FastAPI 앱 초기화
app = FastAPI(
    title="Beta-GO Interview API",
    description="AI 기반 개인화된 면접 시스템",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서만 사용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 엔드포인트
@app.get("/")
async def root():
    """루트 엔드포인트 - API 정보 반환"""
    return {
        "message": "Beta-GO Interview API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "timestamp": datetime.now()}

# 데이터베이스 라우터 등록
if DATABASE_ENABLED:
    app.include_router(user_router)
    app.include_router(resume_router)
    app.include_router(auth_router)
    app.include_router(company_router)
    app.include_router(posting_router)
    app.include_router(position_router)
    app.include_router(interview_router)
    # app.include_router(migration_router)
    # app.include_router(database_router)

    print("="*100)
    print("API 라우터 등록 완료")
    print("="*100)

if __name__ == "__main__":
    import uvicorn
    print("Beta-GO Interview FastAPI 시작!")
    print("브라우저에서 http://localhost:8000 접속")
    print("API 문서: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )