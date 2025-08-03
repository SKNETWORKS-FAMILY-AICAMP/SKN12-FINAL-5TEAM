import { useState, useCallback, useRef } from 'react';
import { interviewApi, handleApiError, InterviewSettings } from '../services/api';

interface UseInterviewStartReturn {
  startInterview: (settings: InterviewSettings, source: 'new' | 'restart' | 'environment') => Promise<any>;
  isStarting: boolean;
  error: string | null;
}

// 전역 상태로 React.StrictMode의 중복 실행 방지
let globalInterviewStarting = false;
let globalStartTimeout: NodeJS.Timeout | null = null;

export const useInterviewStart = (): UseInterviewStartReturn => {
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startAttemptRef = useRef<string | null>(null);

  const startInterview = useCallback(async (
    settings: InterviewSettings, 
    source: 'new' | 'restart' | 'environment'
  ) => {
    // 전역 중복 호출 차단 (React.StrictMode 대응)
    if (globalInterviewStarting) {
      console.log('⚠️ 전역 면접 시작 이미 진행 중 - 중복 호출 차단 (StrictMode 대응)');
      return null;
    }

    // 로컬 중복 호출 차단
    if (isStarting) {
      console.log('⚠️ 로컬 면접 시작 이미 진행 중 - 중복 호출 차단');
      return null;
    }

    // 동일한 시도 ID로 중복 방지
    const attemptId = `${source}_${Date.now()}`;
    if (startAttemptRef.current === attemptId) {
      console.log('⚠️ 동일한 시도 ID - 중복 호출 차단');
      return null;
    }

    // 전역 플래그 설정
    globalInterviewStarting = true;
    startAttemptRef.current = attemptId;
    setIsStarting(true);
    setError(null);

    // 기존 타임아웃 클리어
    if (globalStartTimeout) {
      clearTimeout(globalStartTimeout);
    }

    try {
      console.log(`🚀 면접 시작: ${source} (시도 ID: ${attemptId})`, settings);
      
      // AI 경쟁 면접 시작 API 호출
      const response = await interviewApi.startAICompetition(settings);
      
      console.log('✅ AI 경쟁 면접 시작 성공:', response);
      
      return response;
    } catch (err) {
      console.error(`❌ 면접 시작 실패 (${source}):`, err);
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      throw err;
    } finally {
      setIsStarting(false);
      
      // 전역 플래그를 일정 시간 후 해제 (비동기 처리 완료 보장)
      globalStartTimeout = setTimeout(() => {
        globalInterviewStarting = false;
        startAttemptRef.current = null;
        console.log('🔓 전역 면접 시작 플래그 해제');
      }, 2000); // 2초 후 해제
    }
  }, [isStarting]);

  return {
    startInterview,
    isStarting,
    error
  };
};