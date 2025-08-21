"""
비디오 최적화 유틸리티
다운로드한 비디오 파일에서 시간 탐색(seeking)이 원활하도록 최적화
"""

import subprocess
import tempfile
import os
import logging
from typing import Optional, Tuple
import shutil

logger = logging.getLogger(__name__)

class VideoOptimizer:
    """비디오 파일 웹 최적화 클래스"""
    
    @staticmethod
    def is_ffmpeg_available() -> bool:
        """FFmpeg 설치 여부 확인"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @staticmethod
    def optimize_for_seeking(input_stream, output_path: str, file_extension: str = "webm") -> bool:
        """
        비디오 스트림을 시간 탐색에 최적화된 형태로 변환
        
        Args:
            input_stream: 입력 비디오 스트림 (S3 스트림 등)
            output_path: 최적화된 파일이 저장될 경로
            file_extension: 파일 확장자 (webm, mp4 등)
            
        Returns:
            bool: 최적화 성공 여부
        """
        if not VideoOptimizer.is_ffmpeg_available():
            logger.error("FFmpeg를 찾을 수 없습니다")
            return False
        
        temp_input = None
        try:
            # 1. 임시 파일에 입력 스트림 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
                temp_input = temp_file.name
                # 스트림 데이터를 임시 파일에 쓰기
                shutil.copyfileobj(input_stream, temp_file)
            
            # 2. FFmpeg로 최적화 수행
            success = VideoOptimizer._run_ffmpeg_optimization(temp_input, output_path, file_extension)
            
            return success
            
        except Exception as e:
            logger.error(f"비디오 최적화 중 오류 발생: {e}")
            return False
        finally:
            # 임시 파일 정리
            if temp_input and os.path.exists(temp_input):
                try:
                    os.unlink(temp_input)
                except Exception as e:
                    logger.warning(f"임시 파일 삭제 실패: {e}")
    
    @staticmethod
    def _run_ffmpeg_optimization(input_path: str, output_path: str, file_extension: str) -> bool:
        """
        FFmpeg 명령어 실행으로 비디오 최적화
        
        Args:
            input_path: 입력 파일 경로
            output_path: 출력 파일 경로  
            file_extension: 파일 확장자
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 확장자에 따른 최적화 옵션 설정
            if file_extension.lower() == 'mp4':
                # MP4의 경우 faststart 플래그 사용
                cmd = [
                    'ffmpeg',
                    '-i', input_path,
                    '-movflags', '+faststart',  # 메타데이터를 파일 앞쪽으로 이동
                    '-c', 'copy',  # 재인코딩 없이 복사 (빠름)
                    '-avoid_negative_ts', 'make_zero',
                    '-y',  # 출력 파일 덮어쓰기
                    output_path
                ]
            else:
                # WebM의 경우 키프레임 간격 최적화
                cmd = [
                    'ffmpeg',
                    '-i', input_path,
                    '-c:v', 'copy',  # 비디오 코덱 복사
                    '-c:a', 'copy',  # 오디오 코덱 복사
                    '-avoid_negative_ts', 'make_zero',
                    '-y',  # 출력 파일 덮어쓰기
                    output_path
                ]
            
            logger.info(f"FFmpeg 최적화 시작: {' '.join(cmd)}")
            
            # FFmpeg 실행
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )
            
            if result.returncode == 0:
                logger.info(f"비디오 최적화 완료: {output_path}")
                return True
            else:
                logger.error(f"FFmpeg 실행 실패: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg 실행 시간 초과")
            return False
        except Exception as e:
            logger.error(f"FFmpeg 실행 중 오류: {e}")
            return False
    
    @staticmethod
    def get_video_info(file_path: str) -> Optional[dict]:
        """
        비디오 파일 정보 조회
        
        Args:
            file_path: 비디오 파일 경로
            
        Returns:
            dict: 비디오 정보 (duration, size 등)
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
            else:
                logger.error(f"FFprobe 실행 실패: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"비디오 정보 조회 중 오류: {e}")
            return None