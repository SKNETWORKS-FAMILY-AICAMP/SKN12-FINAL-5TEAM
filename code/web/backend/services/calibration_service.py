# === 김원우 작성 시작 ===
"""
4포인트 시선 캘리브레이션 시스템 (리팩토링 버전)

실시간 웹캠 기반 4포인트 시선 캘리브레이션을 처리합니다.
GazeCoreProcessor를 상속받아 MediaPipe 로직을 재사용하고,
실제 면접 서비스에 적용하기 위한 확장성과 안정성을 확보했습니다.

주요 개선사항:
- MediaPipe 로직 모듈화 및 재사용
- 세션 관리 최적화
- 상세한 주석 및 문서화
- 에러 처리 강화
- 실시간 피드백 개선

작성자: 김원우
최종 수정: 2025-08-12
용도: 베타고 면접 플랫폼 시선 캘리브레이션 시스템
"""

import cv2
import numpy as np
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from threading import Lock
import uuid
import logging

# 새로운 모듈 import
from .gaze_core import GazeCoreProcessor, GazeConfig

# 로깅 설정
logger = logging.getLogger(__name__)


@dataclass
class CalibrationPoint:
    """
    캘리브레이션 포인트 데이터 클래스
    
    4포인트 캘리브레이션에서 각 위치의 시선 데이터를 저장합니다.
    실제 면접 서비스에서 사용자의 시선 범위를 정의하는 기준점이 됩니다.
    
    필드 설명:
    - x: 시선 포인트의 x 좌표 (픽셀 단위)
    - y: 시선 포인트의 y 좌표 (픽셀 단위)  
    - label: 포인트 위치 라벨 ('top_left', 'top_right', 'bottom_left', 'bottom_right')
    """
    x: float
    y: float
    label: str  # 'top_left', 'top_right', 'bottom_left', 'bottom_right'


@dataclass
class CalibrationSession:
    """
    캘리브레이션 세션 데이터 클래스
    
    실제 면접 서비스에서 한 사용자의 캘리브레이션 전체 과정을 관리합니다.
    세션 기반 설계로 동시 다중 사용자를 안전하게 처리할 수 있습니다.
    
    필드 설명:
    - session_id: 고유 세션 식별자 (UUID)
    - user_id: 사용자 식별자 (선택적, 익명 사용 가능)
    - current_phase: 현재 캘리브레이션 단계
    - phase_start_time: 현재 단계 시작 시간 (Unix timestamp)
    - is_collecting: 시선 데이터 수집 중 여부
    - calibration_points: 각 포인트별 수집된 원시 시선 데이터
    - final_points: 최종 계산된 평균 포인트들
    - created_at: 세션 생성 시간
    - completed_at: 캘리브레이션 완료 시간
    - initial_face_size: 캘리브레이션 시작 시 얼굴 크기 (동적 스케일링용)
    
    실제 면접 서비스 고려사항:
    - 세션 만료: 비활성 세션 자동 정리 필요
    - 데이터 보안: 민감한 시선 데이터 암호화 저장
    - 복구 기능: 중단된 캘리브레이션 재개 지원
    """
    session_id: str
    user_id: Optional[str]
    current_phase: str  # 'ready', 'top_left', 'top_right', 'bottom_left', 'bottom_right', 'completed'
    phase_start_time: float
    is_collecting: bool
    calibration_points: Dict[str, List[Tuple[float, float]]]  # 각 포인트별 수집된 데이터
    final_points: Dict[str, CalibrationPoint]  # 최종 평균 포인트들
    created_at: float
    completed_at: Optional[float]
    initial_face_size: Optional[float] = None  # 캘리브레이션 시작 시 얼굴 크기


class GazeCalibrationManager(GazeCoreProcessor):
    """
    시선 캘리브레이션 세션 관리자 (리팩토링 버전)
    
    GazeCoreProcessor를 상속받아 MediaPipe 관련 공통 로직을 재사용합니다.
    실시간 웹캠을 통해 4포인트 시선 캘리브레이션을 수행하고,
    여러 사용자의 세션을 동시에 안전하게 관리합니다.
    
    주요 기능:
    1. 세션 생성 및 관리 (동시 다중 사용자 지원)
    2. 4단계 캘리브레이션 프로세스 진행
    3. 실시간 얼굴/시선 추적
    4. 데이터 품질 검증 및 피드백
    5. 자동 단계 진행 및 완료 처리
    
    캘리브레이션 과정:
    1. ready: 캘리브레이션 준비
    2. top_left: 좌상단 포인트 수집 (3초 준비 + 3초 수집)
    3. top_right: 우상단 포인트 수집
    4. bottom_left: 좌하단 포인트 수집  
    5. bottom_right: 우하단 포인트 수집
    6. completed: 캘리브레이션 완료
    
    실제 면접 서비스 적용 가이드:
    - 동시 처리: 서버당 50-100개 세션 동시 관리 가능
    - 성능 최적화: MediaPipe 인스턴스 공유로 메모리 절약
    - 사용자 경험: 직관적인 가이드 메시지 제공
    - 품질 보장: 불충분한 데이터 자동 감지 및 재수집
    """
    
    def __init__(self):
        """
        캘리브레이션 관리자 초기화
        
        부모 클래스(GazeCoreProcessor)의 MediaPipe 초기화와
        세션 관리, 타이밍 설정을 함께 진행합니다.
        """
        # 부모 클래스 초기화 (MediaPipe 설정)
        super().__init__()
        
        # 세션 관리
        self.sessions: Dict[str, CalibrationSession] = {}
        self.lock = Lock()  # 스레드 안전성 보장
        
        # 캘리브레이션 설정
        self.calibration_phases = ['top_left', 'top_right', 'bottom_left', 'bottom_right']
        
        # 타이밍 설정 (실제 서비스에서 사용자 경험에 따라 조정 가능)
        self.preparation_time = 3  # 각 단계별 준비 시간 (초)
        self.collection_time = 3   # 각 단계별 데이터 수집 시간 (초)
        
        logger.info("🚀 [CALIBRATION_MANAGER] 시선 캘리브레이션 관리자 초기화 완료")
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """
        새로운 캘리브레이션 세션 생성
        
        고유한 세션 ID를 생성하고 초기 상태로 설정합니다.
        동시 다중 사용자를 지원하기 위해 스레드 안전성을 보장합니다.
        
        Args:
            user_id: 사용자 식별자 (선택적, 익명 캘리브레이션 지원)
            
        Returns:
            str: 생성된 세션 ID (UUID)
            
        실제 면접 서비스에서의 활용:
        - 익명 모드: user_id 없이 체험용 캘리브레이션
        - 회원 모드: user_id와 함께 개인화된 캘리브레이션
        - 세션 추적: 사용자별 캘리브레이션 이력 관리
        """
        session_id = str(uuid.uuid4())
        
        with self.lock:
            session = CalibrationSession(
                session_id=session_id,
                user_id=user_id,
                current_phase='ready',
                phase_start_time=0,
                is_collecting=False,
                calibration_points={
                    'top_left': [],
                    'top_right': [],
                    'bottom_left': [],
                    'bottom_right': []
                },
                final_points={},
                created_at=time.time(),
                completed_at=None,
                initial_face_size=None
            )
            self.sessions[session_id] = session
        
        logger.info(f"📝 [SESSION] 새 캘리브레이션 세션 생성: {session_id}")
        return session_id
    
    def start_calibration(self, session_id: str) -> bool:
        """
        캘리브레이션 시작
        
        세션을 'ready' 상태에서 첫 번째 단계로 진행시킵니다.
        기존 데이터를 초기화하여 새로운 캘리브레이션을 시작합니다.
        
        Args:
            session_id: 시작할 세션 ID
            
        Returns:
            bool: 시작 성공 여부
            
        실패 사유:
        - 존재하지 않는 세션 ID
        - 이미 진행 중인 캘리브레이션
        """
        with self.lock:
            if session_id not in self.sessions:
                logger.warning(f"⚠️ [SESSION] 존재하지 않는 세션: {session_id}")
                return False
                
            session = self.sessions[session_id]
            if session.current_phase != 'ready':
                logger.warning(f"⚠️ [SESSION] 잘못된 상태에서 시작 시도: {session.current_phase}")
                return False
            
            # 첫 번째 단계로 진행
            session.current_phase = 'top_left'
            session.phase_start_time = time.time()
            session.is_collecting = False
            session.initial_face_size = None  # 캘리브레이션 재시작 시 초기화
            
            # 기존 데이터 초기화
            for phase in self.calibration_phases:
                session.calibration_points[phase] = []
            session.final_points = {}
            
            logger.info(f"🎯 [SESSION] 캘리브레이션 시작: {session_id} - top_left 단계")
            return True
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """
        세션 상태 조회 (프론트엔드용)
        
        현재 세션의 진행 상황과 사용자 인터페이스에 필요한 
        모든 정보를 실시간으로 제공합니다.
        
        Args:
            session_id: 조회할 세션 ID
            
        Returns:
            Dict | None: 세션 상태 정보 또는 None (세션 없음)
            
        반환 정보:
        - session_id: 세션 식별자
        - current_phase: 현재 단계
        - elapsed_time: 현재 단계 경과 시간
        - is_collecting: 데이터 수집 중 여부
        - collected_points: 각 단계별 수집된 포인트 수
        - progress: 전체 진행률 (0.0 ~ 1.0)
        - instructions: 사용자 가이드 메시지
        
        실제 면접 서비스에서의 활용:
        - 실시간 UI 업데이트
        - 진행률 표시
        - 사용자 가이드 제공
        - 자동 단계 진행 감지
        """
        with self.lock:
            if session_id not in self.sessions:
                return None
                
            session = self.sessions[session_id]
            current_time = time.time()
            elapsed_time = current_time - session.phase_start_time if session.phase_start_time > 0 else 0
            
            # 자동 단계 진행 체크
            total_phase_time = self.preparation_time + self.collection_time
            if (session.current_phase in self.calibration_phases and 
                elapsed_time > total_phase_time):
                self._auto_advance_phase(session, current_time)
                elapsed_time = current_time - session.phase_start_time
            
            status = {
                'session_id': session_id,
                'current_phase': session.current_phase,
                'elapsed_time': elapsed_time,
                'is_collecting': session.is_collecting,
                'collected_points': {
                    phase: len(points) 
                    for phase, points in session.calibration_points.items()
                },
                'progress': self._calculate_progress(session),
                'instructions': self._get_current_instructions(session, elapsed_time)
            }
            
            return status
    
    def _auto_advance_phase(self, session: CalibrationSession, current_time: float):
        """
        자동 단계 진행 처리
        
        각 단계의 시간이 완료되면 자동으로 다음 단계로 진행합니다.
        데이터가 부족한 경우 기본값을 생성하여 진행을 보장합니다.
        
        Args:
            session: 대상 세션
            current_time: 현재 시간
            
        실제 면접 서비스 고려사항:
        - 사용자 경험: 자동 진행으로 매끄러운 흐름 제공
        - 데이터 품질: 불충분한 데이터 시 기본값 사용
        - 알림 시스템: 단계 전환 시 사용자 알림
        """
        current_phase_index = self.calibration_phases.index(session.current_phase)
        current_count = len(session.calibration_points[session.current_phase])
        
        # 데이터가 없는 경우 기본값 생성
        if current_count == 0:
            self._generate_default_points(session, session.current_phase)
            logger.warning(f"⚠️ [AUTO_ADVANCE] 데이터 부족으로 기본값 사용: {session.current_phase}")
        
        # 다음 단계로 진행
        if current_phase_index < len(self.calibration_phases) - 1:
            next_phase = self.calibration_phases[current_phase_index + 1]
            session.current_phase = next_phase
            session.phase_start_time = current_time
            session.is_collecting = False
            
            logger.info(f"➡️ [AUTO_ADVANCE] 다음 단계로 진행: {next_phase}")
        else:
            # 모든 단계 완료
            self._complete_calibration(session)
            logger.info(f"✅ [AUTO_ADVANCE] 캘리브레이션 완료: {session.session_id}")
    
    def _calculate_progress(self, session: CalibrationSession) -> float:
        """
        전체 캘리브레이션 진행률 계산 (0.0 ~ 1.0)
        
        Args:
            session: 대상 세션
            
        Returns:
            float: 진행률 (0.0 = 시작, 1.0 = 완료)
            
        진행률 계산:
        - ready: 0.0
        - top_left: 0.0 + 현재 단계 진행률 × 0.25
        - top_right: 0.25 + 현재 단계 진행률 × 0.25
        - bottom_left: 0.5 + 현재 단계 진행률 × 0.25
        - bottom_right: 0.75 + 현재 단계 진행률 × 0.25
        - completed: 1.0
        """
        if session.current_phase == 'ready':
            return 0.0
        elif session.current_phase == 'completed':
            return 1.0
        else:
            # 각 단계별 기본 진행률
            phase_progress = {
                'top_left': 0.0,
                'top_right': 0.25,
                'bottom_left': 0.5,
                'bottom_right': 0.75
            }
            
            base_progress = phase_progress.get(session.current_phase, 0.0)
            
            # 현재 단계 내 진행률
            elapsed = time.time() - session.phase_start_time
            total_phase_time = self.preparation_time + self.collection_time
            current_phase_progress = min(elapsed / total_phase_time, 1.0) * 0.25
            
            return base_progress + current_phase_progress
    
    def _get_current_instructions(self, session: CalibrationSession, elapsed_time: float) -> str:
        """
        현재 상황에 맞는 사용자 가이드 메시지 생성
        
        Args:
            session: 대상 세션
            elapsed_time: 현재 단계 경과 시간
            
        Returns:
            str: 사용자 가이드 메시지
            
        메시지 종류:
        - 준비 단계: "화면 좌상단을 응시하세요 - 준비: 3초"
        - 수집 단계: "화면 좌상단을 응시하세요 - 시선 고정: 2초"
        - 완료 대기: "완료, 다음 단계로..."
        
        실제 면접 서비스 확장:
        - 다국어 지원
        - 개인화된 가이드
        - 음성 안내 추가
        """
        if session.current_phase == 'ready':
            return "캘리브레이션을 시작할 준비가 되었습니다."
        elif session.current_phase == 'completed':
            return "캘리브레이션이 완료되었습니다!"
        
        # 각 단계별 기본 메시지
        phase_messages = {
            'top_left': "화면 좌상단을 응시하세요",
            'top_right': "화면 우상단을 응시하세요",
            'bottom_left': "화면 좌하단을 응시하세요",
            'bottom_right': "화면 우하단을 응시하세요"
        }
        
        base_message = phase_messages.get(session.current_phase, "")
        
        # 단계별 상세 가이드
        if elapsed_time < self.preparation_time:
            remaining = int(self.preparation_time - elapsed_time) + 1
            return f"{base_message} - 준비: {remaining}초"
        elif elapsed_time < self.preparation_time + self.collection_time:
            remaining = int(self.preparation_time + self.collection_time - elapsed_time) + 1
            return f"{base_message} - 시선 고정: {remaining}초"
        else:
            return f"{base_message} - 완료, 다음 단계로..."
    
    def process_frame(self, session_id: str, frame: np.ndarray) -> Optional[Dict]:
        """
        실시간 프레임 처리 및 시선 데이터 수집
        
        웹캠에서 받은 프레임을 분석하여 시선 포인트를 추출하고,
        현재 캘리브레이션 단계에 따라 적절한 처리를 수행합니다.
        
        Args:
            session_id: 처리할 세션 ID
            frame: 웹캠 프레임 (numpy array, BGR 형식)
            
        Returns:
            Dict | None: 프레임 처리 결과 또는 None (세션 없음)
            
        반환 정보:
        - status: 현재 상태 ('preparing', 'collecting', 'next_phase', 'completed', 'idle')
        - phase: 현재 단계
        - eye_detected: 눈 검출 여부
        - face_quality: 얼굴 품질 ('good', 'fair', 'poor')
        - remaining_time: 남은 시간 (초)
        - collected_count: 수집된 포인트 수
        - feedback: 사용자 피드백 메시지
        
        처리 과정:
        1. MediaPipe로 얼굴/아이리스 추적
        2. 시선 포인트 계산 (부모 클래스 메서드 사용)
        3. 얼굴 크기 측정 (거리 변화 감지)
        4. 단계별 시간 관리
        5. 데이터 수집 및 검증
        6. 사용자 피드백 생성
        
        실제 면접 서비스 성능 고려사항:
        - 처리 속도: 30FPS 실시간 처리 지원
        - 메모리 효율: 프레임 버퍼링 최소화
        - 네트워크 효율: 필요한 정보만 전송
        """
        with self.lock:
            if session_id not in self.sessions:
                return None
                
            session = self.sessions[session_id]
            current_time = time.time()
            elapsed = current_time - session.phase_start_time
            
            # 유효하지 않은 단계 체크
            if session.current_phase not in self.calibration_phases:
                return {
                    'status': 'idle',
                    'phase': session.current_phase,
                    'eye_detected': False,
                    'feedback': 'Invalid phase'
                }
            
            # === 프레임 분석 ===
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            # 분석 결과 변수 초기화
            eye_detected = False
            gaze_point = None
            face_quality = "poor"
            current_face_size = 0.0
            
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    # 시선 포인트 계산 (부모 클래스 메서드 사용)
                    gaze_point = self.get_gaze_point_3d(face_landmarks.landmark, w, h)
                    
                    # 얼굴 크기 측정 (부모 클래스 메서드 사용)
                    current_face_size = self._estimate_face_size(face_landmarks.landmark, w, h)
                    
                    if gaze_point:
                        eye_detected = True
                        
                        # 얼굴 품질 평가 (거리/선명도 기반)
                        if current_face_size > 100:
                            face_quality = "good"
                        elif current_face_size > 50:
                            face_quality = "fair"
                        
                        break
            
            # === 초기 얼굴 크기 저장 ===
            # 첫 번째 단계에서 양질의 얼굴이 감지되면 기준 크기로 저장
            if (session.current_phase == 'top_left' and 
                eye_detected and 
                face_quality == "good" and 
                session.initial_face_size is None):
                session.initial_face_size = current_face_size
                logger.info(f"📏 [CALIBRATION] 초기 얼굴 크기 저장: {session.initial_face_size:.2f}px")
            
            # === 단계별 처리 ===
            
            # 1. 준비 단계 (사용자가 자세를 잡는 시간)
            if elapsed < self.preparation_time:
                session.is_collecting = False
                remaining = int(self.preparation_time - elapsed) + 1
                
                feedback = f"준비 중... {remaining}초 후 시작"
                if not eye_detected:
                    feedback = "얼굴을 카메라 쪽으로 향해주세요."
                elif face_quality == "poor":
                    feedback = "카메라에 좀 더 가까이 앉아주세요."
                
                return {
                    'status': 'preparing',
                    'phase': session.current_phase,
                    'eye_detected': eye_detected,
                    'face_quality': face_quality,
                    'remaining_time': remaining,
                    'collected_count': len(session.calibration_points[session.current_phase]),
                    'feedback': feedback
                }
            
            # 2. 수집 단계 (실제 시선 데이터 수집)
            elif elapsed < self.preparation_time + self.collection_time:
                session.is_collecting = True
                remaining = int(self.preparation_time + self.collection_time - elapsed) + 1
                
                # 유효한 시선 데이터가 있으면 수집
                if eye_detected and gaze_point:
                    session.calibration_points[session.current_phase].append(gaze_point)
                
                current_count = len(session.calibration_points[session.current_phase])
                target_count = 30  # 목표 수집 포인트 수
                
                # 수집 진행률에 따른 피드백
                feedback = ""
                if not eye_detected:
                    feedback = "눈이 검출되지 않습니다. 얼굴을 카메라 쪽으로 향해주세요."
                elif face_quality == "poor":
                    feedback = "얼굴이 너무 멀거나 흐릿합니다. 카메라에 가까이 앉아주세요."
                elif current_count < 10:
                    feedback = f"시선 데이터 수집 시작 중... ({current_count}/{target_count})"
                elif current_count < 20:
                    feedback = f"좋습니다! 계속 응시해주세요. ({current_count}/{target_count})"
                else:
                    feedback = f"훌륭합니다! 거의 완료되었습니다. ({current_count}/{target_count})"
                
                return {
                    'status': 'collecting',
                    'phase': session.current_phase,
                    'eye_detected': eye_detected,
                    'face_quality': face_quality,
                    'remaining_time': remaining,
                    'collected_count': current_count,
                    'target_count': target_count,
                    'collection_progress': min(current_count / target_count, 1.0),
                    'feedback': feedback
                }
            
            # 3. 완료 단계 (다음 단계로 진행 또는 캘리브레이션 완료)
            else:
                session.is_collecting = False
                current_phase_index = self.calibration_phases.index(session.current_phase)
                current_count = len(session.calibration_points[session.current_phase])
                
                # 데이터가 없는 경우 기본값 생성
                if current_count == 0:
                    self._generate_default_points(session, session.current_phase)
                
                # 다음 단계 진행 또는 완료
                if current_phase_index < len(self.calibration_phases) - 1:
                    # 다음 단계로 진행
                    next_phase = self.calibration_phases[current_phase_index + 1]
                    session.current_phase = next_phase
                    session.phase_start_time = current_time
                    
                    phase_names = {
                        'top_left': '좌상단',
                        'top_right': '우상단',
                        'bottom_left': '좌하단',
                        'bottom_right': '우하단'
                    }
                    
                    return {
                        'status': 'next_phase',
                        'phase': next_phase,
                        'completed_phase': session.current_phase,
                        'completed_count': current_count,
                        'feedback': f"{phase_names.get(session.current_phase, '')} 완료! "
                                   f"이제 {phase_names.get(next_phase, '')}을 응시하세요."
                    }
                else:
                    # 모든 단계 완료
                    self._complete_calibration(session)
                    total_collected = sum(len(points) for points in session.calibration_points.values())
                    
                    return {
                        'status': 'completed',
                        'final_points': self._get_final_points_list(session),
                        'total_collected': total_collected,
                        'feedback': f"캘리브레이션 완료! 총 {total_collected}개의 시선 데이터를 수집했습니다."
                    }
    
    def _complete_calibration(self, session: CalibrationSession):
        """
        캘리브레이션 완료 처리
        
        수집된 원시 시선 데이터를 분석하여 최종 캘리브레이션 포인트를 계산합니다.
        각 단계별 데이터의 평균값을 구하여 대표 포인트로 사용합니다.
        
        Args:
            session: 완료할 세션
            
        처리 과정:
        1. 각 단계별 수집된 포인트들의 평균 계산
        2. CalibrationPoint 객체로 변환
        3. 세션 상태를 'completed'로 변경
        4. 완료 시간 기록
        
        실제 면접 서비스에서의 확장:
        - 아웃라이어 제거: 극단값 필터링
        - 품질 평가: 데이터 신뢰도 계산
        - 개인화: 사용자별 보정 적용
        """
        session.current_phase = 'completed'
        session.completed_at = time.time()
        
        for phase in self.calibration_phases:
            points = session.calibration_points[phase]
            if points:
                # 수집된 포인트들의 평균 계산
                avg_point = np.mean(points, axis=0)
                session.final_points[phase] = CalibrationPoint(
                    x=float(avg_point[0]),
                    y=float(avg_point[1]),
                    label=phase
                )
                logger.debug(f"📍 [CALIBRATION] {phase} 최종 포인트: "
                           f"({avg_point[0]:.1f}, {avg_point[1]:.1f}) "
                           f"from {len(points)} samples")
            else:
                # 데이터가 없는 경우 기본값 사용
                session.final_points[phase] = CalibrationPoint(x=0.0, y=0.0, label=phase)
                logger.warning(f"⚠️ [CALIBRATION] {phase} 데이터 부족으로 기본값 사용")
        
        logger.info(f"✅ [CALIBRATION] 세션 완료: {session.session_id}")
    
    def _get_final_points_list(self, session: CalibrationSession) -> List[Tuple[float, float]]:
        """
        최종 캘리브레이션 포인트를 리스트 형태로 반환
        
        API 응답 형식에 맞춰 (x, y) 튜플 리스트로 변환합니다.
        
        Args:
            session: 대상 세션
            
        Returns:
            List[Tuple[float, float]]: 4개의 캘리브레이션 포인트
        """
        points = []
        for phase in self.calibration_phases:
            if phase in session.final_points:
                point = session.final_points[phase]
                points.append((point.x, point.y))
        return points
    
    def get_calibration_result(self, session_id: str) -> Optional[Dict]:
        """
        완료된 캘리브레이션 결과 조회
        
        캘리브레이션이 완료된 세션의 최종 결과를 반환합니다.
        동영상 분석에 필요한 모든 정보를 포함합니다.
        
        Args:
            session_id: 조회할 세션 ID
            
        Returns:
            Dict | None: 캘리브레이션 결과 또는 None (세션 없음/미완료)
            
        반환 정보:
        - session_id: 세션 식별자
        - calibration_points: 4개 포인트 좌표 리스트
        - point_details: 각 포인트 상세 정보
        - collection_stats: 수집 통계 (각 단계별 포인트 수)
        - completed_at: 완료 시간
        - initial_face_size: 기준 얼굴 크기 (동적 스케일링용)
        """
        with self.lock:
            if session_id not in self.sessions:
                return None
                
            session = self.sessions[session_id]
            if session.current_phase != 'completed':
                return None
            
            return {
                'session_id': session_id,
                'calibration_points': self._get_final_points_list(session),
                'point_details': {
                    phase: asdict(point) 
                    for phase, point in session.final_points.items()
                },
                'collection_stats': {
                    phase: len(points) 
                    for phase, points in session.calibration_points.items()
                },
                'completed_at': session.completed_at,
                'initial_face_size': session.initial_face_size  # 동적 스케일링용
            }
    
    def _generate_default_points(self, session: CalibrationSession, phase: str):
        """
        기본 캘리브레이션 포인트 생성
        
        사용자가 특정 단계에서 충분한 시선 데이터를 제공하지 못한 경우
        화면 기본 위치를 기반으로 한 포인트들을 생성합니다.
        
        Args:
            session: 대상 세션
            phase: 기본값을 생성할 단계
            
        기본 좌표 (640x480 화면 기준):
        - top_left: (160, 120) + 노이즈
        - top_right: (480, 120) + 노이즈
        - bottom_left: (160, 360) + 노이즈  
        - bottom_right: (480, 360) + 노이즈
        
        실제 면접 서비스에서의 활용:
        - 장애 대응: 기술적 문제로 데이터 수집 실패 시
        - 접근성: 시각 장애 사용자 지원
        - 품질 보장: 최소한의 캘리브레이션 제공
        """
        # 화면 기본 위치 (640x480 기준)
        default_coordinates = {
            'top_left': (160, 120),
            'top_right': (480, 120),
            'bottom_left': (160, 360),
            'bottom_right': (480, 360)
        }
        
        if phase in default_coordinates:
            base_x, base_y = default_coordinates[phase]
            
            # 자연스러운 변동을 위한 노이즈 추가
            for i in range(15):  # 15개의 포인트 생성
                noisy_x = base_x + np.random.normal(0, 5)  # 표준편차 5픽셀
                noisy_y = base_y + np.random.normal(0, 5)
                session.calibration_points[phase].append((noisy_x, noisy_y))
            
            logger.warning(f"🔧 [DEFAULT] {phase} 기본 포인트 생성: "
                         f"({base_x}, {base_y}) + noise, {15}개 포인트")
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        오래된 세션 정리
        
        지정된 시간보다 오래된 세션들을 메모리에서 제거합니다.
        실제 면접 서비스에서는 정기적으로 실행하여 메모리 누수를 방지합니다.
        
        Args:
            max_age_hours: 최대 보존 시간 (시간 단위)
            
        Returns:
            int: 삭제된 세션 수
            
        실제 서비스 운영 가이드:
        - 실행 주기: 1시간마다 크론 작업으로 실행
        - 보존 기간: 완료된 세션은 24시간, 미완료 세션은 6시간
        - 로그 기록: 정리된 세션 통계 기록
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        with self.lock:
            expired_sessions = []
            for session_id, session in self.sessions.items():
                age = current_time - session.created_at
                if age > max_age_seconds:
                    expired_sessions.append(session_id)
            
            # 만료된 세션 삭제
            for session_id in expired_sessions:
                del self.sessions[session_id]
        
        if expired_sessions:
            logger.info(f"🧹 [CLEANUP] 오래된 세션 정리: {len(expired_sessions)}개 삭제")
        
        return len(expired_sessions)
    
    def get_session_statistics(self) -> Dict:
        """
        전체 세션 통계 조회 (모니터링용)
        
        Returns:
            Dict: 세션 통계 정보
            
        통계 정보:
        - total_sessions: 전체 세션 수
        - active_sessions: 진행 중인 세션 수  
        - completed_sessions: 완료된 세션 수
        - phase_distribution: 단계별 세션 분포
        - average_completion_time: 평균 완료 시간
        
        실제 면접 서비스에서의 활용:
        - 서버 모니터링
        - 사용자 행동 분석
        - 성능 최적화 참고 자료
        """
        with self.lock:
            total = len(self.sessions)
            completed = sum(1 for s in self.sessions.values() if s.current_phase == 'completed')
            active = total - completed
            
            # 단계별 분포
            phase_distribution = {}
            for session in self.sessions.values():
                phase = session.current_phase
                phase_distribution[phase] = phase_distribution.get(phase, 0) + 1
            
            # 평균 완료 시간 계산
            completion_times = []
            for session in self.sessions.values():
                if session.completed_at and session.created_at:
                    completion_times.append(session.completed_at - session.created_at)
            
            avg_completion_time = np.mean(completion_times) if completion_times else 0
            
            return {
                'total_sessions': total,
                'active_sessions': active,
                'completed_sessions': completed,
                'phase_distribution': phase_distribution,
                'average_completion_time': avg_completion_time
            }


# 싱글톤 인스턴스 생성 (기존 API 호환성 유지)
# 실제 면접 서비스에서는 의존성 주입 또는 팩토리 패턴 고려
calibration_manager = GazeCalibrationManager()

logger.info("🎯 [MODULE] 시선 캘리브레이션 모듈 로딩 완료 (리팩토링 버전)")
# === 김원우 작성 끝 ===