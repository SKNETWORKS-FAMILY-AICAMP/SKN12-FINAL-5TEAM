# === 김원우 작성 시작 ===
"""
미디어 파일 관리 서비스

이 모듈은 S3 미디어 파일의 업로드, 관리, 처리를 담당하는 서비스입니다.
기존 test/video_api.py와 file_utils.py의 기능을 서비스 레이어로 통합했습니다.

주요 기능:
- S3 파일 업로드/다운로드
- Presigned URL 생성
- 파일 유효성 검증
- 안전한 임시 파일 관리

작성자: 김원우
작성일: 2025-08-12
"""

import os
import boto3
import uuid
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import contextmanager
import logging

from models.media import MediaFile, UploadStatus, MediaFileType

# 로깅 설정
logger = logging.getLogger(__name__)


class MediaService:
    """미디어 파일 관리 서비스"""
    
    def __init__(self):
        """서비스 초기화"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'ap-northeast-2')
        )
        
        self.bucket_name = 'betago-s3'
        self.max_file_size_mb = 100
        self.allowed_extensions = {'.mp4', '.webm', '.avi', '.mov', '.wav', '.mp3'}
        
        logger.info("✅ [MEDIA_SERVICE] 미디어 서비스 초기화 완료")
    
    def generate_upload_url(
        self,
        user_id: str,
        interview_id: int,
        file_name: str,
        file_type: str = "video",
        is_test: bool = False
    ) -> Dict[str, Any]:
        """
        S3 업로드용 Presigned URL 생성
        
        Args:
            user_id: 사용자 ID
            interview_id: 면접 ID
            file_name: 파일명
            file_type: 파일 타입 (video/audio)
            is_test: 테스트용 여부
            
        Returns:
            Dict: upload_url과 media_id 포함
        """
        try:
            # S3 키 생성
            prefix = "test-videos" if is_test else "interviews"
            s3_key = f"{prefix}/{user_id}/{interview_id}/{file_name}"
            
            # Content-Type 결정
            content_type = 'video/webm' if file_type == 'video' else 'audio/webm'
            
            # Presigned URL 생성 (1시간 유효)
            upload_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ContentType': content_type
                },
                ExpiresIn=3600
            )
            
            # 미디어 ID 생성
            media_id = str(uuid.uuid4())
            
            logger.info(f"📤 [MEDIA_SERVICE] 업로드 URL 생성: {s3_key}")
            
            return {
                'upload_url': upload_url,
                'media_id': media_id,
                's3_key': s3_key,
                's3_url': f"https://{self.bucket_name}.s3.ap-northeast-2.amazonaws.com/{s3_key}",
                'expires_in': 3600
            }
            
        except Exception as e:
            logger.error(f"❌ [MEDIA_SERVICE] 업로드 URL 생성 실패: {e}")
            raise
    
    def generate_play_url(self, s3_key: str) -> str:
        """
        S3 재생용 Presigned URL 생성
        
        Args:
            s3_key: S3 키
            
        Returns:
            str: 재생용 URL
        """
        try:
            play_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=3600
            )
            
            logger.info(f"▶️ [MEDIA_SERVICE] 재생 URL 생성: {s3_key}")
            return play_url
            
        except Exception as e:
            logger.error(f"❌ [MEDIA_SERVICE] 재생 URL 생성 실패: {e}")
            raise
    
    def delete_file(self, s3_key: str) -> bool:
        """
        S3 파일 삭제
        
        Args:
            s3_key: S3 키
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"🗑️ [MEDIA_SERVICE] 파일 삭제 완료: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [MEDIA_SERVICE] 파일 삭제 실패: {s3_key} - {e}")
            return False
    
    def check_file_exists(self, s3_key: str) -> bool:
        """
        S3 파일 존재 확인
        
        Args:
            s3_key: S3 키
            
        Returns:
            bool: 파일 존재 여부
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except:
            return False
    
    def get_file_info(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        S3 파일 정보 조회
        
        Args:
            s3_key: S3 키
            
        Returns:
            Dict: 파일 정보 (크기, 수정시간 등)
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            return {
                'size': response['ContentLength'],
                'content_type': response.get('ContentType'),
                'etag': response.get('ETag'),
                'last_modified': response.get('LastModified')
            }
            
        except Exception as e:
            logger.error(f"❌ [MEDIA_SERVICE] 파일 정보 조회 실패: {s3_key} - {e}")
            return None
    
    @contextmanager
    def secure_temp_file(self, suffix: str = '.tmp'):
        """
        안전한 임시 파일 생성 및 관리
        
        Args:
            suffix: 파일 확장자
            
        Yields:
            str: 임시 파일 경로
        """
        temp_path = None
        try:
            temp_dir = tempfile.gettempdir()
            unique_filename = f"media_{uuid.uuid4().hex}{suffix}"
            temp_path = os.path.join(temp_dir, unique_filename)
            
            logger.info(f"📁 [MEDIA_SERVICE] 임시 파일 생성: {temp_path}")
            yield temp_path
            
        except Exception as e:
            logger.error(f"❌ [MEDIA_SERVICE] 임시 파일 처리 오류: {e}")
            raise
            
        finally:
            # 파일 정리
            if temp_path and os.path.exists(temp_path):
                try:
                    os.chmod(temp_path, 0o777)
                    os.unlink(temp_path)
                    logger.info(f"🗑️ [MEDIA_SERVICE] 임시 파일 삭제: {temp_path}")
                except Exception as e:
                    logger.error(f"❌ [MEDIA_SERVICE] 임시 파일 삭제 실패: {e}")
    
    def download_from_s3(self, s3_key: str, local_path: str) -> bool:
        """
        S3에서 파일 다운로드
        
        Args:
            s3_key: S3 키
            local_path: 로컬 저장 경로
            
        Returns:
            bool: 다운로드 성공 여부
        """
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"📥 [MEDIA_SERVICE] S3 다운로드 완료: {s3_key} -> {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [MEDIA_SERVICE] S3 다운로드 실패: {s3_key} - {e}")
            return False
    
    def validate_file(self, file_name: str, file_size: Optional[int] = None) -> Dict[str, Any]:
        """
        파일 유효성 검증
        
        Args:
            file_name: 파일명
            file_size: 파일 크기 (바이트)
            
        Returns:
            Dict: 검증 결과
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 파일명 검증
        if not file_name or len(file_name.strip()) == 0:
            result['valid'] = False
            result['errors'].append('파일명이 비어있습니다')
            return result
        
        # 확장자 검증
        file_ext = os.path.splitext(file_name.lower())[1]
        if file_ext not in self.allowed_extensions:
            result['valid'] = False
            result['errors'].append(f'지원하지 않는 파일 형식입니다: {file_ext}')
        
        # 파일 크기 검증
        if file_size:
            file_size_mb = file_size / (1024 * 1024)
            
            if file_size_mb < 0.1:  # 100KB 미만
                result['warnings'].append('파일이 너무 작을 수 있습니다')
            
            if file_size_mb > self.max_file_size_mb:
                result['valid'] = False
                result['errors'].append(f'파일이 너무 큽니다: {file_size_mb:.1f}MB > {self.max_file_size_mb}MB')
        
        # 위험한 문자 검사
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in file_name:
                result['valid'] = False
                result['errors'].append(f'파일명에 허용되지 않는 문자가 포함되어 있습니다: {char}')
                break
        
        logger.info(f"📋 [MEDIA_SERVICE] 파일 검증: {file_name} - Valid: {result['valid']}")
        return result
    
    def get_file_size_mb(self, file_path: str) -> float:
        """
        파일 크기를 MB 단위로 반환
        
        Args:
            file_path: 파일 경로
            
        Returns:
            float: 파일 크기 (MB)
        """
        try:
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            return round(size_mb, 2)
        except Exception as e:
            logger.error(f"❌ [MEDIA_SERVICE] 파일 크기 확인 실패: {e}")
            return 0.0
    
    def cleanup_old_temp_files(self, max_age_hours: int = 24) -> int:
        """
        오래된 임시 파일 정리
        
        Args:
            max_age_hours: 최대 보존 시간 (시간)
            
        Returns:
            int: 삭제된 파일 수
        """
        temp_dir = tempfile.gettempdir()
        deleted_count = 0
        current_time = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for filename in os.listdir(temp_dir):
                if filename.startswith('media_') and filename.endswith('.tmp'):
                    file_path = os.path.join(temp_dir, filename)
                    
                    try:
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            os.chmod(file_path, 0o777)
                            os.unlink(file_path)
                            deleted_count += 1
                    except Exception as e:
                        logger.warning(f"⚠️ [MEDIA_SERVICE] 파일 정리 실패: {filename} - {e}")
            
            logger.info(f"🧹 [MEDIA_SERVICE] 임시 파일 정리 완료: {deleted_count}개 삭제")
            
        except Exception as e:
            logger.error(f"❌ [MEDIA_SERVICE] 임시 파일 정리 오류: {e}")
        
        return deleted_count


# 전역 서비스 인스턴스
media_service = MediaService()
# === 김원우 작성 끝 ===