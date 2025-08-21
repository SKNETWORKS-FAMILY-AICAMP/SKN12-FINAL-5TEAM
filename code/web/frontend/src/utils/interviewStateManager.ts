// Interview State Management Utility
// localStorage의 interview_state를 관리하기 위한 유틸리티

export interface InterviewState {
  sessionId: string;
  settings: any; // InterviewSettings 타입
  interviewStatus: string;
  timestamp: number;
  jobPosting?: any;
  resume?: any;
  interviewMode?: string;
  aiSettings?: any;
  interviewStartResponse?: any;
  
  // API 호출 관리 플래그들
  needsApiCall?: boolean;        // API 호출이 필요한지 여부
  apiCallCompleted?: boolean;    // API 호출이 완료되었는지 여부
  apiCallError?: string;         // API 호출 중 발생한 에러 메시지
  
  // 추가 메타데이터
  questions?: any[];
  lastUpdateTime?: number;
}

const STORAGE_KEY = 'interview_state';

/**
 * localStorage에서 면접 상태를 안전하게 가져옴
 */
export const getInterviewState = (): InterviewState | null => {
  try {
    const savedState = localStorage.getItem(STORAGE_KEY);
    if (!savedState) return null;
    
    const parsedState = JSON.parse(savedState) as InterviewState;
    
    // 기본적인 유효성 검증
    if (!parsedState.sessionId || !parsedState.settings) {
      console.warn('⚠️ localStorage에 저장된 면접 상태가 불완전함');
      return null;
    }
    
    return parsedState;
  } catch (error) {
    console.error('❌ localStorage에서 면접 상태 파싱 실패:', error);
    return null;
  }
};

/**
 * localStorage에 면접 상태를 안전하게 저장
 */
export const saveInterviewState = (state: InterviewState): void => {
  try {
    const stateToSave = {
      ...state,
      lastUpdateTime: Date.now()
    };
    
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
    console.log('💾 면접 상태 localStorage 저장 완료');
  } catch (error) {
    console.error('❌ localStorage에 면접 상태 저장 실패:', error);
  }
};

/**
 * API 호출 완료 상태로 업데이트 (sessionId 동기화 포함)
 */
export const markApiCallCompleted = (response?: any, error?: string): void => {
  const currentState = getInterviewState();
  if (!currentState) return;
  
  const updatedState: InterviewState = {
    ...currentState,
    apiCallCompleted: true,
    needsApiCall: false,  // API 호출이 완료되면 더이상 필요 없음
    // 🆕 실제 API 응답의 sessionId로 동기화
    ...(response?.session_id && { sessionId: response.session_id }),
    ...(response && { interviewStartResponse: response }),
    ...(error && { apiCallError: error })
  };
  
  saveInterviewState(updatedState);
  
  // 🆕 메모리 기반 진행 상태도 완료로 설정
  setApiCallInProgress(response?.session_id || currentState.sessionId, false);
  
  console.log('✅ API 호출 완료 상태로 업데이트됨 (sessionId 동기화 포함):', {
    oldSessionId: currentState.sessionId,
    newSessionId: response?.session_id || currentState.sessionId,
    apiCallCompleted: true
  });
};

/**
 * API 호출이 필요한 상태인지 확인
 */
export const needsApiCall = (): boolean => {
  const state = getInterviewState();
  if (!state) return false;
  
  return Boolean(state.needsApiCall && !state.apiCallCompleted);
};

/**
 * localStorage 면접 상태 초기화
 */
export const clearInterviewState = (): void => {
  localStorage.removeItem(STORAGE_KEY);
  console.log('🗑️ localStorage 면접 상태 초기화 완료');
};

// 🆕 메모리 기반 실시간 호출 상태 관리 (React Strict Mode 대응)
let _apiCallInProgress = false;
let _currentSessionId: string | null = null;

/**
 * API 호출 진행 상태 설정
 */
export const setApiCallInProgress = (sessionId: string, inProgress: boolean): void => {
  _apiCallInProgress = inProgress;
  _currentSessionId = sessionId;
  console.log(`🚦 API 호출 진행 상태 변경: ${inProgress ? '진행 중' : '완료'} (세션: ${sessionId})`);
};

/**
 * API 호출 진행 중인지 확인 (메모리 기반, React Strict Mode 안전)
 */
export const isApiCallInProgress = (sessionId?: string): boolean => {
  const inProgress = _apiCallInProgress && (!sessionId || _currentSessionId === sessionId);
  console.log(`🔍 API 호출 진행 상태 확인: ${inProgress ? '진행 중' : '완료/대기'} (요청 세션: ${sessionId}, 현재 세션: ${_currentSessionId})`);
  return inProgress;
};

/**
 * 면접 상태 디버그 정보 출력
 */
export const debugInterviewState = (): void => {
  const state = getInterviewState();
  if (!state) {
    console.log('🔍 DEBUG: localStorage에 저장된 면접 상태 없음');
    return;
  }
  
  console.log('🔍 DEBUG: 현재 면접 상태:', {
    sessionId: state.sessionId,
    mode: state.settings?.mode,
    needsApiCall: state.needsApiCall,
    apiCallCompleted: state.apiCallCompleted,
    hasResponse: Boolean(state.interviewStartResponse),
    lastUpdate: state.lastUpdateTime ? new Date(state.lastUpdateTime).toLocaleString() : 'Unknown',
    // 🆕 메모리 상태 추가
    memoryApiInProgress: _apiCallInProgress,
    memoryCurrentSession: _currentSessionId
  });
};