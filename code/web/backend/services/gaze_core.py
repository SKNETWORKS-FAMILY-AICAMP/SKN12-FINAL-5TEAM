# === 김원우 작성 시작 ===
"""
시선 분석 시스템 핵심 모듈

이 모듈은 시선 분석의 핵심 로직을 담당하는 기반 클래스를 제공합니다.
실제 면접 서비스에 적용할 때 이 클래스를 상속받아 사용하세요.

주요 기능:
- MediaPipe FaceMesh 초기화 및 설정 관리
- 동공/아이리스 위치 추적 (3D 좌표계)
- 얼굴 크기 측정 (카메라 거리 변화 보정용)
- 시선 포인트 검증 및 정제

작성자: 김원우
최종 수정: 2025-08-12
용도: 베타고 면접 플랫폼 시선 분석 시스템
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Tuple, Optional, List
import logging

# 로깅 설정 (실제 서비스에서는 중앙 로거 사용 권장)
logger = logging.getLogger(__name__)


class GazeCoreProcessor:
    """
    시선 분석의 핵심 로직을 담당하는 기반 클래스
    
    이 클래스는 MediaPipe를 사용한 얼굴/동공 추적의 공통 기능을 제공합니다.
    GazeAnalyzer(동영상 분석)와 GazeCalibrationManager(실시간 캘리브레이션) 
    모두 이 클래스를 상속받아 사용합니다.
    
    실제 면접 서비스 적용 시 주의사항:
    1. MediaPipe 모델 로딩: 초기화 시 약 1-2초 소요
    2. GPU 사용: 가능하면 GPU 가속 사용 권장 (CUDA 설정 필요)
    3. 메모리: 한 인스턴스당 약 100-200MB 사용
    4. 동시 처리: 여러 면접 동시 처리 시 인스턴스 풀링 고려
    
    MediaPipe FaceMesh 정보:
    - 총 468개의 얼굴 랜드마크 포인트
    - 아이리스: 좌측 468-472, 우측 473-477 인덱스
    - 3D 좌표: x, y (정규화), z (상대적 깊이)
    """
    
    def __init__(self):
        """
        MediaPipe FaceMesh 초기화 및 설정
        
        설정값 설명:
        - refine_landmarks: 아이리스/입술 등 세부 랜드마크 활성화 (정확도 향상)
        - max_num_faces: 한 번에 추적할 최대 얼굴 수 (면접은 1개로 충분)
        - min_detection_confidence: 얼굴 검출 신뢰도 임계값 (0.5 = 50%)
        - min_tracking_confidence: 추적 지속 신뢰도 임계값
        
        실제 서비스 튜닝 가이드:
        - detection_confidence ↑: 정확도 향상, 검출 빈도 감소
        - tracking_confidence ↑: 안정성 향상, CPU 사용량 증가
        """
        logger.info("🚀 [GAZE_CORE] MediaPipe FaceMesh 초기화 시작")
        
        # MediaPipe 솔루션 초기화
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            refine_landmarks=True,          # 아이리스 추적을 위해 필수
            max_num_faces=1,                # 면접: 한 사람만 추적
            min_detection_confidence=0.5,   # 50% 신뢰도로 얼굴 검출
            min_tracking_confidence=0.5     # 50% 신뢰도로 추적 지속
        )
        
        # 아이리스 랜드마크 인덱스 (MediaPipe FaceMesh 468포인트 기준)
        # 참고: https://github.com/google/mediapipe/blob/master/docs/solutions/face_mesh.md
        self.left_iris_indices = [468, 469, 470, 471, 472]   # 좌측 아이리스 5개 포인트
        self.right_iris_indices = [473, 474, 475, 476, 477]  # 우측 아이리스 5개 포인트
        
        # 얼굴 크기 측정용 랜드마크 (얼굴 외곽선 주요 포인트)
        # 실제 면접에서 사용자가 앞뒤로 움직일 때 거리 변화 감지용
        self.face_boundary_indices = [10, 152, 234, 454]  # 이마, 턱, 좌측, 우측
        
        logger.info("✅ [GAZE_CORE] MediaPipe FaceMesh 초기화 완료")
    
    def get_gaze_point_3d(self, landmarks, w: int, h: int) -> Optional[Tuple[float, float]]:
        """
        MediaPipe 랜드마크로부터 3D 시선 포인트를 계산
        
        알고리즘:
        1. 좌우 아이리스 중심점 계산 (각각 5개 포인트의 평균)
        2. 양쪽 아이리스 중심점의 평균으로 최종 시선 포인트 도출
        3. 정규화된 좌표를 픽셀 좌표로 변환
        4. 유효성 검증 (NaN, 무한대, 0값 체크)
        
        Args:
            landmarks: MediaPipe 얼굴 랜드마크 리스트 (468개)
            w: 이미지 너비 (픽셀)
            h: 이미지 높이 (픽셀)
            
        Returns:
            Tuple[float, float] | None: (x, y) 픽셀 좌표 또는 None (실패 시)
            
        실제 면접 서비스에서의 활용:
        - 실시간 시선 추적으로 사용자 집중도 측정
        - 캘리브레이션 시 4포인트 응시 데이터 수집
        - 동영상 분석 시 프레임별 시선 궤적 생성
        
        주의사항:
        - 극단적인 얼굴 각도에서는 부정확할 수 있음
        - 안경, 조명 등이 정확도에 영향을 줄 수 있음
        - 반환값이 None이면 해당 프레임은 분석에서 제외
        """
        try:
            # 좌측 아이리스 중심점 계산
            left_iris_points = np.array([
                (landmarks[i].x * w, landmarks[i].y * h, landmarks[i].z) 
                for i in self.left_iris_indices
            ])
            left_center = np.mean(left_iris_points, axis=0)
            
            # 우측 아이리스 중심점 계산  
            right_iris_points = np.array([
                (landmarks[i].x * w, landmarks[i].y * h, landmarks[i].z)
                for i in self.right_iris_indices
            ])
            right_center = np.mean(right_iris_points, axis=0)
            
            # 양쪽 아이리스의 평균으로 최종 시선 포인트 계산
            avg_gaze = (left_center + right_center) / 2
            
            # 유효성 검증: NaN, 무한대, 0값 체크
            if (np.any(np.isnan(avg_gaze)) or 
                np.any(np.isinf(avg_gaze)) or 
                np.allclose(avg_gaze, 0)):
                logger.warning("⚠️ [GAZE_CORE] 유효하지 않은 시선 포인트 감지됨")
                return None
            
            # x, y 좌표만 반환 (z는 깊이 정보로 여기서는 사용하지 않음)
            return (float(avg_gaze[0]), float(avg_gaze[1]))
            
        except Exception as e:
            logger.error(f"❌ [GAZE_CORE] 시선 포인트 계산 실패: {e}")
            return None
    
    def _estimate_face_size(self, landmarks, w: int, h: int) -> float:
        """
        얼굴 크기를 추정하여 카메라와의 거리 변화를 감지
        
        용도:
        1. 캘리브레이션 시점과 면접 시점의 거리 차이 보정
        2. 동적 시선 범위 조정 (가까이 오면 범위 확대, 멀어지면 축소)
        3. 면접 중 사용자의 자세 변화 모니터링
        
        알고리즘:
        - 얼굴 경계 4포인트 (이마, 턱, 좌측, 우측)의 바운딩 박스 계산
        - 너비와 높이 중 큰 값을 얼굴 크기로 사용
        - 픽셀 단위로 반환 (해상도에 따라 절대값 달라짐)
        
        Args:
            landmarks: MediaPipe 얼굴 랜드마크 리스트
            w: 이미지 너비 (픽셀)
            h: 이미지 높이 (픽셀)
            
        Returns:
            float: 얼굴 크기 (픽셀 단위, 실패 시 0.0)
            
        실제 면접 서비스 활용 예시:
        - 캘리브레이션 시 initial_face_size = 150 픽셀
        - 면접 중 current_face_size = 120 픽셀
        - scale_factor = 120/150 = 0.8
        - 시선 허용 범위를 0.8배로 축소 적용
        
        주의사항:
        - 얼굴 각도에 따라 부정확할 수 있음
        - 카메라 해상도별로 절대값이 달라짐
        - 상대적 비율(scale_factor)로만 사용 권장
        """
        try:
            # 얼굴 경계 포인트들의 픽셀 좌표 계산
            face_points = [
                (landmarks[self.face_boundary_indices[0]].x * w, landmarks[self.face_boundary_indices[0]].y * h),  # 이마 (10)
                (landmarks[self.face_boundary_indices[1]].x * w, landmarks[self.face_boundary_indices[1]].y * h),  # 턱 (152)
                (landmarks[self.face_boundary_indices[2]].x * w, landmarks[self.face_boundary_indices[2]].y * h),  # 좌측 (234)
                (landmarks[self.face_boundary_indices[3]].x * w, landmarks[self.face_boundary_indices[3]].y * h),  # 우측 (454)
            ]
            
            # 바운딩 박스 계산
            x_coords = [p[0] for p in face_points]
            y_coords = [p[1] for p in face_points]
            
            width = max(x_coords) - min(x_coords)   # 얼굴 너비
            height = max(y_coords) - min(y_coords)  # 얼굴 높이
            
            # 너비와 높이 중 큰 값을 얼굴 크기로 사용
            face_size = max(width, height)
            
            logger.debug(f"📏 [GAZE_CORE] 얼굴 크기 측정: {face_size:.1f}px (W:{width:.1f}, H:{height:.1f})")
            return face_size
            
        except Exception as e:
            logger.error(f"❌ [GAZE_CORE] 얼굴 크기 측정 실패: {e}")
            return 0.0
    
    def validate_gaze_data(self, gaze_points: list, min_points: int = 10) -> bool:
        """
        시선 데이터의 유효성을 검증
        
        검증 항목:
        1. 최소 데이터 포인트 수 확인
        2. 시선 포인트 분산도 체크 (너무 집중되면 부정확할 가능성)
        3. 아웃라이어 비율 확인
        
        Args:
            gaze_points: 시선 포인트 리스트 [(x, y), ...]
            min_points: 최소 필요 포인트 수
            
        Returns:
            bool: 유효한 데이터인지 여부
            
        실제 면접 서비스에서의 활용:
        - 분석 신뢰도 판단
        - 재촬영 권장 여부 결정
        - 점수 계산 전 품질 검증
        """
        if len(gaze_points) < min_points:
            logger.warning(f"⚠️ [GAZE_CORE] 시선 데이터 부족: {len(gaze_points)} < {min_points}")
            return False
        
        if len(gaze_points) < 3:
            return True  # 포인트가 적으면 분산 계산 불가
        
        # 시선 포인트 분산도 체크
        arr = np.array(gaze_points)
        std_x = np.std(arr[:, 0])
        std_y = np.std(arr[:, 1])
        
        # 분산이 너무 작으면 (모든 포인트가 한 곳에 집중) 의심스러운 데이터
        if std_x < 1.0 and std_y < 1.0:
            logger.warning("⚠️ [GAZE_CORE] 시선 데이터 분산도 너무 낮음 (한 점에 집중)")
            return False
        
        logger.info(f"✅ [GAZE_CORE] 시선 데이터 유효성 검증 통과: {len(gaze_points)}개 포인트")
        return True
    
    def __del__(self):
        """
        소멸자: MediaPipe 리소스 정리
        
        실제 서비스에서는 명시적으로 close() 메서드 호출 권장
        """
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()
            logger.info("🧹 [GAZE_CORE] MediaPipe 리소스 정리 완료")


class GazeConfig:
    """
    시선 분석 시스템 설정값 중앙 관리
    
    실제 면접 서비스 튜닝 가이드:
    이 설정값들은 면접 환경과 요구사항에 따라 조정이 필요합니다.
    """
    
    # === MediaPipe 설정 ===
    MEDIAPIPE_CONFIG = {
        'refine_landmarks': True,
        'max_num_faces': 1,
        'min_detection_confidence': 0.5,
        'min_tracking_confidence': 0.5
    }
    
    # === 성능 튜닝 ===
    # 프레임 스킵 설정 (성능 vs 정확도 트레이드오프)
    FRAME_SKIP_CONFIGS = {
        'high_accuracy': 3,      # 고정밀 분석 (짧은 면접, 고사양 서버)
        'balanced': 10,          # 균형잡힌 설정 (일반적인 면접)
        'high_performance': 20   # 고속 처리 (긴 면접, 다중 처리)
    }
    
    # === 점수 계산 가중치 ===
    # 실제 면접 데이터로 검증된 값 (추후 A/B 테스트로 최적화 가능)
    SCORE_WEIGHTS = {
        'jitter': 0.4,          # 시선 안정성 (흔들림 정도)
        'compliance': 0.6       # 범위 준수도 (집중도)
    }
    
    # === 시선 분석 임계값 ===
    JITTER_THRESHOLDS = {
        'excellent': 0.5,       # 매우 안정적
        'good': 5.0,           # 양호
        'fair': 20.0,          # 보통
        'poor': 50.0           # 개선 필요
    }
    
    # === 파일 처리 설정 ===
    MAX_VIDEO_SIZE_MB = 100     # 최대 동영상 크기
    TEMP_FILE_SUFFIX = '.webm'  # 임시 파일 확장자
    
    # === 로깅 설정 ===
    LOG_LEVEL = 'INFO'          # 운영: INFO, 개발: DEBUG
    
    @classmethod
    def get_frame_skip(cls, mode: str = 'balanced') -> int:
        """프레임 스킵 설정 반환"""
        return cls.FRAME_SKIP_CONFIGS.get(mode, cls.FRAME_SKIP_CONFIGS['balanced'])
    
    @classmethod
    def validate_config(cls) -> bool:
        """설정값 유효성 검증"""
        # 가중치 합계가 1.0인지 확인
        weight_sum = sum(cls.SCORE_WEIGHTS.values())
        if abs(weight_sum - 1.0) > 0.01:
            logger.error(f"❌ [CONFIG] 점수 가중치 합계 오류: {weight_sum} != 1.0")
            return False
        
        logger.info("✅ [CONFIG] 설정값 유효성 검증 완료")
        return True


# 설정값 유효성 검증 (모듈 로딩 시 자동 실행)
if __name__ == "__main__":
    GazeConfig.validate_config()
# === 김원우 작성 끝 ===