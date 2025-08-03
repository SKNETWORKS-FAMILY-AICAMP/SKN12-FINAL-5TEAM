import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useInterview } from '../contexts/InterviewContext';
import { useTextCompetitionInit } from '../hooks/useTextCompetitionInit';
import { useTextCompetitionState } from '../hooks/useTextCompetitionState';
import TextCompetitionHeader from '../components/interview/TextCompetitionHeader';
import ChatHistory from '../components/interview/ChatHistory';
import AnswerInput from '../components/interview/AnswerInput';

const InterviewActiveTemp: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  
  // 초기화 훅
  const initializationState = useTextCompetitionInit({
    sessionId: state.sessionId,
    settings: state.settings,
    textCompetitionData: state.textCompetitionData,
    onSessionIdUpdate: (sessionId: string) => {
      dispatch({ type: 'SET_SESSION_ID', payload: sessionId });
    }
  });

  // 상태 관리 훅
  const competitionState = useTextCompetitionState({
    sessionId: initializationState.sessionId || state.sessionId,
    currentQuestion: initializationState.currentQuestion,
    onProgressUpdate: (progress) => {
      // 진행률 업데이트 처리 (필요시 Context에 저장)
      console.log('진행률 업데이트:', progress);
    }
  });

  // 초기화 상태에서 데이터 가져오기
  const currentQuestion = initializationState.currentQuestion;
  const aiPersona = initializationState.aiPersona;
  const progress = initializationState.progress || { current: 0, total: 15, percentage: 0 };

  // 초기화가 완료되면 채팅 히스토리 초기화
  React.useEffect(() => {
    if (initializationState.isInitialized && currentQuestion) {
      competitionState.initializeChatHistory(currentQuestion);
    }
  }, [initializationState.isInitialized, currentQuestion, competitionState]);


  // 초기화 에러 처리
  if (initializationState.error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex items-center justify-center">
        <div className="text-white text-center">
          <p className="text-xl mb-4 text-red-400">면접 초기화 실패</p>
          <p className="text-gray-300 mb-6">{initializationState.error}</p>
          <div className="space-x-4">
            <button
              onClick={initializationState.retry}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              다시 시도
            </button>
            <button
              onClick={() => navigate('/interview/setup')}
              className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              설정으로 돌아가기
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!state.settings) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex items-center justify-center">
        <div className="text-white text-center">
          <p className="text-xl mb-4">면접 설정이 없습니다.</p>
          <button
            onClick={() => navigate('/interview/setup')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            설정으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  // 텍스트 경쟁 모드 UI 렌더링 함수
  const renderTextCompetitionUI = () => {
    if (initializationState.isLoading || !initializationState.isInitialized || !currentQuestion || !aiPersona) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex items-center justify-center">
          <div className="text-white text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-xl">텍스트 면접을 준비 중입니다...</p>
            {initializationState.isLoading && (
              <p className="text-sm text-gray-400 mt-2">AI 면접관과 연결 중...</p>
            )}
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-black">
        <TextCompetitionHeader 
          aiPersona={aiPersona}
          progress={progress}
        />

        <div className="max-w-4xl mx-auto p-6 h-screen flex flex-col">
          <ChatHistory
            chatHistory={competitionState.chatHistory}
            aiPersona={aiPersona}
            candidateName={state.settings?.candidate_name || '지원자'}
            isCompleted={competitionState.isCompleted}
          />

          <AnswerInput
            currentAnswer={competitionState.currentAnswer}
            setCurrentAnswer={competitionState.setCurrentAnswer}
            onSubmit={competitionState.submitAnswer}
            isSubmitting={competitionState.isSubmitting}
            isCompleted={competitionState.isCompleted}
          />
        </div>
      </div>
    );
  };

  // 텍스트 경쟁 모드라면 전용 UI 렌더링
  if (state.settings.mode === 'text_competition') {
    return renderTextCompetitionUI();
  }

  // 기존 모드는 간단한 메시지만 표시
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex items-center justify-center">
      <div className="text-white text-center">
        <h2 className="text-2xl font-bold mb-4">면접 모드: {state.settings.mode}</h2>
        <p className="text-gray-300 mb-6">
          현재 이 모드는 텍스트 경쟁 모드가 아닙니다.<br/>
          InterviewActive_temp.tsx는 text_competition 모드 전용입니다.
        </p>
        <button
          onClick={() => navigate('/interview/setup')}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          설정으로 돌아가기
        </button>
      </div>
    </div>
  );
};

export default InterviewActiveTemp;