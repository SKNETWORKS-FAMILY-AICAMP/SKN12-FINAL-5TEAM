// 테스트 관련 타입 정의

export interface TestUploadRequest {
  file_name: string;
  file_type: 'video' | 'audio';
  file_size?: number;
  duration?: number;
}

export interface TestUploadResponse {
  upload_url: string;
  media_id: string;
  test_id: string;
}

export interface TestPlayResponse {
  play_url: string;
  file_name: string;
  file_type: string;
  test_id: string;
}

export interface TestVideo {
  media_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  created_at: string;
  test_id: string;
}

export interface TestSessionState {
  step: 'calibration' | 'record' | 'upload' | 'analyze' | 'result' | 'complete';
  isRecording: boolean;
  isUploading: boolean;
  uploadProgress: number;
  error: string | null;
  recordedBlob: Blob | null;
  testId: string | null;
  mediaId: string | null;
  // 시선 분석 관련 상태
  calibrationSessionId: string | null;
  isCalibrating: boolean;
  calibrationPhase: string;
  isAnalyzing: boolean;
  analysisTaskId: string | null;
  gazeResult: GazeAnalysisResult | null;
}

export interface RecorderProps {
  onRecordingComplete: (blob: Blob) => void;
  onError: (error: string) => void;
}

export interface UploaderProps {
  blob: Blob;
  onUploadComplete: (testId: string, mediaId: string) => void;
  onUploadProgress: (progress: number) => void;
  onError: (error: string) => void;
}

export interface PlayerProps {
  testId: string;
  onError: (error: string) => void;
}

// 시선 분석 관련 타입들
export interface CalibrationPoint {
  x: number;
  y: number;
  label: string;
}

export interface CalibrationStartResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface CalibrationStatusResponse {
  session_id: string;
  current_phase: string;
  elapsed_time: number;
  is_collecting: boolean;
  collected_points: { [key: string]: number };
  progress: number;
  instructions: string;
}

export interface CalibrationResult {
  session_id: string;
  calibration_points: [number, number][];
  initial_face_size?: number | null; // null 값도 허용하도록 수정
  point_details: { [key: string]: CalibrationPoint };
  collection_stats: { [key: string]: number };
  completed_at: number;
  allowed_range?: {
    left_bound: number;
    right_bound: number;
    top_bound: number;
    bottom_bound: number;
  };
}

export interface GazeAnalysisResult {
  gaze_score: number;
  total_frames: number;
  analyzed_frames: number;
  in_range_frames: number;
  in_range_ratio: number;
  jitter_score: number;
  compliance_score: number;
  stability_rating: string;
  feedback: string;
  gaze_points: [number, number][];
  analysis_duration: number;
  allowed_range: {
    left_bound: number;
    right_bound: number;
    top_bound: number;
    bottom_bound: number;
  };
  calibration_points: [number, number][];
}

export interface VideoAnalysisResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface AnalysisStatusResponse {
  task_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress?: number;
  result?: GazeAnalysisResult;
  error?: string;
  message?: string;
}

export interface CalibrationProps {
  onCalibrationComplete: (sessionId: string) => void;
  onError: (error: string) => void;
}

export interface GazeAnalysisProps {
  videoUrl: string;
  calibrationSessionId: string;
  onAnalysisComplete: (result: GazeAnalysisResult) => void;
  onProgress: (progress: number) => void;
  onError: (error: string) => void;
}

export interface GazeResultProps {
  result: GazeAnalysisResult;
  onRestart: () => void;
}