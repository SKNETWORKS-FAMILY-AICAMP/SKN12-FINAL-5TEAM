# === 김원우 작성 시작 ===
"""
S3 미디어 파일 관리 스키마

이 모듈은 S3 미디어 파일 관련 API의 요청/응답 스키마를 정의합니다.
Pydantic을 사용하여 데이터 유효성 검증과 직렬화를 처리합니다.

주요 기능:
- API 요청 데이터 유효성 검증
- 응답 데이터 구조 정의
- 타입 안전성 보장

작성자: 김원우  
작성일: 2025-08-12
"""

from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime


class UploadRequest(BaseModel):
    """미디어 업로드 요청 스키마"""
    interview_id: int = Field(..., description="면접 ID", gt=0)
    file_name: str = Field(..., description="파일명", min_length=1, max_length=255)
    file_type: str = Field("video", description="파일 타입", pattern=r"^(video|audio)$")
    file_size: Optional[int] = Field(None, description="파일 크기 (바이트)", ge=0)
    duration: Optional[int] = Field(None, description="재생 시간 (초)", ge=0)
    
    @validator('file_name')
    def validate_file_name(cls, v):
        """파일명 유효성 검증"""
        # 위험한 문자 제거
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f'파일명에 허용되지 않는 문자가 포함되어 있습니다: {char}')
        return v


class TestUploadRequest(BaseModel):
    """테스트용 업로드 요청 스키마"""
    interview_id: int = Field(..., description="면접 ID", gt=0)
    file_name: str = Field(..., description="파일명", min_length=1, max_length=255)
    file_type: str = Field("video", description="파일 타입", pattern=r"^(video|audio)$")
    file_size: Optional[int] = Field(None, description="파일 크기 (바이트)", ge=0)
    
    @validator('file_name')
    def validate_file_name(cls, v):
        """파일명 유효성 검증"""
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f'파일명에 허용되지 않는 문자가 포함되어 있습니다: {char}')
        return v


class UploadResponse(BaseModel):
    """업로드 응답 스키마"""
    upload_url: str = Field(..., description="S3 업로드 URL")
    media_id: str = Field(..., description="미디어 파일 ID")
    s3_key: str = Field(..., description="S3 저장 키")
    expires_in: Optional[int] = Field(3600, description="URL 만료 시간 (초)")
    
    class Config:
        schema_extra = {
            "example": {
                "upload_url": "https://betago-s3.s3.amazonaws.com/...",
                "media_id": "uuid4-generated-id",
                "s3_key": "gaze-videos/123/456/video.webm",
                "expires_in": 3600
            }
        }


class PlayResponse(BaseModel):
    """재생 응답 스키마"""
    play_url: str = Field(..., description="S3 재생 URL")
    file_name: Optional[str] = Field(None, description="원본 파일명")
    file_type: Optional[str] = Field(None, description="파일 타입")
    test_id: Optional[str] = Field(None, description="테스트 ID (호환성)")
    
    class Config:
        schema_extra = {
            "example": {
                "play_url": "https://betago-s3.s3.amazonaws.com/...",
                "file_name": "interview-video.webm",
                "file_type": "video",
                "test_id": "uuid4-id"
            }
        }


class UploadCompleteRequest(BaseModel):
    """업로드 완료 요청 스키마"""
    file_size: Optional[int] = Field(None, description="실제 업로드된 파일 크기", ge=0)
    duration: Optional[int] = Field(None, description="실제 재생 시간 (초)", ge=0)
    checksum: Optional[str] = Field(None, description="파일 체크섬 (MD5)")


class UploadCompleteResponse(BaseModel):
    """업로드 완료 응답 스키마"""
    message: str = Field(..., description="완료 메시지")
    media_id: str = Field(..., description="미디어 파일 ID")
    status: str = Field("completed", description="업로드 상태")
    
    class Config:
        schema_extra = {
            "example": {
                "message": "업로드 완료",
                "media_id": "uuid4-generated-id",
                "status": "completed"
            }
        }


class MediaFileInfo(BaseModel):
    """미디어 파일 정보 스키마"""
    media_id: str = Field(..., description="미디어 파일 ID")
    file_name: str = Field(..., description="파일명")
    file_type: str = Field(..., description="파일 타입")
    file_size: Optional[int] = Field(None, description="파일 크기 (바이트)")
    duration: Optional[int] = Field(None, description="재생 시간 (초)")
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: datetime = Field(..., description="수정 시간")
    s3_url: Optional[str] = Field(None, description="S3 URL")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MediaListResponse(BaseModel):
    """미디어 파일 목록 응답 스키마"""
    media_files: List[MediaFileInfo] = Field(..., description="미디어 파일 목록")
    total_count: int = Field(..., description="전체 파일 수")
    page: int = Field(1, description="현재 페이지")
    page_size: int = Field(20, description="페이지 크기")
    total_pages: int = Field(..., description="전체 페이지 수")


class MediaStatsResponse(BaseModel):
    """미디어 파일 통계 응답 스키마"""
    total_files: int = Field(..., description="전체 파일 수")
    total_size_mb: float = Field(..., description="전체 파일 크기 (MB)")
    video_count: int = Field(..., description="동영상 파일 수")
    audio_count: int = Field(..., description="오디오 파일 수")
    avg_file_size_mb: float = Field(..., description="평균 파일 크기 (MB)")
    latest_upload: Optional[datetime] = Field(None, description="최근 업로드 시간")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "total_files": 150,
                "total_size_mb": 2048.5,
                "video_count": 120,
                "audio_count": 30,
                "avg_file_size_mb": 13.66,
                "latest_upload": "2025-08-12T10:30:00Z"
            }
        }


class GazeUploadRequest(BaseModel):
    """시선 추적 영상 업로드 요청 스키마"""
    session_id: str = Field(..., description="면접 세션 ID", min_length=1)
    file_name: str = Field(..., description="파일명", min_length=1, max_length=255)
    file_size: Optional[int] = Field(None, description="파일 크기 (바이트)", ge=0)
    content_type: Optional[str] = Field('video/mp4', description="실제 파일 MIME 타입", pattern=r"^video/(mp4|webm|quicktime)$")
    
    @validator('file_name')
    def validate_file_name(cls, v):
        """파일명 유효성 검증"""
        # 위험한 문자 제거
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f'파일명에 허용되지 않는 문자가 포함되어 있습니다: {char}')
        return v
    
    @validator('file_name')
    def validate_gaze_file_extension(cls, v):
        """시선 추적 비디오 파일 확장자 검증"""
        allowed_extensions = ['.webm', '.mp4', '.mov']
        if not any(v.lower().endswith(ext) for ext in allowed_extensions):
            raise ValueError(f'지원되지 않는 파일 형식입니다. 허용된 형식: {", ".join(allowed_extensions)}')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "comp_abc123def456",
                "file_name": "gaze_video_20250818_123456.webm",
                "file_size": 15728640
            }
        }


class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    error: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: Optional[dict] = Field(None, description="상세 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="에러 발생 시간")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "error": "UPLOAD_FAILED",
                "message": "파일 업로드에 실패했습니다",
                "details": {"reason": "S3 권한 오류"},
                "timestamp": "2025-08-12T10:30:00Z"
            }
        }
# === 김원우 작성 끝 ===