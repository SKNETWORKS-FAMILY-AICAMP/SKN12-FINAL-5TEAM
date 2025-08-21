# === 김원우 작성 시작 ===
"""
시선 분석 시스템 스키마

이 모듈은 시선 분석 관련 API의 요청/응답 스키마를 정의합니다.
기존 test/gaze_api.py의 Pydantic 모델들을 표준 스키마 구조로 이전했습니다.

주요 기능:
- 캘리브레이션 API 스키마
- 시선 분석 API 스키마
- 실시간 피드백 스키마
- 결과 데이터 구조화

작성자: 김원우
작성일: 2025-08-12
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from uuid import UUID


class CalibrationStartRequest(BaseModel):
    """캘리브레이션 시작 요청 스키마"""
    user_id: Optional[str] = Field(None, description="사용자 ID (선택적)")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user123"
            }
        }


class CalibrationStartResponse(BaseModel):
    """캘리브레이션 시작 응답 스키마"""
    session_id: str = Field(..., description="생성된 세션 ID")
    status: str = Field(..., description="캘리브레이션 상태")
    message: str = Field(..., description="응답 메시지")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "cal_uuid4_generated_id",
                "status": "started",
                "message": "캘리브레이션이 시작되었습니다."
            }
        }


class CalibrationStatusResponse(BaseModel):
    """캘리브레이션 상태 응답 스키마"""
    session_id: str = Field(..., description="세션 ID")
    current_phase: str = Field(..., description="현재 진행 단계")
    progress: float = Field(..., description="진행률 (0.0 ~ 1.0)", ge=0.0, le=1.0)
    instructions: str = Field(..., description="사용자 안내 메시지")
    feedback: Optional[str] = Field(None, description="실시간 피드백")
    
    # 수집 상태 정보
    is_collecting: Optional[bool] = Field(None, description="데이터 수집 중 여부")
    collected_points: Optional[Dict[str, int]] = Field(None, description="단계별 수집된 포인트")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "cal_uuid4_generated_id",
                "current_phase": "top_left",
                "progress": 0.25,
                "instructions": "화면 좌상단 모서리를 응시하세요",
                "feedback": "눈 검출 성공",
                "is_collecting": True,
                "collected_points": {
                    "top_left": 15,
                    "top_right": 0,
                    "bottom_left": 0,
                    "bottom_right": 0
                }
            }
        }


class CalibrationResult(BaseModel):
    """캘리브레이션 결과 스키마"""
    session_id: str = Field(..., description="세션 ID")
    calibration_points: List[Tuple[float, float]] = Field(..., description="4점 캘리브레이션 좌표")
    initial_face_size: Optional[float] = Field(None, description="초기 얼굴 크기", ge=0.0)
    allowed_range: Optional[Dict[str, float]] = Field(None, description="허용 시선 범위")
    
    @validator('calibration_points')
    def validate_calibration_points(cls, v):
        """캘리브레이션 포인트가 정확히 4개인지 확인"""
        if len(v) != 4:
            raise ValueError('캘리브레이션 포인트는 정확히 4개여야 합니다')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "cal_uuid4_generated_id",
                "calibration_points": [
                    [100.0, 100.0],   # top_left
                    [500.0, 100.0],   # top_right
                    [100.0, 400.0],   # bottom_left
                    [500.0, 400.0]    # bottom_right
                ],
                "initial_face_size": 150.5,
                "allowed_range": {
                    "left": 80.0,
                    "right": 520.0,
                    "top": 80.0,
                    "bottom": 420.0
                }
            }
        }


class VideoAnalysisRequest(BaseModel):
    """동영상 시선 분석 요청 스키마"""
    video_url: str = Field(..., description="분석할 동영상 URL", min_length=1)
    session_id: str = Field(..., description="캘리브레이션 세션 ID", min_length=1)
    
    # 선택적 분석 설정
    frame_skip: Optional[int] = Field(10, description="프레임 스킵 간격", gt=0, le=30)
    
    @validator('video_url')
    def validate_video_url(cls, v):
        """비디오 URL 형식 검증"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('유효한 HTTP/HTTPS URL이어야 합니다')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "video_url": "http://127.0.0.1:8000/video/play/uuid4_media_id",
                "session_id": "cal_uuid4_generated_id",
                "frame_skip": 10
            }
        }


class VideoAnalysisResponse(BaseModel):
    """동영상 시선 분석 응답 스키마"""
    task_id: str = Field(..., description="분석 작업 ID")
    status: str = Field(..., description="작업 상태")
    message: str = Field(..., description="응답 메시지")
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "task_uuid4_generated_id",
                "status": "processing",
                "message": "동영상 시선 분석이 시작되었습니다."
            }
        }


class GazeAnalysisResult(BaseModel):
    """시선 분석 결과 스키마"""
    # 종합 점수
    gaze_score: int = Field(..., description="종합 시선 점수 (0-100)", ge=0, le=100)
    
    # 프레임 분석 통계
    total_frames: int = Field(..., description="전체 동영상 프레임 수", ge=0)
    analyzed_frames: int = Field(..., description="분석된 프레임 수", ge=0)
    in_range_frames: int = Field(..., description="범위 내 시선 프레임 수", ge=0)
    in_range_ratio: float = Field(..., description="범위 준수 비율 (0.0 ~ 1.0)", ge=0.0, le=1.0)
    
    # 세부 점수
    jitter_score: int = Field(..., description="시선 안정성 점수 (0-100)", ge=0, le=100)
    compliance_score: int = Field(..., description="범위 준수 점수 (0-100)", ge=0, le=100)
    
    # 정성 평가
    stability_rating: str = Field(..., description="안정성 등급")
    feedback: str = Field(..., description="종합 피드백 메시지")
    
    # 상세 데이터
    gaze_points: List[Tuple[float, float]] = Field(..., description="시선 포인트 좌표 리스트")
    analysis_duration: float = Field(..., description="분석 소요 시간 (초)", gt=0)
    allowed_range: Dict[str, float] = Field(..., description="허용 시선 범위")
    calibration_points: List[Tuple[float, float]] = Field(..., description="캘리브레이션 기준 좌표")
    
    class Config:
        schema_extra = {
            "example": {
                "gaze_score": 78,
                "total_frames": 1500,
                "analyzed_frames": 150,
                "in_range_frames": 120,
                "in_range_ratio": 0.8,
                "jitter_score": 85,
                "compliance_score": 75,
                "stability_rating": "good",
                "feedback": "전반적으로 안정적인 시선을 유지했습니다. 집중도를 조금 더 높이면 좋겠습니다.",
                "gaze_points": [[300.0, 200.0], [305.0, 198.0], [298.0, 205.0]],
                "analysis_duration": 45.2,
                "allowed_range": {
                    "left": 80.0,
                    "right": 520.0,
                    "top": 80.0,
                    "bottom": 420.0
                },
                "calibration_points": [
                    [100.0, 100.0],
                    [500.0, 100.0],
                    [100.0, 400.0],
                    [500.0, 400.0]
                ]
            }
        }


class AnalysisStatusResponse(BaseModel):
    """분석 상태 조회 응답 스키마"""
    task_id: str = Field(..., description="작업 ID")
    status: str = Field(..., description="작업 상태 (processing/completed/failed)")
    progress: Optional[float] = Field(None, description="진행률 (0.0 ~ 1.0)", ge=0.0, le=1.0)
    result: Optional[GazeAnalysisResult] = Field(None, description="분석 결과 (완료시)")
    error: Optional[str] = Field(None, description="오류 메시지 (실패시)")
    message: Optional[str] = Field(None, description="현재 상태 메시지")
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "task_uuid4_generated_id",
                "status": "processing",
                "progress": 0.65,
                "result": None,
                "error": None,
                "message": "MediaPipe로 시선 추적 중..."
            }
        }


class FrameFeedbackResponse(BaseModel):
    """실시간 프레임 피드백 응답 스키마"""
    status: str = Field(..., description="프레임 처리 상태")
    phase: str = Field(..., description="현재 캘리브레이션 단계")
    eye_detected: bool = Field(..., description="눈 검출 여부")
    face_quality: str = Field(..., description="얼굴 검출 품질 (good/fair/poor)")
    feedback: str = Field(..., description="실시간 피드백 메시지")
    
    # 수집 진행 상황 (선택적)
    collected_count: Optional[int] = Field(None, description="수집된 포인트 수", ge=0)
    target_count: Optional[int] = Field(None, description="목표 포인트 수", gt=0)
    remaining_time: Optional[int] = Field(None, description="남은 시간 (초)", ge=0)
    collection_progress: Optional[float] = Field(None, description="수집 진행률 (0.0 ~ 1.0)", ge=0.0, le=1.0)
    
    class Config:
        schema_extra = {
            "example": {
                "status": "collecting",
                "phase": "top_left",
                "eye_detected": True,
                "face_quality": "good",
                "feedback": "좌상단 모서리를 응시하세요 (15/30)",
                "collected_count": 15,
                "target_count": 30,
                "remaining_time": 5,
                "collection_progress": 0.5
            }
        }


class GazeSessionListRequest(BaseModel):
    """시선 분석 세션 목록 요청 스키마"""
    page: int = Field(1, description="페이지 번호", gt=0)
    page_size: int = Field(20, description="페이지 크기", gt=0, le=100)
    status: Optional[str] = Field(None, description="상태 필터")
    date_from: Optional[datetime] = Field(None, description="시작 날짜")
    date_to: Optional[datetime] = Field(None, description="종료 날짜")


class GazeSessionListResponse(BaseModel):
    """시선 분석 세션 목록 응답 스키마"""
    sessions: List[Dict[str, Any]] = Field(..., description="세션 목록")
    total_count: int = Field(..., description="전체 세션 수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기")
    total_pages: int = Field(..., description="전체 페이지 수")


class GazeStatsResponse(BaseModel):
    """시선 분석 통계 응답 스키마"""
    total_sessions: int = Field(..., description="전체 세션 수", ge=0)
    completed_sessions: int = Field(..., description="완료된 세션 수", ge=0)
    failed_sessions: int = Field(..., description="실패한 세션 수", ge=0)
    success_rate: float = Field(..., description="성공률 (0.0 ~ 1.0)", ge=0.0, le=1.0)
    
    average_gaze_score: Optional[float] = Field(None, description="평균 시선 점수", ge=0.0, le=100.0)
    average_completion_time: Optional[float] = Field(None, description="평균 완료 시간 (초)", ge=0.0)
    
    # 시간 범위
    period_start: Optional[datetime] = Field(None, description="통계 시작 시간")
    period_end: Optional[datetime] = Field(None, description="통계 종료 시간")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "total_sessions": 150,
                "completed_sessions": 135,
                "failed_sessions": 15,
                "success_rate": 0.9,
                "average_gaze_score": 76.5,
                "average_completion_time": 42.3,
                "period_start": "2025-08-01T00:00:00Z",
                "period_end": "2025-08-12T23:59:59Z"
            }
        }


class ErrorResponse(BaseModel):
    """시선 분석 오류 응답 스키마"""
    error: str = Field(..., description="오류 코드")
    message: str = Field(..., description="오류 메시지")
    details: Optional[Dict[str, Any]] = Field(None, description="상세 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="오류 발생 시간")
    
    # 시선 분석 특화 오류 정보
    session_id: Optional[str] = Field(None, description="관련 세션 ID")
    task_id: Optional[str] = Field(None, description="관련 작업 ID")
    phase: Optional[str] = Field(None, description="오류 발생 단계")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "error": "CALIBRATION_FAILED",
                "message": "캘리브레이션 데이터가 부족합니다",
                "details": {
                    "collected_points": 15,
                    "required_points": 30,
                    "phase": "top_left"
                },
                "timestamp": "2025-08-12T10:30:00Z",
                "session_id": "cal_uuid4_generated_id",
                "task_id": None,
                "phase": "top_left"
            }
        }


class CalibrationQualityCheck(BaseModel):
    """캘리브레이션 품질 체크 스키마"""
    session_id: str = Field(..., description="세션 ID")
    quality_score: float = Field(..., description="품질 점수 (0.0 ~ 1.0)", ge=0.0, le=1.0)
    is_valid: bool = Field(..., description="캘리브레이션 유효성")
    issues: List[str] = Field(default_factory=list, description="발견된 문제점들")
    recommendations: List[str] = Field(default_factory=list, description="개선 권장사항들")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "cal_uuid4_generated_id",
                "quality_score": 0.85,
                "is_valid": True,
                "issues": ["우하단 데이터 약간 부족"],
                "recommendations": ["조명을 밝게 하고 다시 시도해보세요"]
            }
        }

class GazeAnalysisResponse(BaseModel):
    """시선 분석 결과 응답 스키마"""
    gaze_id: UUID
    interview_id: int
    user_id: int
    gaze_score: float
    jitter_score: float
    compliance_score: float
    stability_rating: str
    created_at: datetime
    gaze_points: Optional[Any] = None
    calibration_points: Optional[Any] = None
    video_metadata: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class GazeAnalysisTriggerRequest(BaseModel):
    """
    시선 분석 트리거 요청 스키마
    
    프론트엔드에서 S3 업로드 완료 후 백엔드에 시선 분석을 요청할 때 사용됩니다.
    """
    session_id: str = Field(..., description="면접 세션 ID", min_length=1)
    s3_key: str = Field(..., description="S3에 업로드된 영상의 키 (경로)", min_length=1)
    calibration_data: CalibrationResult = Field(..., description="캘리브레이션 결과 데이터")
    media_id: str = Field(..., description="임시 미디어 ID (Pre-signed URL 응답에서 받은 값)", min_length=1)
    
    @validator('s3_key')
    def validate_s3_key_format(cls, v):
        """S3 키 형식 검증"""
        if not v.startswith('gaze-videos/'):
            raise ValueError('S3 키는 gaze-videos/로 시작해야 합니다')
        return v
    
    @validator('calibration_data')
    def validate_calibration_data(cls, v):
        """캘리브레이션 데이터 검증"""
        if not v.calibration_points or len(v.calibration_points) != 4:
            raise ValueError('캘리브레이션 포인트는 정확히 4개여야 합니다')
        if v.initial_face_size is not None and v.initial_face_size <= 0:
            raise ValueError('초기 얼굴 크기는 0보다 커야 합니다')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "comp_abc123def456",
                "s3_key": "gaze-videos/user123/comp_abc123def456/gaze_video_20250818_123456.webm",
                "calibration_data": {
                    "session_id": "cal_uuid4_generated_id",
                    "calibration_points": [
                        [100.0, 100.0],
                        [500.0, 100.0],
                        [100.0, 400.0],
                        [500.0, 400.0]
                    ],
                    "initial_face_size": 150.5,
                    "point_details": {},
                    "collection_stats": {},
                    "completed_at": 1692345678,
                    "allowed_range": {
                        "left_bound": 80.0,
                        "right_bound": 520.0,
                        "top_bound": 80.0,
                        "bottom_bound": 420.0
                    }
                },
                "media_id": "temp_uuid4_generated_id"
            }
        }


class GazeAnalysisTriggerResponse(BaseModel):
    """
    시선 분석 트리거 응답 스키마
    
    시선 분석 요청에 대한 응답으로 task_id를 반환하여 진행률 추적이 가능합니다.
    """
    task_id: str = Field(..., description="분석 작업 ID", min_length=1)
    status: str = Field(..., description="작업 상태", min_length=1)
    message: Optional[str] = Field(None, description="응답 메시지")
    
    @validator('status')
    def validate_status(cls, v):
        """상태 값 검증"""
        allowed_statuses = ['started', 'processing', 'completed', 'failed']
        if v not in allowed_statuses:
            raise ValueError(f'상태는 {allowed_statuses} 중 하나여야 합니다')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "task_uuid4_generated_id",
                "status": "started",
                "message": "시선 분석이 시작되었습니다"
            }
        }

# === 김원우 작성 끝 ===