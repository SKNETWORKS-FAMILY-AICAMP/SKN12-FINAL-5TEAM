from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request, Query
from fastapi.responses import StreamingResponse, HTMLResponse
from typing import Optional
import logging
from typing import List, Union
import boto3
from botocore.exceptions import ClientError
from backend.services.supabase_client import supabase_client
from backend.schemas.user import UserResponse
from schemas.interview import InterviewHistoryResponse, InterviewSettings, AnswerSubmission, AICompetitionAnswerSubmission, CompetitionTurnSubmission, InterviewResponse, TTSRequest, STTResponse, MemoUpdateRequest
from backend.schemas.gaze import GazeAnalysisResponse
from services.interview_service import InterviewService
from services.interview_service_temp import InterviewServiceTemp
from backend.services.auth_service import AuthService
from backend.services.voice_service import elevenlabs_tts_stream
from fastapi.responses import HTMLResponse
import io
import time
import os
import tempfile
import aiohttp
from dotenv import load_dotenv



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

# AI 경쟁 모드 엔드포인트

@interview_router.post("/ai/start")
async def start_ai_competition(
    settings: InterviewSettings,
    service: InterviewService = Depends(get_interview_service),
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    """AI 지원자와의 경쟁 면접 시작"""
    start_time = time.perf_counter()
    try:
        interview_logger.info(f"🐛 FastAPI DEBUG: 받은 settings = {settings.dict()}")

        # 1. Pydantic 모델을 딕셔너리로 변환하여 원본 데이터를 모두 보존합니다.
        settings_dict = settings.dict()
        
        # 2. user_id를 추가합니다.
        settings_dict['user_id'] = current_user.user_id

        # 3. user_resume_id가 없으면 DB에서 조회하여 추가합니다.
        if not settings.user_resume_id:
            try:
                from backend.services.existing_tables_service import existing_tables_service
                user_resumes = await existing_tables_service.get_user_resumes(current_user.user_id)
                if user_resumes:
                    # settings_dict를 직접 업데이트합니다.
                    settings_dict['user_resume_id'] = user_resumes[0].get('user_resume_id')
                    interview_logger.info(f"✅ 자동 조회된 user_resume_id: {settings_dict['user_resume_id']}")
            except Exception as e:
                interview_logger.error(f"❌ user_resume_id 자동 조회 실패: {e}")

        # 4. posting_id가 있으면 DB 정보를 이용해 일부 값을 덮어씁니다. (update 사용)
        if settings.posting_id:
            from backend.services.existing_tables_service import existing_tables_service
            posting_info = await existing_tables_service.get_posting_by_id(settings.posting_id)
            if posting_info:
                interview_logger.info(f"📋 실제 채용공고 사용: posting_id={settings.posting_id}")
                # 덮어쓸 내용만 update()를 사용하여 기존 데이터를 보존합니다.
                settings_dict.update({
                    "company": posting_info.get('company', {}).get('name', settings.company),
                    "position": posting_info.get('position', {}).get('position_name', settings.position),
                    "company_id": posting_info.get('company_id'),
                    "position_id": posting_info.get('position_id'),
                })
            else:
                interview_logger.warning(f"⚠️ 채용공고를 찾을 수 없음: posting_id={settings.posting_id}")
        
        interview_logger.info(f"🐛 FastAPI DEBUG: 서비스에 전달할 최종 settings_dict = {settings_dict}")
        
        result = await service.start_ai_competition(settings_dict, start_time=start_time)
        
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        interview_logger.info(f"✅ AI 경쟁 면접 시작 성공. 총 처리 시간: {elapsed_time:.4f}초")
        
        return result
        
    except Exception as e:
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        interview_logger.error(f"AI 경쟁 면접 시작 오류: {str(e)}. 처리 시간: {elapsed_time:.4f}초", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.post("/answer")
async def submit_user_answer(
    submission: AICompetitionAnswerSubmission,
    service: InterviewService = Depends(get_interview_service)
):
    """사용자 답변 제출 - AI 경쟁 면접용"""
    try:
        interview_logger.info(f"👤 사용자 답변 제출 요청: {submission.session_id}")
        
        result = await service.submit_user_answer(
            session_id=submission.session_id,
            user_answer=submission.answer,
            time_spent=submission.time_spent
        )
        
        interview_logger.info(f"✅ 사용자 답변 제출 완료: {submission.session_id}")
        return result
        
    except Exception as e:
        interview_logger.error(f"사용자 답변 제출 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.get("/session/active")
async def get_active_sessions(
    service: InterviewService = Depends(get_interview_service)
):
    """현재 활성 세션들 조회"""
    try:
        active_sessions = service.get_active_sessions()
        return {
            "active_sessions": active_sessions,
            "count": len(active_sessions)
        }
    except Exception as e:
        interview_logger.error(f"활성 세션 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.get("/session/{session_id}/state")
async def get_session_state(
    session_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """특정 세션의 상태 조회"""
    try:
        state = service.get_session_state(session_id)
        if not state:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        return {
            "session_id": session_id,
            "state": state,
            "is_active": True
        }
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"세션 상태 조회 오류: {str(e)}")
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
    print(f"🔍 DEBUG: 면접 히스토리 조회 - 사용자 ID: {current_user.user_id} (타입: {type(current_user.user_id)}), 이메일: {current_user.email}")
    
    # 전체 interview 테이블 데이터 확인
    all_interviews = supabase_client.client.from_("interview").select("interview_id, user_id").execute()
    print(f"🔍 DEBUG: 전체 interview 테이블 레코드 수: {len(all_interviews.data) if all_interviews.data else 0}")
    if all_interviews.data:
        user_ids_with_types = [(item['user_id'], type(item['user_id'])) for item in all_interviews.data[:5]]
        print(f"🔍 DEBUG: 전체 interview 사용자 ID들과 타입: {user_ids_with_types}")
        
        # 현재 사용자 ID와 일치하는지 직접 확인
        matching_interviews = [item for item in all_interviews.data if str(item['user_id']) == str(current_user.user_id)]
        print(f"🔍 DEBUG: 문자열 변환 후 일치하는 면접 수: {len(matching_interviews)}")
    
    # 첫 번째 파일의 더 상세한 쿼리 사용 (company, position join 포함)
    # 타입 불일치 방지를 위해 문자열로 변환하여 조회
    res = supabase_client.client.from_("interview").select(
        "*, company(name), position(position_name)"
    ).eq("user_id", str(current_user.user_id)).execute()
    
    print(f"🔍 DEBUG: 사용자별 면접 기록 조회 결과: {len(res.data) if res.data else 0}개")
    if res.data:
        print(f"🔍 DEBUG: 첫 번째 면접 기록: {res.data[0]}")
    
    if not res.data:
        return []  # 빈 배열 반환 (404 에러 대신)
    # ai_resume_id/user_resume_id가 None인 경우에도 스키마 검증을 통과하도록 보정
    data = res.data
    for row in data:
        if 'ai_resume_id' in row and row['ai_resume_id'] is None:
            row['ai_resume_id'] = None
        if 'user_resume_id' in row and row['user_resume_id'] is None:
            row['user_resume_id'] = None
        # total_feedback이 None인 경우 빈 문자열로 변환
        if 'total_feedback' in row and row['total_feedback'] is None:
            row['total_feedback'] = ""
    return data


@interview_router.get("/history/{interview_id}")
async def get_interview_results(
    interview_id: int,
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    """현재 로그인한 유저의 특정 면접 기록 조회 (상세 데이터 + 전체 피드백 + 영상 URL)"""
    
    # 1. history_detail 테이블에서 질문별 상세 데이터 가져오기
    detail_res = supabase_client.client.from_("history_detail") \
        .select("*") \
        .eq("interview_id", interview_id) \
        .execute()
    
    # 2. interview 테이블에서 전체 피드백 가져오기
    interview_res = supabase_client.client.from_("interview") \
        .select("total_feedback") \
        .eq("interview_id", interview_id) \
        .execute()
    
    # 3. plans 테이블에서 개선 계획 가져오기
    plans_res = supabase_client.client.from_("plans") \
        .select("shortly_plan, long_plan") \
        .eq("interview_id", interview_id) \
        .execute()
    
    # 4. media_files 테이블에서 영상 파일 정보 확인
    video_url = None
    video_metadata = None
    
    try:
        media_res = supabase_client.client.from_("media_files") \
            .select("s3_key, file_name, file_size, duration, created_at") \
            .eq("interview_id", interview_id) \
            .eq("file_type", "video") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        if media_res.data and len(media_res.data) > 0:
            video_file = media_res.data[0]
            # 영상이 있으면 스트리밍 URL 제공
            video_url = f"/interview/video/{interview_id}/stream"
            video_metadata = {
                "file_name": video_file.get("file_name"),
                "file_size": video_file.get("file_size"),
                "duration": video_file.get("duration"),
                "created_at": video_file.get("created_at")
            }
            interview_logger.info(f"✅ 면접 {interview_id}의 영상 파일 발견: {video_file.get('file_name')}")
        else:
            interview_logger.info(f"ℹ️ 면접 {interview_id}에 대한 영상 파일이 없습니다")
            
    except Exception as e:
        interview_logger.warning(f"⚠️ 영상 파일 조회 중 오류 (무시됨): {e}")
        # 영상 파일 조회 실패는 전체 API를 실패시키지 않음
    
    # 다운로드 URL 생성
    download_url = None
    download_optimized_url = None
    if video_url:
        download_url = f"/interview/video/{interview_id}/download"
        download_optimized_url = f"/interview/video/{interview_id}/download?optimize=true"
    
    # 데이터 통합
    result = {
        "details": detail_res.data or [],
        "total_feedback": interview_res.data[0]["total_feedback"] if interview_res.data else None,
        "plans": plans_res.data[0] if plans_res.data else None,
        "video_url": video_url,
        "download_url": download_url,
        "download_optimized_url": download_optimized_url,
        "video_metadata": video_metadata
    }
    
    return result


@interview_router.get("/{interview_id}/gaze-analysis", response_model=GazeAnalysisResponse, summary="[신규] 특정 면접의 시선 분석 결과 조회")
async def get_gaze_analysis_for_interview(
    interview_id: int,
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    """특정 면접에 대한 시선 분석(비언어적 피드백) 결과를 조회합니다."""
    try:
        interview_logger.info(f"📈 시선 분석 결과 요청: interview_id={interview_id}")
        
        # 1. 해당 면접이 현재 사용자의 것인지 확인 (보안 강화)
        interview_res = supabase_client.client.from_("interview") \
            .select("user_id") \
            .eq("interview_id", interview_id) \
            .eq("user_id", current_user.user_id) \
            .single() \
            .execute()

        if not interview_res.data:
            raise HTTPException(status_code=403, detail="해당 면접에 접근할 권한이 없습니다.")

        # 2. gaze_analysis 테이블에서 결과 조회 (테이블명은 가정)
        # TODO: 2단계에서 실제 DB 조회 로직으로 변경해야 합니다.
        gaze_res = supabase_client.client.from_("gaze_analysis") \
            .select("*") \
            .eq("interview_id", interview_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if not gaze_res.data:
            # 🚨 중요: 현재는 데이터가 없으면 404를 반환합니다.
            # 2단계에서 gaze.py가 DB에 데이터를 저장하도록 수정해야 합니다.
            interview_logger.warning(f"⚠️ interview_id={interview_id}에 대한 시선 분석 데이터 없음")
            raise HTTPException(status_code=404, detail="해당 면접의 시선 분석 데이터를 찾을 수 없습니다.")

        analysis_data = gaze_res.data[0]
        
        # 프론트엔드가 기대하는 GazeAnalysisResponse 모델로 변환
        return GazeAnalysisResponse(
            gaze_id=analysis_data.get("gaze_id"),
            interview_id=analysis_data.get("interview_id"),
            user_id=analysis_data.get("user_id"),
            gaze_score=analysis_data.get("gaze_score", 0),
            jitter_score=analysis_data.get("jitter_score", 0),
            compliance_score=analysis_data.get("compliance_score", 0),
            stability_rating=analysis_data.get("stability_rating", "N/A"),
            created_at=analysis_data.get("created_at"),
            gaze_points=analysis_data.get("gaze_points"),
            calibration_points=analysis_data.get("calibration_points"),
            video_metadata=analysis_data.get("video_metadata"),
        )

    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"❌ 시선 분석 결과 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="시선 분석 결과 조회 중 서버 오류가 발생했습니다.")


@interview_router.get("/video/{interview_id}/stream")
async def stream_interview_video(interview_id: int, request: Request):
    """
    면접 영상 스트리밍 엔드포인트 (Range 헤더 지원 - 비디오 탐색 기능).
    이 엔드포인트는 인증된 사용자에게만 노출되는 결과 페이지를 통해 접근되므로,
    엔드포인트 자체의 인증은 생략하여 비디오 플레이어 호환성을 높입니다.
    """
    try:
        # 1. DB에서 영상 정보 조회
        interview_logger.info(f"📹 스트리밍 요청 수신: interview_id={interview_id}")
        media_res = supabase_client.client.from_("media_files") \
            .select("s3_key, file_name, file_size") \
            .eq("interview_id", interview_id) \
            .eq("file_type", "video") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if not media_res.data:
            interview_logger.warning(f"⚠️ 영상 파일을 DB에서 찾을 수 없음: interview_id={interview_id}")
            raise HTTPException(status_code=404, detail="해당 면접의 영상 파일을 DB에서 찾을 수 없습니다.")

        video_file = media_res.data[0]
        s3_key = video_file["s3_key"]
        file_size = video_file.get("file_size")
        interview_logger.info(f"✅ DB 조회 성공. S3 Key: {s3_key}, File Size: {file_size}")

        # 2. S3 클라이언트 설정
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        s3_client = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name='ap-northeast-2')
        bucket_name = 'betago-s3'

        # 3. Range 헤더 처리
        range_header = request.headers.get('range')
        if range_header and file_size:
            interview_logger.info(f"📊 Range 요청: {range_header}, 파일 크기: {file_size}")
            
            try:
                # Range 헤더 파싱 개선 (예: "bytes=0-1023", "bytes=1024-", "bytes=-1000")
                range_match = range_header.replace('bytes=', '').split('-')
                interview_logger.info(f"📊 Range 파싱 결과: {range_match}")
                
                # 다양한 Range 패턴 처리
                if len(range_match) == 2:
                    if range_match[0] == '' and range_match[1] != '':
                        # suffix-byte-range-spec: "bytes=-1000" (마지막 1000바이트)
                        suffix_length = int(range_match[1])
                        start = max(0, file_size - suffix_length)
                        end = file_size - 1
                    elif range_match[0] != '' and range_match[1] == '':
                        # range from start to end: "bytes=1024-"
                        start = int(range_match[0])
                        end = file_size - 1
                    elif range_match[0] != '' and range_match[1] != '':
                        # range with both start and end: "bytes=0-1023"
                        start = int(range_match[0])
                        end = int(range_match[1])
                    else:
                        # 잘못된 Range 헤더
                        interview_logger.warning(f"⚠️ 잘못된 Range 헤더 형식: {range_header}")
                        start = 0
                        end = file_size - 1
                else:
                    interview_logger.warning(f"⚠️ Range 헤더 파싱 실패: {range_header}")
                    start = 0
                    end = file_size - 1
                
                # 범위 검증 및 조정
                start = max(0, min(start, file_size - 1))
                end = max(start, min(end, file_size - 1))
                content_length = end - start + 1
                
                interview_logger.info(f"📊 Range 처리 완료: {start}-{end}/{file_size} (Length: {content_length})")
                
            except (ValueError, IndexError) as e:
                interview_logger.error(f"❌ Range 헤더 파싱 오류: {e}")
                # 오류 시 전체 파일 반환
                start = 0
                end = file_size - 1
                content_length = file_size
            
            # S3에서 Range로 객체 가져오기
            s3_object = s3_client.get_object(
                Bucket=bucket_name, 
                Key=s3_key,
                Range=f'bytes={start}-{end}'
            )
            streaming_content = s3_object['Body']
            
            # Range 응답 헤더 설정 (RFC 7233 준수)
            response_headers = {
                "Accept-Ranges": "bytes",
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Accept-Ranges, Content-Range, Content-Length",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            
            interview_logger.info(f"✅ Range 스트리밍 시작: {start}-{end}/{file_size} -> Content-Range: bytes {start}-{end}/{file_size}")
            return StreamingResponse(
                streaming_content, 
                status_code=206,  # Partial Content
                media_type=s3_object.get('ContentType', 'video/webm'), 
                headers=response_headers
            )
        else:
            # Range 헤더가 없는 경우 전체 파일 스트리밍
            interview_logger.info("📊 전체 파일 스트리밍")
            s3_object = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            streaming_content = s3_object['Body']

            response_headers = {
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Accept-Ranges, Content-Length",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            if file_size:
                response_headers["Content-Length"] = str(file_size)

            interview_logger.info(f"✅ 전체 스트리밍 시작: {s3_key} (파일 크기: {file_size})")
            return StreamingResponse(
                streaming_content, 
                media_type=s3_object.get('ContentType', 'video/webm'), 
                headers=response_headers
            )

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        interview_logger.error(f"S3 스트리밍 오류 (interview_id: {interview_id}): {error_code}")
        if error_code == 'NoSuchKey':
            raise HTTPException(status_code=404, detail=f"S3에 해당 파일이 없습니다: {s3_key}")
        else:
            raise HTTPException(status_code=500, detail=f"S3 처리 오류: {error_code}")

    except HTTPException:
        # 이미 처리된 HTTPException은 그대로 전달
        raise
    except Exception as e:
        interview_logger.error(f"영상 스트리밍 중 알 수 없는 오류 (interview_id: {interview_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="영상 스트리밍 중 서버 오류가 발생했습니다.")

@interview_router.get("/video/{interview_id}/download")
async def download_interview_video(interview_id: int, optimize: bool = False):
    """
    면접 영상 다운로드 엔드포인트.
    스트리밍과 달리 Range 헤더를 무시하고 전체 파일을 다운로드합니다.
    optimize=true 시 시간 탐색에 최적화된 파일로 변환하여 제공합니다.
    """
    try:
        # 1. DB에서 영상 정보 조회
        interview_logger.info(f"📥 다운로드 요청 수신: interview_id={interview_id}, optimize={optimize}")
        media_res = supabase_client.client.from_("media_files") \
            .select("s3_key, file_name, file_size") \
            .eq("interview_id", interview_id) \
            .eq("file_type", "video") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if not media_res.data:
            interview_logger.warning(f"⚠️ 다운로드할 영상 파일을 DB에서 찾을 수 없음: interview_id={interview_id}")
            raise HTTPException(status_code=404, detail="해당 면접의 영상 파일을 DB에서 찾을 수 없습니다.")

        video_file = media_res.data[0]
        s3_key = video_file["s3_key"]
        file_name = video_file.get("file_name", f"interview_{interview_id}_video.webm")
        file_size = video_file.get("file_size")
        interview_logger.info(f"✅ 다운로드 DB 조회 성공. S3 Key: {s3_key}, File Name: {file_name}")

        # 2. S3 클라이언트 설정
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        s3_client = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name='ap-northeast-2')
        bucket_name = 'betago-s3'

        # 3. S3에서 전체 파일 가져오기
        s3_object = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        
        if optimize:
                        # FFmpeg 최적화 적용
            interview_logger.info("🔧 FFmpeg 최적화 적용 중...")
            from services.video_optimizer import VideoOptimizer
            
            if not VideoOptimizer.is_ffmpeg_available():
                interview_logger.warning("FFmpeg를 찾을 수 없어 원본 파일로 제공합니다")
                streaming_content = s3_object['Body']
                optimized_file_name = file_name
            else:
                import tempfile
                
                # 최적화된 파일을 위한 임시 파일 생성
                file_extension = file_name.split('.')[-1] if '.' in file_name else 'webm'
                optimized_file_name = file_name.replace(f'.{file_extension}', f'_optimized.{file_extension}')
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_output:
                    temp_output_path = temp_output.name
                
                try:
                    # FFmpeg로 최적화 수행
                    optimization_success = VideoOptimizer.optimize_for_seeking(
                        s3_object['Body'], 
                        temp_output_path, 
                        file_extension
                    )
                    
                    if optimization_success and os.path.exists(temp_output_path):
                        interview_logger.info("✅ FFmpeg 최적화 완료")
                        
                        # 최적화된 파일을 메모리로 읽어서 스트림으로 변환
                        import io
                        optimized_data = io.BytesIO()
                        with open(temp_output_path, 'rb') as f:
                            optimized_data.write(f.read())
                        optimized_data.seek(0)
                        
                        streaming_content = optimized_data
                        
                        # 최적화된 파일 크기 업데이트
                        file_size = os.path.getsize(temp_output_path)
                    else:
                        interview_logger.warning("FFmpeg 최적화 실패, 원본 파일로 제공합니다")
                        # S3 객체를 다시 가져와야 함 (스트림이 이미 읽혔으므로)
                        s3_object = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
                        streaming_content = s3_object['Body']
                        optimized_file_name = file_name
                        
                except Exception as e:
                    interview_logger.error(f"최적화 중 오류: {e}")
                    # S3 객체를 다시 가져와야 함
                    s3_object = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
                    streaming_content = s3_object['Body']
                    optimized_file_name = file_name
                finally:
                    # 임시 파일 정리
                    if os.path.exists(temp_output_path):
                        try:
                            os.unlink(temp_output_path)
                        except Exception as cleanup_error:
                            interview_logger.warning(f"임시 파일 정리 실패: {cleanup_error}")
        else:
            # 원본 파일 그대로 제공
            streaming_content = s3_object['Body']
            optimized_file_name = file_name

        # 4. 다운로드용 응답 헤더 설정
        response_headers = {
            "Content-Disposition": f'attachment; filename="{optimized_file_name}"',
            "Cache-Control": "no-cache",
            "Content-Description": "File Transfer"
        }
        if file_size:
            response_headers["Content-Length"] = str(file_size)

        interview_logger.info(f"✅ 다운로드 시작: {optimized_file_name}")
        return StreamingResponse(
            streaming_content, 
            media_type="application/octet-stream",  # 다운로드 강제
            headers=response_headers
        )

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        interview_logger.error(f"S3 다운로드 오류 (interview_id: {interview_id}): {error_code}")
        if error_code == 'NoSuchKey':
            raise HTTPException(status_code=404, detail=f"S3에 해당 파일이 없습니다: {s3_key}")
        else:
            raise HTTPException(status_code=500, detail=f"S3 처리 오류: {error_code}")

    except HTTPException:
        # 이미 처리된 HTTPException은 그대로 전달
        raise
    except Exception as e:
        interview_logger.error(f"영상 다운로드 중 알 수 없는 오류 (interview_id: {interview_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="영상 다운로드 중 서버 오류가 발생했습니다.")

@interview_router.post("/memo")
async def update_memo(memo_update: MemoUpdateRequest):
    """
    Updates the memo field in the history_detail table.
    """
    try:
        response = supabase_client.client.from_("history_detail").update(
            {"memo": memo_update.memo}
        ).eq("interview_id", memo_update.interview_id).eq(
            "question_index", memo_update.question_index
        ).eq(
            "who", memo_update.who
        ).execute()

        if response.data:
            interview_logger.info(f"메모 업데이트 성공: interview_id={memo_update.interview_id}, question_index={memo_update.question_index}, who={memo_update.who}")
            return {"message": "메모가 성공적으로 업데이트되었습니다."}
        else:
            interview_logger.warning(f"메모 업데이트 실패: 해당 항목을 찾을 수 없음. interview_id={memo_update.interview_id}, question_index={memo_update.question_index}, who={memo_update.who}")
            raise HTTPException(status_code=404, detail="해당 면접 기록을 찾을 수 없습니다.")

    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"메모 업데이트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"메모 업데이트 중 오류 발생: {str(e)}")

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
    """음성 파일을 OpenAI Whisper로 텍스트 변환 후 파일 삭제"""
    # 파일 유효성 검사
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="음성 파일이 필요합니다.")
    
    # 지원하는 오디오 형식 확인
    allowed_extensions = ['.wav', '.mp3', '.m4a', '.webm', '.ogg', '.flac']
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(allowed_extensions)}"
        )
    
    # OpenAI API 키 확인
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다.")
    
    temp_file_path = None
    try:
        # 임시 파일로 음성 데이터 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        interview_logger.info(f"🎙️ STT 처리 시작: {file.filename} ({len(content)} bytes)")
        interview_logger.info(f"📄 파일 정보: content_type={file.content_type}, filename={file.filename}")
        
        # OpenAI Whisper API 호출
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        # 파일을 한 번에 읽어서 메모리에 저장
        with open(temp_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
            
        interview_logger.info(f"📊 오디오 데이터 크기: {len(audio_data)} bytes")
        
        form_data = aiohttp.FormData()
        form_data.add_field('file', audio_data, filename=file.filename, content_type=file.content_type or 'audio/webm')
        form_data.add_field('model', 'whisper-1')
        form_data.add_field('response_format', 'json')
        # 언어를 자동 감지로 변경 (더 정확할 수 있음)
        # form_data.add_field('language', 'ko')  # 한국어 강제 설정 제거
        form_data.add_field('temperature', '0')  # 일관성 있는 결과를 위해 temperature 0 설정
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                data=form_data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    interview_logger.error(f"❌ Whisper API 오류: {response.status} - {error_text}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"STT API 오류: {error_text}"
                    )
                
                result = await response.json()
                transcribed_text = result.get('text', '').strip()
                
                # 전체 Whisper API 응답 로깅
                interview_logger.info(f"🤖 Whisper API 전체 응답: {result}")
                interview_logger.info(f"📝 추출된 텍스트: '{transcribed_text}'")
        
        return STTResponse(
            text=transcribed_text,
            confidence=1.0,  # Whisper는 confidence score를 제공하지 않으므로 기본값
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"❌ STT 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"STT 처리 중 오류가 발생했습니다: {str(e)}")
    finally:
        # 임시 파일 삭제
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                interview_logger.info(f"🗑️ 임시 음성 파일 삭제 완료: {temp_file_path}")
            except Exception as cleanup_error:
                interview_logger.warning(f"⚠️ 임시 파일 삭제 실패: {cleanup_error}")



# Feedback 모델 임포트
try:
    from llm.feedback.api_models import QuestionRequest, QuestionResponse, PlansRequest, PlansResponse
    from llm.feedback.api_service import InterviewEvaluationService
    
    # 전역 평가 서비스 인스턴스 (싱글톤)
    evaluation_service = InterviewEvaluationService()
    
    @interview_router.post("/feedback/evaluate")
    async def evaluate_interview(request: Union[QuestionRequest, List[QuestionRequest]]):
        """면접 질문-답변 평가 (단일 또는 배치)"""
        try:
            # 단일 요청인지 리스트인지 체크
            if isinstance(request, list):
                # 리스트인 경우 - 배치 처리
                results = []
                for i, req in enumerate(request):
                    interview_logger.info(f"배치 평가 {i+1}/{len(request)}: user_id={req.user_id}, questions={len(req.qa_pairs)}")
                    
                    result = evaluation_service.evaluate_multiple_questions(
                        user_id=req.user_id,
                        qa_pairs=req.qa_pairs,
                        ai_resume_id=req.ai_resume_id,
                        user_resume_id=req.user_resume_id,
                        posting_id=req.posting_id,
                        company_id=req.company_id,
                        position_id=req.position_id
                    )
                    results.append(result)
                
                return {
                    "success": True,
                    "message": f"{len(results)}개 평가 완료",
                    "results": results
                }
            else:
                # 기존 단일 처리 로직 유지
                interview_logger.info(f"면접 평가 요청: user_id={request.user_id}, questions={len(request.qa_pairs)}")
                
                result = evaluation_service.evaluate_multiple_questions(
                    user_id=request.user_id,
                    qa_pairs=request.qa_pairs,
                    ai_resume_id=request.ai_resume_id,
                    user_resume_id=request.user_resume_id,
                    posting_id=request.posting_id,
                    company_id=request.company_id,
                    position_id=request.position_id
                )
                
                return QuestionResponse(**result)
            
        except Exception as e:
            interview_logger.error(f"면접 평가 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"면접 평가 중 오류 발생: {str(e)}")

    @interview_router.post("/feedback/plans", response_model=PlansResponse)
    async def generate_interview_plans(request: PlansRequest):
        """면접 준비 계획 생성"""
        try:
            interview_logger.info(f"면접 계획 생성 요청: interview_id={request.interview_id}")
            
            result = evaluation_service.generate_interview_plans(request.interview_id)
            
            return PlansResponse(**result)
            
        except Exception as e:
            interview_logger.error(f"면접 계획 생성 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"면접 계획 생성 중 오류 발생: {str(e)}")

except ImportError as e:
    interview_logger.warning(f"Feedback 모듈 로드 실패: {e}")
    
    @interview_router.post("/feedback/evaluate")
    async def evaluate_interview_fallback():
        raise HTTPException(status_code=503, detail="면접 평가 서비스를 사용할 수 없습니다.")
    
    @interview_router.post("/feedback/plans")
    async def generate_interview_plans_fallback():
        raise HTTPException(status_code=503, detail="면접 계획 서비스를 사용할 수 없습니다.")

# 🟢 POST /interview/complete – 면접 완료 처리 (비동기)
@interview_router.post("/complete")
async def complete_interview_async(
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    """면접 완료 시 즉시 응답하고 백그라운드에서 피드백 처리"""
    try:
        interview_logger.info(f"🏁 면접 완료 요청: session_id={session_id}, user={current_user.user_id}")
        
        # 백그라운드에서 피드백 처리 스케줄링
        if FEEDBACK_ENABLED:
            background_tasks.add_task(process_feedback_async, session_id, current_user.user_id)
        
        # 즉시 응답 반환
        return {
            "status": "completed",
            "message": "면접이 완료되었습니다. 피드백 처리가 백그라운드에서 진행됩니다.",
            "session_id": session_id,
            "feedback_processing": FEEDBACK_ENABLED
        }
        
    except Exception as e:
        interview_logger.error(f"❌ 면접 완료 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_feedback_async(session_id: str, user_id: int):
    """백그라운드에서 실행되는 피드백 처리"""
    try:
        interview_logger.info(f"🔄 백그라운드 피드백 처리 시작: session_id={session_id}")
        
        if FEEDBACK_ENABLED:
            # 기존 피드백 평가 로직 실행
            request = EvaluationRequest(session_id=session_id)
            evaluation_service.evaluate_interview(request)
            
            interview_logger.info(f"✅ 백그라운드 피드백 처리 완료: session_id={session_id}")
        else:
            interview_logger.warning(f"⚠️ 피드백 서비스 비활성화: session_id={session_id}")
            
    except Exception as e:
        interview_logger.error(f"❌ 백그라운드 피드백 처리 실패: session_id={session_id}, error={str(e)}")

# 🟢 GET /interview/global-stats – 전체 사용자 통계 조회
@interview_router.get("/global-stats")
async def get_global_interview_stats():
    """전체 사용자의 면접 통계를 조회합니다."""
    try:
        # 전체 면접 수 조회
        total_interviews_res = supabase_client.client.from_("interview").select("interview_id", count="exact").execute()
        total_interviews = total_interviews_res.count if total_interviews_res.count else 0
        
        # 전체 평균 점수 계산 (total_feedback에서 점수 추출)
        interviews_with_feedback = supabase_client.client.from_("interview").select("total_feedback").not_.is_("total_feedback", "null").execute()
        
        total_score = 0
        score_count = 0
        
        for interview in interviews_with_feedback.data:
            try:
                if interview.get('total_feedback'):
                    feedback_data = interview['total_feedback']
                    if isinstance(feedback_data, str):
                        import json
                        feedback_data = json.loads(feedback_data)
                    
                    # 점수 추출 로직 (기존과 동일)
                    score = 0
                    if isinstance(feedback_data, dict):
                        if feedback_data.get('user', {}).get('overall_score') is not None:
                            score = feedback_data['user']['overall_score']
                        elif feedback_data.get('overall_score') is not None:
                            score = feedback_data['overall_score']
                        elif feedback_data.get('ai_interviewer', {}).get('overall_score') is not None:
                            score = feedback_data['ai_interviewer']['overall_score']
                    
                    if score > 0:
                        total_score += score
                        score_count += 1
            except:
                continue
        
        global_average_score = round(total_score / score_count) if score_count > 0 else 0
        
        return {
            "total_interviews": total_interviews,
            "global_average_score": global_average_score
        }
        
    except Exception as e:
        interview_logger.error(f"전체 통계 조회 실패: {str(e)}")
        return {
            "total_interviews": 0,
            "global_average_score": 0
        }