#!/usr/bin/env python3
"""
FastAPI 기반 AI 면접 시스템
새로운 서비스 계층 구조 적용
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys
from datetime import datetime
import mimetypes

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
    
    # S3 비디오 API 임포트
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 's3'))
    from test.video_api import router as test_video_router
    
    # 시선 분석 API 임포트
    from test.gaze_api import get_gaze_router

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

# API 엔드포인트 (API 정보는 /api 경로로 이동)
@app.get("/api")
async def root():
    """API 정보 반환"""
    return {
        "message": "Beta-GO Interview API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

@app.post("/api")
async def debug_log(request: Request):
    """프론트엔드 디버깅 로그 수신"""
    try:
        body = await request.json()
        print(f"🔍 FRONTEND_DEBUG: {body}")
        return {"status": "logged"}
    except Exception as e:
        print(f"❌ 디버깅 로그 처리 실패: {e}")
        return {"error": str(e)}

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "timestamp": datetime.now()}


# SPA 라우팅을 위한 간단한 미들웨어
@app.middleware("http")
async def spa_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # API 경로들은 그대로 반환 (더 구체적으로 지정)
    api_paths = ['/auth', '/user', '/resume', '/company', '/posting', '/position', '/gaze', '/docs', '/redoc', '/openapi.json', '/health']
    
    # /interview API 경로들 (정확한 매칭을 위해)
    is_interview_api = (
        request.url.path.startswith('/interview/start') or
        request.url.path.startswith('/interview/answer') or
        request.url.path.startswith('/interview/question') or
        request.url.path.startswith('/interview/history/') or  # /interview/history/123 (API)
        request.url.path == '/interview/history' or  # /interview/history (API)
        request.url.path.startswith('/interview/ai/') or
        request.url.path.startswith('/interview/complete') or
        request.url.path.startswith('/interview/upload') or
        request.url.path.startswith('/interview/tts') or
        request.url.path.startswith('/interview/stt') or
        request.url.path.startswith('/interview/text-competition') or
        request.url.path.startswith('/interview/comparison') or
        request.url.path.startswith('/interview/session') or
        request.url.path.startswith('/interview/feedback') or
        request.url.path.startswith('/interview/video/') or # 비디오 스트리밍 API
                '/gaze-analysis' in request.url.path  # 시선 분석 결과 API  # 시선 분석 결과 API
    )
    
    # 디버깅: 면접 관련 API 호출 로깅
    if request.url.path.startswith('/interview/'):
        print(f"🔍 면접 API 요청: {request.method} {request.url.path}")
        print(f"📊 API 매칭 결과: is_interview_api={is_interview_api}")
        print(f"📈 응답 상태: {response.status_code}")
    
    if (any(request.url.path.startswith(path) for path in api_paths) or is_interview_api):
        return response
    
    # 정적 파일들은 그대로 반환
    static_extensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot']
    if any(request.url.path.endswith(ext) for ext in static_extensions):
        return response
    
    # /static, /js, /css, /img 경로들은 그대로 반환
    if request.url.path.startswith('/static') or request.url.path.startswith('/js') or request.url.path.startswith('/css') or request.url.path.startswith('/img'):
        return response
    
    # 404 에러인 경우 React 앱 반환
    if response.status_code == 404:
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path, media_type="text/html")
    
    return response

# 루트 경로와 앱 경로는 React 앱 반환
@app.get("/")
@app.get("/app")
async def serve_root():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Beta-GO Interview API", "version": "2.0.0", "status": "running", "docs": "/docs", "health": "/health"}

# 정적 파일 서빙 설정 (React 앱)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount("/js", StaticFiles(directory=os.path.join(static_dir, "js")), name="js")
    app.mount("/css", StaticFiles(directory=os.path.join(static_dir, "css")), name="css")
    
    # 이미지 파일 서빙
    img_dir = os.path.join(static_dir, "img")
    if os.path.exists(img_dir):
        app.mount("/img", StaticFiles(directory=img_dir), name="img")
    
    print(f"정적 파일 서빙 활성화: {static_dir}")
else:
    print("정적 파일 디렉토리가 존재하지 않습니다. API 모드로만 실행됩니다.")

# 데이터베이스 라우터 등록
if DATABASE_ENABLED:
    app.include_router(user_router)
    app.include_router(resume_router)
    app.include_router(auth_router)
    app.include_router(company_router)
    app.include_router(posting_router)
    app.include_router(position_router)
    app.include_router(interview_router)
    app.include_router(test_video_router)  # S3 테스트 비디오 API 라우터 추가
    app.include_router(get_gaze_router())  # 시선 분석 API 라우터 추가
    # app.include_router(migration_router)
    # app.include_router(database_router)
    
    # === 김원우 작성 시작 ===
    # 새로운 표준 구조 라우터 등록
    try:
        from routers.media import media_router
        from routers.gaze import gaze_router
        
        app.include_router(media_router)
        app.include_router(gaze_router)
        
        print("✅ 새로운 미디어 및 시선 분석 라우터 등록 완료")
        print("   - /media/* : S3 미디어 파일 관리 API")  
        print("   - /gaze/* : 시선 분석 및 캘리브레이션 API")
    except ImportError as e:
        print(f"⚠️ 새로운 라우터 로드 실패: {e}")
        print("   기존 test 라우터를 계속 사용합니다.")
    # === 김원우 작성 끝 ===

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