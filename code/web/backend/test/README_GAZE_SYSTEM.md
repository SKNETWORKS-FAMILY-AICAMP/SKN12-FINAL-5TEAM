# 베타고 시선 분석 시스템 (리팩토링 버전)

## 🎯 개요

이 문서는 베타고 면접 플랫폼의 시선 분석 시스템 리팩토링 결과와 실제 면접 서비스 적용 가이드를 제공합니다.

**작성일**: 2025-01-11  
**작성자**: Claude AI  
**목적**: 실제 면접 서비스 적용을 위한 포괄적 가이드  

## 📁 파일 구조

```
backend/test/
├── gaze_core.py          # 🆕 공통 MediaPipe 로직 기반 클래스
├── file_utils.py         # 🆕 Windows 호환 파일 관리 유틸리티
├── gaze_analysis.py      # 🔄 리팩토링: 동영상 시선 분석 (상속 구조)
├── gaze_calibration.py   # 🔄 리팩토링: 실시간 캘리브레이션 (상속 구조)
├── gaze_api.py          # ✅ 기존 유지: API 엔드포인트
└── README_GAZE_SYSTEM.md # 🆕 종합 문서
```

## 🚀 주요 개선사항

### 1. 아키텍처 개선
- **모듈화**: MediaPipe 로직을 `GazeCoreProcessor` 기반 클래스로 분리
- **상속 구조**: 코드 중복 제거 및 재사용성 향상
- **확장성**: 새로운 시선 관련 기능 추가 용이

### 2. 안정성 강화
- **Windows 호환성**: `SecureFileManager`로 파일 권한 문제 해결
- **에러 처리**: 포괄적 예외 처리 및 복구 로직
- **메모리 관리**: 자동 리소스 정리 및 누수 방지

### 3. 운영 최적화
- **로깅 시스템**: 구조화된 로그 메시지 및 모니터링 지원
- **성능 튜닝**: 설정 가능한 프레임 스킵 및 처리 옵션
- **모니터링**: 세션 통계 및 성능 지표 제공

### 4. 개발자 경험
- **상세 주석**: 모든 클래스/메서드에 실제 서비스 적용 가이드 포함
- **타입 힌트**: 완전한 타입 안전성 보장
- **문서화**: API 사용법 및 확장 방법 명시

## 🏗️ 클래스 다이어그램

```
GazeCoreProcessor (gaze_core.py)
├── MediaPipe FaceMesh 초기화
├── get_gaze_point_3d()
├── _estimate_face_size()
└── validate_gaze_data()

GazeAnalyzer(GazeCoreProcessor) (gaze_analysis.py)
├── S3 클라이언트 초기화
├── download_video_from_s3()
├── analyze_video()
└── generate_feedback()

GazeCalibrationManager(GazeCoreProcessor) (gaze_calibration.py)
├── 세션 관리 (다중 사용자)
├── create_session()
├── process_frame()
└── get_calibration_result()

SecureFileManager (file_utils.py)
├── secure_temp_file()
├── secure_temp_directory()
└── cleanup_old_temp_files()
```

## 🛠️ 실제 면접 서비스 적용 가이드

### 1. 환경 설정

#### 필수 Python 패키지
```bash
pip install mediapipe opencv-python numpy boto3 fastapi
```

#### 환경 변수 설정
```bash
# AWS S3 접근 (면접 동영상 저장소)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="ap-northeast-2"

# 로깅 레벨
export GAZE_LOG_LEVEL="INFO"  # 운영환경
export GAZE_LOG_LEVEL="DEBUG" # 개발환경
```

### 2. 성능 최적화 설정

#### GPU 가속 (권장)
```python
# CUDA 사용 가능 시 자동으로 GPU 가속 적용
# MediaPipe는 TensorFlow Lite GPU delegate 사용
```

#### 프레임 스킵 튜닝
```python
from gaze_core import GazeConfig

# 고정밀 분석 (짧은 면접, 고사양 서버)
frame_skip = GazeConfig.get_frame_skip('high_accuracy')  # 3

# 균형잡힌 설정 (일반적인 면접)
frame_skip = GazeConfig.get_frame_skip('balanced')       # 10

# 고속 처리 (긴 면접, 다중 처리)
frame_skip = GazeConfig.get_frame_skip('high_performance') # 20
```

### 3. 서버 아키텍처 권장사항

#### 동시 처리 용량
- **소형 서버**: 3-5개 동시 분석
- **중형 서버**: 10-15개 동시 분석  
- **대형 서버**: 20-30개 동시 분석

#### 리소스 요구사항
```yaml
# 1개 동시 분석 기준
CPU: 1 core (2 vCPU 권장)
RAM: 500MB - 1GB
GPU: 선택적 (CUDA 지원 시 성능 향상)
스토리지: 임시 저장용 1GB 여유 공간
```

#### 스케일링 전략
```python
# 방법 1: 인스턴스 풀링
class GazeAnalyzerPool:
    def __init__(self, pool_size=5):
        self.analyzers = [GazeAnalyzer() for _ in range(pool_size)]
        self.available = Queue()
        for analyzer in self.analyzers:
            self.available.put(analyzer)
    
    def get_analyzer(self):
        return self.available.get()
    
    def return_analyzer(self, analyzer):
        self.available.put(analyzer)

# 방법 2: 비동기 큐 시스템 (Celery + Redis)
from celery import Celery

app = Celery('gaze_analysis', broker='redis://localhost:6379')

@app.task
def analyze_video_async(bucket, key, calibration_points, initial_face_size):
    analyzer = GazeAnalyzer()
    return analyzer.analyze_video(bucket, key, calibration_points, initial_face_size)
```

### 4. 모니터링 및 알림

#### 핵심 지표
```python
# 성능 지표
- 분석 성공률: 95% 이상 목표
- 평균 처리 시간: 동영상 길이의 30% 이내
- 에러율: 5% 이하 유지
- 메모리 사용량: 인스턴스당 1GB 이하

# 품질 지표  
- 시선 데이터 수집율: 80% 이상
- 얼굴 검출율: 90% 이상
- 캘리브레이션 완료율: 95% 이상
```

#### 로그 모니터링
```python
# 주요 로그 패턴
INFO: Created TensorFlow Lite XNNPACK delegate for CPU.  # 정상 초기화
ERROR: [GAZE_ANALYZER] S3 클라이언트 초기화 실패        # AWS 설정 문제
WARNING: [JITTER] 시선 데이터 부족으로 기본 점수 반환    # 데이터 품질 이슈
```

### 5. 보안 고려사항

#### 데이터 보호
```python
# 1. 임시 파일 자동 정리
with SecureFileManager.secure_temp_file() as temp_path:
    # 면접 동영상 처리
    pass  # 자동으로 완전 삭제됨

# 2. 세션 데이터 암호화 (실제 서비스에서 적용)
from cryptography.fernet import Fernet

class EncryptedCalibrationSession:
    def __init__(self, encryption_key):
        self.cipher = Fernet(encryption_key)
    
    def encrypt_session_data(self, session_data):
        return self.cipher.encrypt(json.dumps(session_data).encode())
```

#### 접근 제어
```python
# JWT 토큰 기반 인증 (gaze_api.py에서 구현됨)
from services.auth_service import AuthService

@router.post("/test/gaze/analyze")
async def analyze_video(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # 인증된 사용자만 접근 가능
    pass
```

### 6. 에러 처리 및 복구

#### 일반적인 오류 상황
```python
# 1. S3 접근 오류
try:
    analyzer.analyze_video(bucket, key, calibration_points, initial_face_size)
except FileNotFoundError:
    # 동영상 파일이 S3에 없음
    return {"error": "VIDEO_NOT_FOUND", "message": "업로드된 동영상을 찾을 수 없습니다"}
except ClientError as e:
    # AWS 권한 또는 네트워크 문제
    return {"error": "S3_ACCESS_ERROR", "message": "동영상 접근 중 오류가 발생했습니다"}

# 2. MediaPipe 초기화 오류
try:
    analyzer = GazeAnalyzer()
except RuntimeError as e:
    # GPU 메모리 부족 또는 드라이버 문제
    logger.error(f"MediaPipe 초기화 실패: {e}")
    # Fallback: CPU 전용 모드로 재시도
```

#### 자동 복구 전략
```python
class ResilientGazeAnalyzer:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
    
    def analyze_with_retry(self, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return self.analyzer.analyze_video(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"분석 재시도 {attempt + 1}/{self.max_retries}: {e}")
                time.sleep(2 ** attempt)  # 지수 백오프
```

### 7. A/B 테스트 지원

#### 알고리즘 파라미터 테스트
```python
# 점수 계산 가중치 A/B 테스트
class GazeConfigVariant:
    VARIANT_A = {'jitter': 0.4, 'compliance': 0.6}  # 기본값
    VARIANT_B = {'jitter': 0.3, 'compliance': 0.7}  # 집중도 중시
    VARIANT_C = {'jitter': 0.5, 'compliance': 0.5}  # 균등 가중치

def get_user_variant(user_id):
    # 사용자 ID 해시로 일관된 변형 할당
    hash_value = hash(user_id) % 100
    if hash_value < 50:
        return 'A'
    elif hash_value < 75:
        return 'B'
    else:
        return 'C'
```

### 8. 개발 및 디버깅

#### 로컬 개발 환경
```python
# 개발용 설정
import logging
logging.basicConfig(level=logging.DEBUG)

# S3 없이 로컬 파일로 테스트
class LocalGazeAnalyzer(GazeAnalyzer):
    def analyze_local_video(self, video_path, calibration_points, initial_face_size):
        with SecureFileManager.secure_temp_file() as temp_path:
            # 로컬 파일 복사
            shutil.copy2(video_path, temp_path)
            # 기존 분석 로직 재사용
            return super().analyze_video_file(temp_path, calibration_points, initial_face_size)
```

#### 테스트 케이스
```python
import unittest

class TestGazeSystem(unittest.TestCase):
    def setUp(self):
        self.analyzer = GazeAnalyzer()
        self.calibration_manager = GazeCalibrationManager()
    
    def test_calibration_session_lifecycle(self):
        # 세션 생성
        session_id = self.calibration_manager.create_session()
        self.assertIsNotNone(session_id)
        
        # 세션 시작
        success = self.calibration_manager.start_calibration(session_id)
        self.assertTrue(success)
        
        # 상태 확인
        status = self.calibration_manager.get_session_status(session_id)
        self.assertEqual(status['current_phase'], 'top_left')
    
    def test_gaze_point_calculation(self):
        # 모의 랜드마크 데이터로 시선 포인트 계산 테스트
        # ...
```

## 🚨 알려진 제한사항 및 해결방안

### 1. MediaPipe 관련
- **문제**: 극단적 얼굴 각도에서 정확도 저하
- **해결**: 사용자 가이드로 정면 응시 유도

### 2. 하드웨어 호환성
- **문제**: 저사양 웹캠에서 품질 저하
- **해결**: 최소 품질 요구사항 사전 체크

### 3. 네트워크 의존성
- **문제**: S3 접근 실패 시 분석 불가
- **해결**: 로컬 백업 저장소 및 재시도 로직

## 📈 향후 개발 로드맵

### Phase 1: 기능 강화 (1-2개월)
- [ ] 실시간 스트리밍 분석 지원
- [ ] 다중 얼굴 동시 분석
- [ ] 감정 분석 통합

### Phase 2: 성능 최적화 (2-3개월)  
- [ ] ONNX 모델 최적화
- [ ] 에지 컴퓨팅 지원
- [ ] 배치 처리 개선

### Phase 3: 고도화 (3-6개월)
- [ ] AI 기반 개인화 피드백
- [ ] 다국어 지원
- [ ] 실시간 협업 면접 지원

## 🤝 기여 가이드

### 코드 컨트리뷰션
1. 기존 주석 스타일 준수
2. 실제 서비스 적용 가이드 포함
3. 테스트 케이스 작성 필수
4. 성능 영향 분석 포함

### 이슈 리포팅
```markdown
## 버그 리포트 템플릿
- **환경**: OS, Python 버전, 패키지 버전
- **재현 단계**: 구체적인 단계
- **예상 결과**: 기대했던 동작
- **실제 결과**: 실제 발생한 동작
- **로그**: 관련 에러 메시지
```

## 📞 지원 및 문의

**기술 지원**: 시스템 아키텍처 및 성능 관련  
**사용 문의**: API 사용법 및 통합 관련  
**기능 제안**: 새로운 기능 및 개선사항  

---

**최종 업데이트**: 2025-01-11  
**문서 버전**: 1.0  
**호환성**: Python 3.8+, MediaPipe 0.10.x