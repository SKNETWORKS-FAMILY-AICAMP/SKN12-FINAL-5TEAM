
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// 요청 중복 방지를 위한 맵
const activeRequests = new Map<string, Promise<any>>();

// 중복 요청 방지 래퍼
const withDuplicationPrevention = <T>(
  key: string, 
  requestFn: () => Promise<T>
): Promise<T> => {
  if (activeRequests.has(key)) {
    console.log(`🚫 중복 요청 방지: ${key} - 기존 요청 대기 중`);
    return activeRequests.get(key)!;
  }

  console.log(`✅ 새로운 요청 시작: ${key}`);
  const promise = requestFn()
    .finally(() => {
      console.log(`🏁 요청 완료 및 정리: ${key}`);
      activeRequests.delete(key);
    });

  activeRequests.set(key, promise);
  return promise;
};

// 공통 fetch 함수
const fetchApi = async (url: string, options: RequestInit = {}) => {
  const token = localStorage.getItem('access_token');
  
  const defaultHeaders = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` })
  };

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers
    }
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
};

// 텍스트 경쟁 면접 시작
export const startTextCompetition = async (settings: any) => {
  // 더 간단한 중복 방지 키 생성 (JSON.stringify 제거)
  const requestKey = `start-text-competition-${settings.company}-${settings.position}-${settings.candidate_name}`;
  
  return withDuplicationPrevention(requestKey, async () => {
    console.log('🚀 텍스트 경쟁 면접 시작 API 호출 시작');
    console.log('📋 요청 설정 전체:', settings);
    console.log('📄 이력서 데이터 확인:', settings.resume ? '있음' : '없음');
    if (settings.resume) {
      console.log('📝 이력서 상세:', {
        name: settings.resume.name,
        tech: settings.resume.tech,
        career: settings.resume.career
      });
    }
    
    const response = await fetchApi('/interview/text-competition/start', {
      method: 'POST',
      body: JSON.stringify(settings)
    });

    console.log('✅ 텍스트 경쟁 면접 시작 성공');
    console.log('📄 응답 데이터:', response);
    return response;
  });
};

// 답변 제출 및 다음 질문 받기
export const submitTextAnswer = async (sessionId: string, answer: string) => {
  const requestKey = `submit-answer-${sessionId}-${Date.now()}`;
  
  return withDuplicationPrevention(requestKey, async () => {
    console.log('📝 텍스트 답변 제출 API 호출');
    
    const response = await fetchApi('/interview/text-competition/submit-answer', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        answer: answer
      })
    });

    console.log('✅ 텍스트 답변 제출 성공:', response);
    return response;
  });
};

// 면접 진행률 조회
export const getTextProgress = async (sessionId: string) => {
  return fetchApi(`/interview/text-competition/progress/${sessionId}`);
};

// 면접 결과 조회
export const getTextResults = async (sessionId: string) => {
  return fetchApi(`/interview/text-competition/results/${sessionId}`);
};

// AI 페르소나 정보 조회
export const getAiPersona = async (sessionId: string) => {
  return fetchApi(`/interview/text-competition/ai-persona/${sessionId}`);
};

// 면접 세션 종료
export const endTextSession = async (sessionId: string) => {
  return fetchApi('/interview/text-competition/end', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId })
  });
};

// 텍스트 경쟁 API 객체
export const textCompetitionApi = {
  startTextCompetition,
  submitTextAnswer,
  getTextProgress,
  getTextResults,
  getAiPersona,
  endTextSession
};