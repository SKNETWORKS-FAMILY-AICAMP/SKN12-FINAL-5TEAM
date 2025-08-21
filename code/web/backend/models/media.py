# === 김원우 작성 시작 ===
"""
S3 미디어 파일 관리 모델

이 모듈은 S3에 저장되는 미디어 파일(동영상, 오디오)의 
데이터 모델을 정의합니다.

주요 기능:
- 미디어 파일 메타데이터 관리
- 업로드 세션 상태 추적  
- S3 키 및 URL 관리

작성자: 김원우
작성일: 2025-08-12
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum


class MediaFileType(str, Enum):
    """미디어 파일 타입"""
    VIDEO = "video"
    AUDIO = "audio"


class UploadStatus(str, Enum):
    """업로드 상태"""
    PENDING = "pending"
    UPLOADING = "uploading" 
    COMPLETED = "completed"
    FAILED = "failed"


class MediaFile(BaseModel):
    """S3 미디어 파일 모델"""
    media_id: str
    user_id: str
    interview_id: int
    file_name: str
    file_type: MediaFileType
    s3_key: str
    s3_url: str
    file_size: Optional[int] = None
    duration: Optional[int] = None  # 동영상/오디오 길이 (초)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic 설정"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VideoUpload(BaseModel):
    """비디오 업로드 세션 모델"""
    upload_id: str
    media_id: str
    status: UploadStatus
    upload_url: str
    expires_at: datetime
    user_id: str
    progress: Optional[float] = 0.0  # 업로드 진행률 (0.0 ~ 1.0)
    error_message: Optional[str] = None
    
    class Config:
        """Pydantic 설정"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MediaFileStats(BaseModel):
    """미디어 파일 통계 모델"""
    total_files: int
    total_size_mb: float
    video_count: int
    audio_count: int
    avg_file_size_mb: float
    latest_upload: Optional[datetime] = None
    
    class Config:
        """Pydantic 설정"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class S3FileInfo(BaseModel):
    """S3 파일 정보 모델"""
    bucket: str
    key: str
    url: str
    size: Optional[int] = None
    content_type: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[datetime] = None
    
    class Config:
        """Pydantic 설정"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
# === 김원우 작성 끝 ===