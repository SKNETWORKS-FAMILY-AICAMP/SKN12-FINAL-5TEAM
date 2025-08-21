"""
시선 분석 FastAPI 엔드포인트 (개선된 버전)
S3 직접 접근 및 인증 강화
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Form
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple
import uuid
from datetime import datetime
import os
import sys

# --- 의존성 주입 ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .gaze_calibration import calibration_manager
from .gaze_analysis import gaze_analyzer, GazeAnalysisResult as GazeAnalyzerResultData
from services.auth_service import AuthService, security
from services.supabase_client import get_user_supabase_client

# --- 초기화 ---
auth_service = AuthService()
router = APIRouter(prefix="/test/gaze", tags=["Gaze Analysis"])
analysis_tasks: Dict[str, Dict] = {}
BUCKET_NAME = 'betago-s3'

# --- Pydantic 모델 ---

class CalibrationStartRequest(BaseModel):
    user_id: Optional[int] = None

class CalibrationStartResponse(BaseModel):
    session_id: str
    status: str
    message: str

class CalibrationStatusResponse(BaseModel):
    session_id: str
    current_phase: str
    progress: float
    instructions: str
    feedback: Optional[str] = None

class CalibrationResult(BaseModel):
    session_id: str
    calibration_points: List[Tuple[float, float]]
    initial_face_size: Optional[float] = None # 🚀 추가
    allowed_range: Optional[Dict[str, float]] = None # 🎯 허용 범위 추가

class VideoAnalysisRequest(BaseModel):
    video_url: str
    session_id: str

class VideoAnalysisResponse(BaseModel):
    task_id: str
    status: str
    message: str

class GazeAnalysisResult(BaseModel):
    gaze_score: int
    total_frames: int
    analyzed_frames: int
    in_range_frames: int
    in_range_ratio: float
    jitter_score: int
    compliance_score: int
    stability_rating: str
    feedback: str
    gaze_points: List[Tuple[float, float]]
    analysis_duration: float
    allowed_range: Dict[str, float]
    calibration_points: List[Tuple[float, float]]

class AnalysisStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[GazeAnalysisResult] = None
    error: Optional[str] = None
    message: Optional[str] = None

# --- 백그라운드 분석 작업 ---

async def run_video_analysis(task_id: str, bucket: str, key: str, calibration_points: List[Tuple[float, float]], initial_face_size: Optional[float]): # 🚀 initial_face_size 추가
    """
    백그라운드에서 S3의 동영상을 직접 분석 (URL 변환 없음)
    """
    try:
        print(f"🚀 [ANALYSIS] Task ID: {task_id} - 분석 시작")
        print(f"   - S3 Path: s3://{bucket}/{key}")
        start_time = datetime.now()
        
        analysis_tasks[task_id]['progress'] = 0.1
        analysis_tasks[task_id]['message'] = "분석 엔진 초기화 중..."

        result: GazeAnalyzerResultData = gaze_analyzer.analyze_video(
            bucket=bucket,
            key=key,
            calibration_points=calibration_points,
            initial_face_size=initial_face_size, # 🚀 전달
            frame_skip=10
        )
        
        end_time = datetime.now()
        analysis_duration = (end_time - start_time).total_seconds()
        
        print(f"✅ [ANALYSIS] Task ID: {task_id} - 분석 완료 ({analysis_duration:.2f}초)")

        MIN_ANALYZED_FRAMES = 30
        if result.analyzed_frames < MIN_ANALYZED_FRAMES:
            print(f"⚠️ [ANALYSIS] 데이터 부족: 분석된 프레임 {result.analyzed_frames}개 < 최소 기준 {MIN_ANALYZED_FRAMES}개")
            raise ValueError(f"분석에 사용된 데이터가 너무 적습니다({result.analyzed_frames} 프레임). 10초 이상 선명한 영상을 다시 녹화해주세요.")
        
        analysis_tasks[task_id].update({
            'status': 'completed',
            'progress': 1.0,
            'message': '분석이 성공적으로 완료되었습니다.',
            'completed_at': end_time,
            'result': GazeAnalysisResult(
                gaze_score=result.gaze_score,
                total_frames=result.total_frames,
                analyzed_frames=result.analyzed_frames,
                in_range_frames=result.in_range_frames,
                in_range_ratio=result.in_range_ratio,
                jitter_score=result.jitter_score,
                compliance_score=result.compliance_score,
                stability_rating=result.stability_rating,
                feedback=result.feedback,
                gaze_points=result.gaze_points,
                analysis_duration=analysis_duration,
                allowed_range=result.allowed_range,
                calibration_points=result.calibration_points
            )
        })

    except Exception as e:
        import traceback
        print(f"❌ [ANALYSIS] Task ID: {task_id} - 분석 실패")
        traceback.print_exc()
        
        analysis_tasks[task_id].update({
            'status': 'failed',
            'error': str(e),
            'failed_at': datetime.now()
        })

# --- API 엔드포인트 ---

@router.post("/analyze", response_model=VideoAnalysisResponse)
async def analyze_gaze(
    request: VideoAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        if not request.video_url.startswith('http://127.0.0.1:8000/video/play/'):
            raise HTTPException(status_code=400, detail="유효하지 않은 video_url 형식입니다.")
        media_id = request.video_url.split('/')[-1]

        calib_result = calibration_manager.get_calibration_result(request.session_id)
        if not calib_result or len(calib_result.get('calibration_points', [])) != 4:
            raise HTTPException(status_code=404, detail="유효한 캘리브레이션 데이터를 찾을 수 없습니다.")
        calibration_points = calib_result['calibration_points']
        initial_face_size = calib_result.get('initial_face_size') # 🚀 추출

        supabase = get_user_supabase_client(credentials.credentials)
        db_result = supabase.table('media_files').select('s3_key').eq('media_id', media_id).eq('user_id', current_user.user_id).execute()

        if not db_result.data:
            raise HTTPException(status_code=404, detail=f"미디어 파일(ID: {media_id})을 찾을 수 없거나 접근 권한이 없습니다.")
        s3_key = db_result.data[0]['s3_key']

        task_id = str(uuid.uuid4())
        analysis_tasks[task_id] = {
            'task_id': task_id,
            'status': 'processing',
            'progress': 0.0,
            'message': '분석 작업을 대기열에 추가했습니다.',
            'started_at': datetime.now()
        }

        background_tasks.add_task(
            run_video_analysis,
            task_id,
            BUCKET_NAME,
            s3_key,
            calibration_points,
            initial_face_size # 🚀 전달
        )

        return VideoAnalysisResponse(
            task_id=task_id,
            status="processing",
            message="동영상 시선 분석이 시작되었습니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 시작 오류: {str(e)}")


@router.get("/analyze/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(task_id: str):
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    
    task = analysis_tasks[task_id]
    return AnalysisStatusResponse(**task)

# --- 캘리브레이션 엔드포인트 ---

@router.post("/calibration/start", response_model=CalibrationStartResponse)
async def start_calibration(request: CalibrationStartRequest):
    session_id = calibration_manager.create_session(request.user_id)
    calibration_manager.start_calibration(session_id)
    return CalibrationStartResponse(
        session_id=session_id,
        status="started",
        message="캘리브레이션이 시작되었습니다."
    )

@router.get("/calibration/status/{session_id}", response_model=CalibrationStatusResponse)
async def get_calibration_status(session_id: str):
    status = calibration_manager.get_session_status(session_id)
    if status is None:
        raise HTTPException(status_code=404, detail="캘리브레이션 세션을 찾을 수 없습니다.")
    return CalibrationStatusResponse(**status)

@router.post("/calibration/frame/{session_id}")
async def process_calibration_frame(session_id: str, frame_data: str = Form(...)):
    if ',' in frame_data:
        frame_data = frame_data.split(',')[1]
    
    import base64
    import numpy as np
    import cv2
    
    try:
        image_bytes = base64.b64decode(frame_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(status_code=400, detail="Failed to decode frame")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 frame data")

    result = calibration_manager.process_frame(session_id, frame)
    if result is None:
        raise HTTPException(status_code=404, detail="Calibration session not found")
    return result

@router.get("/calibration/result/{session_id}", response_model=CalibrationResult)
async def get_calibration_result(session_id: str):
    print(f"✅ [DEBUG] get_calibration_result 함수 호출됨. 찾는 세션 ID:  {session_id}")
    print(f"✅ [DEBUG] 현재 calibration_manager가 아는 세션 목록:  {list(calibration_manager.sessions.keys())}")
    result = calibration_manager.get_calibration_result(session_id)
    if result is None or not result.get('calibration_points'):
        raise HTTPException(status_code=404, detail="캘리브레이션 결과를 찾을 수 없거나 아직 완료되지 않았습니다.")
    
    # 허용 범위 계산 추가
    calibration_points = result.get('calibration_points', [])
    print(f"🎯 [DEBUG] Calibration points count: {len(calibration_points)}")
    print(f"🎯 [DEBUG] Calibration points: {calibration_points}")
    
    if len(calibration_points) == 4:
        # GazeAnalyzer의 범위 계산 로직 재사용
        allowed_range = gaze_analyzer.calculate_allowed_gaze_range(calibration_points)
        result['allowed_range'] = allowed_range
        print(f"🎯 [DEBUG] Calculated allowed range: {allowed_range}")
    else:
        print(f"🎯 [DEBUG] Not enough calibration points for range calculation")
    
    return CalibrationResult(**result)

def get_gaze_router():
    return router
