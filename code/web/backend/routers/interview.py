from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, HTMLResponse
from typing import Optional
import logging
from typing import List
from backend.services.supabase_client import supabase_client
from backend.schemas.user import UserResponse
from schemas.interview import InterviewHistoryResponse, InterviewSettings, AnswerSubmission, CompetitionTurnSubmission, InterviewResponse, TTSRequest, STTResponse
from services.interview_service import InterviewService
from services.interview_service_temp import InterviewServiceTemp
from backend.services.auth_service import AuthService
from backend.services.voice_service import elevenlabs_tts_stream
from fastapi.responses import HTMLResponse
import io




# 서비스 계층 사용
interview_service = InterviewService()
interview_service_temp = InterviewServiceTemp()

# AuthService 인스턴스 생성
auth_service = AuthService()

# 의존성 주입
def get_interview_service():
    return interview_service

def get_temp_interview_service():
    return interview_service_temp

# 로거 설정
interview_logger = logging.getLogger("interview_logger")

# APIRouter 인스턴스 생성
interview_router = APIRouter(
    prefix="/interview",
    tags=["Interview"],
)

# @interview_router.post("/start")
# async def start_interview(
#     settings: InterviewSettings,
#     service: InterviewService = Depends(get_interview_service)
# ):
#     """면접 시작 - 서비스 계층 사용"""
#     try:
#         settings_dict = {
#             "company": settings.company,
#             "position": settings.position,
#             "candidate_name": settings.candidate_name,
#             "documents": settings.documents
#         }
# =================================================================
# 🚀 TTS 테스트용 임시 코드 START (나중에 이 부분을 삭제하세요)
# =================================================================


@interview_router.get("/tts-test", response_class=HTMLResponse, summary="[테스트용] TTS 웹 페이지")
async def get_tts_test_page():
    """
    TTS API를 테스트하기 위한 간단한 HTML 페이지를 반환합니다.
    이 엔드포인트는 개발 및 디버깅 목적으로만 사용됩니다.
    """
    try:
        with open("temp_test.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="테스트 파일을 찾을 수 없습니다: temp_test.html")
# =================================================================
# 🚀 TTS 테스트용 임시 코드 END
# =================================================================
        
#         result = await service.start_interview(settings_dict)
#         return result
        
#     except Exception as e:
#         interview_logger.error(f"면접 시작 오류: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
    
# @interview_router.post("/upload")
# async def upload_document(
#     file: UploadFile = File(...),
#     service: InterviewService = Depends(get_interview_service)
# ):
#     """문서 업로드 및 분석"""
#     try:
#         content = await file.read()
#         file_data = {
#             "filename": file.filename,
#             "content": content
#         }
        
#         result = await service.upload_document(file_data)
#         return result
        
#     except Exception as e:
#         interview_logger.error(f"문서 업로드 오류: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @interview_router.get("/question")
# async def get_next_question(
#     session_id: str,
#     service: InterviewService = Depends(get_interview_service)
# ):
#     """다음 질문 가져오기 - 서비스 계층 사용"""
#     try:
#         result = await service.get_next_question(session_id)
#         return result
        
#     except Exception as e:
#         interview_logger.error(f"질문 가져오기 오류: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @interview_router.post("/answer")
# async def submit_answer(
#     answer_data: AnswerSubmission,
#     service: InterviewService = Depends(get_interview_service)
# ):
#     """답변 제출 - 서비스 계층 사용"""
#     try:
#         answer_dict = {
#             "session_id": answer_data.session_id,
#             "answer": answer_data.answer,
#             "time_spent": answer_data.time_spent
#         }
        
#         result = await service.submit_answer(answer_dict)
#         return result
        
#     except Exception as e:
#         interview_logger.error(f"답변 제출 오류: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# AI 경쟁 모드 엔드포인트

@interview_router.post("/ai/start")
async def start_ai_competition(
    settings: InterviewSettings,
    service: InterviewService = Depends(get_interview_service)
):
    """AI 지원자와의 경쟁 면접 시작"""
    try:
        # 🐛 디버깅: FastAPI에서 받은 설정값 로깅
        interview_logger.info(f"🐛 FastAPI DEBUG: 받은 settings = {settings.dict()}")
        interview_logger.info(f"🐛 FastAPI DEBUG: use_interviewer_service = {settings.use_interviewer_service}")
        
        # 🆕 posting_id가 있으면 DB에서 실제 채용공고 정보를 가져와서 사용
        if settings.posting_id:
            from backend.services.existing_tables_service import existing_tables_service
            posting_info = await existing_tables_service.get_posting_by_id(settings.posting_id)
            
            if posting_info:
                interview_logger.info(f"📋 실제 채용공고 사용: posting_id={settings.posting_id}")
                interview_logger.info(f"   회사: {posting_info.get('company', {}).get('name', 'Unknown')}")
                interview_logger.info(f"   직무: {posting_info.get('position', {}).get('position_name', 'Unknown')}")
                
                settings_dict = {
                    "company": posting_info.get('company', {}).get('name', settings.company),
                    "position": posting_info.get('position', {}).get('position_name', settings.position),
                    "candidate_name": settings.candidate_name,
                    "posting_id": settings.posting_id,
                    "company_id": posting_info.get('company_id'),
                    "position_id": posting_info.get('position_id'),
                    "use_interviewer_service": settings.use_interviewer_service  # 🎯 플래그 포함
                }
            else:
                interview_logger.warning(f"⚠️ 채용공고를 찾을 수 없음: posting_id={settings.posting_id}, fallback to original")
                settings_dict = {
                    "company": settings.company,
                    "position": settings.position,
                    "candidate_name": settings.candidate_name,
                    "use_interviewer_service": settings.use_interviewer_service  # 🎯 플래그 포함
                }
        else:
            # 기존 방식: company/position 문자열 사용
            settings_dict = {
                "company": settings.company,
                "position": settings.position,
                "candidate_name": settings.candidate_name,
                "use_interviewer_service": settings.use_interviewer_service  # 🎯 플래그 포함
            }
        
        # 🐛 디버깅: 서비스에 전달할 settings_dict 로깅
        interview_logger.info(f"🐛 FastAPI DEBUG: 서비스에 전달할 settings_dict = {settings_dict}")
        
        result = await service.start_ai_competition(settings_dict)
        return result
        
    except Exception as e:
        interview_logger.error(f"AI 경쟁 면접 시작 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.get("/ai-answer/{session_id}/{question_id}")
async def get_ai_answer(
    session_id: str,
    question_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """AI 지원자의 답변 생성"""
    try:
        result = await service.get_ai_answer(session_id, question_id)
        return result
        
    except Exception as e:
        interview_logger.error(f"AI 답변 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.post("/comparison/turn")
async def process_competition_turn(
    submission: CompetitionTurnSubmission,
    service: InterviewService = Depends(get_interview_service)
):
    """경쟁 면접 통합 턴 처리"""
    try:
        result = await service.process_competition_turn(
            submission.comparison_session_id,
            submission.answer
        )
        return result
    except Exception as e:
        interview_logger.error(f"경쟁 면접 턴 처리 API 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 🚀 새로운 턴제 면접 엔드포인트
@interview_router.post("/turn-based/start")
async def start_turn_based_interview(
    settings: InterviewSettings,
    service: InterviewService = Depends(get_interview_service)
):
    """턴제 면접 시작 - 새로운 InterviewerService 사용"""
    try:
        settings_dict = {
            "company": settings.company,
            "position": settings.position,
            "candidate_name": settings.candidate_name
        }
        
        result = await service.start_turn_based_interview(settings_dict)
        return result
        
    except Exception as e:
        interview_logger.error(f"턴제 면접 시작 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.get("/turn-based/question/{session_id}")
async def get_turn_based_question(
    session_id: str,
    user_answer: Optional[str] = None,
    service: InterviewService = Depends(get_interview_service)
):
    """턴제 면접 다음 질문 가져오기"""
    try:
        result = await service.get_turn_based_question(session_id, user_answer)
        return result
        
    except Exception as e:
        interview_logger.error(f"턴제 질문 가져오기 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 🟢 GET /interview/history – 내 면접 기록 조회
@interview_router.get("/history", response_model=List[InterviewResponse])
async def get_interview_history(current_user: UserResponse = Depends(auth_service.get_current_user)):
    """현재 인증된 사용자의 면접 기록을 Supabase에서 조회합니다."""
    res = supabase_client.client.from_("interview").select("*").eq("user_id", current_user.user_id).execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="No interview history found")
    
    return res.data


@interview_router.get("/history/{interview_id}", response_model=List[InterviewHistoryResponse])
async def get_interview_results(
    interview_id: int,
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    """현재 로그인한 유저의 특정 면접 기록 조회"""
    res = supabase_client.client.from_("history_detail") \
        .select("*") \
        .eq("interview_id", interview_id) \
        .execute()
        # .eq("user_id", current_user.user_id) \
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    return res.data

# 🟢 POST /interview/tts
@interview_router.post("/tts")
async def text_to_speech_elevenlabs(req: TTSRequest):
    # 로그 추가
    interview_logger.info(f"TTS 요청 수신: voice_id='{req.voice_id}', text='{req.text[:50]}...'")

    # 빈 텍스트 유효성 검사
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="TTS를 위한 텍스트 내용이 비어있습니다.")

    try:
        audio_bytes = await elevenlabs_tts_stream(req.text, req.voice_id)
        return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
    except HTTPException as e:
        # voice_service에서 발생한 HTTPException을 그대로 전달
        interview_logger.error(f"TTS API 오류 발생: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        # 그 외 예기치 않은 오류 처리
        interview_logger.error(f"TTS 처리 중 예기치 않은 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="TTS 처리 중 서버 오류가 발생했습니다.")

# 🟢 POST /interview/stt
@interview_router.post("/stt", response_model=STTResponse)
async def speech_to_text(file: UploadFile = File(...)):
    pass


# ============================================================================
# 🚀 텍스트 기반 AI 경쟁 면접 엔드포인트들 (InterviewServiceTemp 사용)
# ============================================================================

@interview_router.post("/text-competition/start")
async def start_text_competition(
    settings: InterviewSettings,
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 기반 AI 경쟁 면접 시작"""
    try:
        interview_logger.info(f"🎯 텍스트 경쟁 면접 시작 요청: {settings.company} - {settings.position}")
        
        settings_dict = {
            "company": settings.company,
            "position": settings.position,
            "candidate_name": settings.candidate_name,
            "documents": settings.documents or []
        }
        
        result = await temp_service.start_text_interview(settings_dict)
        
        interview_logger.info(f"✅ 텍스트 경쟁 면접 시작 성공: {result.get('session_id')}")
        return result
        
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 경쟁 면접 시작 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.post("/text-competition/submit-answer")
async def submit_text_answer(
    answer_data: dict,
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 답변 제출 및 AI 답변 + 다음 질문 받기"""
    try:
        session_id = answer_data.get("session_id")
        answer = answer_data.get("answer")
        
        if not session_id or not answer:
            raise HTTPException(status_code=400, detail="session_id와 answer가 필요합니다")
        
        interview_logger.info(f"📝 텍스트 답변 제출: {session_id}")
        
        result = await temp_service.submit_answer_and_get_next(session_id, answer)
        
        interview_logger.info(f"✅ 텍스트 답변 처리 완료: {session_id} - {result.get('status')}")
        return result
        
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 답변 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.get("/text-competition/session/{session_id}")
async def get_text_session_info(
    session_id: str,
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 기반 면접 세션 정보 조회"""
    try:
        interview_logger.info(f"🔍 텍스트 세션 정보 조회: {session_id}")
        
        result = await temp_service.get_session_info(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 세션 정보 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.get("/text-competition/results/{session_id}")
async def get_text_interview_results(
    session_id: str,
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 기반 면접 결과 조회"""
    try:
        interview_logger.info(f"📊 텍스트 면접 결과 조회: {session_id}")
        
        result = await temp_service.get_interview_results(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 면접 결과 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.delete("/text-competition/session/{session_id}")
async def cleanup_text_session(
    session_id: str,
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 기반 면접 세션 정리"""
    try:
        interview_logger.info(f"🧹 텍스트 세션 정리 요청: {session_id}")
        
        success = temp_service.cleanup_session(session_id)
        
        if success:
            return {"message": "세션이 성공적으로 정리되었습니다.", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 세션 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.get("/text-competition/stats")
async def get_text_interview_stats(
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 기반 면접 시스템 통계"""
    try:
        active_sessions = temp_service.get_active_sessions_count()
        
        return {
            "active_sessions": active_sessions,
            "service_type": "text_based_competition",
            "system_status": "operational"
        }
        
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 면접 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
