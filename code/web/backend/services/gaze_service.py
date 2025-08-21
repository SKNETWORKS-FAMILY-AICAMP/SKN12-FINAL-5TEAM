# === 김원우 작성 시작 ===
"""
동영상 기반 시선 분석 엔진 (리팩토링 버전)

이 모듈은 S3에 저장된 면접 동영상에서 시선 안정성을 분석하는 기능을 제공합니다.
GazeCoreProcessor를 상속받아 공통 로직을 재사용하고, 
실제 면접 서비스에 적용하기 위한 확장성과 안정성을 확보했습니다.

주요 개선사항:
- MediaPipe 로직 모듈화 및 재사용
- Windows 호환 파일 관리
- 상세한 주석 및 문서화
- 에러 처리 강화
- 성능 최적화 옵션

작성자: 김원우
최종 수정: 2025-08-12
용도: 베타고 면접 플랫폼 시선 분석 시스템
"""

import cv2
import numpy as np
import os
import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import time
import logging
import subprocess
import shutil

# 새로운 모듈 import
from .gaze_core import GazeCoreProcessor, GazeConfig
from .secure_file_manager import SecureFileManager, FileValidator

# 로깅 설정
logger = logging.getLogger(__name__)


@dataclass
class GazeAnalysisResult:
    """
    시선 분석 결과 데이터 클래스
    
    실제 면접 서비스에서 프론트엔드로 전달되는 데이터 구조입니다.
    API 응답 형식과 일치하도록 설계되었으며, 확장 가능합니다.
    
    필드 설명:
    - gaze_score: 종합 시선 안정성 점수 (0-100점)
    - total_frames: 동영상 총 프레임 수
    - analyzed_frames: 실제 분석된 프레임 수
    - in_range_frames: 허용 범위 내 시선 프레임 수
    - in_range_ratio: 범위 준수율 (0.0-1.0)
    - jitter_score: 시선 흔들림 점수 (0-100점, 높을수록 안정)
    - compliance_score: 범위 준수 점수 (0-100점)
    - stability_rating: 안정성 등급 ("우수", "양호", "보통", "개선 필요")
    - feedback: AI 피드백 메시지
    - gaze_points: 시선 궤적 포인트 리스트 [(x, y), ...]
    - allowed_range: 캘리브레이션 기반 허용 시선 범위 좌표
    - calibration_points: 4개 캘리브레이션 포인트 [(x, y), ...]
    """
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
    allowed_range: Dict[str, float]
    calibration_points: List[Tuple[float, float]]


class GazeAnalyzer(GazeCoreProcessor):
    """
    동영상 시선 분석기 (리팩토링 버전)
    
    GazeCoreProcessor를 상속받아 MediaPipe 관련 공통 로직을 재사용합니다.
    S3에서 동영상을 다운로드하고 프레임별로 시선을 추적하여 
    종합적인 시선 안정성 점수를 계산합니다.
    
    주요 기능:
    1. S3 동영상 안전 다운로드 (임시 파일 관리)
    2. MediaPipe 기반 시선 추적
    3. 캘리브레이션 데이터 기반 허용 범위 계산
    4. 동적 스케일링 (거리 변화 보정)
    5. 시선 안정성 점수 계산
    6. AI 피드백 생성
    
    실제 면접 서비스 적용 가이드:
    - 동시 처리: 여러 면접 동시 분석 시 인스턴스 분리 권장
    - 성능 튜닝: frame_skip 값으로 속도 vs 정확도 조절
    - 모니터링: 분석 시간, 성공률, 오류율 추적 필요
    - 스케일링: 대용량 처리 시 비동기 큐 시스템 고려
    """
    
    def __init__(self):
        """
        시선 분석기 초기화
        
        부모 클래스(GazeCoreProcessor)의 MediaPipe 초기화와
        S3 클라이언트 설정을 함께 진행합니다.
        """
        # 부모 클래스 초기화 (MediaPipe 설정)
        super().__init__()
        
        # S3 클라이언트 초기화
        self._initialize_s3_client()
        
        logger.info("🚀 [GAZE_ANALYZER] 동영상 시선 분석기 초기화 완료")
    
    def _initialize_s3_client(self):
        """
        AWS S3 클라이언트 초기화
        
        실제 면접 서비스에서는 다음 환경변수 설정 필요:
        - AWS_ACCESS_KEY_ID: AWS 액세스 키
        - AWS_SECRET_ACCESS_KEY: AWS 시크릿 키  
        - AWS_REGION: S3 버킷 리전 (기본값: ap-northeast-2)
        
        보안 고려사항:
        - IAM 역할 사용 권장 (하드코딩된 키 사용 금지)
        - 최소 권한 원칙 적용 (S3 읽기 권한만)
        - 키 로테이션 정기 실행
        """
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'ap-northeast-2')
            )
            logger.info("✅ [GAZE_ANALYZER] S3 클라이언트 초기화 성공")
            
        except Exception as e:
            logger.error(f"❌ [GAZE_ANALYZER] S3 클라이언트 초기화 실패: {e}")
            raise RuntimeError(f"S3 클라이언트 초기화 실패: {e}")
    
    def _check_ffmpeg_availability(self) -> bool:
        """
        FFmpeg 설치 및 사용 가능 여부 확인
        
        시스템에 ffmpeg가 설치되어 있고 실행 가능한지 확인합니다.
        비디오 트랜스코딩 기능 사용 전 필수 체크입니다.
        
        Returns:
            bool: FFmpeg 사용 가능 여부
            
        실제 면접 서비스 고려사항:
        - 서버 초기화 시 1회 체크하여 결과 캐싱 권장
        - FFmpeg 버전 호환성 확인 (4.0 이상 권장)
        - 필요한 코덱 지원 여부 확인 (libx264)
        """
        try:
            # ffmpeg 명령어 실행 가능 여부 확인
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # 버전 정보에서 libx264 지원 확인
                if 'libx264' in result.stdout:
                    logger.info("✅ [FFMPEG] FFmpeg 사용 가능 (libx264 지원)")
                    return True
                else:
                    logger.warning("⚠️ [FFMPEG] FFmpeg는 설치되어 있지만 libx264 코덱이 지원되지 않음")
                    return False
            else:
                logger.warning("⚠️ [FFMPEG] FFmpeg 실행 실패")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ [FFMPEG] FFmpeg 버전 확인 시 타임아웃 발생")
            return False
        except FileNotFoundError:
            logger.warning("⚠️ [FFMPEG] FFmpeg가 설치되어 있지 않거나 PATH에 없습니다")
            return False
        except Exception as e:
            logger.error(f"❌ [FFMPEG] FFmpeg 확인 중 오류 발생: {e}")
            return False
    
    def _validate_video_metadata(self, video_path: str) -> bool:
        """
        OpenCV로 읽은 비디오 메타데이터 유효성 검증
        
        webm 파일에서 OpenCV가 부정확한 메타데이터를 읽는 경우를 감지합니다.
        트랜스코딩 필요 여부를 판단하는 핵심 함수입니다.
        
        Args:
            video_path: 검증할 비디오 파일 경로
            
        Returns:
            bool: 메타데이터가 유효한 경우 True, 트랜스코딩이 필요한 경우 False
            
        검증 기준:
        - 총 프레임 수: 1 이상의 유효한 값
        - FPS: 1 이상 120 이하의 합리적인 값
        - 비디오 스트림 존재 여부
        - 기본적인 프레임 읽기 가능 여부
        
        실제 면접 서비스 고려사항:
        - 엄격한 검증: 정확한 분석을 위한 높은 기준
        - 성능: 빠른 검증을 위해 첫 몇 프레임만 확인
        - 로깅: 문제가 되는 파일 패턴 추적
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.warning(f"⚠️ [METADATA] 비디오 파일을 열 수 없음: {video_path}")
                return False
            
            # 기본 메타데이터 읽기
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 메타데이터 유효성 검사
            is_valid = True
            validation_issues = []
            
            # 프레임 수 검증 (1 이상의 합리적인 값)
            if total_frames <= 0 or total_frames > 1000000:  # 1백만 프레임 = 약 9시간 (30fps 기준)
                is_valid = False
                validation_issues.append(f"비정상적인 프레임 수: {total_frames}")
            
            # FPS 검증 (1-120 fps 범위)
            if fps <= 0 or fps > 120:
                is_valid = False
                validation_issues.append(f"비정상적인 FPS: {fps}")
            
            # 해상도 검증 (최소 160x120, 최대 4K)
            if width <= 0 or height <= 0 or width > 3840 or height > 2160:
                is_valid = False
                validation_issues.append(f"비정상적인 해상도: {width}x{height}")
            
            # 실제 프레임 읽기 테스트 (첫 프레임만)
            ret, frame = cap.read()
            if not ret or frame is None:
                is_valid = False
                validation_issues.append("첫 프레임 읽기 실패")
            
            cap.release()
            
            if is_valid:
                logger.info(f"✅ [METADATA] 비디오 메타데이터 유효: {total_frames}프레임, {fps:.1f}FPS, {width}x{height}")
                return True
            else:
                logger.warning(f"⚠️ [METADATA] 비디오 메타데이터 무효: {', '.join(validation_issues)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [METADATA] 메타데이터 검증 중 오류: {e}")
            return False
    
    def _transcode_webm_to_mp4(self, input_path: str, output_path: str) -> bool:
        """
        FFmpeg을 사용하여 webm 파일을 mp4로 트랜스코딩
        
        시선 분석에 최적화된 설정으로 webm을 mp4(H.264)로 변환합니다.
        OpenCV 호환성 문제를 해결하는 핵심 기능입니다.
        
        Args:
            input_path: 입력 webm 파일 경로
            output_path: 출력 mp4 파일 경로
            
        Returns:
            bool: 트랜스코딩 성공 여부
            
        FFmpeg 옵션 설명:
        - c:v libx264: H.264 비디오 코덱 (OpenCV 호환성 최고)
        - preset faster: 빠른 인코딩 (품질 vs 속도 균형)
        - crf 28: 적절한 품질 (시선 분석용, 18-32 범위)
        - s 640x480: 해상도 최적화 (시선 분석 충분)
        - r 15: 프레임레이트 제한 (처리 속도 향상)
        - an: 오디오 제거 (시선 분석 불필요)
        - movflags +faststart: 웹 스트리밍 최적화
        
        실제 면접 서비스 고려사항:
        - 변환 시간: 1분 영상 기준 10-30초 소요
        - 파일 크기: 원본의 30-50% 수준
        - CPU 사용: 멀티코어 활용 최적화
        - 메모리: 피크 시 200-500MB 사용
        """
        try:
            transcode_start = time.time()
            logger.info(f"🔄 [TRANSCODE] webm → mp4 변환 시작: {input_path}")
            
            # 최적화된 FFmpeg 명령어 구성
            ffmpeg_command = [
                'ffmpeg',
                '-y',  # 출력 파일 덮어쓰기
                '-i', input_path,  # 입력 파일
                
                # 비디오 인코딩 옵션
                '-c:v', 'libx264',     # H.264 코덱
                '-preset', 'faster',    # 인코딩 속도 우선
                '-crf', '28',          # 품질 설정 (시선 분석용)
                
                # 해상도 및 프레임레이트 최적화
                '-s', '640x480',       # 시선 분석 충분 해상도
                '-r', '15',            # 프레임레이트 제한 (처리 속도)
                
                # 오디오 및 기타 옵션
                '-an',                 # 오디오 제거
                '-movflags', '+faststart',  # 웹 최적화
                
                # 출력 파일
                output_path
            ]
            
            # FFmpeg 실행 (타임아웃 포함)
            result = subprocess.run(
                ffmpeg_command,
                capture_output=True,
                text=True,
                timeout=120,  # 2분 타임아웃 (대용량 파일 고려)
                check=False   # returncode 수동 확인
            )
            
            logger.info(f"📊 [TRANSCODE_FFMPEG_OUTPUT] stdout: {result.stdout[:1000]}...") # 🆕 추가
            logger.error(f"❌ [TRANSCODE_FFMPEG_OUTPUT] stderr: {result.stderr[:1000]}...") # 🆕 추가 (오류가 아니어도 로깅)
            
            transcode_duration = time.time() - transcode_start
            
            # 트랜스코딩 성공 여부 확인
            if result.returncode == 0:
                # 출력 파일 존재 및 크기 확인
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    input_size = SecureFileManager.get_file_size_mb(input_path)
                    output_size = SecureFileManager.get_file_size_mb(output_path)
                    compression_ratio = (output_size / input_size) * 100 if input_size > 0 else 0
                    
                    logger.info(f"✅ [TRANSCODE] 변환 성공 - {transcode_duration:.1f}초 소요")
                    logger.info(f"📊 [TRANSCODE] 크기 변화: {input_size:.1f}MB → {output_size:.1f}MB ({compression_ratio:.1f}%)")
                    return True
                else:
                    logger.error("❌ [TRANSCODE] 출력 파일이 생성되지 않았거나 비어있음")
                    return False
            else:
                # FFmpeg 오류 메시지 로깅
                logger.error(f"❌ [TRANSCODE] FFmpeg 실행 실패 (코드: {result.returncode})")
                logger.error(f"❌ [TRANSCODE] stderr: {result.stderr[:500]}...")  # 처음 500자만
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ [TRANSCODE] 트랜스코딩 시간 초과 (2분)")
            return False
        except FileNotFoundError:
            logger.error("❌ [TRANSCODE] FFmpeg를 찾을 수 없습니다")
            return False
        except Exception as e:
            logger.error(f"❌ [TRANSCODE] 트랜스코딩 중 예상치 못한 오류: {e}")
            return False
    
    def download_video_from_s3(self, bucket: str, key: str, local_path: str) -> None:
        """
        S3에서 동영상을 안전하게 다운로드
        
        Args:
            bucket: S3 버킷 이름
            key: S3 객체 키 (파일 경로)
            local_path: 로컬 저장 경로
            
        Raises:
            FileNotFoundError: S3에 파일이 없는 경우
            Exception: 다운로드 실패 시
            
        실제 면접 서비스 고려사항:
        - 대용량 파일: 청크 단위 다운로드 권장
        - 네트워크 안정성: 재시도 로직 필요
        - 진행률 추적: 실시간 진행률 업데이트
        - 보안: 다운로드 후 원본 파일 접근 로그 기록
        """
        try:
            logger.info(f"📥 [DOWNLOAD] S3에서 다운로드 시작: s3://{bucket}/{key}")
            start_time = time.time()
            
            # S3에서 로컬 파일로 다운로드
            self.s3_client.download_file(bucket, key, local_path)
            
            # 다운로드 완료 정보
            download_time = time.time() - start_time
            file_size_mb = SecureFileManager.get_file_size_mb(local_path)
            
            logger.info(f"✅ [DOWNLOAD] 다운로드 완료: {local_path}")
            logger.info(f"📊 [DOWNLOAD] 소요시간: {download_time:.1f}초, 크기: {file_size_mb:.1f}MB")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"S3에서 파일을 찾을 수 없습니다: s3://{bucket}/{key}")
            else:
                raise Exception(f"S3 다운로드 오류 ({error_code}): {e}")
                
        except Exception as e:
            logger.error(f"❌ [DOWNLOAD] 동영상 다운로드 실패: {e}")
            raise Exception(f"동영상 다운로드 중 오류 발생: {str(e)}")
    
    def calculate_jitter_score(self, gaze_points: List[Tuple[float, float]]) -> int:
        """
        시선 흔들림 점수 계산 (0-100점, 높을수록 안정적)
        
        알고리즘:
        1. x, y 좌표별 표준편차 계산
        2. 평균 표준편차를 흔들림 지표로 사용
        3. 임계값 기반으로 0-100점 스케일링
        
        Args:
            gaze_points: 시선 포인트 리스트 [(x, y), ...]
            
        Returns:
            int: 흔들림 점수 (0-100점)
            
        실제 면접 서비스에서의 활용:
        - 긴장도 측정: 높은 jitter = 긴장 상태
        - 집중도 평가: 낮은 jitter = 안정적 집중
        - 개선 피드백: 구체적인 점수로 개선점 제시
        
        튜닝 가이드:
        - max_jitter: 최대 허용 흔들림 (높을수록 관대한 평가)
        - min_jitter: 최소 흔들림 (낮을수록 엄격한 평가)
        """
        if len(gaze_points) < 10:
            logger.warning("⚠️ [JITTER] 시선 데이터 부족으로 기본 점수 반환")
            return 50  # 데이터 부족 시 중간 점수
        
        # 시선 포인트를 numpy 배열로 변환
        arr = np.array(gaze_points)
        
        # x, y 좌표별 표준편차 계산
        jitter_x = np.std(arr[:, 0])
        jitter_y = np.std(arr[:, 1])
        jitter = (jitter_x + jitter_y) / 2
        
        # 점수 계산 (임계값 기반 스케일링)
        max_jitter = GazeConfig.JITTER_THRESHOLDS['poor']     # 50.0
        min_jitter = GazeConfig.JITTER_THRESHOLDS['excellent'] # 0.5
        
        if jitter <= min_jitter:
            score = 100  # 매우 안정적
        elif jitter >= max_jitter:
            score = 0    # 매우 불안정
        else:
            # 선형 스케일링
            score = int(100 * (1 - (jitter - min_jitter) / (max_jitter - min_jitter)))
        
        score = max(0, min(100, score))  # 0-100 범위 보장
        
        logger.debug(f"📊 [JITTER] 흔들림 계산: jitter={jitter:.2f}, score={score}")
        return score
    
    def calculate_gaze_compliance_score(self, gaze_points: List[Tuple[float, float]], 
                                       allowed_range: Dict[str, float]) -> int:
        """
        시선 범위 준수 점수 계산 (0-100점)
        
        캘리브레이션 시 설정된 허용 범위 내에 시선이 얼마나 머물렀는지 계산합니다.
        이는 면접자의 집중도와 아이컨택 능력을 평가하는 핵심 지표입니다.
        
        Args:
            gaze_points: 시선 포인트 리스트
            allowed_range: 허용 시선 범위 {'left_bound', 'right_bound', 'top_bound', 'bottom_bound'}
            
        Returns:
            int: 범위 준수 점수 (0-100점)
            
        실제 면접 서비스에서의 의미:
        - 높은 점수: 면접관을 지속적으로 응시 (좋은 아이컨택)
        - 낮은 점수: 시선이 자주 분산 (집중력 부족, 긴장감)
        
        개선 피드백 가이드:
        - 90점 이상: "훌륭한 아이컨택"
        - 70-89점: "양호한 집중도"  
        - 50-69점: "개선 가능"
        - 50점 미만: "집중력 향상 필요"
        """
        if not gaze_points or not all(allowed_range.values()) or len(gaze_points) < 10:
            logger.warning("⚠️ [COMPLIANCE] 유효하지 않은 데이터로 기본 점수 반환")
            return 50
        
        # 허용 범위 내 포인트 수 계산
        in_range_count = 0
        for x, y in gaze_points:
            if (allowed_range['left_bound'] <= x <= allowed_range['right_bound'] and
                allowed_range['top_bound'] <= y <= allowed_range['bottom_bound']):
                in_range_count += 1
        
        # 준수율 계산 (0.0 ~ 1.0)
        compliance_ratio = in_range_count / len(gaze_points)
        
        # 100점 스케일로 변환
        compliance_score = int(compliance_ratio * 100)
        
        logger.debug(f"📊 [COMPLIANCE] 범위 준수: {in_range_count}/{len(gaze_points)} = {compliance_score}%")
        return compliance_score
    
    def calculate_allowed_gaze_range(self, calibration_points: List[Tuple[float, float]]) -> Dict[str, float]:
        """
        캘리브레이션 포인트를 기반으로 허용 시선 범위 계산
        
        4포인트 캘리브레이션 데이터로부터 시선이 허용되는 사각형 영역을 정의합니다.
        실제 면접에서 이 범위를 벗어나면 집중도가 떨어진 것으로 판단합니다.
        
        Args:
            calibration_points: 4개의 캘리브레이션 포인트 [(x,y), ...]
                               순서: [top_left, top_right, bottom_left, bottom_right]
            
        Returns:
            Dict[str, float]: 허용 범위 {'left_bound', 'right_bound', 'top_bound', 'bottom_bound'}
            
        Raises:
            ValueError: 캘리브레이션 포인트가 4개가 아닌 경우
            
        알고리즘:
        1. 4포인트의 최소/최대 x, y 좌표 계산
        2. 5% 마진 추가 (자연스러운 시선 움직임 허용)
        3. 사각형 범위 반환
        
        실제 면접 서비스 튜닝:
        - 마진 조정: 엄격한 평가(3%) vs 관대한 평가(10%)
        - 개인화: 사용자별 다른 마진 적용 가능
        - 적응형: 면접 진행에 따라 범위 동적 조정
        """
        if len(calibration_points) != 4:
            raise ValueError(f"4개의 캘리브레이션 포인트가 필요합니다. 현재: {len(calibration_points)}개")
        
        # numpy 배열로 변환하여 계산 편의성 확보
        points = np.array(calibration_points)
        
        # 바운딩 박스 계산
        min_x, max_x = np.min(points[:, 0]), np.max(points[:, 0])
        min_y, max_y = np.min(points[:, 1]), np.max(points[:, 1])
        
        # 마진 추가 (자연스러운 시선 움직임 허용)
        margin_rate = 0.05  # 5% 마진
        x_margin = (max_x - min_x) * margin_rate
        y_margin = (max_y - min_y) * margin_rate
        
        allowed_range = {
            'left_bound': min_x - x_margin,
            'right_bound': max_x + x_margin,
            'top_bound': min_y - y_margin,
            'bottom_bound': max_y + y_margin
        }
        
        logger.info(f"📐 [RANGE] 허용 시선 범위 계산 완료: "
                   f"X({allowed_range['left_bound']:.1f}~{allowed_range['right_bound']:.1f}), "
                   f"Y({allowed_range['top_bound']:.1f}~{allowed_range['bottom_bound']:.1f})")
        
        return allowed_range
    
    def apply_dynamic_scaling(self, original_range: Dict[str, float], 
                            initial_face_size: float, current_face_size: float) -> Dict[str, float]:
        """
        얼굴 크기 변화에 따른 동적 범위 스케일링
        
        사용자가 캘리브레이션 시점보다 카메라에 가까이 오거나 멀어질 때
        허용 시선 범위를 적절히 조정하여 공정한 평가를 보장합니다.
        
        Args:
            original_range: 원본 허용 범위
            initial_face_size: 캘리브레이션 시 얼굴 크기 (픽셀)
            current_face_size: 현재 프레임의 얼굴 크기 (픽셀)
            
        Returns:
            Dict[str, float]: 스케일링된 허용 범위
            
        스케일링 원리:
        - 얼굴이 커짐 (가까워짐) → 시선 범위 확대
        - 얼굴이 작아짐 (멀어짐) → 시선 범위 축소
        - 범위 중심점은 유지하면서 크기만 조정
        
        실제 면접 서비스에서의 중요성:
        - 공정성: 거리에 상관없이 일관된 평가
        - 사용자 경험: 자연스러운 자세 변화 허용
        - 정확도: 실제 시선 의도를 정확히 반영
        """
        if initial_face_size <= 0 or current_face_size <= 0:
            logger.warning("⚠️ [SCALING] 유효하지 않은 얼굴 크기로 원본 범위 반환")
            return original_range
        
        # 스케일 팩터 계산
        scale_factor = current_face_size / initial_face_size
        
        # 원본 범위의 중심점과 크기 계산
        center_x = (original_range['left_bound'] + original_range['right_bound']) / 2
        center_y = (original_range['top_bound'] + original_range['bottom_bound']) / 2
        
        original_width = original_range['right_bound'] - original_range['left_bound']
        original_height = original_range['bottom_bound'] - original_range['top_bound']
        
        # 스케일링된 새로운 크기
        new_width = original_width * scale_factor
        new_height = original_height * scale_factor
        
        # 중심점 유지하면서 새로운 범위 계산
        scaled_range = {
            'left_bound': center_x - new_width / 2,
            'right_bound': center_x + new_width / 2,
            'top_bound': center_y - new_height / 2,
            'bottom_bound': center_y + new_height / 2
        }
        
        logger.debug(f"📏 [SCALING] 동적 스케일링 적용: "
                    f"scale_factor={scale_factor:.2f}, "
                    f"크기변화={original_width:.1f}→{new_width:.1f}")
        
        return scaled_range
    
    def generate_feedback(self, final_score: int, jitter_score: int, 
                         compliance_score: int, stability_rating: str) -> str:
        """
        AI 기반 개인화된 피드백 메시지 생성
        
        분석 결과를 바탕으로 구체적이고 실행 가능한 피드백을 제공합니다.
        실제 면접 서비스에서 사용자의 면접 스킬 향상을 돕는 핵심 기능입니다.
        
        Args:
            final_score: 최종 종합 점수
            jitter_score: 시선 안정성 점수
            compliance_score: 범위 준수 점수
            stability_rating: 안정성 등급
            
        Returns:
            str: 개인화된 피드백 메시지
            
        피드백 우선순위:
        1. 범위 준수 문제 (아이컨택 부족)
        2. 시선 안정성 문제 (흔들림 과다)
        3. 종합적 개선 방향 제시
        
        실제 면접 서비스 확장 방안:
        - 개인화: 사용자 이력 기반 맞춤 피드백
        - 다국어: 언어별 문화적 특성 반영
        - 상세화: 구체적 개선 액션 아이템 제시
        """
        # 우선순위별 문제점 진단
        if compliance_score < 50:
            return (f"시선이 화면 중앙을 벗어나는 비율이 높습니다 (화면 주시 점수: {compliance_score}점). "
                   f"카메라 렌즈를 면접관의 눈이라고 생각하고 꾸준히 응시하는 연습이 필요합니다. "
                   f"면접 중 노트를 보거나 주변을 둘러보는 것을 최소화하세요.")
        
        elif jitter_score < 60:
            return (f"시선이 안정적이지 못하고 흔들리는 경향이 있습니다 (시선 안정 점수: {jitter_score}점). "
                   f"편안한 자세로 긴장을 풀고 화면의 한 지점에 시선을 고정하는 연습을 해보세요. "
                   f"심호흡을 통해 긴장을 완화하고, 답변할 때는 차분하게 말하는 것이 도움됩니다.")
        
        elif final_score >= 85:
            return (f"매우 안정적인 시선 처리를 보였습니다! 면접관과의 아이컨택이 자연스럽고 집중도가 높습니다. "
                   f"이런 안정적인 시선 유지는 면접에서 자신감과 진정성을 전달하는 데 큰 도움이 됩니다. "
                   f"현재 수준을 유지하시면 됩니다.")
        
        elif final_score >= 70:
            return (f"전반적으로 좋은 시선 처리입니다. 조금 더 안정적인 시선 유지를 연습하면 더욱 좋겠습니다. "
                   f"면접관을 바라볼 때 3-5초 정도 시선을 유지한 후 자연스럽게 시선을 이동하는 패턴을 연습해보세요.")
        
        else:
            return (f"시선 처리에 약간의 개선이 필요합니다. 면접관을 바라보는 연습과 긴장 완화가 도움될 것입니다. "
                   f"거울을 보면서 아이컨택 연습을 하거나, 모의 면접을 통해 자연스러운 시선 처리를 익혀보세요. "
                   f"규칙적인 연습으로 충분히 개선할 수 있습니다.")
    
    def analyze_video_from_s3(self,
                     bucket: str,
                     key: str,
                     calibration_points: List[Tuple[float, float]],
                     initial_face_size: Optional[float] = None,
                     frame_skip: int = None) -> GazeAnalysisResult:
        """
        S3 동영상의 종합적인 시선 안정성 분석
        
        이 메서드는 시선 분석의 전체 워크플로우를 관리하는 핵심 함수입니다.
        실제 면접 서비스에서 호출되는 메인 분석 엔진입니다.
        
        분석 과정:
        1. S3에서 동영상 안전 다운로드
        2. 프레임별 얼굴/시선 추적
        3. 캘리브레이션 기반 허용 범위 계산
        4. 동적 스케일링 적용 (거리 변화 보정)
        5. 시선 안정성 점수 계산
        6. AI 피드백 생성
        
        Args:
            bucket: S3 버킷 이름
            key: S3 객체 키 (동영상 파일 경로)
            calibration_points: 4포인트 캘리브레이션 데이터
            initial_face_size: 캘리브레이션 시 얼굴 크기 (선택적)
            frame_skip: 프레임 스킵 간격 (성능 튜닝용, 기본값: 10)
            
        Returns:
            GazeAnalysisResult: 종합 분석 결과
            
        Raises:
            FileNotFoundError: S3 파일이 없는 경우
            Exception: 분석 실패 시
            
        실제 면접 서비스 성능 고려사항:
        - 처리 시간: 1분 동영상 기준 10-30초 소요 (frame_skip에 따라)
        - 메모리 사용: 피크 시 500MB-1GB (동영상 크기에 따라)
        - CPU 사용: MediaPipe GPU 가속 권장
        - 동시 처리: 서버당 3-5개 동시 분석 권장
        
        모니터링 지표:
        - 분석 성공률: 95% 이상 목표
        - 평균 처리 시간: 동영상 길이의 30% 이내
        - 에러율: 5% 이하 유지
        """
        # 설정값 적용
        if frame_skip is None:
            frame_skip = GazeConfig.get_frame_skip('balanced')
        
        logger.info(f"🎬 [ANALYZE] 동영상 분석 시작: s3://{bucket}/{key}")
        analysis_start_time = time.time()
        
        # 안전한 임시 파일 관리 (webm 파일)
        with SecureFileManager.secure_temp_file('.webm') as video_path:
            try:
                # === 1단계: S3에서 동영상 다운로드 ===
                self.download_video_from_s3(bucket, key, video_path)
                
                # 파일 유효성 검증
                validation = FileValidator.validate_video_file(video_path)
                if not validation['valid']:
                    raise Exception(f"동영상 파일 검증 실패: {', '.join(validation['errors'])}")
                
                # === 2단계: FFmpeg 트랜스코딩 (ValidationError 근본 해결) ===
                # 메타데이터 검증 및 FFmpeg 가용성 확인
                metadata_valid = self._validate_video_metadata(video_path)
                ffmpeg_available = self._check_ffmpeg_availability()
                
                final_video_path = video_path  # 기본값: 원본 webm 파일
                transcoded_success = False
                
                if ffmpeg_available:
                    # FFmpeg 사용 가능한 경우 트랜스코딩 시도
                    if not metadata_valid:
                        logger.info("🔄 [ANALYZE] 메타데이터 오류로 FFmpeg 트랜스코딩 시작")
                    else:
                        logger.info("🔄 [ANALYZE] 안정성을 위한 FFmpeg 트랜스코딩 실행")
                    
                    # 임시 MP4 파일 경로 생성
                    import tempfile
                    mp4_path = video_path.replace('.webm', '_transcoded.mp4')
                    
                    try:
                        if self._transcode_webm_to_mp4(video_path, mp4_path):
                            # 트랜스코딩 성공 - MP4 파일 메타데이터 검증
                            if self._validate_video_metadata(mp4_path):
                                logger.info("✅ [ANALYZE] FFmpeg 트랜스코딩 성공 - 메타데이터 유효")
                                final_video_path = mp4_path
                                transcoded_success = True
                            else:
                                logger.warning("⚠️ [ANALYZE] 트랜스코딩은 성공했으나 MP4 메타데이터 여전히 문제")
                                # MP4 파일 정리
                                if os.path.exists(mp4_path):
                                    os.remove(mp4_path)
                        else:
                            logger.warning("⚠️ [ANALYZE] FFmpeg 트랜스코딩 실패")
                    except Exception as e:
                        logger.error(f"❌ [ANALYZE] 트랜스코딩 중 오류 발생: {e}")
                        if os.path.exists(mp4_path):
                            os.remove(mp4_path)
                else:
                    logger.warning("⚠️ [ANALYZE] FFmpeg를 사용할 수 없음")
                
                # 결과 로깅
                if transcoded_success:
                    logger.info("📁 [ANALYZE] 트랜스코딩된 MP4 파일 사용")
                else:
                    logger.info("📁 [ANALYZE] 원본 WebM 파일 사용 (메타데이터 보정 적용 예정)")
                
                # === 3단계: 허용 시선 범위 계산 ===
                logger.info(f"🎯 [ANALYZE] Calibration points: {calibration_points}")
                original_allowed_range = self.calculate_allowed_gaze_range(calibration_points)
                current_allowed_range = original_allowed_range.copy()
                logger.info(f"🎯 [ANALYZE] Calculated allowed range: {original_allowed_range}")
                
                # === 4단계: 동영상 프레임 분석 (최종 결정된 파일 사용) ===
                cap = cv2.VideoCapture(final_video_path)
                if not cap.isOpened():
                    raise Exception(f"동영상을 열 수 없습니다: {final_video_path}")
                
                # 🆕 동영상 정보 유효성 검사 및 처리
                raw_total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                raw_fps = cap.get(cv2.CAP_PROP_FPS)

                corrected_total_frames = raw_total_frames
                corrected_fps = raw_fps

                if corrected_total_frames <= 0:
                    logger.warning(f"⚠️ [ANALYZE] 동영상 총 프레임 수가 유효하지 않습니다: {corrected_total_frames}. 기본값 1로 설정.")
                    corrected_total_frames = 1 # Corrected value

                if corrected_fps <= 0:
                    logger.warning(f"⚠️ [ANALYZE] 동영상 FPS가 유효하지 않습니다: {corrected_fps}. 기본값 30으로 설정.")
                    corrected_fps = 30.0 # Corrected value

                duration = corrected_total_frames / corrected_fps

                logger.info(f"📹 [ANALYZE] 동영상 정보: {corrected_total_frames}프레임, {corrected_fps:.1f}FPS, {duration:.1f}초 (원본: {raw_total_frames}프레임, {raw_fps:.1f}FPS)")

                # duration = total_frames / fps if fps > 0 else 0
                
                # 분석 변수 초기화
                gaze_points = []
                analyzed_count = 0
                frame_count = 0
                face_sizes = []  # 동적 스케일링용
                
                # === 4단계: 프레임별 시선 추적 ===
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    frame_count += 1
                    
                    # 프레임 스킵 적용 (성능 최적화)
                    if frame_count % frame_skip != 0:
                        continue
                    
                    h, w, _ = frame.shape
                    
                    # MediaPipe 얼굴 분석
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = self.face_mesh.process(rgb_frame)
                    
                    if results.multi_face_landmarks:
                        for face_landmarks in results.multi_face_landmarks:
                            # 시선 포인트 계산 (부모 클래스 메서드 사용)
                            gaze_point = self.get_gaze_point_3d(face_landmarks.landmark, w, h)
                            
                            # 얼굴 크기 측정 (부모 클래스 메서드 사용)
                            current_face_size = self._estimate_face_size(face_landmarks.landmark, w, h)
                            
                            if gaze_point and current_face_size > 0:
                                gaze_points.append(gaze_point)
                                face_sizes.append(current_face_size)
                                analyzed_count += 1
                                
                                # === 5단계: 동적 스케일링 적용 ===
                                if initial_face_size and initial_face_size > 0:
                                    current_allowed_range = self.apply_dynamic_scaling(
                                        original_allowed_range, initial_face_size, current_face_size
                                    )
                
                cap.release()
                
                # === 6단계: 분석 결과 검증 ===
                if not self.validate_gaze_data(gaze_points):
                    raise Exception("충분한 시선 데이터를 수집하지 못했습니다. 얼굴이 명확히 보이는 동영상으로 다시 시도해주세요.")
                
                # === 7단계: 점수 계산 ===
                jitter_score = self.calculate_jitter_score(gaze_points)
                compliance_score = self.calculate_gaze_compliance_score(gaze_points, current_allowed_range)
                
                # 최종 종합 점수 (가중 평균)
                weights = GazeConfig.SCORE_WEIGHTS
                final_score = int((jitter_score * weights['jitter']) + 
                                (compliance_score * weights['compliance']))
                
                # 범위 내 프레임 통계
                in_range_count = sum(1 for x, y in gaze_points 
                                   if (current_allowed_range['left_bound'] <= x <= current_allowed_range['right_bound'] and
                                       current_allowed_range['top_bound'] <= y <= current_allowed_range['bottom_bound']))
                in_range_ratio = in_range_count / analyzed_count if analyzed_count > 0 else 0
                
                # === 8단계: 안정성 등급 결정 ===
                if final_score >= 85:
                    stability_rating = "우수"
                elif final_score >= 70:
                    stability_rating = "양호"
                elif final_score >= 50:
                    stability_rating = "보통"
                else:
                    stability_rating = "개선 필요"
                
                # === 9단계: AI 피드백 생성 ===
                feedback = self.generate_feedback(final_score, jitter_score, compliance_score, stability_rating)
                
                # === 10단계: 결과 정리 ===
                analysis_duration = time.time() - analysis_start_time
                
                # 시각화용 시선 포인트 샘플링 (프론트엔드 성능 고려)
                max_points = 50
                if len(gaze_points) > max_points:
                    step = len(gaze_points) // max_points
                    sampled_points = gaze_points[::step]
                else:
                    sampled_points = gaze_points
                
                logger.info(f"✅ [ANALYZE] 분석 완료: 점수={final_score}, 소요시간={analysis_duration:.1f}초")
                logger.info(f"🎯 [ANALYZE] Final allowed range in result: {current_allowed_range}")
                
                # === 11단계: 분석 완료 ===
                
                return GazeAnalysisResult(
                    gaze_score=final_score,
                    total_frames=corrected_total_frames,
                    analyzed_frames=analyzed_count,
                    in_range_frames=in_range_count,
                    in_range_ratio=in_range_ratio,
                    jitter_score=jitter_score,
                    compliance_score=compliance_score,
                    stability_rating=stability_rating,
                    feedback=feedback,
                    gaze_points=sampled_points,
                    allowed_range=current_allowed_range,
                    calibration_points=calibration_points
                )
                
            except Exception as e:
                logger.error(f"❌ [ANALYZE] 분석 실패: {e}")
                raise
            finally:
                # 트랜스코딩된 임시 파일 정리
                if 'transcoded_success' in locals() and transcoded_success and 'mp4_path' in locals():
                    try:
                        if os.path.exists(mp4_path):
                            os.remove(mp4_path)
                            logger.debug(f"🗑️ [CLEANUP] 트랜스코딩된 임시 파일 정리: {mp4_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"⚠️ [CLEANUP] 임시 파일 정리 실패: {cleanup_error}")


# 싱글톤 인스턴스 생성 (기존 API 호환성 유지)
# 실제 면접 서비스에서는 인스턴스 풀링 또는 의존성 주입 고려
gaze_analyzer = GazeAnalyzer()

logger.info("🎯 [MODULE] 시선 분석 모듈 로딩 완료 (리팩토링 버전)")
# === 김원우 작성 끝 ===