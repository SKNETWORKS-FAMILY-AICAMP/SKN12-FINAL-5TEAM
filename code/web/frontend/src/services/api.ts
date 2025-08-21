import axios from 'axios';

export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// API 클라이언트 설정
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터 - JWT 토큰 자동 추가
apiClient.interceptors.request.use(
  (config) => {
    console.log('API 요청:', config.method?.toUpperCase(), config.url);
    
    // JWT 토큰이 있으면 Authorization 헤더에 추가
    const token = localStorage.getItem('auth_token');
    if (token) {
      // config.headers가 undefined일 경우 빈 객체로 초기화
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    console.error('요청 오류:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 토큰 만료 처리
apiClient.interceptors.response.use(
  (response) => {
    // 오디오 데이터가 포함된 경우 해당 필드를 제외하고 출력
    if (response.data && typeof response.data === 'object') {
      const filteredData: any = { ...response.data };
      
      // 오디오 필드들을 간단한 표시로 대체
      if (filteredData.intro_audio) {
        filteredData.intro_audio = `[오디오 데이터 ${filteredData.intro_audio.length} chars]`;
      }
      if (filteredData.ai_question_audio) {
        filteredData.ai_question_audio = `[오디오 데이터 ${filteredData.ai_question_audio.length} chars]`;
      }
      if (filteredData.ai_answer_audio) {
        filteredData.ai_answer_audio = `[오디오 데이터 ${filteredData.ai_answer_audio.length} chars]`;
      }
      if (filteredData.question_audio) {
        filteredData.question_audio = `[오디오 데이터 ${filteredData.question_audio.length} chars]`;
      }
      
      console.log('API 응답:', response.status, filteredData);
    } else {
      console.log('API 응답:', response.status, response.data);
    }
    return response;
  },
  (error) => {
    console.error('응답 오류:', error.response?.status, error.response?.data);
    
    // 401 에러 (인증 실패) 시 토큰 삭제 및 로그인 페이지로 리다이렉트
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_profile');
      
      // 현재 페이지가 로그인/회원가입 페이지가 아닌 경우에만 리다이렉트
      if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/signup')) {
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

// 타입 정의 - 실제 DB 구조에 맞게 단순화
export interface JobPosting {
  posting_id: number;
  company_id: number;
  position_id: number;
  company: string;      // company 테이블 JOIN 결과
  position: string;     // position 테이블 JOIN 결과
  content: string;      // 원본 content (설명으로 사용)
}

export interface InterviewSettings {
  company: string;
  position: string;
  mode: string;
  difficulty: string;
  candidate_name: string;
  documents?: string[];
  posting_id?: number;  // 🆕 채용공고 ID 추가
  use_interviewer_service?: boolean;  // 🆕 InterviewerService 플래그 추가
  resume?: any;
  calibration_data?: any
}

export interface Question {
  id: string;
  question: string;
  category: string;
  time_limit: number;
  keywords: string[];
}

export interface AnswerSubmission {
  session_id: string;
  question_id: string;
  answer: string;
  time_spent: number;
}

export interface InterviewResult {
  session_id: string;
  total_score: number;
  category_scores: Record<string, number>;
  detailed_feedback: Array<{
    question: string;
    answer: string;
    score: number;
    feedback: string;
    strengths: string[];
    improvements: string[];
  }>;
  recommendations: string[];
  interview_info: InterviewSettings;
}

// 🆕 백엔드 InterviewResponse 스키마에 맞는 타입 정의 (JOIN된 데이터 포함)
export interface InterviewResponse {
  interview_id: number;
  user_id: number;
  ai_resume_id: number;
  user_resume_id: number;
  posting_id: number;
  company_id: number;
  position_id: number;
  total_feedback: string;
  date: string; // ISO 날짜 문자열
  // JOIN된 데이터
  company: {
    name: string;
  };
  position: {
    position_name: string;
  };
}

// 🆕 시선 분석 상태 응답 타입
export interface AnalysisStatusResponse {
  task_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress?: number;
  result?: {
    gaze_score: number;
    jitter_score: number;
    compliance_score: number;
    stability_rating: string;
    total_frames: number;
    analyzed_frames: number;
    in_range_frames: number;
    in_range_ratio: number;
    feedback: string;
    analysis_duration: number;
    gaze_points: [number, number][];
    allowed_range: {
      left_bound: number;
      right_bound: number;
      top_bound: number;
      bottom_bound: number;
    };
    calibration_points: [number, number][];
  };
  error?: string;
  message?: string;
}

// 🆕 시선 분석 작업 시작 응답 타입
export interface AnalysisTaskResponse {
  task_id: string;
  status: string;
  message: string;
}

// 🆕 파일 업로드 응답 타입
export interface FileUploadResponse {
  upload_url?: string;
  play_url: string;
  file_name: string;
  file_type: string;
  test_id?: string;
  media_id?: string;
}

// 🆕 STT 응답 타입
export interface STTResponse {
  text: string;
  confidence?: number;
  duration?: number;
}

// 🆕 캘리브레이션 결과 타입 (기존 타입과 완전히 일치하도록 확장)
export interface CalibrationResult {
  session_id: string;
  calibration_points: [number, number][];
  initial_face_size?: number | null; // Optional[float]에 대응
  point_details: { [key: string]: any }; // CalibrationPoint 타입
  collection_stats: { [key: string]: number };
  completed_at: number;
  allowed_range?: { // Optional 필드로 수정
    left_bound: number;
    right_bound: number;
    top_bound: number;
    bottom_bound: number;
  };
}

// 🆕 피드백 평가 응답 타입
export interface FeedbackEvaluationResponse {
  success: boolean;
  results?: Array<{
    interview_id: number;
    user_id: number;
    evaluation_data: any;
  }>;
  message?: string;
}

// 🆕 시선 분석 DB 저장 응답 타입
export interface GazeAnalysisSaveResponse {
  success: boolean;
  message: string;
  data?: {
    analysis_id: number;
    interview_id: number;
    user_id: number;
  };
}

// 🆕 피드백 계획 생성 응답 타입
export interface FeedbackPlanResponse {
  success: boolean;
  message: string;
  data?: {
    plan_id: number;
    interview_id: number;
    plans: Array<{
      category: string;
      recommendations: string[];
    }>;
  };
}

// 🆕 시선 분석 응답 타입
export interface GazeAnalysisResponse {
  gaze_id: number;
  interview_id: number;
  user_id: number;
  gaze_score: number;
  jitter_score: number;
  compliance_score: number;
  stability_rating: string;
  created_at: string;
  gaze_points?: Array<{x: number, y: number}>;
  calibration_points?: Array<[number, number]>;
  video_metadata?: any;
}

// 🆕 면접 진행 응답 공통 타입 (턴 정보 포함)
export interface InterviewSubmitResponse {
  status: string;
  flow_state?: string;
  content?: {
    content: string;
    type?: string;
    metadata?: {
      resume_id?: number;
      [key: string]: any;
    };
    ai_answer?: {
      metadata?: {
        resume_id?: number;
        [key: string]: any;
      };
    };
  };
  metadata?: {
    next_agent?: string;
    task?: string;
    resume_id?: number;
    [key: string]: any;
  };
  turn_info?: {
    is_user_turn?: boolean;
    is_ai_turn?: boolean;
    ai_metadata?: {
      resume_id?: number;
      [key: string]: any;
    };
  };
  session_id?: string;
  intro_message?: string;
  question?: string | {
    question: string;
    category: string;
    time_limit: number;
    id?: string;
  };
  ai_question?: {
    content: string;
  };
  ai_answer?: {
    content: string;
    metadata?: {
      resume_id?: number;
      [key: string]: any;
    };
  };
  ai_response?: {
    content: string;
    metadata?: {
      resume_id?: number;
      [key: string]: any;
    };
  };
  // TTS 오디오 필드들
  intro_audio?: string;
  ai_question_audio?: string;
  ai_answer_audio?: string;
  question_audio?: string;
}

// 🆕 AI 경쟁 면접 시작 응답 타입
export interface AICompetitionStartResponse {
  session_id?: string;
  interview_id?: string;
  status?: string;
  content?: {
    content: string;
    type?: string;
    metadata?: {
      resume_id?: number;
      [key: string]: any;
    };
    ai_answer?: {
      metadata?: {
        resume_id?: number;
        [key: string]: any;
      };
    };
  };
  metadata?: {
    next_agent?: string;
    task?: string;
    resume_id?: number;
    [key: string]: any;
  };
  turn_info?: {
    is_user_turn?: boolean;
    is_ai_turn?: boolean;
    ai_metadata?: {
      resume_id?: number;
      [key: string]: any;
    };
  };
  intro_message?: string;
  question?: string | {
    question: string;
    category: string;
    time_limit: number;
    id?: string;
  };
  ai_question?: {
    content: string;
  };
  ai_answer?: {
    content: string;
    metadata?: {
      resume_id?: number;
      [key: string]: any;
    };
  };
  ai_response?: {
    content: string;
    metadata?: {
      resume_id?: number;
      [key: string]: any;
    };
  };
  // TTS 오디오 필드들
  intro_audio?: string;
  ai_question_audio?: string;
  ai_answer_audio?: string;
  question_audio?: string;
}

// UI에서 사용할 확장된 면접 히스토리 타입 (추가 정보만 포함)
export interface InterviewHistoryItem extends InterviewResponse {
  score?: number;        // 계산된 점수 (total_feedback에서 파싱)
  status?: 'completed' | 'in_progress' | 'failed'; // UI 상태
}

export interface InterviewHistory {
  total_interviews: number;
  interviews: Array<{
    session_id: string;
    settings: InterviewSettings;
    completed_at: string;
    total_score: number;
  }>;
}

// API 함수들
export const interviewApi = {
  // 면접 시작
  async startInterview(settings: InterviewSettings): Promise<{
    session_id: string;
    total_questions: number;
    message: string;
  }> {
    const response = await apiClient.post('/interview/start', settings);
    return response.data as {
      session_id: string;
      total_questions: number;
      message: string;
    };
  },

  // 문서 업로드
  async uploadDocument(file: File): Promise<{
    file_id: string;
    analyzed_content: any;
    message: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post('/interview/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data as {
      file_id: string;
      analyzed_content: any;
      message: string;
    };
  },

  // 다음 질문 가져오기
  async getNextQuestion(sessionId: string): Promise<{
    question?: Question;
    question_index?: number;
    total_questions?: number;
    progress?: number;
    completed?: boolean;
    message?: string;
  }> {
    const response = await apiClient.get(`/interview/question?session_id=${sessionId}`);
    return response.data as {
      question?: Question;
      question_index?: number;
      total_questions?: number;
      progress?: number;
      completed?: boolean;
      message?: string;
    };
  },

  // 답변 제출 (Orchestrator 기반)
  async submitAnswer(answerData: AnswerSubmission): Promise<{
    status: string;
    content?: {
      content: string;
    };
    flow_state?: string;
    next_action?: string;
    message?: string;
    question?: string;
    ai_answer?: string;
    next_question?: string;
    interview_progress?: {
      turn_count: number;
      total_questions: number;
      answer_seq: number;
      current_interviewer: string;
    };
    // 🆕 TTS 오디오 필드들 추가
    intro_audio?: string;
    ai_question_audio?: string;
    ai_answer_audio?: string;
    question_audio?: string;
  }> {
    const response = await apiClient.post('/interview/answer', answerData);
    return response.data as {
      status: string;
      content?: {
        content: string;
      };
      flow_state?: string;
      next_action?: string;
      message?: string;
      question?: string;
      ai_answer?: string;
      next_question?: string;
      interview_progress?: {
        turn_count: number;
        total_questions: number;
        answer_seq: number;
        current_interviewer: string;
      };
      // 🆕 TTS 오디오 필드들 추가
      intro_audio?: string;
      ai_question_audio?: string;
      ai_answer_audio?: string;
      question_audio?: string;
    };
  },

  // 면접 결과 조회
  async getInterviewResults(sessionId: string): Promise<InterviewResult> {
    const response = await apiClient.get(`/interview/results/${sessionId}`);
    return response.data as InterviewResult;
  },

  // 면접 기록 조회 (백엔드 /interview/history API 호출)
  async getInterviewHistory(): Promise<InterviewResponse[]> {
    const response = await apiClient.get('/interview/history');
    return response.data as InterviewResponse[];
  },

  // 전체 사용자 통계 조회
  async getGlobalStats(): Promise<{
    total_interviews: number;
    global_average_score: number;
  }> {
    const response = await apiClient.get('/interview/global-stats');
    return response.data as {
      total_interviews: number;
      global_average_score: number;
    };
  },

  // 면접 상세 결과 조회
  async getInterviewDetails(interviewId: string): Promise<any> {
    const response = await apiClient.get(`/interview/history/${interviewId}`);
    return response.data;
  },

  // 비언어적 피드백 (시선 분석) 조회
  async getGazeAnalysis(interviewId: string): Promise<GazeAnalysisResponse | null> {
    try {
      const response = await apiClient.get(`/interview/${interviewId}/gaze-analysis`);
      return response.data as GazeAnalysisResponse;
    } catch (error: any) {
      if (error.response?.status === 404) {
        // 시선 분석 데이터가 없는 경우
        return null;
      }
      throw error;
    }
  },

  // AI 경쟁 면접 시작 (Orchestrator 기반)
  async startAICompetition(settings: InterviewSettings): Promise<AICompetitionStartResponse> {
    // 🎯 무조건 InterviewerService 사용하도록 하드코딩
    console.log('🐛 DEBUG: API로 전송하는 원본 설정값:', settings);
    
    const finalSettings = {
      ...settings,
      use_interviewer_service: true  // 항상 InterviewerService 사용
    };
    
    console.log('🎯 DEBUG: 최종 전송 설정값 (InterviewerService 강제):', finalSettings);
    console.log('>>> [FRONTEND DEBUG] 최종 전송 직전 데이터:', JSON.stringify(finalSettings, null, 2));
    const response = await apiClient.post('/interview/ai/start', finalSettings);
    return response.data as AICompetitionStartResponse;
  },

  // 사용자 답변 제출
  async submitUserAnswer(sessionId: string, answer: string, timeSpent?: number): Promise<InterviewSubmitResponse> {
    const response = await apiClient.post('/interview/answer', {
      session_id: sessionId,
      answer: answer,
      time_spent: timeSpent || 0
    });
    return response.data as InterviewSubmitResponse;
  },

  // 경쟁 면접 통합 턴 처리 (사용자 답변 → AI 답변 + 다음 질문)
  async processCompetitionTurn(comparisonSessionId: string, answer: string): Promise<{
    status: string;
    ai_answer: {
      content: string;
    };
    next_question: any;
    next_user_question: any;
    interview_status: string;
    progress: {
      current: number;
      total: number;
      percentage: number;
    };
  }> {
    const response = await apiClient.post('/interview/comparison/turn', {
      comparison_session_id: comparisonSessionId,
      answer: answer
    });
    return response.data as {
      status: string;
      ai_answer: {
        content: string;
      };
      next_question: any;
      next_user_question: any;
      interview_status: string;
      progress: {
        current: number;
        total: number;
        percentage: number;
      };
    };
  },


  // AI 답변 생성
  async getAIAnswer(sessionId: string, questionId: string): Promise<{
    question: string;
    questionType: string;
    questionIntent: string;
    answer: string;
    time_spent: number;
    score: number;
    quality_level: string;
    persona_name: string;
  }> {
    const response = await apiClient.get(`/interview/ai-answer/${sessionId}/${questionId}`);
    return response.data as {
      question: string;
      questionType: string;
      questionIntent: string;
      answer: string;
      time_spent: number;
      score: number;
      quality_level: string;
      persona_name: string;
    };
  },

  // 서버 상태 확인
  async healthCheck(): Promise<{
    status: string;
    timestamp: string;
  }> {
    const response = await apiClient.get('/health');
    return response.data as {
      status: string;
      timestamp: string;
    };
  },

  // ============================================================================
  // 🚀 텍스트 기반 AI 경쟁 면접 API 메서드들
  // ============================================================================

  // 텍스트 기반 AI 경쟁 면접 시작
  async startTextCompetition(settings: InterviewSettings): Promise<{
    session_id: string;
    question: any;
    ai_persona: {
      name: string;
      summary: string;
      background: any;
    };
    interview_type: string;
    progress: {
      current: number;
      total: number;
      percentage: number;
    };
    message: string;
  }> {
    console.log('🎯 텍스트 경쟁 면접 API 호출:', settings);
    
    const response = await apiClient.post('/interview/text-competition/start', settings);
    
    console.log('✅ 텍스트 경쟁 면접 시작 응답:', response.data);
    
    return response.data as {
      session_id: string;
      question: any;
      ai_persona: {
        name: string;
        summary: string;
        background: any;
      };
      interview_type: string;
      progress: {
        current: number;
        total: number;
        percentage: number;
      };
      message: string;
    };
  },

  // 텍스트 답변 제출 및 AI 답변 + 다음 질문 받기
  async submitTextAnswer(sessionId: string, answer: string): Promise<{
    status: string;
    ai_answer?: {
      content: string;
    };
    next_question?: any;
    progress?: {
      current: number;
      total: number;
      percentage: number;
    };
    final_stats?: {
      total_questions: number;
      user_answers: number;
      ai_answers: number;
    };
    message: string;
    session_id?: string;
  }> {
    console.log('📝 텍스트 답변 제출:', sessionId, answer.substring(0, 50) + '...');
    
    const response = await apiClient.post('/interview/text-competition/answer', {
      session_id: sessionId,
      answer: answer
    });
    
    console.log('✅ 텍스트 답변 처리 응답:', response.data);
    
    return response.data as {
      status: string;
      ai_answer?: {
        content: string;
      };
      next_question?: any;
      progress?: {
        current: number;
        total: number;
        percentage: number;
      };
      final_stats?: {
        total_questions: number;
        user_answers: number;
        ai_answers: number;
      };
      message: string;
      session_id?: string;
    };
  },

  // 텍스트 기반 면접 세션 정보 조회
  async getTextSessionInfo(sessionId: string): Promise<{
    session_id: string;
    company_id: string;
    position: string;
    candidate_name: string;
    ai_persona: {
      name: string;
      summary: string;
    };
    progress: {
      current: number;
      total: number;
      percentage: number;
    };
    created_at: string;
  }> {
    const response = await apiClient.get(`/interview/text-competition/session/${sessionId}`);
    return response.data as {
      session_id: string;
      company_id: string;
      position: string;
      candidate_name: string;
      ai_persona: {
        name: string;
        summary: string;
      };
      progress: {
        current: number;
        total: number;
        percentage: number;
      };
      created_at: string;
    };
  },

  // 텍스트 기반 면접 결과 조회
  async getTextInterviewResults(sessionId: string): Promise<{
    session_id: string;
    company: string;
    position: string;
    candidate: string;
    ai_competitor: string;
    interview_type: string;
    total_questions: number;
    qa_pairs: Array<{
      question: string;
      user_answer: string;
      ai_answer: string;
      interviewer_type: string;
      timestamp: string;
    }>;
    summary: {
      message: string;
      user_answers_count: number;
      ai_answers_count: number;
    };
    completed_at: string;
  }> {
    const response = await apiClient.get(`/interview/text-competition/results/${sessionId}`);
    return response.data as {
      session_id: string;
      company: string;
      position: string;
      candidate: string;
      ai_competitor: string;
      interview_type: string;
      total_questions: number;
      qa_pairs: Array<{
        question: string;
        user_answer: string;
        ai_answer: string;
        interviewer_type: string;
        timestamp: string;
      }>;
      summary: {
        message: string;
        user_answers_count: number;
        ai_answers_count: number;
      };
      completed_at: string;
    };
  },

  // 텍스트 기반 면접 세션 정리
  async cleanupTextSession(sessionId: string): Promise<{
    message: string;
    session_id: string;
  }> {
    const response = await apiClient.delete(`/interview/text-competition/session/${sessionId}`);
    return response.data as {
      message: string;
      session_id: string;
    };
  },

  // 텍스트 기반 면접 시스템 통계
  async getTextInterviewStats(): Promise<{
    active_sessions: number;
    service_type: string;
    system_status: string;
  }> {
    const response = await apiClient.get('/interview/text-competition/stats');
    return response.data as {
      active_sessions: number;
      service_type: string;
      system_status: string;
    };
  },

  // TTS (Text-to-Speech) 음성 재생
  async playTTS(text: string): Promise<HTMLAudioElement> {
    console.log('🔊 TTS 요청:', text.substring(0, 50) + '...');
    
    const response = await apiClient.post('/interview/tts', 
      { 
        text: text,
        voice_id: '21m00Tcm4TlvDq8ikWAM' // Rachel 음성 (무료 기본 제공)
      }, 
      { 
        responseType: 'blob' // 오디오 데이터를 blob으로 받음
      }
    );
    
    // Blob을 오디오 URL로 변환
    const audioBlob = new Blob([response.data as BlobPart], { type: 'audio/mp3' });
    const audioUrl = URL.createObjectURL(audioBlob);
    
    // Audio 객체 생성 및 반환
    const audio = new Audio(audioUrl);
    
    console.log('✅ TTS 오디오 생성 완료');
    return audio;
  },

  // 면접 완료 (비동기 피드백 처리)
  async completeInterview(sessionId: string): Promise<{
    status: string;
    message: string;
    session_id: string;
    feedback_processing: boolean;
  }> {
    const response = await apiClient.post(`/interview/complete?session_id=${sessionId}`, {});
    return response.data as {
      status: string;
      message: string;
      session_id: string;
      feedback_processing: boolean;
    };
  },

  // 캘리브레이션 결과 조회
  async getCalibrationResult(sessionId: string): Promise<CalibrationResult> {
    try {
      const response = await apiClient.get<CalibrationResult>(`/test/gaze/calibration/result/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error(`캘리브레이션 결과 조회 API 실패 (세션 ID: ${sessionId}):`, error);
      throw error;
    }
  },

  // 🆕 시선 영상용 Pre-signed URL 요청
  async getGazeUploadUrl(request: GazeUploadUrlRequest): Promise<GazeUploadUrlResponse> {
    try {
      // 🛡️ 요청 데이터 검증
      if (!validateGazeUploadUrlRequest(request)) {
        throw new Error('잘못된 시선 업로드 요청 데이터입니다');
      }

      console.log('📤 시선 업로드 URL 요청:', request);
      const response = await apiClient.post('/media/gaze/upload-url', request);
      
      console.log('✅ 시선 업로드 URL 응답:', response.data);
      return response.data as GazeUploadUrlResponse;
    } catch (error) {
      console.error('🚨 시선 업로드 URL 요청 실패:', error);
      throw handleApiError(error);
    }
  },

  // 🆕 시선 분석 백그라운드 작업 트리거
  async triggerGazeAnalysis(request: GazeAnalysisTriggerRequest): Promise<GazeAnalysisTriggerResponse> {
    try {
      // 🛡️ 요청 데이터 검증
      if (!validateGazeAnalysisTriggerRequest(request)) {
        throw new Error('잘못된 시선 분석 트리거 요청 데이터입니다');
      }

      // 🛡️ 캘리브레이션 데이터 상세 검증
      if (!validateCalibrationData(request.calibration_data)) {
        throw new Error('유효하지 않은 캘리브레이션 데이터입니다');
      }

      console.log('🔍 시선 분석 트리거 요청:', {
        session_id: request.session_id,
        s3_key: request.s3_key,
        calibration_points_count: request.calibration_data.calibration_points?.length,
        has_initial_face_size: !!request.calibration_data.initial_face_size
      });
      console.log('DEBUG: POST /gaze/analyze/trigger 요청 전송 시도:', request); // 🆕 추가
      const response = await apiClient.post('/gaze/analyze-trigger', request);
      console.log('DEBUG: POST /gaze/analyze/trigger 응답 수신:', response.data); // 🆕 추가
      
      console.log('✅ 시선 분석 트리거 응답:', response.data);
      return response.data as GazeAnalysisTriggerResponse;
    } catch (error) {
      console.error('🚨 시선 분석 트리거 실패:', error);
      throw handleApiError(error);
    }
  },

  // 🆕 시선 분석 상태 조회
  async getGazeAnalysisStatus(taskId: string): Promise<any> {
    try {
      console.log('📊 시선 분석 상태 조회:', taskId);
      const response = await apiClient.get(`/gaze/analyze/status/${taskId}`);
      
      console.log('📊 시선 분석 상태 응답:', response.data);
      return response.data;
    } catch (error) {
      console.error('🚨 시선 분석 상태 조회 실패:', error);
      throw handleApiError(error);
    }
  },
};

// 에러 처리 유틸리티
export const handleApiError = (error: any): string => {
  console.log('API Error:', error); // 디버깅용
  
  if (error.response) {
    const status = error.response.status;
    const data = error.response.data;
    
    switch (status) {
      case 422:
        // 유효성 검증 실패 - 구체적 메시지
        if (data?.detail && Array.isArray(data.detail)) {
          return data.detail.map((err: any) => err.msg).join(', ');
        }
        return data?.detail || '입력한 정보가 올바르지 않습니다.';
      
      case 401:
        return '이메일 또는 비밀번호를 다시 확인해주세요.';
      
      case 400:
        return data?.detail || '입력하신 정보를 다시 확인해주세요.';
      
      case 404:
        return '요청한 정보를 찾을 수 없습니다.';
      
      case 500:
        return '일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      
      default:
        return data?.detail || '서버 오류가 발생했습니다.';
    }
  } else if (error.request) {
    // 네트워크 에러
    return '네트워크 연결을 확인해주세요.';
  } else {
    // 기타 에러
    return '알 수 없는 오류가 발생했습니다.';
  }
};

// 파일 크기 검증
export const validateFileSize = (file: File, maxSize: number = 16 * 1024 * 1024): boolean => {
  return file.size <= maxSize;
};

// 파일 확장자 검증
export const validateFileExtension = (file: File, allowedExtensions: string[] = ['pdf', 'doc', 'docx']): boolean => {
  const extension = file.name.split('.').pop()?.toLowerCase();
  return extension ? allowedExtensions.includes(extension) : false;
};

// 🆕 회사 정보 인터페이스
export interface Company {
  company_id: number;
  name: string;
  talent_profile?: string;
  core_competencies?: string;
  tech_focus?: string;
  interview_keywords?: string;
  question_direction?: string;
  company_culture?: string;
  technical_challenges?: string;
}

// 🆕 직군 정보 인터페이스
export interface Position {
  position_id: number;
  position_name: string;
}

// 🆕 채용공고 관련 API 함수들
export const postingAPI = {
  // 모든 회사 목록 조회
  async getAllCompanies(): Promise<Company[]> {
    try {
      const response = await apiClient.get('/company');
      return response.data as Company[];
    } catch (error) {
      console.error('회사 목록 조회 실패:', error);
      return [];
    }
  },

  // 모든 직군 목록 조회
  async getAllPositions(): Promise<Position[]> {
    try {
      const response = await apiClient.get('/position');
      return response.data as Position[];
    } catch (error) {
      console.error('직군 목록 조회 실패:', error);
      return [];
    }
  },

  // 회사와 직군으로 공고 조회
  async getPostingByCompanyAndPosition(companyId: number, positionId: number): Promise<JobPosting | null> {
    try {
      const response = await apiClient.get(`/posting/company/${companyId}/position/${positionId}`);
      return response.data as JobPosting;
    } catch (error) {
      console.error('회사/직군별 공고 조회 실패:', error);
      return null;
    }
  },

  // 모든 채용공고 조회
  async getAllPostings(): Promise<JobPosting[]> {
    try {
      const response = await apiClient.get('/posting');
      return response.data as JobPosting[];
    } catch (error) {
      console.error('채용공고 목록 조회 실패:', error);
      // fallback: 빈 배열 반환
      return [];
    }
  },

  // 특정 채용공고 상세 조회
  async getPostingById(postingId: number): Promise<JobPosting | null> {
    try {
      const response = await apiClient.get(`/posting/${postingId}`);
      return response.data as JobPosting;
    } catch (error) {
      console.error(`채용공고 상세 조회 실패 (ID: ${postingId}):`, error);
      return null;
    }
  },
};

// 🔐 인증 관련 타입 정의
export interface LoginRequest {
  email: string;
  pw: string;
}

export interface SignupRequest {
  name: string;
  email: string;
  pw: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  user: {
    user_id: number;
    name: string;
    email: string;
  };
}

export interface UserProfile {
  user_id: number;
  name: string;
  email: string;
}

// 🔐 인증 관련 API 함수들
export const authApi = {
  // 회원가입
  async signup(userData: SignupRequest): Promise<AuthResponse> {
    const response = await apiClient.post('/auth/signup', userData);
    return response.data as AuthResponse;
  },

  // 로그인
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await apiClient.post('/auth/login', credentials);
    return response.data as AuthResponse;
  },

  // 로그아웃
  async logout(): Promise<{ message: string }> {
    const response = await apiClient.post('/auth/logout');
    return response.data as { message: string };
  },

  // 현재 사용자 정보 조회
  async getCurrentUser(): Promise<UserProfile> {
    const response = await apiClient.get('/auth/user');
    return response.data as UserProfile;
  },

  // 토큰 검증
  async verifyToken(): Promise<{ valid: boolean; user?: any; error?: string }> {
    const response = await apiClient.get('/auth/verify');
    return response.data as { valid: boolean; user?: any; error?: string };
  },

  // OTP 발송
  async sendOtp(email: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/auth/send-otp', { email });
    return response.data as { success: boolean; message: string };
  },

  // OTP 검증
  async verifyOtp(email: string, code: string): Promise<{ success: boolean; verified: boolean; message: string }> {
    const response = await apiClient.post('/auth/verify-otp', { email, code });
    return response.data as { success: boolean; verified: boolean; message: string };
  },
};

// 토큰 관리 유틸리티
export const tokenManager = {
  // 토큰 저장
  setToken(token: string): void {
    localStorage.setItem('auth_token', token);
  },

  // 토큰 조회
  getToken(): string | null {
    return localStorage.getItem('auth_token');
  },

  // 토큰 삭제
  removeToken(): void {
    localStorage.removeItem('auth_token');
  },

  // 사용자 정보 저장
  setUser(user: UserProfile): void {
    localStorage.setItem('user_profile', JSON.stringify(user));
  },

  // 사용자 정보 조회
  getUser(): UserProfile | null {
    const userStr = localStorage.getItem('user_profile');
    return userStr ? JSON.parse(userStr) : null;
  },

  // 사용자 정보 삭제
  removeUser(): void {
    localStorage.removeItem('user_profile');
  },

  // 전체 인증 정보 삭제
  clearAuth(): void {
    this.removeToken();
    this.removeUser();
  },
};

// 🆕 Position 관련 타입 정의 (중복 제거됨 - 위의 Position 인터페이스 사용)

// 🆕 Resume 관련 타입 정의 (백엔드 스키마와 일치)
export interface ResumeCreate {
  academic_record: string;
  position_id: number;
  career: string;
  tech: string;
  activities: string;
  certificate: string;
  awards: string;
}

export interface ResumeResponse {
  user_resume_id: number;
  user_id: number;
  academic_record: string;
  position_id: number;
  created_date: string;
  updated_date: string;
  career: string;
  tech: string;
  activities: string;
  certificate: string;
  awards: string;
}

// 🆕 Position API 함수들
export const positionApi = {
  // 전체 직군 목록 조회
  async getPositions(): Promise<Position[]> {
    const response = await apiClient.get('/position');
    return response.data as Position[];
  },
};

// 🆕 Resume API 함수들
export const resumeApi = {
  // 내 이력서 목록 조회
  async getResumes(): Promise<ResumeResponse[]> {
    const response = await apiClient.get('/resume');
    return response.data as ResumeResponse[];
  },

  // 이력서 생성
  async createResume(resumeData: ResumeCreate): Promise<ResumeResponse> {
    const response = await apiClient.post('/resume', resumeData);
    return response.data as ResumeResponse;
  },

  // 이력서 상세 조회
  async getResumeById(resumeId: number): Promise<ResumeResponse> {
    const response = await apiClient.get(`/resume/${resumeId}`);
    return response.data as ResumeResponse;
  },

  // 이력서 수정
  async updateResume(resumeId: number, resumeData: ResumeCreate): Promise<ResumeResponse> {
    const response = await apiClient.put(`/resume/${resumeId}`, resumeData);
    return response.data as ResumeResponse;
  },

  // 이력서 삭제
  async deleteResume(resumeId: number): Promise<{ message: string }> {
    const response = await apiClient.delete(`/resume/${resumeId}`);
    return response.data as { message: string };
  },
};

// 🆕 Session API 함수들 - InterviewService 상태에서 sessionId 관리
export const sessionApi = {
  // 현재 활성 세션들 조회
  async getActiveSessions(): Promise<{ active_sessions: string[]; count: number }> {
    const response = await apiClient.get('/interview/session/active');
    return response.data as { active_sessions: string[]; count: number };
  },

  // 특정 세션의 상태 조회
  async getSessionState(sessionId: string): Promise<{ session_id: string; state: any; is_active: boolean }> {
    const response = await apiClient.get(`/interview/session/${sessionId}/state`);
    return response.data as { session_id: string; state: any; is_active: boolean };
  },

  // 가장 최신 활성 세션 ID 가져오기
  async getLatestSessionId(): Promise<string | null> {
    try {
      const { active_sessions } = await this.getActiveSessions();
      return active_sessions.length > 0 ? active_sessions[active_sessions.length - 1] : null;
    } catch (error) {
      console.error('최신 세션 ID 조회 실패:', error);
      return null;
    }
  },
};

// 🆕 시선 추적 관련 API 타입 정의 (백엔드 스키마와 정확히 일치)
export interface GazeUploadUrlRequest {
  session_id: string;
  file_name: string;
  file_type: 'video';
  file_size?: number;
  content_type?: string;  // 실제 MIME 타입 추가
}

export interface GazeUploadUrlResponse {
  upload_url: string;
  media_id: string;
  s3_key: string;
  expires_in: number;
}

export interface GazeAnalysisTriggerRequest {
  session_id: string;
  s3_key: string;
  calibration_data: CalibrationResult;
  media_id?: string;
}

export interface GazeAnalysisTriggerResponse {
  task_id: string;
  status: string;
  message?: string;
}

// 🛡️ 타입 가드 및 검증 함수들
const validateGazeUploadUrlRequest = (request: any): request is GazeUploadUrlRequest => {
  return request && 
         typeof request.session_id === 'string' && 
         request.session_id.length > 0 && 
         typeof request.file_name === 'string' && 
         request.file_name.length > 0 &&
         request.file_type === 'video';
};

const validateCalibrationData = (data: any): data is CalibrationResult => {
  return data && 
         typeof data.session_id === 'string' && // Add session_id check
         data.calibration_points && 
         Array.isArray(data.calibration_points) && 
         data.calibration_points.length === 4 &&
         (data.initial_face_size === undefined || data.initial_face_size === null || typeof data.initial_face_size === 'number');
         // Removed checks for point_details, collection_stats, completed_at
};

const validateGazeAnalysisTriggerRequest = (request: any): request is GazeAnalysisTriggerRequest => {
  return request &&
         typeof request.session_id === 'string' &&
         request.session_id.length > 0 &&
         typeof request.s3_key === 'string' &&
         request.s3_key.length > 0 &&
         // 🆕 media_id 검증 수정: media_id가 존재할 경우에만 string 및 length 검증
         (request.media_id === undefined || (typeof request.media_id === 'string' && request.media_id.length > 0)) &&
         validateCalibrationData(request.calibration_data);
};


export default apiClient;