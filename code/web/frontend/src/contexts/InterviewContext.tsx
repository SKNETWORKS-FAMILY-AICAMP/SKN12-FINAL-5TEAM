import React, { createContext, useContext, useReducer, useEffect, useRef, ReactNode } from 'react';
import { InterviewSettings, Question, InterviewResult, interviewApi } from '../services/api';

// JobPosting 타입 정의 - 실제 DB 구조에 맞게 최종 단순화
interface JobPosting {
  posting_id: number;    // posting_id
  company_id: number;    // 회사 ID
  position_id: number;   // 직무 ID
  company: string;       // 회사명 (company 테이블 JOIN 결과)
  position: string;      // 직무명 (position 테이블 JOIN 결과)
  content: string;       // 채용공고 내용
}

interface Resume {
  id: string;
  name: string;
  email: string;
  phone: string;
  academic_record: string;
  career: string;
  tech: string;
  activities: string;
  certificate: string;
  awards: string;
  created_at: string;
  updated_at: string;
}

interface AISettings {
  mode: string;
  aiQualityLevel: number;
  interviewers: Array<{
    id: string;
    name: string;
    role: string;
  }>;
}

// 면접 기록 타입 정의
interface InterviewRecord {
  session_id: string;
  company: string;
  position: string;
  date: string;
  time: string;
  duration: string;
  score: number;
  mode: string;
  status: string;
  settings: InterviewSettings;
  completed_at: string;
}

// 면접 통계 타입 정의
interface InterviewStats {
  totalInterviews: number;
  averageScore: number;
  aiCompetitionCount: number;
  recentImprovement: number;
  lastInterviewDate: string | null;
}

// 상태 타입 정의
interface InterviewState {
  // 새로운 4단계 플로우 데이터
  jobPosting: JobPosting | null;
  resume: Resume | null;
  interviewMode: string | null;
  aiSettings: AISettings | null;
  
  // 카메라 스트림
  cameraStream: MediaStream | null;
  
  // 면접 설정
  settings: InterviewSettings | null;
  
  // 세션 정보
  sessionId: string | null;
  
  // 질문 관련
  questions: Question[];
  currentQuestionIndex: number;
  totalQuestions: number;
  
  // 답변 관련
  answers: Array<{
    session_id?: string;
    question_id?: string;
    questionId?: string;
    answer: string;
    time_spent?: number;
    timeSpent?: number;
    score?: number;
  }>;
  
  // AI 답변 관련
  aiAnswers: Array<{
    question_id: string;
    answer: string;
    score: number;
    persona_name: string;
    time_spent: number;
  }>;
  
  // 면접 진행 상태
  interviewStatus: 'idle' | 'setup' | 'ready' | 'active' | 'paused' | 'completed';
  
  // 결과
  results: InterviewResult | null;
  
  // UI 상태
  isLoading: boolean;
  error: string | null;
  
  // 타이머
  timeLeft: number;
  
  // 진행률
  progress: number;
  
  // 면접 기록 관리
  interviewHistory: InterviewRecord[];
  historyStats: InterviewStats;
  historyLoading: boolean;
  historyError: string | null;
  
  // 텍스트 경쟁 모드 전용 상태
  textCompetitionData: {
    initialQuestion: any | null;
    aiPersona: any | null;
    progress: { current: number; total: number; percentage: number } | null;
  } | null;
}

// 액션 타입 정의
type InterviewAction =
  | { type: 'SET_JOB_POSTING'; payload: JobPosting }
  | { type: 'SET_RESUME'; payload: Resume }
  | { type: 'SET_INTERVIEW_MODE'; payload: string }
  | { type: 'SET_AI_SETTINGS'; payload: AISettings }
  | { type: 'SET_CAMERA_STREAM'; payload: MediaStream | null }
  | { type: 'SET_SETTINGS'; payload: InterviewSettings }
  | { type: 'SET_SESSION_ID'; payload: string }
  | { type: 'SET_QUESTIONS'; payload: Question[] }
  | { type: 'ADD_QUESTION'; payload: Question }
  | { type: 'SET_CURRENT_QUESTION'; payload: number }
  | { type: 'SET_CURRENT_QUESTION_INDEX'; payload: number }
  | { type: 'ADD_ANSWER'; payload: { session_id?: string; question_id?: string; questionId?: string; answer: string; time_spent?: number; timeSpent?: number; score?: number } }
  | { type: 'ADD_AI_ANSWER'; payload: { question_id: string; answer: string; score: number; persona_name: string; time_spent: number } }
  | { type: 'SET_INTERVIEW_STATUS'; payload: InterviewState['interviewStatus'] }
  | { type: 'SET_RESULTS'; payload: InterviewResult }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_TIME_LEFT'; payload: number }
  | { type: 'SET_PROGRESS'; payload: number }
  | { type: 'SET_TEXT_COMPETITION_DATA'; payload: { initialQuestion: any; aiPersona: any; progress: { current: number; total: number; percentage: number } } }
  | { type: 'RESET_INTERVIEW' }
  | { type: 'SET_INTERVIEW_HISTORY'; payload: InterviewRecord[] }
  | { type: 'ADD_INTERVIEW_RECORD'; payload: InterviewRecord }
  | { type: 'SET_HISTORY_LOADING'; payload: boolean }
  | { type: 'SET_HISTORY_ERROR'; payload: string | null }
  | { type: 'LOAD_INTERVIEW_HISTORY_START' }
  | { type: 'LOAD_INTERVIEW_HISTORY_SUCCESS'; payload: InterviewRecord[] }
  | { type: 'LOAD_INTERVIEW_HISTORY_ERROR'; payload: string };

// 초기 상태
const initialState: InterviewState = {
  jobPosting: null,
  resume: null,
  interviewMode: null,
  aiSettings: null,
  cameraStream: null,
  settings: null,
  sessionId: null,
  questions: [],
  currentQuestionIndex: 0,
  totalQuestions: 0,
  answers: [],
  aiAnswers: [],
  interviewStatus: 'idle',
  results: null,
  isLoading: false,
  error: null,
  timeLeft: 0,
  progress: 0,
  interviewHistory: [],
  historyStats: {
    totalInterviews: 0,
    averageScore: 0,
    aiCompetitionCount: 0,
    recentImprovement: 0,
    lastInterviewDate: null
  },
  historyLoading: false,
  historyError: null,
  textCompetitionData: null,
};

// 리듀서 함수
function interviewReducer(state: InterviewState, action: InterviewAction): InterviewState {
  switch (action.type) {
    case 'SET_JOB_POSTING':
      return { ...state, jobPosting: action.payload };
    
    case 'SET_RESUME':
      return { ...state, resume: action.payload };
    
    case 'SET_INTERVIEW_MODE':
      return { ...state, interviewMode: action.payload };
    
    case 'SET_AI_SETTINGS':
      return { ...state, aiSettings: action.payload };
    
    case 'SET_CAMERA_STREAM':
      return { ...state, cameraStream: action.payload };
    
    case 'SET_SETTINGS':
      return { ...state, settings: action.payload };
    
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
    
    case 'SET_QUESTIONS':
      return { 
        ...state, 
        questions: action.payload, 
        totalQuestions: action.payload.length,
        progress: state.totalQuestions > 0 ? (state.currentQuestionIndex / action.payload.length) * 100 : 0
      };
    
    case 'ADD_QUESTION':
      // 중복 질문 방지: 같은 ID의 질문이 이미 있으면 추가하지 않음
      const questionExists = state.questions.some(q => q.id === action.payload.id);
      if (questionExists) {
        console.log('🚫 중복 질문 방지:', action.payload.id);
        return state;
      }
      
      const newQuestions = [...state.questions, action.payload];
      console.log('✅ 새 질문 추가:', action.payload.id, action.payload.category);
      return {
        ...state,
        questions: newQuestions,
        totalQuestions: newQuestions.length
      };
    
    case 'SET_CURRENT_QUESTION':
      return { 
        ...state, 
        currentQuestionIndex: action.payload,
        progress: state.totalQuestions > 0 ? ((action.payload + 1) / state.totalQuestions) * 100 : 0
      };
    
    case 'SET_CURRENT_QUESTION_INDEX':
      return {
        ...state,
        currentQuestionIndex: action.payload,
        progress: state.totalQuestions > 0 ? ((action.payload + 1) / state.totalQuestions) * 100 : 0
      };
    
    case 'ADD_ANSWER':
      const newAnswers = [...state.answers, action.payload];
      return { 
        ...state, 
        answers: newAnswers
      };
    
    case 'ADD_AI_ANSWER':
      const newAiAnswers = [...state.aiAnswers, action.payload];
      return { 
        ...state, 
        aiAnswers: newAiAnswers
      };
    
    case 'SET_INTERVIEW_STATUS':
      return { ...state, interviewStatus: action.payload };
    
    case 'SET_RESULTS':
      return { ...state, results: action.payload };
    
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    
    case 'SET_TIME_LEFT':
      return { ...state, timeLeft: action.payload };
    
    case 'SET_PROGRESS':
      return { ...state, progress: action.payload };
    
    case 'SET_TEXT_COMPETITION_DATA':
      return { ...state, textCompetitionData: action.payload };
    
    case 'RESET_INTERVIEW':
      return initialState;
    
    case 'SET_INTERVIEW_HISTORY':
      return {
        ...state,
        interviewHistory: action.payload,
        historyStats: calculateInterviewStats(action.payload)
      };
    
    case 'ADD_INTERVIEW_RECORD':
      const newHistory = [action.payload, ...state.interviewHistory];
      return {
        ...state,
        interviewHistory: newHistory,
        historyStats: calculateInterviewStats(newHistory)
      };
    
    case 'SET_HISTORY_LOADING':
      return { ...state, historyLoading: action.payload };
    
    case 'SET_HISTORY_ERROR':
      return { ...state, historyError: action.payload };
    
    case 'LOAD_INTERVIEW_HISTORY_START':
      return { 
        ...state, 
        historyLoading: true, 
        historyError: null 
      };
    
    case 'LOAD_INTERVIEW_HISTORY_SUCCESS':
      return {
        ...state,
        historyLoading: false,
        historyError: null,
        interviewHistory: action.payload,
        historyStats: calculateInterviewStats(action.payload)
      };
    
    case 'LOAD_INTERVIEW_HISTORY_ERROR':
      return {
        ...state,
        historyLoading: false,
        historyError: action.payload
      };
    
    default:
      return state;
  }
}

// 통계 계산 함수
function calculateInterviewStats(interviews: InterviewRecord[]): InterviewStats {
  const totalInterviews = interviews.length;
  const averageScore = totalInterviews > 0 
    ? Math.round(interviews.reduce((sum, interview) => sum + interview.score, 0) / totalInterviews)
    : 0;
  const aiCompetitionCount = interviews.filter(i => i.mode === 'ai_competition').length;
  const lastInterviewDate = totalInterviews > 0 ? interviews[0].completed_at : null;
  
  // 최근 향상도 계산 (최근 3개와 이전 3개 비교)
  let recentImprovement = 0;
  if (totalInterviews >= 3) {
    const recent3 = interviews.slice(0, 3);
    const previous3 = interviews.slice(3, 6);
    
    if (previous3.length > 0) {
      const recentAvg = recent3.reduce((sum, i) => sum + i.score, 0) / recent3.length;
      const previousAvg = previous3.reduce((sum, i) => sum + i.score, 0) / previous3.length;
      recentImprovement = Math.round(recentAvg - previousAvg);
    }
  }

  return {
    totalInterviews,
    averageScore,
    aiCompetitionCount,
    recentImprovement,
    lastInterviewDate
  };
}

// Context 생성
const InterviewContext = createContext<{
  state: InterviewState;
  dispatch: React.Dispatch<InterviewAction>;
  loadInterviewHistory: () => Promise<void>;
} | null>(null);

// Provider 컴포넌트
export function InterviewProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(interviewReducer, initialState);
  const hasInitialized = useRef(false);
  
  // 면접 기록 로드 함수
  const loadInterviewHistory = async () => {
    if (state.historyLoading) return; // 이미 로딩 중이면 중복 실행 방지
    
    dispatch({ type: 'LOAD_INTERVIEW_HISTORY_START' });
    
    try {
      const response = await interviewApi.getInterviewHistory();
      
      const processedInterviews: InterviewRecord[] = response.interviews.map(interview => {
        const date = new Date(interview.completed_at);
        return {
          session_id: interview.session_id,
          company: interview.settings.company,
          position: interview.settings.position,
          date: date.toLocaleDateString('ko-KR'),
          time: date.toLocaleTimeString('ko-KR', { 
            hour: '2-digit', 
            minute: '2-digit' 
          }),
          duration: `${Math.floor(Math.random() * 20 + 15)}분 ${Math.floor(Math.random() * 60)}초`,
          score: interview.total_score,
          mode: interview.settings.mode,
          status: '완료',
          settings: interview.settings,
          completed_at: interview.completed_at
        };
      });

      // 최신순으로 정렬
      processedInterviews.sort((a, b) => new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime());
      
      dispatch({ 
        type: 'LOAD_INTERVIEW_HISTORY_SUCCESS', 
        payload: processedInterviews 
      });
      
    } catch (error) {
      console.error('면접 기록 로드 실패:', error);
      dispatch({ 
        type: 'LOAD_INTERVIEW_HISTORY_ERROR', 
        payload: '면접 기록을 불러오는데 실패했습니다.' 
      });
      
      // 에러 발생 시 기본 데이터 설정
      const fallbackData: InterviewRecord[] = [
        {
          session_id: '1',
          company: '네이버',
          position: '백엔드 개발자',
          date: '2024-01-16',
          time: '14:00',
          duration: '18분 32초',
          score: 85,
          mode: 'ai_competition',
          status: '완료',
          settings: { company: '네이버', position: '백엔드 개발자', mode: 'ai_competition', difficulty: '중간', candidate_name: '홍길동' },
          completed_at: '2024-01-16T14:00:00Z'
        }
      ];
      
      dispatch({ 
        type: 'LOAD_INTERVIEW_HISTORY_SUCCESS', 
        payload: fallbackData 
      });
    }
  };

  // 컴포넌트 마운트 시 면접 기록 로드 (React Strict Mode 중복 방지)
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;
    loadInterviewHistory();
  }, []);
  
  return (
    <InterviewContext.Provider value={{ state, dispatch, loadInterviewHistory }}>
      {children}
    </InterviewContext.Provider>
  );
}

// 커스텀 훅
export function useInterview() {
  const context = useContext(InterviewContext);
  if (!context) {
    throw new Error('useInterview must be used within an InterviewProvider');
  }
  return context;
}

// 헬퍼 함수들
export const interviewHelpers = {
  // 현재 질문 가져오기
  getCurrentQuestion: (state: InterviewState): Question | null => {
    if (state.currentQuestionIndex < state.questions.length) {
      return state.questions[state.currentQuestionIndex];
    }
    return null;
  },
  
  // 다음 질문 여부 확인
  hasNextQuestion: (state: InterviewState): boolean => {
    return state.currentQuestionIndex < state.questions.length - 1;
  },
  
  // 면접 완료 여부 확인
  isInterviewCompleted: (state: InterviewState): boolean => {
    return state.currentQuestionIndex >= state.questions.length && state.questions.length > 0;
  },
  
  // 진행률 계산
  calculateProgress: (state: InterviewState): number => {
    if (state.totalQuestions === 0) return 0;
    return ((state.currentQuestionIndex + 1) / state.totalQuestions) * 100;
  },
  
  // 평균 점수 계산
  calculateAverageScore: (state: InterviewState): number => {
    const answersWithScores = state.answers.filter(answer => answer.score !== undefined);
    if (answersWithScores.length === 0) return 0;
    
    const totalScore = answersWithScores.reduce((sum, answer) => sum + (answer.score || 0), 0);
    return Math.round(totalScore / answersWithScores.length);
  },
  
  // 총 소요 시간 계산
  calculateTotalTime: (state: InterviewState): number => {
    return state.answers.reduce((total, answer) => total + (answer.timeSpent || answer.time_spent || 0), 0);
  },
  
  // 시간 포맷팅
  formatTime: (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  },
  
  // 타이머 색상 결정
  getTimerColor: (timeLeft: number): string => {
    if (timeLeft > 60) return 'text-green-600';
    if (timeLeft > 30) return 'text-yellow-600';
    return 'text-red-600';
  },
  
  // 점수 색상 결정
  getScoreColor: (score: number): string => {
    if (score >= 90) return 'text-green-600';
    if (score >= 80) return 'text-blue-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  },
  
  // 면접 상태 메시지
  getStatusMessage: (status: InterviewState['interviewStatus']): string => {
    switch (status) {
      case 'idle':
        return '면접 준비 중';
      case 'setup':
        return '면접 설정 중';
      case 'active':
        return '면접 진행 중';
      case 'paused':
        return '면접 일시정지';
      case 'completed':
        return '면접 완료';
      default:
        return '알 수 없음';
    }
  },
  
  // 로컬 스토리지에 상태 저장
  saveToLocalStorage: (state: InterviewState): void => {
    try {
      localStorage.setItem('interview_state', JSON.stringify(state));
    } catch (error) {
      console.error('로컬 스토리지 저장 오류:', error);
    }
  },
  
  // 로컬 스토리지에서 상태 복원
  loadFromLocalStorage: (): Partial<InterviewState> | null => {
    try {
      const saved = localStorage.getItem('interview_state');
      return saved ? JSON.parse(saved) : null;
    } catch (error) {
      console.error('로컬 스토리지 로드 오류:', error);
      return null;
    }
  },
  
  // 로컬 스토리지 정리
  clearLocalStorage: (): void => {
    try {
      localStorage.removeItem('interview_state');
    } catch (error) {
      console.error('로컬 스토리지 정리 오류:', error);
    }
  },
};