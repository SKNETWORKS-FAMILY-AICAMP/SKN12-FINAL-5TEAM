# === 김원우 작성 시작 ===
"""
안전한 파일 관리 유틸리티

이 모듈은 시선 분석 시스템에서 임시 파일을 안전하게 관리하는 기능을 제공합니다.
특히 Windows 환경에서 발생하는 파일 권한 문제를 해결하고, 
실제 면접 서비스에서 대용량 동영상 파일을 안전하게 처리할 수 있도록 설계되었습니다.

주요 기능:
- Windows 호환 임시 파일 관리
- 자동 파일 정리 (메모리 누수 방지)
- 파일 권한 오류 처리
- 보안 강화 (민감한 면접 데이터 보호)

작성자: 김원우
최종 수정: 2025-08-12
용도: 베타고 면접 플랫폼 파일 관리 시스템
"""

import os
import tempfile
import contextlib
import shutil
import time
import logging
from typing import Generator, Optional
from pathlib import Path
import uuid

# 로깅 설정
logger = logging.getLogger(__name__)


class SecureFileManager:
    """
    보안이 강화된 파일 관리자
    
    실제 면접 서비스에서 고려해야 할 보안 요소:
    1. 면접 동영상은 민감한 개인정보
    2. 임시 파일은 처리 후 즉시 완전 삭제
    3. 파일 접근 권한 최소화
    4. 디스크 공간 모니터링
    """
    
    @staticmethod
    @contextlib.contextmanager
    def secure_temp_file(suffix: str = '.webm', prefix: str = 'gaze_') -> Generator[str, None, None]:
        """
        보안이 강화된 임시 파일 생성 및 관리
        
        특징:
        1. Windows 파일 권한 문제 해결
        2. 자동 파일 정리 (컨텍스트 관리자)
        3. 고유한 파일명 생성 (충돌 방지)
        4. 완전한 파일 삭제 보장
        
        Args:
            suffix: 파일 확장자 (기본값: .webm)
            prefix: 파일명 접두사 (기본값: gaze_)
            
        Yields:
            str: 임시 파일 경로
            
        사용 예시:
            with SecureFileManager.secure_temp_file('.mp4') as temp_path:
                # 면접 동영상 처리
                download_video(bucket, key, temp_path)
                result = analyze_video(temp_path)
                # 여기서 자동으로 파일이 삭제됨
                
        실제 면접 서비스 적용 시 주의사항:
        - 대용량 파일: 10MB~100MB 동영상 처리 가능
        - 동시 처리: 여러 면접이 동시에 진행될 수 있음
        - 디스크 공간: 임시 저장소 모니터링 필요
        - 네트워크: S3 다운로드 실패 시에도 정리 보장
        """
        temp_path = None
        try:
            # 고유한 임시 파일 경로 생성
            temp_dir = tempfile.gettempdir()
            unique_filename = f"{prefix}{uuid.uuid4().hex}{suffix}"
            temp_path = os.path.join(temp_dir, unique_filename)
            
            logger.info(f"📁 [FILE_MANAGER] 임시 파일 생성: {temp_path}")
            
            # 파일 경로 반환 (실제 파일은 사용하는 쪽에서 생성)
            yield temp_path
            
        except Exception as e:
            logger.error(f"❌ [FILE_MANAGER] 임시 파일 처리 오류: {e}")
            raise
            
        finally:
            # 파일 정리 (Windows 호환성 고려)
            if temp_path and os.path.exists(temp_path):
                SecureFileManager._safe_delete_file(temp_path)
    
    @staticmethod
    @contextlib.contextmanager
    def secure_temp_directory() -> Generator[str, None, None]:
        """
        보안이 강화된 임시 디렉토리 생성 및 관리
        
        여러 파일을 동시에 처리해야 할 때 사용
        (예: 동영상 + 썸네일 + 메타데이터)
        
        사용 예시:
            with SecureFileManager.secure_temp_directory() as temp_dir:
                video_path = os.path.join(temp_dir, 'video.webm')
                thumbnail_path = os.path.join(temp_dir, 'thumb.jpg')
                # 처리 후 디렉토리 전체가 자동 삭제됨
        """
        temp_dir = None
        try:
            # 고유한 임시 디렉토리 생성
            temp_dir = tempfile.mkdtemp(prefix='gaze_analysis_')
            logger.info(f"📁 [FILE_MANAGER] 임시 디렉토리 생성: {temp_dir}")
            
            yield temp_dir
            
        except Exception as e:
            logger.error(f"❌ [FILE_MANAGER] 임시 디렉토리 처리 오류: {e}")
            raise
            
        finally:
            # 디렉토리 전체 정리
            if temp_dir and os.path.exists(temp_dir):
                SecureFileManager._safe_delete_directory(temp_dir)
    
    @staticmethod
    def _safe_delete_file(file_path: str, max_retries: int = 3, retry_delay: float = 0.1) -> bool:
        """
        Windows 호환 안전한 파일 삭제
        
        Windows에서는 파일이 다른 프로세스에서 사용 중일 때 삭제가 실패할 수 있습니다.
        이 메서드는 재시도 로직을 통해 안전한 삭제를 보장합니다.
        
        Args:
            file_path: 삭제할 파일 경로
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 간격 (초)
            
        Returns:
            bool: 삭제 성공 여부
            
        실제 서비스에서의 중요성:
        - 면접 동영상은 민감한 개인정보
        - 임시 파일이 남아있으면 보안 위험
        - 디스크 공간 부족 방지
        """
        for attempt in range(max_retries + 1):
            try:
                if os.path.exists(file_path):
                    # 파일 권한을 쓰기 가능으로 변경 (Windows 대응)
                    os.chmod(file_path, 0o777)
                    os.unlink(file_path)
                    
                logger.info(f"🗑️ [FILE_MANAGER] 파일 삭제 완료: {file_path}")
                return True
                
            except PermissionError as e:
                if attempt < max_retries:
                    logger.warning(f"⚠️ [FILE_MANAGER] 파일 삭제 재시도 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"❌ [FILE_MANAGER] 파일 삭제 최종 실패: {file_path} - {e}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ [FILE_MANAGER] 파일 삭제 오류: {file_path} - {e}")
                return False
        
        return False
    
    @staticmethod
    def _safe_delete_directory(dir_path: str, max_retries: int = 3) -> bool:
        """
        안전한 디렉토리 삭제 (하위 파일 포함)
        
        Args:
            dir_path: 삭제할 디렉토리 경로
            max_retries: 최대 재시도 횟수
            
        Returns:
            bool: 삭제 성공 여부
        """
        for attempt in range(max_retries + 1):
            try:
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
                    
                logger.info(f"🗑️ [FILE_MANAGER] 디렉토리 삭제 완료: {dir_path}")
                return True
                
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"⚠️ [FILE_MANAGER] 디렉토리 삭제 재시도 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(0.1)
                    continue
                else:
                    logger.error(f"❌ [FILE_MANAGER] 디렉토리 삭제 최종 실패: {dir_path} - {e}")
                    return False
        
        return False
    
    @staticmethod
    def get_file_size_mb(file_path: str) -> float:
        """
        파일 크기를 MB 단위로 반환
        
        실제 면접 서비스에서 활용:
        - 업로드 크기 제한 검증
        - 처리 시간 예측
        - 스토리지 사용량 모니터링
        """
        try:
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            return round(size_mb, 2)
        except Exception as e:
            logger.error(f"❌ [FILE_MANAGER] 파일 크기 확인 실패: {e}")
            return 0.0
    
    @staticmethod
    def check_disk_space_gb(path: str = None) -> float:
        """
        디스크 여유 공간을 GB 단위로 반환
        
        실제 면접 서비스에서 활용:
        - 임시 파일 생성 전 공간 확인
        - 서버 모니터링
        - 알림 시스템 연동
        """
        try:
            if path is None:
                path = tempfile.gettempdir()
                
            statvfs = os.statvfs(path) if hasattr(os, 'statvfs') else None
            if statvfs:
                # Unix/Linux 시스템
                free_bytes = statvfs.f_frsize * statvfs.f_bavail
            else:
                # Windows 시스템
                import shutil
                _, _, free_bytes = shutil.disk_usage(path)
            
            free_gb = free_bytes / (1024 ** 3)
            return round(free_gb, 2)
            
        except Exception as e:
            logger.error(f"❌ [FILE_MANAGER] 디스크 공간 확인 실패: {e}")
            return 0.0


class FileValidator:
    """
    파일 유효성 검증 클래스
    
    실제 면접 서비스에서 업로드된 파일의 안전성과 유효성을 검증
    """
    
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.avi', '.mov'}
    MAX_FILE_SIZE_MB = 100
    MIN_FILE_SIZE_KB = 100
    
    @classmethod
    def validate_video_file(cls, file_path: str) -> dict:
        """
        동영상 파일 유효성 검증
        
        검증 항목:
        1. 파일 존재 여부
        2. 파일 확장자
        3. 파일 크기
        4. 파일 손상 여부 (기본적인 체크)
        
        Returns:
            dict: 검증 결과 {'valid': bool, 'errors': list, 'info': dict}
        """
        result = {
            'valid': True,
            'errors': [],
            'info': {}
        }
        
        try:
            # 파일 존재 확인
            if not os.path.exists(file_path):
                result['valid'] = False
                result['errors'].append('파일이 존재하지 않습니다')
                return result
            
            # 확장자 확인
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in cls.ALLOWED_VIDEO_EXTENSIONS:
                result['valid'] = False
                result['errors'].append(f'지원하지 않는 파일 형식: {file_ext}')
            
            # 파일 크기 확인
            file_size_mb = SecureFileManager.get_file_size_mb(file_path)
            result['info']['size_mb'] = file_size_mb
            
            if file_size_mb < cls.MIN_FILE_SIZE_KB / 1024:
                result['valid'] = False
                result['errors'].append(f'파일이 너무 작습니다: {file_size_mb}MB')
            
            if file_size_mb > cls.MAX_FILE_SIZE_MB:
                result['valid'] = False
                result['errors'].append(f'파일이 너무 큽니다: {file_size_mb}MB > {cls.MAX_FILE_SIZE_MB}MB')
            
            # 기본적인 파일 무결성 체크 (헤더 확인)
            if file_ext in {'.mp4', '.webm'}:
                if not cls._check_video_header(file_path):
                    result['valid'] = False
                    result['errors'].append('손상된 동영상 파일일 가능성이 있습니다')
            
            logger.info(f"📋 [FILE_VALIDATOR] 파일 검증 완료: {file_path} - Valid: {result['valid']}")
            
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f'파일 검증 중 오류 발생: {str(e)}')
            logger.error(f"❌ [FILE_VALIDATOR] 파일 검증 실패: {e}")
        
        return result
    
    @staticmethod
    def _check_video_header(file_path: str) -> bool:
        """
        동영상 파일 헤더 기본 검증
        
        완전한 검증은 아니지만, 명백히 손상된 파일은 걸러냄
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)
                
                # MP4 파일 체크
                if b'ftyp' in header:
                    return True
                
                # WebM 파일 체크 (EBML 헤더)
                if header.startswith(b'\x1a\x45\xdf\xa3'):
                    return True
                
                # AVI 파일 체크
                if header.startswith(b'RIFF') and b'AVI' in header:
                    return True
                    
            return False
            
        except Exception:
            return False


# 유틸리티 함수들

def cleanup_old_temp_files(max_age_hours: int = 24) -> int:
    """
    오래된 임시 파일들을 정리
    
    실제 면접 서비스에서는 정기적으로 실행하여 디스크 공간 확보
    (예: 크론 작업으로 매시간 실행)
    
    Args:
        max_age_hours: 최대 보존 시간 (시간 단위)
        
    Returns:
        int: 삭제된 파일 수
    """
    temp_dir = tempfile.gettempdir()
    deleted_count = 0
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    try:
        for filename in os.listdir(temp_dir):
            if filename.startswith('gaze_'):
                file_path = os.path.join(temp_dir, filename)
                
                try:
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        if SecureFileManager._safe_delete_file(file_path):
                            deleted_count += 1
                            
                except Exception as e:
                    logger.warning(f"⚠️ [CLEANUP] 파일 정리 실패: {filename} - {e}")
        
        logger.info(f"🧹 [CLEANUP] 임시 파일 정리 완료: {deleted_count}개 삭제")
        
    except Exception as e:
        logger.error(f"❌ [CLEANUP] 임시 파일 정리 오류: {e}")
    
    return deleted_count


def get_system_info() -> dict:
    """
    시스템 정보 수집 (모니터링용)
    
    실제 면접 서비스에서 활용:
    - 서버 상태 모니터링
    - 성능 최적화 참고 자료
    - 장애 대응 정보
    """
    import platform
    try:
        import psutil
        memory_info = round(psutil.virtual_memory().total / (1024**3), 2)
    except ImportError:
        memory_info = 0.0
    
    return {
        'platform': platform.system(),
        'python_version': platform.python_version(),
        'cpu_count': os.cpu_count(),
        'memory_gb': memory_info,
        'disk_free_gb': SecureFileManager.check_disk_space_gb(),
        'temp_dir': tempfile.gettempdir()
    }


if __name__ == "__main__":
    # 테스트 코드
    print("🧪 파일 관리 유틸리티 테스트")
    print(f"시스템 정보: {get_system_info()}")
    
    # 임시 파일 테스트
    with SecureFileManager.secure_temp_file('.test') as temp_path:
        print(f"임시 파일 생성: {temp_path}")
        
        # 테스트 파일 생성
        with open(temp_path, 'w') as f:
            f.write("테스트 데이터")
        
        print(f"파일 크기: {SecureFileManager.get_file_size_mb(temp_path)}MB")
    
    print("테스트 완료 - 임시 파일이 자동으로 정리되었습니다")
# === 김원우 작성 끝 ===