import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

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
    console.log('API 응답:', response.status, response.data);
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

  // 답변 제출
  async submitAnswer(answerData: AnswerSubmission): Promise<{
    score: number;
    message: string;
    detailed_evaluation: string;
  }> {
    const response = await apiClient.post('/interview/answer', answerData);
    return response.data as {
      score: number;
      message: string;
      detailed_evaluation: string;
    };
  },

  // 면접 결과 조회
  async getInterviewResults(sessionId: string): Promise<InterviewResult> {
    const response = await apiClient.get(`/interview/results/${sessionId}`);
    return response.data as InterviewResult;
  },

  // 면접 기록 조회
  async getInterviewHistory(userId?: string): Promise<InterviewHistory> {
    const params = userId ? { user_id: userId } : {};
    const response = await apiClient.get('/interview/history', { params });
    return response.data as InterviewHistory;
  },

  // AI 경쟁 면접 시작
  async startAICompetition(settings: InterviewSettings): Promise<{
    session_id: string;
    comparison_session_id: string;
    user_session_id: string;
    ai_session_id: string;
    question?: Question;
    current_phase: string;
    current_respondent: string;
    question_index: number;
    total_questions: number;
    ai_name: string;
    user_name?: string;
    starts_with_user: boolean;
    message: string;
  }> {
    // 🎯 무조건 InterviewerService 사용하도록 하드코딩
    console.log('🐛 DEBUG: API로 전송하는 원본 설정값:', settings);
    
    const finalSettings = {
      ...settings,
      use_interviewer_service: true  // 항상 InterviewerService 사용
    };
    
    console.log('🎯 DEBUG: 최종 전송 설정값 (InterviewerService 강제):', finalSettings);
    
    const response = await apiClient.post('/interview/ai/start', finalSettings);
    return response.data as {
      session_id: string;
      comparison_session_id: string;
      user_session_id: string;
      ai_session_id: string;
      question?: Question;
      current_phase: string;
      current_respondent: string;
      question_index: number;
      total_questions: number;
      ai_name: string;
      user_name?: string;
      starts_with_user: boolean;
      message: string;
    };
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
        return '이메일 또는 비밀번호가 올바르지 않습니다.';
      
      case 400:
        return data?.detail || '잘못된 요청입니다.';
      
      case 404:
        return data?.detail || '요청한 정보를 찾을 수 없습니다.';
      
      case 500:
        return '서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      
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

// 🆕 채용공고 관련 API 함수들
export const postingAPI = {
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

// 🆕 Position 관련 타입 정의
export interface Position {
  position_id: number;
  position_name: string;
}

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

export default apiClient;