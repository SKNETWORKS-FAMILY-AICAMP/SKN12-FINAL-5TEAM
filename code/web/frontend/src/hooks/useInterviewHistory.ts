import { useInterview } from '../contexts/InterviewContext';

// 면접 기록 관련 커스텀 훅
export const useInterviewHistory = () => {
  const { state, dispatch, loadInterviewHistory } = useInterview();
  
  const {
    interviewHistory,
    historyStats,
    historyLoading,
    historyError
  } = state;

  // 새로운 면접 기록 추가
  const addInterviewRecord = (interview: any) => {
    dispatch({ type: 'ADD_INTERVIEW_RECORD', payload: interview });
  };

  // 데이터 새로고침
  const refreshHistory = async () => {
    await loadInterviewHistory();
  };

  return {
    // 데이터
    interviews: interviewHistory,
    stats: historyStats,
    
    // 상태
    isLoading: historyLoading,
    error: historyError,
    
    // 액션
    addInterviewRecord,
    refreshHistory
  };
};

// 메인 페이지 통계용 커스텀 훅
export const useInterviewStats = () => {
  const { state } = useInterview();
  
  return {
    totalInterviews: state.historyStats.totalInterviews,
    averageScore: state.historyStats.averageScore,
    lastInterviewDate: state.historyStats.lastInterviewDate,
    isLoading: state.historyLoading
  };
};