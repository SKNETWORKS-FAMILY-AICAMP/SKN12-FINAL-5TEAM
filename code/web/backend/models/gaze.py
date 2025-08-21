# === 김원우 작성 시작 ===
"""
시선 분석 시스템 모델

이 모듈은 시선 분석과 캘리브레이션 관련 데이터 모델을 정의합니다.
MediaPipe 기반 시선 추적과 분석 결과를 구조화합니다.

주요 기능:
- 시선 캘리브레이션 세션 관리
- 시선 분석 작업 및 결과 모델링
- 실시간 시선 데이터 구조화

작성자: 김원우
작성일: 2025-08-12
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum


class CalibrationPhase(str, Enum):
    """캘리브레이션 단계"""
    READY = "ready"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    COMPLETED = "completed"


class CalibrationStatus(str, Enum):
    """캘리브레이션 상태"""
    READY = "ready"
    CALIBRATING = "calibrating"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisTaskStatus(str, Enum):
    """분석 작업 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FaceQuality(str, Enum):
    """얼굴 검출 품질"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class GazeCalibrationSession(BaseModel):
    """시선 캘리브레이션 세션 모델"""
    session_id: str = Field(..., description="캘리브레이션 세션 ID")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    status: CalibrationStatus = Field(CalibrationStatus.READY, description="캘리브레이션 상태")
    current_phase: CalibrationPhase = Field(CalibrationPhase.READY, description="현재 진행 단계")
    progress: float = Field(0.0, description="진행률 (0.0 ~ 1.0)", ge=0.0, le=1.0)
    
    # 캘리브레이션 데이터
    calibration_points: List[Tuple[float, float]] = Field(default_factory=list, description="4점 캘리브레이션 좌표")
    initial_face_size: Optional[float] = Field(None, description="초기 얼굴 크기", ge=0.0)
    allowed_range: Optional[Dict[str, float]] = Field(None, description="허용 시선 범위")
    
    # 수집 상태
    collected_points: Dict[str, int] = Field(default_factory=dict, description="단계별 수집된 포인트 수")
    target_points_per_phase: int = Field(30, description="단계별 목표 포인트 수", gt=0)
    
    # 실시간 피드백
    is_collecting: bool = Field(False, description="데이터 수집 중 여부")
    face_quality: FaceQuality = Field(FaceQuality.GOOD, description="얼굴 검출 품질")
    eye_detected: bool = Field(False, description="눈 검출 여부")
    feedback_message: Optional[str] = Field(None, description="실시간 피드백 메시지")
    
    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")
    started_at: Optional[datetime] = Field(None, description="시작 시간")
    completed_at: Optional[datetime] = Field(None, description="완료 시간")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GazeAnalysisTask(BaseModel):
    """시선 분석 작업 모델"""
    task_id: str = Field(..., description="분석 작업 ID")
    session_id: str = Field(..., description="연관된 캘리브레이션 세션 ID")
    video_url: str = Field(..., description="분석할 동영상 URL")
    
    # 작업 상태
    status: AnalysisTaskStatus = Field(AnalysisTaskStatus.PENDING, description="작업 상태")
    progress: float = Field(0.0, description="분석 진행률 (0.0 ~ 1.0)", ge=0.0, le=1.0)
    current_message: Optional[str] = Field(None, description="현재 진행 상황 메시지")
    
    # 분석 설정
    frame_skip: int = Field(10, description="프레임 스킵 간격", gt=0)
    calibration_points: List[Tuple[float, float]] = Field(..., description="캘리브레이션 기준 좌표")
    initial_face_size: Optional[float] = Field(None, description="기준 얼굴 크기")
    
    # 결과 데이터
    result: Optional[Dict[str, Any]] = Field(None, description="분석 결과")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    
    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now, description="작업 생성 시간")
    started_at: Optional[datetime] = Field(None, description="분석 시작 시간")
    completed_at: Optional[datetime] = Field(None, description="분석 완료 시간")
    analysis_duration: Optional[float] = Field(None, description="분석 소요 시간 (초)")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GazeAnalysisResult(BaseModel):
    """시선 분석 결과 모델"""
    # 종합 점수
    gaze_score: int = Field(..., description="종합 시선 점수 (0-100)", ge=0, le=100)
    
    # 프레임 분석 통계
    total_frames: int = Field(..., description="전체 동영상 프레임 수", ge=0)
    analyzed_frames: int = Field(..., description="분석된 프레임 수", ge=0)
    in_range_frames: int = Field(..., description="범위 내 시선 프레임 수", ge=0)
    in_range_ratio: float = Field(..., description="범위 준수 비율", ge=0.0, le=1.0)
    
    # 세부 점수
    jitter_score: int = Field(..., description="시선 안정성 점수 (0-100)", ge=0, le=100)
    compliance_score: int = Field(..., description="범위 준수 점수 (0-100)", ge=0, le=100)
    
    # 정성 평가
    stability_rating: str = Field(..., description="안정성 등급 (excellent/good/fair/poor)")
    feedback: str = Field(..., description="종합 피드백 메시지")
    
    # 상세 데이터
    gaze_points: List[Tuple[float, float]] = Field(..., description="시선 포인트 좌표 리스트")
    allowed_range: Dict[str, float] = Field(..., description="허용 시선 범위")
    calibration_points: List[Tuple[float, float]] = Field(..., description="캘리브레이션 기준 좌표")
    
    # 메타데이터
    analysis_duration: float = Field(..., description="분석 소요 시간 (초)", gt=0)
    algorithm_version: str = Field("1.0", description="분석 알고리즘 버전")
    
    @validator('analyzed_frames')
    def validate_analyzed_frames(cls, v, values):
        """분석된 프레임 수가 전체 프레임 수를 초과하지 않도록 검증"""
        if 'total_frames' in values and v > values['total_frames']:
            raise ValueError('분석된 프레임 수가 전체 프레임 수를 초과할 수 없습니다')
        return v
    
    @validator('in_range_frames')
    def validate_in_range_frames(cls, v, values):
        """범위 내 프레임 수가 분석된 프레임 수를 초과하지 않도록 검증"""
        if 'analyzed_frames' in values and v > values['analyzed_frames']:
            raise ValueError('범위 내 프레임 수가 분석된 프레임 수를 초과할 수 없습니다')
        return v


class FrameFeedback(BaseModel):
    """실시간 프레임 피드백 모델"""
    status: str = Field(..., description="프레임 처리 상태")
    phase: CalibrationPhase = Field(..., description="현재 캘리브레이션 단계")
    eye_detected: bool = Field(..., description="눈 검출 여부")
    face_quality: FaceQuality = Field(..., description="얼굴 검출 품질")
    feedback: str = Field(..., description="실시간 피드백 메시지")
    
    # 수집 진행 상황
    collected_count: Optional[int] = Field(None, description="수집된 포인트 수", ge=0)
    target_count: Optional[int] = Field(None, description="목표 포인트 수", gt=0)
    remaining_time: Optional[int] = Field(None, description="남은 시간 (초)", ge=0)
    collection_progress: Optional[float] = Field(None, description="수집 진행률", ge=0.0, le=1.0)
    
    # 실시간 시선 데이터
    current_gaze_point: Optional[Tuple[float, float]] = Field(None, description="현재 시선 좌표")
    face_size: Optional[float] = Field(None, description="현재 얼굴 크기", ge=0.0)
    
    class Config:
        use_enum_values = True


class GazeSessionStats(BaseModel):
    """시선 분석 세션 통계 모델"""
    total_sessions: int = Field(..., description="전체 세션 수", ge=0)
    completed_sessions: int = Field(..., description="완료된 세션 수", ge=0)
    failed_sessions: int = Field(..., description="실패한 세션 수", ge=0)
    
    average_completion_time: Optional[float] = Field(None, description="평균 완료 시간 (초)", ge=0.0)
    average_gaze_score: Optional[float] = Field(None, description="평균 시선 점수", ge=0.0, le=100.0)
    
    # 성능 지표
    success_rate: float = Field(..., description="성공률", ge=0.0, le=1.0)
    data_quality_score: Optional[float] = Field(None, description="데이터 품질 점수", ge=0.0, le=1.0)
    
    # 시간 통계
    first_session: Optional[datetime] = Field(None, description="첫 세션 시간")
    last_session: Optional[datetime] = Field(None, description="마지막 세션 시간")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GazeConfig(BaseModel):
    """시선 분석 설정 모델"""
    # MediaPipe 설정
    refine_landmarks: bool = Field(True, description="세밀한 랜드마크 검출 활성화")
    max_num_faces: int = Field(1, description="최대 검출 얼굴 수", gt=0)
    min_detection_confidence: float = Field(0.5, description="얼굴 검출 신뢰도", ge=0.0, le=1.0)
    min_tracking_confidence: float = Field(0.5, description="추적 지속 신뢰도", ge=0.0, le=1.0)
    
    # 분석 설정
    frame_skip_mode: str = Field("balanced", description="프레임 스킵 모드", regex=r"^(high_accuracy|balanced|high_performance)$")
    jitter_weight: float = Field(0.4, description="안정성 가중치", ge=0.0, le=1.0)
    compliance_weight: float = Field(0.6, description="준수도 가중치", ge=0.0, le=1.0)
    
    # 임계값 설정
    excellent_threshold: float = Field(0.5, description="우수 등급 임계값", ge=0.0)
    good_threshold: float = Field(5.0, description="양호 등급 임계값", ge=0.0)
    fair_threshold: float = Field(20.0, description="보통 등급 임계값", ge=0.0)
    poor_threshold: float = Field(50.0, description="개선필요 등급 임계값", ge=0.0)
    
    @validator('compliance_weight')
    def validate_weights_sum(cls, v, values):
        """가중치 합계가 1.0인지 검증"""
        jitter_weight = values.get('jitter_weight', 0.0)
        if abs(jitter_weight + v - 1.0) > 0.01:
            raise ValueError('jitter_weight와 compliance_weight의 합은 1.0이어야 합니다')
        return v
# === 김원우 작성 끝 ===