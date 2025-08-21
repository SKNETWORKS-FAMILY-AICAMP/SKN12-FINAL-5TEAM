// 시선 추적 관련 상수 정의

export const GAZE_CONSTANTS = {
  // API 호출 간격 (ms)
  FRAME_STREAM_INTERVAL: 200,
  STATUS_CHECK_INTERVAL: 2000,
  
  // 타임아웃 설정 (ms)
  API_TIMEOUT: 10000,
  
  // 캘리브레이션 설정
  CALIBRATION: {
    TARGET_POINTS: 30,
    PHASES: ['ready', 'collecting', 'completed'] as const,
  },
  
  // 녹화 설정
  RECORDING: {
    MAX_DURATION: 300, // 5분
    TIMER_INTERVAL: 1000,
  },
  
  // 비디오 설정
  VIDEO: {
    WIDTH: 640,
    HEIGHT: 480,
  },
  
  // 업로드 설정
  UPLOAD: {
    CHUNK_SIZE: 1024 * 1024, // 1MB
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000,
  },
  
  // 분석 설정
  ANALYSIS: {
    PROGRESS_CHECK_INTERVAL: 2000,
    MAX_WAIT_TIME: 300000, // 5분
  }
} as const;

// 시선 분석 결과 등급
export const GAZE_RATINGS = {
  EXCELLENT: { min: 90, label: '우수', color: 'green' },
  GOOD: { min: 70, label: '양호', color: 'blue' },
  FAIR: { min: 50, label: '보통', color: 'yellow' },
  POOR: { min: 0, label: '개선 필요', color: 'red' },
} as const;

// 에러 메시지
export const GAZE_ERROR_MESSAGES = {
  CAMERA_PERMISSION: '카메라 권한을 허용해주세요.',
  CAMERA_NOT_FOUND: '카메라를 찾을 수 없습니다.',
  NETWORK_ERROR: '네트워크 연결을 확인해주세요.',
  SERVER_ERROR: '서버 오류가 발생했습니다.',
  TIMEOUT_ERROR: '요청 시간이 초과되었습니다.',
  CALIBRATION_FAILED: '캘리브레이션에 실패했습니다.',
  UPLOAD_FAILED: '파일 업로드에 실패했습니다.',
  ANALYSIS_FAILED: '시선 분석에 실패했습니다.',
} as const;