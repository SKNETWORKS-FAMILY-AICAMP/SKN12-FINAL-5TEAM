"""
베타고 시선 분석 시스템 패키지

이 패키지는 베타고 면접 플랫폼의 시선 분석 기능을 제공합니다.

모듈 구성:
- gaze_core: 공통 MediaPipe 로직
- file_utils: 안전한 파일 관리 유틸리티  
- gaze_analysis: 동영상 시선 분석
- gaze_calibration: 실시간 캘리브레이션
- gaze_api: FastAPI 엔드포인트
"""

# 주요 클래스와 함수 export (선택적 import 허용)
try:
    from .gaze_core import GazeCoreProcessor, GazeConfig
    from .file_utils import SecureFileManager, FileValidator
    from .gaze_analysis import GazeAnalyzer, gaze_analyzer
    from .gaze_calibration import GazeCalibrationManager, calibration_manager
    
    __all__ = [
        'GazeCoreProcessor',
        'GazeConfig', 
        'SecureFileManager',
        'FileValidator',
        'GazeAnalyzer',
        'gaze_analyzer',
        'GazeCalibrationManager', 
        'calibration_manager'
    ]
except ImportError:
    # 일부 모듈이 없어도 패키지 로딩은 계속 진행
    pass

__version__ = "1.0.0"
__author__ = "Claude AI"
__description__ = "베타고 면접 플랫폼 시선 분석 시스템"