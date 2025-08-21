import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInterview } from '../contexts/InterviewContext';
import { useAuth } from '../hooks/useAuth';
import { sessionApi, interviewApi, tokenManager } from '../services/api';
import apiClient, { handleApiError } from '../services/api';
import LoadingSpinner from '../components/common/LoadingSpinner';
import SpeechIndicator from '../components/voice/SpeechIndicator';
import GazeVideoUploader from '../components/gaze/GazeVideoUploader';
import { getInterviewState, markApiCallCompleted, debugInterviewState, setApiCallInProgress, isApiCallInProgress } from '../utils/interviewStateManager';
import { GazeAnalysisResult, VideoAnalysisResponse, AnalysisStatusResponse } from '../components/test/types';

// API Base URL 설정
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// API 응답 타입 정의
interface UploadResponse {
  play_url: string;
  file_name?: string;
  file_type?: string;
  media_id?: string;
}

interface PresignedUploadResponse {
  upload_url: string;
  media_id: string;
  test_id?: string; // 백엔드에서 test_id도 반환될 수 있음
}

interface FeedbackEvaluationRequest {
  user_id: number;
  user_resume_id: number | null;
  ai_resume_id: number | null;
  posting_id: number | null;
  company_id: number | null;
  position_id: number | null;
  qa_pairs: {
    question: string;
    answer: string;
    duration: number;
    question_level: number;
  }[];
}

interface FeedbackEvaluationResponse {
  success: boolean;
  results?: {
    interview_id: number;
    evaluation_id: number;
  }[];
  message?: string;
}

const InterviewGO: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  const { user } = useAuth();

  // sessionId를 InterviewService 상태에서 가져오기
  React.useEffect(() => {
    const loadSessionFromService = async () => {
      try {
        // 1. 이미 Context에 sessionId가 있으면 OK
        if (state.sessionId) {
          console.log('✅ Context에 sessionId 존재:', state.sessionId);
          setIsRestoring(false);
          return;
        }

        // 2. InterviewService의 활성 세션에서 sessionId 가져오기
        console.log('🔍 InterviewService에서 활성 세션 조회 중...');
        const latestSessionId = await sessionApi.getLatestSessionId();
        
        if (latestSessionId) {
          console.log('✅ InterviewService에서 sessionId 발견:', latestSessionId);
          
          // 세션 상태도 함께 가져오기
          const sessionState = await sessionApi.getSessionState(latestSessionId);
          console.log('📋 세션 상태:', sessionState);
          
          // Context에 sessionId 설정
          dispatch({ type: 'SET_SESSION_ID', payload: latestSessionId });
          setIsRestoring(false);
          return;
        }

        // 3. localStorage에서 sessionId 복원 시도 (fallback)
        const saved = localStorage.getItem('interview_state');
        if (saved) {
          const parsedState = JSON.parse(saved);
          console.log('📦 localStorage에서 상태 복원 시도:', parsedState.sessionId);
          
          if (parsedState.sessionId) {
            dispatch({ type: 'SET_SESSION_ID', payload: parsedState.sessionId });
            console.log('✅ localStorage에서 sessionId 복원 완료:', parsedState.sessionId);
            setIsRestoring(false);
            return;
          }
        }

        // 4. sessionId가 없으면 환경 체크로 이동
        console.log('❌ sessionId를 찾을 수 없습니다. 환경 체크 페이지로 이동합니다.');
        navigate('/interview/environment-check');
        
      } catch (error) {
        console.error('❌ sessionId 로드 실패:', error);
        navigate('/interview/environment-check');
      } finally {
        setIsRestoring(false);
      }
    };

    loadSessionFromService();
  }, [state.sessionId, dispatch, navigate]);

  // 🎥 카메라 스트림 검증 및 연결
  useEffect(() => {
    const validateAndConnectStream = async () => {
      console.log('🔍 카메라 스트림 검증 시작:', !!state.cameraStream);
      
      // 1. 스트림 객체가 존재하는지 확인
      if (!state.cameraStream) {
        console.log('❌ 카메라 스트림이 없습니다.');
        alert('카메라 연결에 문제가 발생했습니다. 환경 체크 페이지로 다시 이동합니다.');
        navigate('/interview/environment-check');
        return;
      }
      
      // 2. 스트림이 활성화 상태인지 확인
      if (!state.cameraStream.active) {
        console.log('❌ 카메라 스트림이 비활성화 상태입니다.');
        alert('카메라 연결에 문제가 발생했습니다. 환경 체크 페이지로 다시 이동합니다.');
        navigate('/interview/environment-check');
        return;
      }
      
      // 3. 비디오 트랙이 존재하고 live 상태인지 확인
      const videoTracks = state.cameraStream.getVideoTracks();
      if (videoTracks.length === 0 || videoTracks[0].readyState !== 'live') {
        console.log('❌ 카메라 비디오 트랙이 유효하지 않습니다:', videoTracks.length, videoTracks[0]?.readyState);
        alert('카메라 연결에 문제가 발생했습니다. 환경 체크 페이지로 다시 이동합니다.');
        navigate('/interview/environment-check');
        return;
      }
      
      // 4. 모든 검증을 통과했다면 비디오 엘리먼트에 스트림 연결
      if (videoRef.current) {
        console.log('✅ 카메라 스트림 검증 완료 - 비디오 엘리먼트에 연결');
        videoRef.current.srcObject = state.cameraStream;
        
        try {
          await videoRef.current.play();
          console.log('✅ 카메라 비디오 재생 시작');
        } catch (playError) {
          console.warn('⚠️ 비디오 자동 재생 실패 (권한 문제일 수 있음):', playError);
        }
      }
    };

    // cameraStream이 존재할 때 검증 실행
    if (state.cameraStream) {
      validateAndConnectStream();
    }
  }, [state.cameraStream, navigate]);

  // 🧹 컴포넌트 언마운트 시 비디오 스트림 정리 (메모리 누수 방지)
  useEffect(() => {
    const currentVideoRef = videoRef.current;
    return () => {
      if (currentVideoRef) {
        console.log('🧹 비디오 엘리먼트 스트림 연결 해제');
        currentVideoRef.srcObject = null;
      }
    };
  }, []);
  // 🆕 currentPhase 상태 추가
  const [currentPhase, setCurrentPhase] = useState<'user_turn' | 'ai_processing' | 'interview_completed' | 'waiting' | 'unknown' | 'intro' | 'ready'>('waiting');
  // ✨ 새 면접 시작 시 시선 추적 상태 초기화
  useEffect(() => {
    if (currentPhase === 'intro' || currentPhase === 'ready') {
      console.log('✨ 새 면접 시작 - 시선 추적 상태 초기화 시작...', { currentPhase });
      setGazeBlob(null);
      setIsGazeRecording(false);
      setGazeError(null);
      setGazeAnalysisResult(null);
      setPollingError(null);
      // Context 상태 초기화
      dispatch({ type: 'RESET_GAZE_TRACKING' });
      console.log('✨ 시선 추적 상태가 초기화되었습니다.');
    }
  }, [currentPhase]);

  // 난이도별 AI 지원자 이미지 매핑 함수
  const getAICandidateImage = (level: number): string => {
    if (level <= 3) return '/img/nano-banana_____.png'; // 초급자
    if (level <= 7) return '/img/nano-banana__Create_an_image_of_.png'; // 중급자
    return '/img/nano-banana______2.png'; // 고급자
  };

  // 난이도별 AI 지원자 이름 매핑 함수
  const getAICandidateName = (level: number): string => {
    if (level <= 3) return '춘식이 (초급)';
    if (level <= 7) return '춘식이 (중급)';
    return '춘식이 (고급)';
  };
  
  // 🆕 새로운 상태들 추가
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(false); // 면접 초기 시작 로딩
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false); // 답변 제출 중
  const [isRestoring, setIsRestoring] = useState(true); // 복원 상태 추가
  const [currentTTSType, setCurrentTTSType] = useState<string | null>(null); // 현재 TTS 타입
  
  // 🆕 INTRO 메시지 관련 상태
  const [introMessage, setIntroMessage] = useState<string>('');
  const [hasIntroMessage, setHasIntroMessage] = useState(false);
  const [showIntroMessage, setShowIntroMessage] = useState(false);
  
  // 🆕 TTS 관련 상태
  const [isTTSPlaying, setIsTTSPlaying] = useState(false);
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);
  
  // 🔊 TTS 확인용 주석입니다 - TTS 실행 이력 추적
  const [ttsList, setTtsList] = useState<{type: string, text: string, timestamp: string}[]>([]);
  
  // 🔊 TTS 확인용 주석입니다 - TTS 큐 시스템 (타입 정보 포함)
  const [ttsQueue, setTtsQueue] = useState<{type: string, content: string}[]>([]);
  const [currentTTSIndex, setCurrentTTSIndex] = useState(-1);
  
  // 🆕 AI 질문/답변 관련 상태
  const [currentAIQuestion, setCurrentAIQuestion] = useState<string>('');
  const [currentAIAnswer, setCurrentAIAnswer] = useState<string>('');
  
  // 🆕 턴 관리 상태
  const [currentTurn, setCurrentTurn] = useState<'user' | 'ai' | 'waiting'>('waiting');
  const [timeLeft, setTimeLeft] = useState(120); // 2분 타이머
  const [isTimerActive, setIsTimerActive] = useState(false);
  const [canSubmit, setCanSubmit] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  
  
  
  // 🎤 음성 관련 상태
  const [isRecording, setIsRecording] = useState(false);
  const [canRecord, setCanRecord] = useState(false);
  const [sttResult, setSttResult] = useState('');
  const [recordingTime, setRecordingTime] = useState(0);
  const [hasAudioPermission, setHasAudioPermission] = useState<boolean | null>(null);

  // 👁️ 시선 추적 관련 상태
  const [isGazeRecording, setIsGazeRecording] = useState(false);
  const [gazeBlob, setGazeBlob] = useState<Blob | null>(null);
  const [gazeError, setGazeError] = useState<string | null>(null);
  const [gazeAnalysisResult, setGazeAnalysisResult] = useState<GazeAnalysisResult | null>(null);
  
  const answerRef = useRef<HTMLTextAreaElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  
  // 🆕 API 호출 중복 방지를 위한 useRef
  const apiCallCancelRef = useRef<AbortController | null>(null);
  const isApiCallInProgressRef = useRef(false);
  

  // 👁️ 시선 추적용 refs
  const gazeVideoRef = useRef<HTMLVideoElement>(null);
  const gazeMediaRecorderRef = useRef<MediaRecorder | null>(null);
  const gazeChunksRef = useRef<Blob[]>([]);

  // 👁️ 시선 분석 폴링 관련 상태 (Context로 이전됨)
  const [pollingError, setPollingError] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollingMainTimeoutRef = useRef<NodeJS.Timeout | null>(null); // 5분 타임아웃용

  // 📊 백그라운드 피드백 처리 상태
  const [isFeedbackProcessing, setIsFeedbackProcessing] = useState(false);
  const [feedbackProcessingError, setFeedbackProcessingError] = useState<string | null>(null);

  // 🆕 시간 만료 핸들러
  const handleTimeUp = useCallback(() => {
    console.log('⏰ 시간 만료!');
    setIsTimerActive(false);
    setCanSubmit(false);
    
    // 답변이 있을 때만 제출
    if (currentAnswer.trim() && currentPhase === 'user_turn' && !isLoading) {
      alert('시간이 만료되었습니다! 답변을 자동 제출합니다.');
      // submitAnswer 함수를 비동기로 호출하되, 에러를 잡아서 처리
      setTimeout(() => {
        if (typeof submitAnswer === 'function') {
          submitAnswer().catch(console.error);
        }
      }, 0);
    } else {
      alert('시간이 만료되었습니다!');
    }
  }, [currentAnswer, currentPhase, isLoading]);

  // 🆕 타이머 관리
  useEffect(() => {
    // 사용자 턴이고 타이머가 활성화되어 있을 때만 타이머 실행
    if (currentTurn === 'user' && isTimerActive && timeLeft > 0) {
      timerRef.current = setInterval(() => {
        setTimeLeft(prev => {
          if (prev <= 1) {
            handleTimeUp();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      // 타이머 정지
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [currentTurn, isTimerActive, timeLeft, handleTimeUp]);

  // 🆕 백엔드에서 생성된 base64 오디오 재생 함수
  const playBase64Audio = async (base64Data: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      try {
        console.log('🔊 Base64 오디오 재생 시작');
        setIsTTSPlaying(true);
        
        // 이전 오디오가 있으면 정지
        if (currentAudio) {
          currentAudio.pause();
          currentAudio.currentTime = 0;
        }
        
        // base64 → blob → Audio 객체 생성
        const binaryString = atob(base64Data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const audioBlob = new Blob([bytes], { type: 'audio/mp3' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        
        setCurrentAudio(audio);
        
        // 재생 완료 이벤트
        audio.onended = () => {
          console.log('✅ Base64 오디오 재생 완료');
          setIsTTSPlaying(false);
          setCurrentAudio(null);
          URL.revokeObjectURL(audioUrl); // 메모리 정리
          resolve();
        };
        
        // 재생 에러 이벤트
        audio.onerror = () => {
          console.error('❌ Base64 오디오 재생 실패');
          setIsTTSPlaying(false);
          setCurrentAudio(null);
          URL.revokeObjectURL(audioUrl); // 메모리 정리
          reject(new Error('Base64 오디오 재생 실패'));
        };
        
        // 오디오 재생 시작
        audio.play();
        
      } catch (error) {
        console.error('❌ TTS 호출 실패:', error);
        setIsTTSPlaying(false);
        setCurrentAudio(null);
        reject(error);
      }
    });
  };

  const stopTTS = () => {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      setCurrentAudio(null);
    }
    setIsTTSPlaying(false);
  };

  // 🆕 백엔드에서 받은 오디오들을 순차적으로 재생하는 함수
  const playSequentialAudio = async (response: any) => {
    try {
      console.log('🎵 순차 오디오 재생 시작');
      
      // 1. INTRO 오디오 재생
      if (response.intro_audio) {
        console.log('🎤 INTRO 오디오 재생');
        await playBase64Audio(response.intro_audio);
      }
      
      // 2. AI 질문 오디오 재생
      if (response.ai_question_audio) {
        console.log('🤖 AI 질문 오디오 재생');
        await playBase64Audio(response.ai_question_audio);
      }
      
      // 3. AI 답변 오디오 재생
      if (response.ai_answer_audio) {
        console.log('🤖 AI 답변 오디오 재생');
        await playBase64Audio(response.ai_answer_audio);
      }
      
      // 4. 사용자 질문 오디오 재생
      if (response.question_audio) {
        console.log('👤 사용자 질문 오디오 재생');
        await playBase64Audio(response.question_audio);
      }
      
      console.log('✅ 모든 오디오 재생 완료');
      
    } catch (error) {
      console.error('❌ 순차 오디오 재생 실패:', error);
      // TTS 실패해도 정상 진행
    }
  };

  // 🆕 타이머 포맷 함수
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // 🆕 타이머 색상 함수
  const getTimerColor = (): string => {
    if (timeLeft > 60) return 'text-green-600';
    if (timeLeft > 30) return 'text-yellow-600';
    return 'text-red-600';
  };

  // AI 응답에서 resume_id 추출 및 Context 업데이트 함수
  const extractAndSaveAIResumeId = (response: any) => {
    try {
      console.log('🔍 AI resume_id 추출 시도 시작...');
      
      // 다양한 경로에서 AI 메타데이터 찾기
      const sources = [
        { name: 'ai_answer.metadata', data: response?.ai_answer?.metadata },
        { name: 'metadata', data: response?.metadata },
        { name: 'content.metadata', data: response?.content?.metadata },
        { name: 'turn_info.ai_metadata', data: response?.turn_info?.ai_metadata },
        { name: 'ai_response.metadata', data: response?.ai_response?.metadata },
        { name: 'content.ai_answer.metadata', data: response?.content?.ai_answer?.metadata }
      ];

      console.log('🔍 검색할 메타데이터 경로들:');
      sources.forEach((source, index) => {
        console.log(`  ${index + 1}. ${source.name}:`, source.data);
      });

      for (const source of sources) {
        if (source.data?.resume_id && typeof source.data.resume_id === 'number') {
          console.log(`✅ AI resume_id 추출 성공 (${source.name}):`, source.data.resume_id);
          dispatch({ type: 'SET_EXTRACTED_AI_RESUME_ID', payload: source.data.resume_id });
          return; // 첫 번째로 찾은 유효한 ID 사용
        }
      }

      console.log('⚠️ AI resume_id를 찾을 수 없습니다.');
    } catch (error) {
      console.warn('❌ AI resume_id 추출 중 오류:', error);
    }
  };

  // 🆕 텍스트를 TTS로 변환하여 재생하는 함수 (타입별 음성 지원)
  const generateAndPlayTTS = async (text: string, type: string, label: string = "", questionText?: string): Promise<void> => {
    if (!text || !text.trim()) {
      console.log(`[🔊 TTS] ${label} 텍스트가 비어있음 - TTS 건너뜀`);
      return;
    }

    // 🔊 TTS 확인용 주석입니다 - 실행된 TTS를 리스트에 추가
    const ttsEntry = {
      type: label,
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString()
    };
    setTtsList(prev => [...prev, ttsEntry]);

    // 🎯 타입별 음성으로 1차 시도
    try {
      console.log(`[🔊 TTS] ${label} TTS 생성 시작 (타입: ${type}): ${text.slice(0, 50)}...`);
      
      // 타입별 TTS API 호출
      const response = await fetch(`${API_BASE_URL}/interview/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text.trim(),
          voice_id: getVoiceIdByType(type)
        })
      });

      if (!response.ok) {
        throw new Error(`TTS API 오류: ${response.status}`);
      }

      const audioData = await response.arrayBuffer();
      console.log(`[🔊 TTS] ${label} 타입별 TTS 생성 완료, 재생 시작`);

      // 오디오 재생
      const audioBlob = new Blob([audioData], { type: 'audio/mp3' });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      // 🎯 TTS 재생 시작 - 타입 설정, 로딩 상태 해제, 질문 텍스트 표시
      setCurrentTTSType(type);
      setIsInitialLoading(false); // TTS 시작과 동시에 로딩 해제
      
      // 질문 텍스트를 TTS와 동기화하여 표시
      if (questionText) {
        setCurrentQuestion(questionText);
        console.log(`[📝 TTS 동기화] 질문 텍스트 표시: ${questionText}`);
      }
      
      console.log(`[🎯 하이라이트] TTS 재생 시작 - 타입: ${type} 설정됨, 로딩 해제됨`);

      // 재생 완료 대기
      await new Promise<void>((resolve, reject) => {
        audio.onended = () => {
          console.log(`[🔊 TTS] ${label} 타입별 TTS 재생 완료`);
          // 🎯 TTS 재생 완료 - 타입 초기화
          setCurrentTTSType(null);
          console.log(`[🎯 하이라이트] TTS 재생 완료 - 타입 초기화됨`);
          URL.revokeObjectURL(audioUrl);
          resolve();
        };
        audio.onerror = () => {
          console.error(`[🔊 TTS] ${label} 타입별 TTS 재생 실패`);
          // 🎯 TTS 재생 실패 - 타입 초기화
          setCurrentTTSType(null);
          console.log(`[🎯 하이라이트] TTS 재생 실패 - 타입 초기화됨`);
          URL.revokeObjectURL(audioUrl);
          reject(new Error('타입별 TTS 재생 실패'));
        };
        audio.play().catch(reject);
      });

      return; // 성공 시 종료

    } catch (error) {
      console.warn(`[🔊 TTS] ${label} 타입별 TTS 실패, 기본 음성으로 폴백:`, error);
      
      // 🔄 기본 음성으로 2차 시도 (폴백)
      try {
        console.log(`[🔊 TTS] ${label} 기본 음성으로 TTS 재시도...`);
        
        const fallbackResponse = await fetch(`${API_BASE_URL}/interview/tts`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            text: text.trim(),
            voice_id: "21m00Tcm4TlvDq8ikWAM" // Rachel 음성 (기본값)
          })
        });

        if (!fallbackResponse.ok) {
          throw new Error(`폴백 TTS API 오류: ${fallbackResponse.status}`);
        }

        const fallbackAudioData = await fallbackResponse.arrayBuffer();
        console.log(`[🔊 TTS] ${label} 기본 음성 TTS 생성 완료, 재생 시작`);

        // 오디오 재생
        const audioBlob = new Blob([fallbackAudioData], { type: 'audio/mp3' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);

        // 🎯 폴백 TTS 재생 시작 - 타입 설정
        setCurrentTTSType(type);
        // 질문 텍스트를 TTS와 동기화하여 표시
        if (questionText) {
          setCurrentQuestion(questionText);
          console.log(`[📝 TTS 동기화] 질문 텍스트 표시: ${questionText}`);
        }
        console.log(`[🎯 하이라이트] 폴백 TTS 재생 시작 - 타입: ${type} 설정됨`);

        // 재생 완료 대기
        await new Promise<void>((resolve, reject) => {
          audio.onended = () => {
            console.log(`[🔊 TTS] ${label} 기본 음성 TTS 재생 완료`);
            // 🎯 폴백 TTS 재생 완료 - 타입 초기화
            setCurrentTTSType(null);
            console.log(`[🎯 하이라이트] 폴백 TTS 재생 완료 - 타입 초기화됨`);
            URL.revokeObjectURL(audioUrl);
            resolve();
          };
          audio.onerror = () => {
            console.error(`[🔊 TTS] ${label} 기본 음성 TTS 재생 실패`);
            // 🎯 폴백 TTS 재생 실패 - 타입 초기화
            setCurrentTTSType(null);
            console.log(`[🎯 하이라이트] 폴백 TTS 재생 실패 - 타입 초기화됨`);
            URL.revokeObjectURL(audioUrl);
            reject(new Error('기본 음성 TTS 재생 실패'));
          };
          audio.play().catch(reject);
        });

      } catch (fallbackError) {
        console.error(`[🔊 TTS] ${label} 모든 TTS 시도 실패:`, fallbackError);
        // 🎯 모든 TTS 실패 시 타입 초기화
        setCurrentTTSType(null);
        console.log(`[🎯 하이라이트] 모든 TTS 실패 - 타입 초기화됨`);
      }
    }
  };

  // 🎵 개별 TTS 생성 함수 - 스트리밍용
  const generateSingleTTS = async (item: {type: string, content: string}, index: number, totalCount: number): Promise<HTMLAudioElement | null> => {
    try {
      console.log(`🎵 [TTS 개별] ${index + 1}/${totalCount} 생성 시작: [${item.type}] ${item.content.substring(0, 50)}...`);
      
      // 타입별 TTS API 호출
      const response = await fetch(`${API_BASE_URL}/interview/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: item.content.trim(),
          voice_id: getVoiceIdByType(item.type)
        })
      });

      if (!response.ok) {
        throw new Error(`TTS API 오류: ${response.status}`);
      }

      const audioData = await response.arrayBuffer();
      const audioBlob = new Blob([audioData], { type: 'audio/mp3' });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.volume = 0.8; // 🔊 모든 TTS 볼륨 통일
      
      console.log(`🎵 [TTS 개별] ${index + 1}/${totalCount} 생성 완료: [${item.type}]`);
      return audio;
      
    } catch (error) {
      console.warn(`🎵 [TTS 개별] ${index + 1}/${totalCount} 생성 실패, 폴백 시도: [${item.type}]`, error);
      
      // 폴백: 기본 음성으로 재시도
      try {
        const fallbackResponse = await fetch(`${API_BASE_URL}/interview/tts`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            text: item.content.trim(),
            voice_id: "21m00Tcm4TlvDq8ikWAM" // 기본 Rachel 음성
          })
        });

        if (!fallbackResponse.ok) {
          throw new Error(`폴백 TTS API 오류: ${fallbackResponse.status}`);
        }

        const fallbackAudioData = await fallbackResponse.arrayBuffer();
        const audioBlob = new Blob([fallbackAudioData], { type: 'audio/mp3' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.volume = 0.8; // 🔊 폴백 TTS도 동일한 볼륨
        
        console.log(`🎵 [TTS 개별] ${index + 1}/${totalCount} 폴백 생성 완료: [${item.type}]`);
        return audio;
        
      } catch (fallbackError) {
        console.error(`🎵 [TTS 개별] ${index + 1}/${totalCount} 모든 생성 실패: [${item.type}]`, fallbackError);
        return null;
      }
    }
  };

  // 🔊 TTS 확인용 주석입니다 - 큐에 텍스트 추가 함수 (더 이상 사용하지 않음 - 동기적 수집 방식으로 변경)
  // const addToTTSQueue = (text: string, label: string = "") => {
  //   if (text && text.trim()) {
  //     setTtsQueue(prev => [...prev, text.trim()]);
  //     console.log(`🔊 [큐 추가] ${label}: ${text.substring(0, 50)}...`);
  //   }
  // };

  // 🎵 스트리밍 TTS 큐 처리 - 재생 중 백그라운드 생성
  const processTTSQueue = async (ttsItems: {type: string, content: string}[] = []) => {
    console.log(`🎵 [스트리밍 TTS] 함수 호출됨 - 처리할 항목 수: ${ttsItems.length}`);
    console.log(`🎵 [스트리밍 TTS] 처리 항목들:`, ttsItems.map(item => `${item.type}: ${item.content.substring(0, 50)}...`));
    
    if (ttsItems.length === 0) {
      console.log('🎵 [스트리밍 TTS] 처리할 TTS 없음 - 종료');
      return;
    }
    
    // 🆕 TTS 재생 시작 - 타이머 중지
    console.log('🎵 [스트리밍 TTS] TTS 재생 시작 - 타이머 중지');
    setIsTTSPlaying(true);
    setTtsQueue(ttsItems);
    setCurrentTTSIndex(0);
    setIsTimerActive(false);
    
    const startTime = Date.now();
    
    try {
      // 🎵 1단계: 첫 번째 TTS만 먼저 생성
      console.log(`🎵 [스트리밍 TTS] 1단계: 첫 번째 TTS 생성 시작`);
      const firstItem = ttsItems[0];
      const firstAudio = await generateSingleTTS(firstItem, 0, ttsItems.length);
      
      if (!firstAudio) {
        console.error('🎵 [스트리밍 TTS] 첫 번째 TTS 생성 실패 - 중단');
        setIsTTSPlaying(false);
        setCurrentTTSIndex(-1);
        startAnswerTimer();
        return;
      }
      
      // 🎵 2단계: 첫 번째 TTS 재생 시작과 동시에 나머지 TTS들 백그라운드 생성 시작
      console.log(`🎵 [스트리밍 TTS] 2단계: 첫 번째 재생 시작 + 나머지 ${ttsItems.length - 1}개 백그라운드 생성 시작`);
      
      // 나머지 TTS들을 백그라운드에서 생성 (Promise 배열로 관리)
      const backgroundPromises: Promise<HTMLAudioElement | null>[] = [];
      const backgroundAudios: (HTMLAudioElement | null)[] = new Array(ttsItems.length - 1).fill(null);
      
      for (let i = 1; i < ttsItems.length; i++) {
        const promise = generateSingleTTS(ttsItems[i], i, ttsItems.length).then(audio => {
          backgroundAudios[i - 1] = audio;
          console.log(`🎵 [백그라운드] ${i + 1}/${ttsItems.length} 생성 완료: [${ttsItems[i].type}]`);
          return audio;
        });
        backgroundPromises.push(promise);
      }
      
      // 🎵 3단계: 순차 재생 (첫 번째부터 시작, 나머지는 준비되면 재생)
      console.log(`🎵 [스트리밍 TTS] 3단계: 순차 재생 시작`);
      
      const allAudios: (HTMLAudioElement | null)[] = [firstAudio, ...backgroundAudios];
      
      for (let i = 0; i < ttsItems.length; i++) {
        const item = ttsItems[i];
        setCurrentTTSIndex(i);
        
        let audio: HTMLAudioElement | null;
        
        if (i === 0) {
          // 첫 번째는 이미 준비됨
          audio = firstAudio;
        } else {
          // 나머지는 준비될 때까지 대기
          console.log(`🎵 [스트리밍 TTS] ${i + 1}/${ttsItems.length} 생성 대기 중...`);
          
          // 해당 인덱스의 백그라운드 생성이 완료될 때까지 대기
          await backgroundPromises[i - 1];
          audio = backgroundAudios[i - 1];
          
          if (audio) {
            console.log(`🎵 [스트리밍 TTS] ${i + 1}/${ttsItems.length} 생성 완료, 재생 시작`);
          }
        }
        
        if (audio) {
          console.log(`🎵 [스트리밍 TTS] ${i + 1}/${ttsItems.length} 재생 중: [${item.type}] ${item.content.substring(0, 50)}...`);
          
          try {
            // 🎯 TTS 재생 시작 - 타입 설정, 로딩 상태 해제, 질문 텍스트 표시
            setCurrentTTSType(item.type);
            setIsInitialLoading(false);
            
            // 큐의 마지막 요소이고 면접관 타입이면 사용자 질문 표시
            const isLastItem = (i === ttsItems.length - 1);
            if (isLastItem) {
              setCurrentQuestion(item.content);
              console.log(`[📝 TTS 동기화] 질문 텍스트 표시: ${item.content}`);
            }
            
            console.log(`[🎯 하이라이트] TTS 재생 시작 - 타입: ${item.type} 설정됨`);

            // 재생 완료 대기
            await new Promise<void>((resolve) => {
              audio.onended = () => {
                console.log(`🎵 [스트리밍 TTS] ${i + 1}/${ttsItems.length} 재생 완료 [${item.type}]`);
                setCurrentTTSType(null);
                console.log(`[🎯 하이라이트] TTS 재생 완료 - 타입 초기화됨`);
                URL.revokeObjectURL(audio.src);
                resolve();
              };
              audio.onerror = () => {
                console.error(`🎵 [스트리밍 TTS] ${i + 1}/${ttsItems.length} 재생 실패 [${item.type}]`);
                setCurrentTTSType(null);
                URL.revokeObjectURL(audio.src);
                resolve();
              };
              
              audio.play().catch((playError) => {
                console.error(`🎵 [스트리밍 TTS] ${i + 1}/${ttsItems.length} 재생 시작 실패 [${item.type}]:`, playError);
                setCurrentTTSType(null);
                URL.revokeObjectURL(audio.src);
                resolve();
              });
            });
            
          } catch (error) {
            console.error(`🎵 [스트리밍 TTS] ${i + 1}/${ttsItems.length} 재생 처리 실패 [${item.type}]:`, error);
            setCurrentTTSType(null);
          }
        } else {
          console.warn(`🎵 [스트리밍 TTS] ${i + 1}/${ttsItems.length} 오디오가 없음 - 건너뜀 [${item.type}]`);
        }
      }
      
      const totalTime = Date.now() - startTime;
      console.log(`🎵 [스트리밍 TTS] 모든 처리 완료: 총 소요시간 ${totalTime}ms`);
      
    } catch (error) {
      console.error('🎵 [스트리밍 TTS] 전체 처리 실패:', error);
    }
    
    // 🆕 모든 TTS 재생 완료 - 타이머 시작
    console.log('🎵 [스트리밍 TTS] 모든 TTS 처리 완료 - 답변 타이머 시작');
    setIsTTSPlaying(false);
    setCurrentTTSIndex(-1);
    startAnswerTimer();
  };

  // 🆕 백엔드 응답에서 TTS 처리 (동기적 수집 방식)
  const handleTTSFromResponse = async (response: any, task?: string, status?: string): Promise<{type: string, content: string}[]> => {
    try {
      console.log('[🔊 TTS] 응답에서 TTS 처리 시작');
      
      // 즉시 TTS: 인트로 메시지
      if (response.intro_message) {
        await generateAndPlayTTS(response.intro_message, "intro", "INTRO");
      }

      // 첫 질문은 즉시 TTS (사용자가 들어야 하니까)
      const isFirstQuestion = !state.questions || state.questions.length === 0;
      if (isFirstQuestion && response.content?.content) {
        await generateAndPlayTTS(response.content.content, "hr", "첫 질문", response.content.content);
        return [] as {type: string, content: string}[]; // 첫 질문은 즉시 처리했으므로 빈 배열 반환
      } else {
        // 🔊 TTS 처리를 위한 항목들을 동기적으로 수집 (타입 정보 포함)
        const ttsItems: {type: string, content: string}[] = [];
        
        // 🔊 백엔드 TTS 큐를 우선적으로 처리
        if (response.tts_queue && Array.isArray(response.tts_queue)) {
          console.log(`🔊 [TTS 큐] ${response.tts_queue.length}개 항목을 순서대로 수집`);
          response.tts_queue.forEach((item: any, index: number) => {
            if (item.content) {
              console.log(`🔊 [TTS 큐] ${index + 1}. ${item.type}: ${item.content.substring(0, 50)}...`);
              ttsItems.push({type: item.type || 'unknown', content: item.content});
            }
          });
        } else {
          // 🔊 Fallback: 기존 방식으로 수집 (호환성 유지)
          console.log('🔊 [TTS 큐] tts_queue 없음 - 기존 방식으로 fallback');
          
          if (response.ai_question?.content) {
            console.log(`🔊 [Fallback] AI 질문: ${response.ai_question.content.substring(0, 50)}...`);
            ttsItems.push({type: 'ai_question', content: response.ai_question.content});
          }
          if (response.ai_answer?.content) {
            console.log(`🔊 [Fallback] AI 답변: ${response.ai_answer.content.substring(0, 50)}...`);
            ttsItems.push({type: 'ai_answer', content: response.ai_answer.content});
          }
          if (response.content?.content || response.content?.question) {
            const questionText = response.content.content || response.content.question;
            console.log(`🔊 [Fallback] 사용자 질문: ${questionText.substring(0, 50)}...`);
            ttsItems.push({type: 'user_question', content: questionText});
          }
          
          // 🔊 면접 종료 시 종료 메시지 처리
          if (response.message && (task === 'end_interview' || status === 'completed')) {
            console.log(`🔊 [Fallback] 면접 종료 메시지: ${response.message.substring(0, 50)}...`);
            ttsItems.push({type: 'end_message', content: response.message});
          }
        }
        
        console.log(`[🔊 TTS] 응답 TTS 처리 완료 - ${ttsItems.length}개 항목 수집됨`);
        return ttsItems;
      }
      
    } catch (error) {
      console.error('[🔊 TTS] 응답 TTS 처리 중 오류:', error);
      return [] as {type: string, content: string}[];
    }
  };

  // 🔊 TTS 확인용 주석입니다 - TTS 이력 출력 함수
  const showTTSHistory = () => {
    console.log('🔊 === TTS 실행 이력 전체 목록 ===');
    ttsList.forEach((entry, index) => {
      console.log(`${index + 1}. [${entry.timestamp}] ${entry.type}: ${entry.text.substring(0, 50)}${entry.text.length > 50 ? '...' : ''}`);
    });
    console.log(`🔊 총 ${ttsList.length}개의 TTS가 실행되었습니다.`);
    console.log('🔊 === TTS 이력 종료 ===');
  };


  // 🆕 백엔드 응답에 따른 currentPhase 업데이트 함수 + TTS 처리
  const updatePhaseFromResponse = async (response: any): Promise<{ ttsItems: {type: string, content: string}[], isEndInterview: boolean }> => {
    console.log('🔄 === 전체 응답 구조 분석 START ===');
    console.log('📋 응답 객체 전체:', JSON.stringify(response, null, 2));
    console.log('🔍 메타데이터 분석:');
    console.log('  - response.metadata:', response?.metadata);
    console.log('  - response.ai_answer:', response?.ai_answer);
    console.log('  - response.ai_answer?.metadata:', response?.ai_answer?.metadata);
    console.log('  - response.content:', response?.content);
    console.log('  - response.turn_info:', response?.turn_info);
    console.log('🔄 === 전체 응답 구조 분석 END ===');
    
    // AI 응답에서 resume_id 추출 및 Context 업데이트
    extractAndSaveAIResumeId(response);
    
    // 변수들을 먼저 추출
    const nextAgent = response?.metadata?.next_agent;
    const task = response?.metadata?.task;
    const status = response?.status;
    
    // 🆕 TTS 처리 - 하이브리드 방식 (즉시 + 수집)
    const collectedTTSItems: {type: string, content: string}[] = await handleTTSFromResponse(response, task, status);
    const turnInfo = response?.turn_info;

    // 🔍 현재 면접관 타입 업데이트 (metadata에서 추출)
    const interviewerType = response?.metadata?.interviewer_type || 
                           response?.content?.metadata?.interviewer_type || 
                           currentInterviewerType; // 기본값
    if (interviewerType && interviewerType !== currentInterviewerType) {
      console.log(`🔍 면접관 타입 업데이트: ${currentInterviewerType} → ${interviewerType}`);
      setCurrentInterviewerType(interviewerType);
    }

    console.log('🔍 Phase 판단:', { nextAgent, task, status, turnInfo, interviewerType });

    if (task === 'end_interview' || status === 'completed') {
        // 🔊 end_interview 시에는 TTS 처리 후 면접 완료 처리를 submitAnswer에서 수행
        console.log('🔍 면접 종료 응답 감지 - TTS 처리 후 완료 처리 예정');
        // 임시로 사용자 턴으로 설정 (TTS 처리 후 변경될 예정)
        setCurrentPhase('user_turn');
        setCurrentTurn('user');
        setIsTimerActive(false);
        setCanSubmit(false);
        console.log('✅ 면접 완료로 설정됨');

        // // 👁️ 시선 추적 녹화만 중지 (분석은 면접 완전 완료 후 실행)
        // if (isGazeRecording) {
        //   console.log('👁️ 면접 완료 - 시선 추적 녹화 중지');
        //   stopGazeRecording();
        // }
    } else if (nextAgent === 'user' || status === 'waiting_for_user' || turnInfo?.is_user_turn) {
        setCurrentPhase('user_turn');
        setCurrentTurn('user');
        setIsTimerActive(true);
        setTimeLeft(120);
        setCanSubmit(true);
        setCanRecord(true);  // 🎤 녹음 활성화
        console.log('✅ 사용자 턴으로 설정됨 (턴 정보:', turnInfo, ')');
    } else if (nextAgent === 'ai' || nextAgent === 'interviewer') {
        setCurrentPhase('ai_processing');
        setCurrentTurn('ai');
        setIsTimerActive(false);
        setCanSubmit(false);
        setCanRecord(false); // 🎤 녹음 비활성화
        // 진행 중인 녹음이 있으면 자동 중지
        if (isRecording) {
            stopRecording();
        }
        console.log('✅ AI/면접관 처리 중으로 설정됨');
    } else {
        // 기본적으로 사용자 턴으로 설정 (대기 상태 방지)
        console.log('⚠️ 명확한 턴 정보가 없어서 사용자 턴으로 기본 설정');
        setCurrentPhase('user_turn');
        setCurrentTurn('user');
        setIsTimerActive(true);
        setTimeLeft(120);
        setCanSubmit(true);
        setCanRecord(true);  // 🎤 녹음 활성화
    }

    // AI 질문, 답변 및 사용자 질문 TTS 처리
    const aiQuestion = response?.ai_question?.content;
    const aiAnswer = response?.ai_answer?.content || response?.ai_response?.content;
    const question = response?.content?.content;
    
    if (question) {
        // 질문을 즉시 표시하지 않고 TTS와 동기화하기 위해 임시 저장
        console.log('📝 질문 임시 저장 (TTS와 동기화 예정):', question);
        // setCurrentQuestion(question); // TTS 시작 시에 표시하도록 변경
    }
    
    // AI 질문 상태 업데이트
    if (aiQuestion && aiQuestion.trim()) {
        setCurrentAIQuestion(aiQuestion);
        console.log('🤖 AI 질문 상태 업데이트:', aiQuestion);
    }
    
    // AI 답변 상태 업데이트
    if (aiAnswer && aiAnswer.trim()) {
        setCurrentAIAnswer(aiAnswer);
        console.log('🤖 AI 답변 상태 업데이트:', aiAnswer);
    }

    // 🆕 백엔드에서 전달된 텍스트 데이터들을 확인하고 순차 TTS 재생
    console.log('🔍 백엔드 텍스트 데이터 분석:');
    console.log('  - INTRO 메시지 존재:', !!response.intro_message, response.intro_message ? `(${response.intro_message.length}자)` : '');
    console.log('  - AI 질문 텍스트 존재:', !!response.ai_question?.content, response.ai_question?.content ? `(${response.ai_question.content.length}자)` : '');
    console.log('  - AI 답변 텍스트 존재:', !!response.ai_answer?.content, response.ai_answer?.content ? `(${response.ai_answer.content.length}자)` : '');
    console.log('  - 사용자 질문 텍스트 존재:', !!response.content?.content, response.content?.content ? `(${response.content.content.length}자)` : '');
    
    // 🔊 TTS 확인용 주석입니다 - 큐 시스템으로 대체됨 (중복 방지)
    
    // 🎤 녹음 권한 및 상태 업데이트
    updateVoicePermissions();
    
    // 🔊 수집된 TTS 항목들 반환 (end_interview 플래그 포함)
    const isEndInterview = task === 'end_interview' || status === 'completed';
    return { ttsItems: collectedTTSItems, isEndInterview };
  };

  // 🆕 턴 상태 업데이트 함수 (JSON 응답 기반) - 기존 함수 유지
  const updateTurnFromResponse = (response: any) => {
    console.log('🔄 턴 상태 업데이트:', response);
    
    // JSON 응답에서 턴 정보 추출 (실제 응답 구조에 맞게 수정)
    const status = response?.status || '';
    const isUserTurn = status === 'waiting_for_user' || 
                      status === 'waiting_for_user_answer' || 
                      status === 'user_turn' || 
                      status === 'user';
    
    const isAITurn = status === 'ai_answering' || 
                     status === 'ai_turn' || 
                     status === 'ai' ||
                     status === 'waiting_for_ai';
    
    console.log('🔍 턴 판단:', {
      status,
      isUserTurn,
      isAITurn,
      responseKeys: Object.keys(response || {})
    });
    
    if (isUserTurn) {
      setCurrentTurn('user');
      setIsTimerActive(true);
      setTimeLeft(120); // 2분으로 재설정
      setCanSubmit(true);
      console.log('✅ 사용자 턴으로 설정됨');
    } else if (isAITurn) {
      setCurrentTurn('ai');
      setIsTimerActive(false);
      setCanSubmit(false);
      console.log('✅ AI 턴으로 설정됨');
    } else {
      // 기본적으로 사용자 턴으로 설정 (대기 상태 방지)
      console.log('⚠️ 명확한 턴 정보가 없어서 사용자 턴으로 기본 설정');
      setCurrentTurn('user');
      setIsTimerActive(true);
      setTimeLeft(120);
      setCanSubmit(true);
    }

    // 현재 질문 업데이트
    if (response?.question) {
      setCurrentQuestion(response.question);
      console.log('📝 질문 업데이트:', response.question);
    }
  };

  // 🆕 사용자 턴 상태 설정 헬퍼 함수
  const setUserTurnState = (question: string, source: string) => {
    console.log(`✅ 사용자 턴 설정 (${source}):`, question);
    setCurrentPhase('user_turn');
    setCurrentTurn('user');
    setIsTimerActive(true);
    setTimeLeft(120);
    setCanSubmit(true);
    setCanRecord(true);
    setCurrentQuestion(question);
  };

  // 🆕 답변 타이머 시작 함수 (TTS 완료 후 호출)
  const startAnswerTimer = () => {
    console.log('⏰ 답변 타이머 시작 - TTS 완료 후');
    // 사용자 턴일 때만 타이머 시작
    if (currentTurn === 'user') {
      setIsTimerActive(true);
      setTimeLeft(120); // 2분으로 재설정
      setCanSubmit(true);
      setCanRecord(true);
      console.log('✅ 답변 타이머 활성화됨 (120초)');
    } else {
      console.log('⚠️ 사용자 턴이 아니어서 타이머 시작하지 않음');
    }
  };

  // 🔍 현재 면접관 타입 추출 함수 (최근 응답 기반)
  const [currentInterviewerType, setCurrentInterviewerType] = useState<string>('hr');

  // 🔄 백엔드 TTS 타입을 프론트엔드 표준 타입으로 정규화
  const normalizeTTSType = (backendType: string): string => {
    // AI 답변은 그대로
    if (backendType.includes('ai_answer')) return 'ai';
    
    // AI 질문은 현재 면접관 타입으로 변환
    if (backendType.includes('ai_question')) {
      return currentInterviewerType.toLowerCase(); // hr, tech, collaboration
    }
    
    // 질문 타입들 (대소문자 모두 처리)
    if (backendType === 'hr' || backendType.includes('HR')) return 'hr';
    if (backendType === 'tech' || backendType.includes('TECH')) return 'tech';
    if (backendType === 'collaboration' || backendType.includes('COLLABORATION')) return 'collaboration';
    
    // 기타
    if (backendType === 'OUTRO') return 'outro';
    if (backendType.includes('intro')) return 'intro';
    
    // 기본값
    return 'unknown';
  };

  // 🆕 타입별 voice_id 매핑 함수 (AI 지원자는 난이도별로 다른 음성 사용)
  const getVoiceIdByType = (type: string): string => {
    const normalizedType = normalizeTTSType(type);
    
    // AI 지원자인 경우 난이도에 따른 voice_id 선택
    if (normalizedType === 'ai') {
      const aiQualityLevel = state.aiSettings?.aiQualityLevel || 6;
      if (aiQualityLevel <= 3) return 'H8ObVvroE5JXeeUSJakg'; // 초급자 - 높은 톤, 친근한 목소리
      if (aiQualityLevel <= 7) return 'uyVNoMrnUku1dZyVEXwD'; // 중급자 - 안정적이고 명확한 목소리
      return 'WzMnDIgiICcj1oXbUBO0'; // 고급자 - 낮고 자신감 있는 목소리
    }
    
    switch (normalizedType) {
      case 'tech': return 'YBRudLRm83BV5Mazcr42'; // 기술 면접관 음성
      case 'collaboration': return 'mYk0rAapHek2oTw18z8x'; // 협업 면접관 음성
      case 'hr': return 'AW5wrnG1jVizOYY7R1Oo'; // HR 면접관 음성 (기본값)
      default: return 'AW5wrnG1jVizOYY7R1Oo'; // 기본값은 HR과 동일
    }
  };

  // 🎯 TTS 타입별 표시 메시지 생성 함수
  const getTTSDisplayMessage = (type: string): string => {
    const normalizedType = normalizeTTSType(type);
    switch (normalizedType) {
      case 'intro': return '🎬 면접을 시작합니다';
      case 'hr': return '💼 인사 면접관이 질문 중입니다';
      case 'tech': return '💻 기술 면접관이 질문 중입니다';
      case 'collaboration': return '🤝 협업 면접관이 질문 중입니다';
      case 'ai_question': return '🤖 AI 질문이 재생됩니다';
      case 'ai': return '🤖 다른 지원자가 답변 중입니다';
      case 'outro': return '✅ 면접이 완료되었습니다';
      default: return '🔊 음성이 재생됩니다';
    }
  };

  // 🎯 TTS 타입별 하이라이트 확인 함수
  const shouldHighlight = (componentType: 'hr' | 'tech' | 'collaboration' | 'ai'): boolean => {
    if (!currentTTSType) return false;
    
    const normalizedType = normalizeTTSType(currentTTSType);
    switch (componentType) {
      case 'hr': return normalizedType === 'hr' || normalizedType === 'intro' || normalizedType === 'outro';
      case 'tech': return normalizedType === 'tech';
      case 'collaboration': return normalizedType === 'collaboration';
      case 'ai': return normalizedType === 'ai' || normalizedType === 'ai_question';
      default: return false;
    }
  };

  // 🆕 초기 턴 상태 설정 (세션 로드 완료 후)
  useEffect(() => {
    if (!isRestoring && state.sessionId) {
      console.log('🚀 초기 턴 상태 설정');
      
      // 면접 시작 시 받은 응답에서 턴 정보 확인
      const checkInitialTurnStatus = async () => {
        try {
          // 1. 먼저 localStorage에서 면접 시작 응답 확인 (유틸리티 함수 사용)
          debugInterviewState(); // 디버그 정보 출력
          const parsedState = getInterviewState();
          if (parsedState) {
            console.log('📦 localStorage에서 면접 상태 확인:', parsedState);
            
            // 🆕 API 호출이 필요한 경우 (환경 체크에서 온 경우) + 중복 방지 강화
            if (parsedState.needsApiCall && !parsedState.apiCallCompleted) {
              console.log('🎯 API 호출 조건 충족: needsApiCall=true, apiCallCompleted=false');
              
              // 🚦 메모리 기반 중복 호출 체크 (React Strict Mode 대응)
              if (isApiCallInProgress(parsedState.sessionId) || isApiCallInProgressRef.current) {
                console.log('⚠️ API 이미 진행 중 - 중복 호출 방지 (메모리 기반)');
                return;
              }
              
              console.log('🚀 환경 체크에서 온 새로운 면접 - 첫 질문 로딩 시작');
              setCurrentQuestion("🎬 면접을 시작합니다");
              setCurrentPhase('waiting');
              setCurrentTurn('waiting');
              setIsInitialLoading(true);
              
              // 🚦 호출 진행 상태 설정 (메모리 + 전역)
              isApiCallInProgressRef.current = true;
              setApiCallInProgress(parsedState.sessionId, true);
              
              try {
                // 🆕 AbortController 설정 (cleanup을 위한)
                const abortController = new AbortController();
                apiCallCancelRef.current = abortController;
                
                let response: any;
                const finalSettings = parsedState.settings;
                
                if (finalSettings.mode === 'ai_competition') {
                  console.log('🤖 AI 경쟁 모드 - API 호출 시작');
                  response = await interviewApi.startAICompetition(finalSettings);
                } else {
                  console.log('👤 일반 모드 - API 호출 시작');
                  response = await interviewApi.startInterview(finalSettings);
                }

                console.log('🔍 startInterview/startAICompetition 응답:', response);
                console.log('🔍 응답 내 interview_id 값:', response.interview_id);
                
                // AbortController 확인 (호출이 취소되었으면 중단)
                if (abortController.signal.aborted) {
                  console.log('⚠️ API 호출이 취소됨 - 처리 중단');
                  return;
                }
                
                console.log('✅ 첫 질문 로딩 완료:', response);
                
                // 🔧 백엔드에서 받은 실제 세션 ID로 업데이트
                if (response.session_id) {
                  console.log('🔄 세션 ID 업데이트:', parsedState.sessionId, '->', response.session_id);
                  
                  // Context 업데이트
                  dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
                  
                  // localStorage도 즉시 업데이트 (나중에 다시 업데이트하지만 일관성을 위해)
                  parsedState.sessionId = response.session_id;
                }

                // 🆕 interview_id (정수형) 저장
                console.log('🔍 백엔드 응답에서 interview_id 확인:', response.interview_id);
                if (response.interview_id) {
                  console.log('🔄 면접 ID 업데이트:', response.interview_id);
                  dispatch({ type: 'SET_INTERVIEW_ID', payload: response.interview_id });
                } else {
                  console.warn('⚠️ 백엔드 응답에 interview_id가 없습니다. response:', response);
                }
                
                // 질문 처리 함수 (response를 파라미터로 받음)
                const processQuestion = (apiResponse: any) => {
                  const responseContent = apiResponse?.content;
                  const contentText = responseContent?.content;
                  const contentType = responseContent?.type;
                  
                  if (apiResponse && contentText) {
                    try {
                      console.log('📝 컨텐츠 추출 성공:', contentText, '타입:', contentType);
                      
                      // 일반 질문 처리 (HR, TECH, COLLABORATION 등)
                      const questionData = {
                        id: `q_${Date.now()}`,
                        question: contentText,
                        category: contentType || 'HR',
                        time_limit: 120,
                        keywords: []
                      };
                        
                      dispatch({ 
                        type: 'ADD_QUESTION', 
                        payload: questionData
                      });
                      
                      setCurrentQuestion(questionData.question);
                      console.log('✅ 질문 설정 완료:', questionData.question);
                      
                      return questionData; // questionData 반환
                      
                    } catch (error) {
                      console.error('❌ 컨텐츠 처리 실패:', error);
                      setCurrentQuestion("컨텐츠를 처리하는 중 오류가 발생했습니다.");
                    }
                  } else {
                    console.warn('⚠️ API 응답에 컨텐츠가 없습니다:', apiResponse);
                    setCurrentQuestion("컨텐츠를 받지 못했습니다. 새로고침해주세요.");
                  }
                  return null;
                };

                // 🆕 질문 데이터 먼저 처리 (INTRO 여부와 관계없이)
                console.log('📝 질문 데이터 처리 시작');
                const questionData = processQuestion(response);
                
                // 🆕 INTRO 메시지 처리 (텍스트 표시용)
                const introMessageFromResponse = (response as any)?.intro_message;
                if (introMessageFromResponse) {
                  console.log('📢 응답에서 INTRO 메시지 감지:', introMessageFromResponse);
                  setIntroMessage(introMessageFromResponse);
                  setHasIntroMessage(true);
                  setShowIntroMessage(true);
                  
                  // 🎯 인트로가 있을 때는 타이머 없이 질문만 설정
                  console.log('⏰ 인트로 메시지 있음 - 타이머 없이 질문 설정');
                  setCurrentPhase('user_turn');
                  setCurrentTurn('user');
                  setIsTimerActive(false); // 타이머 시작하지 않음
                  setCanSubmit(false); // 인트로 중에는 제출 불가
                  setCanRecord(false); // 인트로 중에는 녹음 불가
                  if (questionData) {
                    setCurrentQuestion(questionData.question);
                  }
                  
                  // INTRO 표시 후 잠시 후 숨기기 (TTS는 백엔드에서 자동 처리됨)
                  setTimeout(() => {
                    setShowIntroMessage(false);
                    setHasIntroMessage(false);
                  }, 3000); // 3초 후 숨김
                  
                  console.log('📢 INTRO 메시지 표시 - TTS는 백엔드에서 자동 처리');
                } else {
                  console.log('📝 INTRO 메시지 없음 - 바로 질문 진행');
                  // 인트로가 없으면 바로 사용자 턴으로 설정 (타이머 포함)
                  if (questionData) {
                    setUserTurnState(questionData.question, "API 로딩");
                  }
                }
                
                // 🆕 첫 번째 응답에서도 TTS 재생 처리
                console.log('🎵 첫 번째 응답 TTS 재생 처리 시작');
                const { ttsItems: firstResponseTTSItems, isEndInterview: firstEndInterview } = await updatePhaseFromResponse(response);
                await processTTSQueue(firstResponseTTSItems);
                
                // 첫 응답에서는 일반적으로 end_interview가 아니지만 혹시 모르니 처리
                if (firstEndInterview) {
                  showTTSHistory();
                  setCurrentPhase('interview_completed');
                  setCurrentTurn('waiting');
                  setIsTimerActive(false);
                  setCanSubmit(false);
                }
                
                setIsInitialLoading(false);
                
                // 🆕 즉시 API 호출 완료 상태로 업데이트 (재호출 방지)
                markApiCallCompleted(response);
                
                // 🚦 로컬 호출 상태 리셋
                isApiCallInProgressRef.current = false;
                apiCallCancelRef.current = null;
                
                console.log('💾 localStorage 즉시 업데이트 완료 - 재호출 방지');
                console.log('✅ 첫 질문 로딩 및 면접 시작 완료');
                return;
                
              } catch (error) {
                console.error('❌ 첫 질문 로딩 실패:', error);
                
                // AbortError인 경우 (cleanup에 의한 취소) 별도 처리
                if (error instanceof Error && error.name === 'AbortError') {
                  console.log('⚠️ API 호출이 cleanup에 의해 취소됨');
                  return;
                }
                
                setCurrentQuestion("질문 로딩에 실패했습니다. 새로고침해주세요.");
                setIsInitialLoading(false);
                setCurrentPhase('unknown');
                setCurrentTurn('waiting');
                
                // 🆕 에러 상황에서도 재호출 방지 플래그 설정 (유틸리티 사용)
                const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류';
                markApiCallCompleted(undefined, errorMessage);
                
                // 🚦 로컬 호출 상태 리셋
                isApiCallInProgressRef.current = false;
                apiCallCancelRef.current = null;
                
                console.log('💾 API 에러 상태로 localStorage 업데이트 (재호출 방지)');
                
                alert(`면접 시작에 실패했습니다: ${errorMessage}\n\n다시 시도해주세요.`);
                return;
              }
            }
            
            // 🆕 API 호출이 이미 완료된 경우 (중복 호출 방지)
            if (parsedState.needsApiCall && parsedState.apiCallCompleted) {
              console.log('⚠️ API 이미 호출 완료됨 - 재호출 건너뛰기');
              console.log('📄 저장된 응답 사용:', parsedState.interviewStartResponse);
              
              // 저장된 응답이 있으면 그것을 사용
              if (parsedState.interviewStartResponse) {
                const { ttsItems: savedResponseTTSItems, isEndInterview: savedEndInterview } = await updatePhaseFromResponse(parsedState.interviewStartResponse);
                await processTTSQueue(savedResponseTTSItems);
                
                // 저장된 응답이 end_interview인 경우 처리
                if (savedEndInterview) {
                  showTTSHistory();
                  setCurrentPhase('interview_completed');
                  setCurrentTurn('waiting');
                  setIsTimerActive(false);
                  setCanSubmit(false);
                  return;
                }
                const question = parsedState.interviewStartResponse.content?.content || "질문을 불러오는 중...";
                setUserTurnState(question, "저장된 응답");
                return;
              }
            }
            
            // 면접 시작 응답에서 턴 정보 확인 (기존 로직)
            if (parsedState.interviewStartResponse && parsedState.interviewStartResponse.status === 'waiting_for_user') {
              const question = parsedState.interviewStartResponse.content?.content || "질문을 불러오는 중...";
              setUserTurnState(question, "localStorage");
              return;
            }
          }
          
          // 2. localStorage에 없으면 현재 면접 상태만 확인 (API 재호출 없이)
          console.log('🔄 현재 면접 상태 확인');
          const currentSettings = state.settings;
          if (currentSettings) {
            console.log('✅ AI 경쟁 면접 기본값으로 사용자 턴 설정');
            setUserTurnState("면접을 시작합니다. 첫 번째 질문을 기다려주세요.", "기본값");
            return;
          }
          
          // 3. 세션 상태 확인 (fallback)
          const sessionState = await sessionApi.getSessionState(state.sessionId!);
          console.log('📋 초기 세션 상태:', sessionState);
          
          // 세션 상태에서 턴 정보 확인
          if (sessionState && sessionState.state?.status) {
            const status = sessionState.state.status;
            console.log('🔍 초기 세션에서 턴 상태 발견:', status);
            
            if (status === 'waiting_for_user') {
              const question = sessionState.state?.current_question || "질문을 불러오는 중...";
              setUserTurnState(question, "세션 상태");
              return;
            }
          }
          
          // 4. 턴 정보가 없으면 unknown 상태로 시작
          setCurrentPhase('unknown');
          setCurrentTurn('waiting');
          setIsTimerActive(false);
          setCanSubmit(false);
          setCurrentQuestion("답변을 제출하여 턴을 시작하세요.");
          
        } catch (error) {
          console.error('❌ 초기 턴 상태 확인 실패:', error);
          setCurrentPhase('unknown');
          setCurrentTurn('waiting');
          setIsTimerActive(false);
          setCanSubmit(false);
          setCurrentQuestion("턴 정보를 확인하는 중...");
        }
      };
      
      checkInitialTurnStatus();
    }
    
    // 🧹 Cleanup 함수 - 컴포넌트 언마운트 또는 의존성 변경 시 API 호출 취소
    return () => {
      if (apiCallCancelRef.current) {
        console.log('🧹 useEffect cleanup - API 호출 취소');
        apiCallCancelRef.current.abort();
        apiCallCancelRef.current = null;
      }
      // 로컬 호출 상태 리셋
      isApiCallInProgressRef.current = false;
    };
  }, [isRestoring, state.sessionId, dispatch]);

  // 🆕 주기적 턴 상태 확인 제거 - 턴 정보는 답변 제출 후 응답에서만 받아옴

  // 🆕 S3 Pre-signed URL 기반 시선 추적 영상 업로드 및 분석 트리거
  const uploadGazeVideoS3 = async (sessionId: string, videoBlob: Blob) => {
    try {
      console.log('📤 S3 시선 추적 비디오 업로드 시작...', { blobSize: videoBlob.size });

      // interview_id 체크 제거 - session_id 기반으로 변경됨

      if (!state.gazeTracking?.calibrationResultData) {
        throw new Error('캘리브레이션 데이터를 찾을 수 없습니다.');
      }

      // 1. 실제 Blob 타입에 따른 파일명 결정
      const timestamp = Date.now();
      const actualMimeType = videoBlob.type || 'video/webm'; // Blob의 실제 MIME 타입
      const fileExtension = actualMimeType.includes('mp4') ? 'mp4' : 'webm';
      const fileName = `gaze-recording-${timestamp}.${fileExtension}`;
      
      console.log('📝 S3 업로드 URL 요청 중... (session_id:', sessionId, ', 실제 타입:', actualMimeType, ')');
      const uploadResponse = await interviewApi.getGazeUploadUrl({
        session_id: sessionId,  // interview_id 대신 session_id 사용
        file_name: fileName,
        file_size: videoBlob.size,
        file_type: 'video',
        content_type: actualMimeType  // 실제 Blob MIME 타입 전달
      });

      console.log('✅ S3 업로드 URL 받음:', uploadResponse.media_id);

      // 2. S3에 직접 업로드
      console.log('📤 S3 직접 업로드 시작...');
      const uploadResult = await fetch(uploadResponse.upload_url, {
        method: 'PUT',
        body: videoBlob,
        headers: {
          'Content-Type': actualMimeType  // 실제 Blob MIME 타입 사용
        }
      });

      if (!uploadResult.ok) {
        throw new Error(`S3 업로드 실패: ${uploadResult.status} ${uploadResult.statusText}`);
      }

      console.log('✅ S3 업로드 완료');

      // 3. Context에 S3 키 저장
      dispatch({ type: 'SET_GAZE_S3_KEY', payload: uploadResponse.s3_key });

      // 4. 시선 분석 트리거 (session_id 기반으로 변경)
      console.log('🚀 시선 분석 트리거 중... (session_id:', sessionId, ')');
      const analysisResponse = await interviewApi.triggerGazeAnalysis({
        session_id: sessionId,  // interview_id 대신 session_id 사용
        s3_key: uploadResponse.s3_key,
        calibration_data: state.gazeTracking.calibrationResultData,
        media_id: uploadResponse.media_id  // 임시 media_id 전달
      });

      console.log('✅ 시선 분석 트리거 완료:', analysisResponse.task_id);
      console.log('📋 시선 분석은 백그라운드에서 처리되며, interview_id는 면접 완료 후 연결됩니다.');

      // 5. Context에 분석 작업 ID 저장
      dispatch({ type: 'SET_GAZE_ANALYSIS_TASK', payload: analysisResponse.task_id });
      dispatch({ type: 'SET_GAZE_ANALYSIS_STATUS', payload: 'analyzing' });

      return analysisResponse.task_id;

    } catch (error) {
      console.error('❌ S3 시선 추적 비디오 업로드 실패:', error);
      dispatch({ type: 'SET_GAZE_ANALYSIS_STATUS', payload: 'failed' });
      throw error;
    }
  };

  // 답변 제출 실패 시에도 unknown 상태로 복구
  const submitAnswer = async (directText?: string) => {
    const answerText = directText || currentAnswer.trim();
    if (!answerText) {
      console.log('❌ 답변이 입력되지 않았습니다.');
      return;
    }

    if (isSubmittingAnswer) {
      console.log('❌ 이미 제출 중입니다.');
      return;
    }

    // 사용자 턴이 아니면 제출 불가
    if (currentPhase !== 'user_turn') {
      console.log('❌ 사용자 턴이 아닙니다.');
      return;
    }

    let sessionId = state.sessionId;
    if (!sessionId) {
      try {
        sessionId = await sessionApi.getLatestSessionId();
        if (sessionId) { dispatch({ type: 'SET_SESSION_ID', payload: sessionId }); }
      } catch (error) { console.error('❌ sessionId 조회 실패:', error); }
    }
    if (!sessionId) {
      alert('세션이 만료되었습니다. 면접을 다시 시작해주세요.');
      navigate('/interview/environment-check');
      return;
    }

    try {
      setIsLoading(true);
      setIsTimerActive(false);
      setCanSubmit(false);
      setCanRecord(false);

      if (isRecording) {
        stopRecording();
      }

      console.log('💬 텍스트 답변을 백엔드로 제출합니다.');
      const result = await interviewApi.submitUserAnswer(
        sessionId,
        answerText,
        120 - timeLeft
      );

      console.log('✅ 답변 제출 성공, 백엔드 응답 수신:', result);
      setCurrentAnswer('');

      const { ttsItems, isEndInterview } = await updatePhaseFromResponse(result);
      await processTTSQueue(ttsItems);

      if (isEndInterview) {
        console.log("🏁 면접 종료 신호 수신! 지금부터 영상 처리를 시작합니다.");
        const finalGazeBlob = await stopGazeRecording();

        if (finalGazeBlob && finalGazeBlob.size > 0) {
          console.log(`UPLOAD_CALL: 이제 uploadGazeVideoS3 함수를 호출합니다. sessionId: ${sessionId}`);
          const taskId = await uploadGazeVideoS3(sessionId, finalGazeBlob);
          console.log('🎯 시선 분석 작업 ID:', taskId);
        } else {
          console.log('⚠️ 최종 gazeBlob이 없거나 크기가 0이므로 업로드를 건너뜁니다.');
        }

        showTTSHistory();
        setCurrentPhase('interview_completed');
        setCurrentTurn('waiting');
        setIsTimerActive(false);
        setCanSubmit(false);
        console.log('✅ 면접 완료로 설정됨');
        console.log('✅ 면접 완료 - 시선 분석은 백그라운드에서 처리됩니다.');
        setIsFeedbackProcessing(true);
        setFeedbackProcessingError(null);
      }

    } catch (error: any) {
      console.error('❌ 답변 제출 오류:', error);
      setCurrentPhase('unknown');
      setCurrentTurn('waiting');
      setIsTimerActive(false);
      setCanSubmit(false);
      let errorMessage = '알 수 없는 오류';
      if (error.response) {
        errorMessage = `HTTP ${error.response.status}: ${error.response.data?.detail || error.response.statusText}`;
      } else if (error.request) {
        errorMessage = '백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.';
      } else {
        errorMessage = error.message;
      }
      alert(`답변 제출 실패: ${errorMessage}`);
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  // 🎤 음성 권한 확인 및 업데이트
  const updateVoicePermissions = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setHasAudioPermission(true);
      // 사용 후 스트림 정리
      stream.getTracks().forEach(track => track.stop());
    } catch (error) {
      console.error('🎤 마이크 권한 없음:', error);
      setHasAudioPermission(false);
    }
  };

  // 🎤 녹음 시작
  const startRecording = async () => {
    // 이중 체크: 사용자 턴인지 확인
    if (currentTurn !== 'user' || currentPhase !== 'user_turn' || !canRecord) {
      alert('지금은 녹음할 수 없습니다. 사용자 차례를 기다려주세요.');
      return;
    }

    if (isRecording) {
      console.log('이미 녹음 중입니다.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 44100,  // 더 높은 품질
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true  // 자동 볼륨 조절 활성화
        }
      });

      // 브라우저 호환성을 위한 MIME 타입 선택
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
      }
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/mp4';
      }
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = ''; // 브라우저 기본값 사용
      }
      
      console.log('🎤 사용할 MIME 타입:', mimeType);
      
      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        console.log('🎤 녹음 완료, STT 처리 시작:', audioBlob.size, 'bytes');
        
        // STT 처리
        await processSTT(audioBlob);
        
        // 스트림 정리
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      
      // 녹음 시간 카운터
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

      console.log('🎤 녹음 시작');

    } catch (error) {
      console.error('🎤 녹음 시작 실패:', error);
      alert('마이크 접근 실패. 브라우저에서 마이크 권한을 허용해주세요.');
    }
  };

  // 🎤 녹음 중지
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      
      console.log('🎤 녹음 중지');
    }
  };

  // 🗣️ STT 처리 (OpenAI Whisper API)
  const processSTT = async (audioBlob: Blob) => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');
      
      console.log('🗣️ STT 요청 전송 중...');
      
      const response = await fetch(`${API_BASE_URL}/interview/stt`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('🔥 STT API 에러 응답:', response.status, errorData);
        throw new Error(`STT API 오류: ${response.status} - ${errorData.detail || response.statusText}`);
      }
      
      const result = await response.json();
      const transcribedText = result.text || '';
      
      console.log('✅ STT 처리 성공:', transcribedText);
      setSttResult(transcribedText);
      
      // 인식된 텍스트를 답변란에 자동 입력
      if (transcribedText.trim()) {
        // UI 표시용으로 currentAnswer 업데이트
        setCurrentAnswer(prev => {
          const newAnswer = prev + (prev ? ' ' : '') + transcribedText;
          return newAnswer;
        });
        
        // 🎯 STT 완료 후 즉시 제출 (상태 업데이트 대기 불필요)
        console.log('🚀 STT 완료 - 자동 답변 제출 시작');
        submitAnswer(transcribedText);
      }
      
    } catch (error) {
      console.error('❌ STT 처리 실패:', error);
      alert(`음성 인식 실패: ${error}`);
    }
  };

  // 👁️ 시선 추적 녹화 시작
  const startGazeRecording = useCallback(async () => {
    // 면접 완료 상태에서는 시선 추적을 시작하지 않음
    if (currentPhase === 'interview_completed') {
      console.log('⚠️ 면접 완료 상태 - 시선 추적 시작 거부');
      return;
    }

    // 이미 gazeBlob이 있으면 새로운 녹화를 시작하지 않음 (기존 데이터 보호)
    if (gazeBlob) {
      console.log('⚠️ 기존 gazeBlob 존재 - 새로운 시선 추적 시작 거부');
      return;
    }

    // 이미 녹화 중이면 중복 시작 방지
    if (isGazeRecording) {
      console.log('⚠️ 이미 시선 추적 녹화 중 - 중복 시작 방지');
      return;
    }

    // 캘리브레이션 세션 ID 확인
    const calibrationSessionId = state.gazeTracking?.calibrationSessionId;
    if (!calibrationSessionId) {
      console.log('⚠️ 캘리브레이션 정보가 없어 시선 추적을 건너뜁니다.');
      return;
    }

    try {
      // 화면 + 웹캠 스트림 가져오기
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 }
        },
        audio: false // 음성은 별도로 녹음
      });

      if (gazeVideoRef.current) {
        gazeVideoRef.current.srcObject = stream;
      }

      // MediaRecorder 설정
      let mimeType = 'video/webm;codecs=vp8';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'video/webm';
      }

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      gazeMediaRecorderRef.current = mediaRecorder;
      gazeChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          gazeChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(gazeChunksRef.current, { type: mimeType });
        setGazeBlob(blob);
        console.log('👁️ 시선 추적 녹화 완료, 크기:', blob.size);

        // 스트림 정리
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.onerror = (event) => {
        console.error('❌ 시선 추적 녹화 오류:', event);
        setGazeError('시선 추적 녹화 중 오류가 발생했습니다.');
      };

      mediaRecorder.start();
      setIsGazeRecording(true);
      console.log('👁️ 시선 추적 녹화 시작');

    } catch (error) {
      console.error('❌ 시선 추적 녹화 시작 실패:', error);
      setGazeError('시선 추적을 시작할 수 없습니다.');
    }
  }, [currentPhase, gazeBlob, isGazeRecording, state.gazeTracking?.calibrationSessionId]);

  // 👁️ 시선 추적 녹화 중지
  const stopGazeRecording = (): Promise<Blob | null> => {
    return new Promise((resolve) => {
      if (gazeMediaRecorderRef.current && isGazeRecording) {
        gazeMediaRecorderRef.current.onstop = () => {
          const blob = new Blob(gazeChunksRef.current, { type: 'video/webm' });
          setGazeBlob(blob);
          console.log('👁️ [Promise] 시선 추적 녹화 완료, 크기:', blob.size);
          setIsGazeRecording(false);
          resolve(blob);
        };
        gazeMediaRecorderRef.current.stop();
        console.log('👁️ 시선 추적 녹화 중지 명령');
      } else {
        resolve(gazeBlob);
      }
    });
  };

  // 👁️ 이전 업로드 및 분석 함수는 새로운 "선-업로드, 후-분석" 아키텍처로 대체되었습니다.
  // 시선 추적 비디오는 이제 답변 제출 시 임시 업로드되고, 백그라운드에서 분석됩니다.


  // 🆕 필요한 데이터 추출 함수들
  const getCurrentUserId = (): number => {
    // 실제 로그인된 사용자 ID 가져오기
    const user = tokenManager.getUser();
    if (user && user.user_id) {
      return user.user_id;
    }
    
    // 로그인되지 않은 경우 에러 로그
    console.error('❌ 로그인된 사용자를 찾을 수 없습니다.');
    throw new Error('로그인된 사용자 정보가 없습니다.');
  };

  const getUserResumeId = (): number | null => {
    console.log('🔍 getUserResumeId 호출 시작...');
    
    // 1순위: Context에 저장된 이력서 데이터에서 추출
    if (state.resume?.id) {
      const resumeId = parseInt(state.resume.id);
      console.log('📋 Context에서 찾은 resume ID:', state.resume.id, '-> 파싱 결과:', resumeId);
      
      if (!isNaN(resumeId)) {
        // 추가 검증: 로그인된 사용자와 이력서 사용자 정보 매칭 확인
        const currentUser = tokenManager.getUser();
        console.log('🔍 이메일 매칭 확인:', {
          resumeEmail: state.resume.email,
          currentUserEmail: currentUser?.email,
          isMatch: state.resume.email === currentUser?.email
        });
        
        if (currentUser && state.resume.email === currentUser.email) {
          console.log('✅ Context에서 유효한 user_resume_id 반환:', resumeId);
          return resumeId;
        } else {
          console.warn('⚠️ 이력서 소유자와 로그인 사용자가 다릅니다.');
        }
      } else {
        console.warn('⚠️ resume.id 파싱 실패:', state.resume.id);
      }
    } else {
      console.warn('⚠️ Context에 resume 데이터가 없습니다.');
    }
    
    // 2순위: 로그인된 사용자 정보로 추정
    const currentUser = tokenManager.getUser();
    if (currentUser?.user_id) {
      console.log('🔍 로그인된 사용자 정보로 user_resume 추정 시도:', currentUser.user_id);
      // TODO: API 호출로 user_id에 해당하는 user_resume_id 조회
      // 지금은 Context 데이터가 없으면 null 반환
    }
    
    console.log('❌ user_resume_id를 찾을 수 없어 null 반환');
    return null;
  };

  const getAIResumeId = (): number | null => {
    // 1순위: AI 응답에서 추출된 resume_id 사용 (가장 정확함)
    if (state.textCompetitionData?.extracted_ai_resume_id) {
      console.log('✅ 추출된 AI resume_id 사용:', state.textCompetitionData.extracted_ai_resume_id);
      return state.textCompetitionData.extracted_ai_resume_id;
    }
    
    // 2순위: 기존 aiPersona에서 resume_id 찾기
    if (state.textCompetitionData?.aiPersona?.resume_id) {
      console.log('⚠️ aiPersona에서 resume_id 사용:', state.textCompetitionData.aiPersona.resume_id);
      return state.textCompetitionData.aiPersona.resume_id;
    }
    
    // 3순위: settings에서 ai_resume_id가 있다면 사용 (create_persona_for_interview에서 전달될 수 있음)
    if (state.settings && 'ai_resume_id' in state.settings) {
      const aiResumeId = (state.settings as any).ai_resume_id;
      if (aiResumeId && aiResumeId !== 0) {
        console.log('⚠️ settings에서 resume_id 사용:', aiResumeId);
        return aiResumeId;
      }
    }
    
    // DB 제약조건 위반 방지를 위해 null 반환 (ai_resume_id=0은 존재하지 않음)
    console.log('❌ AI resume_id를 찾을 수 없어 null 반환');
    return null;
  };

  const getPostingId = (): number | null => {
    // TODO: 채용공고 ID를 가져오는 로직 구현 필요
    return state.settings?.posting_id || null;
  };

  const getCompanyId = (): number | null => {
    // 1순위: jobPosting에서 company_id 추출 (create_persona_for_interview에서 사용하는 방식)
    if (state.jobPosting?.company_id) {
      return state.jobPosting.company_id;
    }
    
    // 2순위: settings에서 posting_id를 통해 company_id 추출하려면 추가 API 호출이 필요
    // 현재는 posting_id만 있으므로 null 반환
    return null;
  };

  const getPositionId = (): number | null => {
    // 1순위: jobPosting에서 position_id 추출 (create_persona_for_interview에서 사용하는 방식)
    if (state.jobPosting?.position_id) {
      return state.jobPosting.position_id;
    }
    
    // 2순위: settings에서 posting_id를 통해 position_id 추출하려면 추가 API 호출이 필요
    // 현재는 posting_id만 있으므로 null 반환
    return null;
  };


  // 🎤 음성 답변 제출 (녹음 후 자동 제출)
  const submitVoiceAnswer = async () => {
    if (isRecording) {
      // 녹음 중지 후 STT 처리가 완료되면 자동으로 submitAnswer 호출
      stopRecording();
      // STT 처리 완료 후 제출은 processSTT에서 처리
    } else if (currentAnswer.trim()) {
      // 이미 텍스트가 있으면 바로 제출
      submitAnswer();
    } else {
      alert('답변을 녹음하시거나 입력해주세요.');
    }
  };

  // 🎯 통합 버튼 핸들러 (녹음 + STT + 제출)
  const handleIntegratedButton = async () => {
    if (isRecording) {
      // 녹음 중지 → STT → 자동 제출
      stopRecording();
      console.log('🎤 통합 버튼: 녹음 중지 및 STT 처리 시작');
    } else {
      // 녹음 시작
      await startRecording();
      console.log('🎤 통합 버튼: 녹음 시작');
    }
  };

  // 🎤 useEffect: 사용자 턴 변경 시 녹음 상태 업데이트
  useEffect(() => {
    if (currentTurn === 'user' && currentPhase === 'user_turn') {
      setCanRecord(true);
      console.log('✅ 사용자 턴 시작 - 녹음 가능');
    } else {
      setCanRecord(false);
      // 진행 중인 녹음이 있으면 자동 중지
      if (isRecording) {
        console.log('❌ 사용자 턴 종료 - 녹음 자동 중지');
        stopRecording();
      }
    }
  }, [currentTurn, currentPhase]);

  // 🎤 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      // 🎤 녹음 정리
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (mediaRecorderRef.current && isRecording) {
        stopRecording();
      }
      
      // 👁️ 시선 추적 정리
      if (gazeMediaRecorderRef.current && isGazeRecording) {
        gazeMediaRecorderRef.current.stop();
        setIsGazeRecording(false);
      }
      
      // 🔊 TTS 오디오 정리
      if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
      }
      
      // ⏱️ 타이머 정리
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      // 👁️ 폴링 타이머들 정리
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
      }
      if (pollingMainTimeoutRef.current) {
        clearTimeout(pollingMainTimeoutRef.current);
      }
    };
  }, []);

  // 👁️ 면접 시작 시 자동으로 시선 추적 시작
  useEffect(() => {
    const startAutoGazeTracking = async () => {
      // 캘리브레이션 세션 ID가 있고, 아직 녹화 중이 아닐 때만 시작
      const calibrationSessionId = state.gazeTracking?.calibrationSessionId;
      
      // 면접 완료 상태에서는 새로운 시선 추적을 시작하지 않음
      if (currentPhase === 'interview_completed') {
        console.log('⚠️ 면접 완료 상태 - 시선 추적 시작 건너뜀');
        return;
      }
      
      // 이미 gazeBlob이 있으면 새로운 녹화를 시작하지 않음 (기존 데이터 보호)
      if (gazeBlob) {
        console.log('📝 시선 추적 비디오 이미 존재 - 새로운 녹화 건너뜀');
        return;
      }
      
      if (calibrationSessionId && !isGazeRecording && !isRestoring) {
        console.log('👁️ 면접 페이지 진입 - 시선 추적 자동 시작');
        await startGazeRecording();
      }
    };

    startAutoGazeTracking();
  }, [state.gazeTracking?.calibrationSessionId, isRestoring, isGazeRecording, gazeBlob, currentPhase]);

  // 👁️ 시선 분석 상태 폴링 useEffect (새로운 Context 기반)
  useEffect(() => {
    const taskId = state.gazeTracking?.gazeAnalysisTaskId;
    const analysisStatus = state.gazeTracking?.gazeAnalysisStatus;
    
    if (!taskId || analysisStatus !== 'analyzing') {
      return;
    }

    console.log('🔄 새로운 시선 분석 폴링 시작:', taskId);

    const stopPolling = () => {
      // 모든 타이머 정리
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
      if (pollingMainTimeoutRef.current) {
        clearTimeout(pollingMainTimeoutRef.current);
        pollingMainTimeoutRef.current = null;
      }
    };

    const pollAnalysisStatus = async () => {
      try {
        const statusResponse = await apiClient.get<AnalysisStatusResponse>(`/gaze/analyze/status/${taskId}`);
        const statusData = statusResponse.data;

        if (statusData.status === 'completed' && statusData.result) {
          // 분석 완료
          console.log('🎉 시선 분석 완료:', statusData.result);
          setGazeAnalysisResult(statusData.result);
          dispatch({ type: 'SET_GAZE_ANALYSIS_STATUS', payload: 'completed' });
          dispatch({ type: 'SET_GAZE_S3_ANALYSIS_PROGRESS', payload: 100 });
          setPollingError(null);
          stopPolling(); // 모든 타이머 정리
          

        } else if (statusData.status === 'failed') {
          // 분석 실패
          console.error('❌ 시선 분석 실패:', statusData.error);
          setGazeError('시선 분석에 실패했습니다.');
          dispatch({ type: 'SET_GAZE_ANALYSIS_STATUS', payload: 'failed' });
          setPollingError('시선 분석에 실패했습니다.');
          stopPolling(); // 모든 타이머 정리
        } else {
          // 분석 진행 중
          console.log('⏳ 시선 분석 진행 중...', statusData.status);
          if (statusData.progress) {
            dispatch({ type: 'SET_GAZE_S3_ANALYSIS_PROGRESS', payload: statusData.progress });
          }
        }
      } catch (error) {
        console.error('❌ 분석 상태 체크 실패:', error);
        setPollingError('시선 분석 상태를 확인할 수 없습니다.');
        // 에러가 발생해도 폴링은 계속 진행 (네트워크 일시 오류일 수 있음)
      }
    };

    // 첫 번째 상태 체크 (5초 후)
    pollingTimeoutRef.current = setTimeout(() => {
      pollAnalysisStatus();
      
      // 그 이후 5초마다 반복
      pollingIntervalRef.current = setInterval(pollAnalysisStatus, 5000);
    }, 5000);

    // 5분 후 타임아웃 처리
    pollingMainTimeoutRef.current = setTimeout(() => {
      console.warn('⏰ 시선 분석 타임아웃 (5분)');
      dispatch({ type: 'SET_GAZE_ANALYSIS_STATUS', payload: 'failed' });
      setPollingError('시선 분석이 시간 초과되었습니다.');
      setGazeError('시선 분석이 시간 초과되었습니다.');
      
      // 피드백 처리도 함께 정리 (장시간 실행된 경우)
      if (isFeedbackProcessing) {
        setIsFeedbackProcessing(false);
        setFeedbackProcessingError('분석이 시간 초과되어 중단되었습니다.');
      }
      
      stopPolling(); // 타임아웃 시에도 모든 타이머 정리
    }, 5 * 60 * 1000); // 5분

    // Cleanup function - 컴포넌트 언마운트나 의존성 변경 시
    return stopPolling;
  }, [state.gazeTracking?.gazeAnalysisTaskId, state.gazeTracking?.gazeAnalysisStatus]);

  // 👁️ gazeBlob이 설정되었을 때 상태만 업데이트 (분석은 피드백 후 실행)
  useEffect(() => {
    if (gazeBlob && state.gazeTracking?.calibrationSessionId) {
      console.log('👁️ gazeBlob 감지 - 분석은 면접 완료 후 실행', { blobSize: gazeBlob.size });
    }
  }, [gazeBlob, state.gazeTracking?.calibrationSessionId]);

  return (
    <div className="h-screen bg-black text-white flex flex-col overflow-hidden">
      {/* 메인 인터페이스 */}
      <div className="flex-1 flex flex-col">
        {/* 상단 면접관 영역 */}
        <div className="grid grid-cols-3 gap-4 p-4" style={{ height: '40vh' }}>
          {/* 인사 면접관 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-4 transition-all duration-300 ${
            shouldHighlight('hr') ? 'border-green-500' : 'border-gray-700'
          }`}>
            <div className="absolute top-4 left-4 font-semibold text-white">
              👔 인사 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/nano-banana_A_front-facing_port_1.png"
                alt="인사 면접관"
                className="w-full h-full object-cover"
              />
            </div>
          </div>

          {/* 기술 면접관 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-4 transition-all duration-300 ${
            shouldHighlight('tech') ? 'border-green-500' : 'border-gray-700'
          }`}>
            <div className="absolute top-4 left-4 font-semibold text-white">
              💻 기술 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/nano-banana_Change_only_the_back.png"
                alt="기술 면접관"
                className="w-full h-full object-cover"
              />
            </div>
          </div>

          {/* 협업 면접관 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-4 transition-all duration-300 ${
            shouldHighlight('collaboration') ? 'border-green-500' : 'border-gray-700'
          }`}>
            <div className="absolute top-4 left-4 font-semibold text-white">
              🤝 협업 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/flux-1-kontext-pro__k-tech___.png"
                alt="협업 면접관"
                className="w-full h-full object-cover"
              />
            </div>
          </div>
        </div>

        {/* 하단 영역 */}
        <div className="grid gap-4 p-4" style={{ height: '60vh', gridTemplateColumns: '2fr 1fr 2fr' }}>
          {/* 사용자 영역 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // 사용자 턴이면서 타이머가 활성화되어 있을 때만
            currentPhase === 'user_turn' && isTimerActive
              ? 'border-yellow-500 shadow-lg shadow-yellow-500/50'
            // 대기 상태
            : 'border-gray-600'
          }`}>
            <div className="absolute top-4 left-4 text-yellow-400 font-semibold z-10">
              사용자: {user?.name || state.settings?.candidate_name || 'You'}
            </div>
            
            {/* 🆕 턴 상태 표시 */}
            {currentPhase === 'user_turn' && (
              <div className="absolute top-4 right-4 bg-yellow-500 text-black px-3 py-1 rounded-full text-xs font-bold z-10">
                🎯 답변 차례
              </div>
            )}
            
            {/* 실제 사용자 비디오 - 항상 렌더링 */}
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
              style={{ transform: 'scaleX(-1)' }}
            />

            {/* 👁️ 시선 추적용 숨겨진 비디오 */}
            <video
              ref={gazeVideoRef}
              autoPlay
              muted
              playsInline
              className="hidden"
            />
            
            {/* 📹 카메라 연결 상태 오버레이 */}
            {!state.cameraStream && (
              <div className="absolute inset-0 h-full flex items-center justify-center bg-gray-800">
                <div className="text-white text-lg opacity-50">
                  카메라 대기 중...
                </div>
              </div>
            )}
            
            {/* 라이브 표시 */}
            <div className="absolute top-4 right-4 bg-red-500 text-white px-2 py-1 rounded text-xs font-medium z-10">
              LIVE
            </div>

            {/* 답변 입력 오버레이 */}
            <div className="absolute bottom-0 left-0 right-0 bg-black/80 p-4">
              
              {/* 🎤 음성 제어 버튼들 */}
              <div className="flex items-center justify-between mt-3 gap-3">
                {/* 음성 인식 결과 표시 */}
                {sttResult && (
                  <div className="text-xs text-blue-400 bg-blue-900/30 px-2 py-1 rounded">
                    🇢 인식: {sttResult.substring(0, 30)}{sttResult.length > 30 ? '...' : ''}
                  </div>
                )}
                
              </div>
              
              <div className="flex items-center justify-end mt-2">
                {/* 🆕 타이머 표시 */}
                {currentPhase === 'user_turn' && isTimerActive && (
                  <div className={`text-lg font-bold ${getTimerColor()}`}>
                    {formatTime(timeLeft)}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 중앙 컨트롤 */}
          <div className="bg-gray-800 rounded-lg p-6 flex flex-col overflow-hidden">
            {/* 스크롤 가능한 컨텐츠 영역 */}
            <div className="flex-1 overflow-y-auto">
              {/* 🆕 현재 턴 상태 표시 */}
              <div className="text-center mb-4">
              
              {/* 🆕 타이머 표시 */}
              {currentPhase === 'user_turn' && isTimerActive && (
                <div className={`text-2xl font-bold ${getTimerColor()} mb-2`}>
                  {formatTime(timeLeft)}
                </div>
              )}
              
              {/* 🎤 음성 상태 표시 */}
              {isRecording && (
                <SpeechIndicator 
                  isListening={true}
                  isSpeaking={false}
                  className="justify-center mb-2"
                />
              )}
              
              {/* 🎤 마이크 권한 상태 */}
              {hasAudioPermission === false && (
                <div className="text-red-400 text-xs mb-2">
                  🚫 마이크 권한이 필요합니다
                </div>
              )}

              {/* 👁️ 시선 추적 상태 표시 */}
              {state.gazeTracking?.calibrationSessionId && (
                <div className="text-center mb-2">
                  {isGazeRecording ? (
                    <div className="text-green-400 text-xs flex items-center justify-center">
                      <div className="w-2 h-2 bg-green-400 rounded-full mr-1 animate-pulse"></div>
                      👁️ 면접 전체 시선 추적 중
                    </div>
                  ) : currentPhase === 'interview_completed' ? (
                    <div className="text-blue-400 text-xs space-y-1">
                      <div className="flex items-center justify-center">
                        {state.gazeTracking?.gazeAnalysisStatus === 'analyzing' ? (
                          <div className="w-2 h-2 bg-blue-400 rounded-full mr-1 animate-pulse"></div>
                        ) : null}
                        👁️ 시선 분석 {state.gazeTracking?.gazeAnalysisStatus === 'analyzing' ? `진행 중 (${state.gazeTracking?.gazeAnalysisProgress || 0}%)` : state.gazeTracking?.gazeAnalysisStatus === 'completed' ? '완료' : state.gazeTracking?.gazeAnalysisStatus === 'failed' ? '실패' : '대기 중'}
                      </div>
                      <div className="flex items-center justify-center">
                        {isFeedbackProcessing ? (
                          <div className="w-2 h-2 bg-purple-400 rounded-full mr-1 animate-pulse"></div>
                        ) : null}
                        📊 면접 피드백 {isFeedbackProcessing ? '처리 중' : '완료'}
                      </div>
                    </div>
                  ) : (
                    <div className="text-gray-400 text-xs">
                      👁️ 시선 추적 준비 중
                    </div>
                  )}
                </div>
              )}

              {/* 👁️ 시선 분석 상태 표시 */}
              {gazeAnalysisResult && (
                <div className="text-center mb-2">
                  <div className="text-blue-400 text-xs">
                    🎉 시선 분석 완료 (점수: {gazeAnalysisResult.gaze_score}/100)
                  </div>
                </div>
              )}

              {/* 👁️ 시선 추적 에러 표시 */}
              {gazeError && (
                <div className="text-red-400 text-xs mb-2 text-center">
                  ⚠️ {gazeError}
                </div>
              )}
            </div>

            {/* INTRO 메시지 및 현재 질문 표시 */}
            <div className="text-center mb-6">
              {showIntroMessage && hasIntroMessage ? (
                // INTRO 메시지 표시
                <div className="intro-message">
                  <div className="text-blue-400 text-sm mb-2">🎤 면접관 인사</div>
                  <div className="text-white text-base leading-relaxed whitespace-pre-line mb-3 bg-blue-900/20 rounded-lg p-4 border border-blue-500/30 max-h-32 overflow-y-auto">
                    {introMessage}
                  </div>
                  <div className="text-gray-400 text-xs">잠시 후 면접이 시작됩니다...</div>
                </div>
              ) : (
                // 일반 질문 표시
                <div>
                  <div className="text-gray-400 text-sm mb-2">
                    {isTTSPlaying ? '현재 진행 중' : '현재 질문'}
                  </div>
                  <div className="text-white text-base leading-relaxed mb-3 max-h-16 overflow-y-auto">
                    {isTTSPlaying && currentTTSIndex >= 0 && ttsQueue[currentTTSIndex] ? (
                      // 🎯 1순위: TTS 재생 중일 때 타입별 메시지 표시
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-3 h-3 bg-purple-400 rounded-full animate-pulse"></div>
                        <span className="text-purple-400">
                          {getTTSDisplayMessage(ttsQueue[currentTTSIndex].type)}
                        </span>
                      </div>
                    ) : currentPhase === 'ai_processing' ? (
                      // 🎯 2순위: AI 답변 생성 중
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                        <span className="text-green-400">🤖 AI가 답변을 생성하고 있습니다...</span>
                      </div>
                    ) : isSubmittingAnswer ? (
                      // 🎯 3순위: 사용자 답변 제출 중
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-3 h-3 bg-orange-400 rounded-full animate-pulse"></div>
                        <span className="text-orange-400">📝 답변을 제출하고 있습니다...</span>
                      </div>
                    ) : currentPhase === 'interview_completed' ? (
                      // 🎯 4순위: 면접 완료
                      "✅ 면접이 완료되었습니다"
                    ) : isInitialLoading ? (
                      // 🎯 5순위: 초기 로딩
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                        <span className="text-blue-400">
                          {ttsQueue.length > 0 ? getTTSDisplayMessage(ttsQueue[0].type) : '🎬 면접을 시작합니다'}
                        </span>
                      </div>
                    ) : (
                      // 🎯 6순위: 기본값 - 현재 질문 표시
                      currentQuestion || "질문을 불러오는 중..."
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* AI 지원자 질문 표시 */}
            {currentAIQuestion && (
              <div className="text-center mb-6">
                <div className="text-orange-400 text-sm mb-2">🎯 AI 지원자용 질문</div>
                <div className="text-white text-base leading-relaxed whitespace-pre-line mb-3 bg-orange-900/20 rounded-lg p-4 border border-orange-500/30 max-h-32 overflow-y-auto">
                  {currentAIQuestion}
                </div>
                <div className="text-orange-300 text-xs">
                  🔊 음성은 자동으로 재생됩니다
                </div>
              </div>
            )}

            {/* AI 지원자 답변 표시 */}
            {currentAIAnswer && (
              <div className="text-center mb-6">
                <div className="text-purple-400 text-sm mb-2">🤖 AI 지원자 답변 (춘식이)</div>
                <div className="text-white text-base leading-relaxed whitespace-pre-line mb-3 bg-purple-900/20 rounded-lg p-4 border border-purple-500/30 max-h-40 overflow-y-auto">
                  {currentAIAnswer}
                </div>
                <div className="text-purple-300 text-xs">
                  🔊 음성은 자동으로 재생됩니다
                </div>
              </div>
            )}
            </div>

            {/* 컨트롤 버튼 */}
             <div className="space-y-3">
               {currentPhase === 'interview_completed' ? (
                 // 면접 완료 시 나가기 버튼 표시
                 <div className="space-y-2">
                   {(state.gazeTracking?.gazeAnalysisStatus === 'analyzing' || isFeedbackProcessing) && !pollingError && !feedbackProcessingError ? (
                     <div className="text-center text-sm text-yellow-400 mb-2">
                       💫 분석이 완료될 때까지 잠시만 기다려주세요
                     </div>
                   ) : null}
                   
                   {(pollingError || feedbackProcessingError) && (
                     <div className="text-center text-sm text-red-400 mb-2">
                       ⚠️ 분석 중 문제가 발생했지만, 면접을 나가실 수 있습니다
                     </div>
                   )}
                   
                   <button 
                     onClick={() => navigate('/mypage')}
                     className={`w-full py-3 text-white rounded-lg font-semibold transition-colors ${
                       (state.gazeTracking?.gazeAnalysisStatus === 'analyzing' || isFeedbackProcessing) && !pollingError && !feedbackProcessingError
                         ? 'bg-gray-600 hover:bg-gray-500' 
                         : 'bg-blue-600 hover:bg-blue-500'
                     }`}
                   >
                     {(state.gazeTracking?.gazeAnalysisStatus === 'analyzing' || isFeedbackProcessing) && !pollingError && !feedbackProcessingError
                       ? '🔄 분석 중... (나가기 가능)'
                       : '🏠 면접 나가기'
                     }
                   </button>
                 </div>
               ) : (
                 // 면접 진행 중일 때 답변 제출 버튼 표시
                 (() => {
                   const hasSessionId = !!state.sessionId || !isRestoring;
                   const isUserTurn = currentPhase === 'user_turn';
                   // 🎯 통합 버튼 활성화 조건: 사용자 턴이면서 타이머가 활성화되어 있을 때
                   const canUseIntegratedButton = isUserTurn && isTimerActive && hasSessionId && !isRestoring;
                   
                   // 🎯 버튼 상태 결정
                   let buttonText = '';
                   let buttonClass = '';
                   let isButtonDisabled = false;
                   
                   if (isSubmittingAnswer) {
                     buttonText = '📝 답변 처리 중...';
                     buttonClass = 'bg-orange-500';
                     isButtonDisabled = true;
                   } else if (isRestoring) {
                     buttonText = '세션 로드 중...';
                     buttonClass = 'bg-gray-600';
                     isButtonDisabled = true;
                   } else if (!hasSessionId) {
                     buttonText = '세션 없음';
                     buttonClass = 'bg-gray-600';
                     isButtonDisabled = true;
                   } else if (!isUserTurn) {
                     buttonText = '대기 중...';
                     buttonClass = 'bg-gray-600';
                     isButtonDisabled = true;
                   } else if (!isTimerActive) {
                     buttonText = '타이머 대기 중...';
                     buttonClass = 'bg-gray-600';
                     isButtonDisabled = true;
                   } else if (isRecording) {
                     buttonText = `🔴 녹음 중지 (${recordingTime}s)`;
                     buttonClass = 'bg-red-500 animate-pulse';
                     isButtonDisabled = false;
                   } else {
                     buttonText = '🎤 녹음 시작';
                     buttonClass = 'bg-blue-600 hover:bg-blue-500';
                     isButtonDisabled = false;
                   }
                   
                   return (
                     <button 
                       className={`w-full py-3 text-white rounded-lg font-semibold transition-colors ${
                         isButtonDisabled 
                           ? 'bg-gray-600 cursor-not-allowed' 
                           : buttonClass
                       }`}
                       onClick={handleIntegratedButton}
                       disabled={isButtonDisabled}
                     >
                       {buttonText}
                     </button>
                   );
                 })()
               )}
             </div>

          </div>

          {/* AI 지원자 춘식이 */}
          <div className={`bg-blue-900 rounded-lg overflow-hidden relative border-4 transition-all duration-300 ${
            // AI 턴일 때 또는 AI TTS 재생 중일 때
            currentPhase === 'ai_processing' || shouldHighlight('ai')
              ? 'border-green-500 shadow-lg shadow-green-500/50'
            // 대기 상태
            : 'border-gray-600'
          }`}>
            <div className="absolute top-4 left-4 text-green-400 font-semibold z-10">
              AI 지원자 {getAICandidateName(state.aiSettings?.aiQualityLevel || 6)}
            </div>
            
            {/* 🆕 AI 턴 상태 표시 */}
            {currentPhase === 'ai_processing' && (
              <div className="absolute top-4 right-4 bg-green-500 text-black px-3 py-1 rounded-full text-xs font-bold z-10">
                🤖 답변 중
              </div>
            )}
            
            {/* AI 지원자 전체 이미지 */}
            <div className="h-full flex items-center justify-center relative">
              <img 
                src={getAICandidateImage(state.aiSettings?.aiQualityLevel || 6)}
                alt={getAICandidateName(state.aiSettings?.aiQualityLevel || 6)}
                className="w-full h-full object-cover"
              />
              
              {/* 상태 표시 오버레이 */}
              {currentPhase === 'ai_processing' ? (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center bg-black/70 rounded-lg p-4">
                  <div className="text-green-400 text-sm font-semibold mb-2">답변 중...</div>
                  <div className="w-6 h-6 border-2 border-green-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
                </div>
              ) : currentPhase === 'interview_completed' ? (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center bg-black/70 rounded-lg p-4">
                  <div className="text-blue-400 text-sm font-semibold mb-2">면접 완료</div>
                  <div className="text-blue-300 text-xs">수고하셨습니다!</div>
                </div>
              ) : (
                <div className="absolute bottom-4 right-4 bg-black/70 rounded-lg p-2">
                  <div className="text-blue-300 text-sm">대기 중</div>
                </div>
              )}
              
              {/* 라이브 표시 */}
              <div className="absolute top-4 right-4 bg-green-500 text-white px-2 py-1 rounded text-xs font-medium z-10">
                AI
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterviewGO;
