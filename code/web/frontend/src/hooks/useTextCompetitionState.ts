import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { textCompetitionApi } from '../services/textCompetitionApi';
import { handleApiError } from '../services/api';

interface ChatMessage {
  type: 'question' | 'user' | 'ai';
  content: string;
  timestamp: Date;
}

interface UseTextCompetitionStateProps {
  sessionId: string | null;
  currentQuestion: any;
  onProgressUpdate?: (progress: any) => void;
}

export const useTextCompetitionState = ({
  sessionId,
  currentQuestion,
  onProgressUpdate
}: UseTextCompetitionStateProps) => {
  const navigate = useNavigate();
  
  // 상태 관리
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastAiAnswer, setLastAiAnswer] = useState<string>('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isCompleted, setIsCompleted] = useState(false);

  // 채팅 히스토리에 메시지 추가
  const addMessage = useCallback((message: ChatMessage) => {
    setChatHistory(prev => [...prev, message]);
  }, []);

  // 초기 질문을 채팅 히스토리에 추가
  const initializeChatHistory = useCallback((question: any) => {
    if (question && chatHistory.length === 0) {
      const questionContent = question?.question || "면접을 시작하겠습니다.";
      setChatHistory([{
        type: 'question',
        content: questionContent,
        timestamp: new Date()
      }]);
    }
  }, [chatHistory.length]);

  // 답변 제출 처리
  const submitAnswer = useCallback(async () => {
    if (!currentAnswer.trim() || !sessionId) {
      alert('답변을 입력해주세요.');
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      console.log('📝 답변 제출:', currentAnswer.substring(0, 50) + '...');
      
      // 채팅 히스토리에 사용자 답변 추가
      addMessage({
        type: 'user',
        content: currentAnswer,
        timestamp: new Date()
      });
      
      // 백엔드 API 호출 - 답변 제출 및 AI 답변 + 다음 질문 받기
      const response = await textCompetitionApi.submitTextAnswer(sessionId, currentAnswer);
      
      console.log('✅ 답변 처리 응답:', response);
      
      // AI 답변이 있다면 채팅 히스토리에 추가
      if (response.ai_answer?.content) {
        setLastAiAnswer(response.ai_answer.content);
        addMessage({
          type: 'ai',
          content: response.ai_answer.content,
          timestamp: new Date()
        });
      }
      
      // 진행률 업데이트
      if (response.progress && onProgressUpdate) {
        onProgressUpdate(response.progress);
      }
      
      if (response.status === 'completed') {
        // 면접 완료
        console.log('🏁 텍스트 면접 완료');
        setIsCompleted(true);
        
        // 결과 페이지로 이동
        setTimeout(() => {
          navigate('/interview/results', {
            state: {
              sessionId: sessionId,
              isTextCompetition: true
            }
          });
        }, 2000);
        
      } else if (response.next_question) {
        // 다음 질문 추가
        addMessage({
          type: 'question',
          content: response.next_question.question,
          timestamp: new Date()
        });
      }
      
      // 답변 입력란 초기화
      setCurrentAnswer('');
      
    } catch (error) {
      console.error('❌ 답변 제출 실패:', error);
      alert(`답변 제출 실패: ${handleApiError(error)}`);
    } finally {
      setIsSubmitting(false);
    }
  }, [currentAnswer, sessionId, addMessage, onProgressUpdate, navigate]);

  return {
    // 상태
    currentAnswer,
    setCurrentAnswer,
    isSubmitting,
    lastAiAnswer,
    chatHistory,
    isCompleted,
    
    // 액션
    addMessage,
    initializeChatHistory,
    submitAnswer
  };
};