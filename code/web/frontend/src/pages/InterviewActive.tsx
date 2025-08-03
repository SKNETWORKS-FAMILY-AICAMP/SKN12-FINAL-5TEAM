import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import VoiceControls from '../components/voice/VoiceControls';
import SpeechIndicator from '../components/voice/SpeechIndicator';
import { useInterview } from '../contexts/InterviewContext';
import { interviewApi, handleApiError } from '../services/api';
import { useInterviewStart } from '../hooks/useInterviewStart';
import { 
  createSTT, 
  createTTS, 
  mapQuestionCategoryToInterviewer,
  SpeechToText,
  TextToSpeech
} from '../utils/speechUtils';

// 페이지 레벨 초기화 플래그 (컴포넌트 외부)
let pageInitialized = false;

const InterviewActive: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  const { startInterview: startInterviewAPI, isStarting } = useInterviewStart();

  // 난이도별 AI 지원자 이미지 매핑 함수
  const getAICandidateImage = (level: number): string => {
    if (level <= 3) return '/img/candidate_1.png'; // 초급자
    if (level <= 7) return '/img/candidate_2.png'; // 중급자
    return '/img/candidate_3.png'; // 고급자
  };

  // 난이도별 AI 지원자 이름 매핑 함수
  const getAICandidateName = (level: number): string => {
    if (level <= 3) return '춘식이 (초급)';
    if (level <= 7) return '춘식이 (중급)';
    return '춘식이 (고급)';
  };
  
  const [interviewState, setInterviewState] = useState<'ready' | 'active' | 'paused' | 'completed' | 'ai_answering' | 'comparison_mode'>('ready');
  const [comparisonMode, setComparisonMode] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<'user_turn' | 'ai_turn' | 'interviewer_question'>('user_turn');
  const [comparisonSessionId, setComparisonSessionId] = useState<string>('');
  const [hasInitialized, setHasInitialized] = useState(false);  // 중복 초기화 방지
  const [timeline, setTimeline] = useState<Array<{
    id: string;
    type: 'user' | 'ai' | 'interviewer';
    question: string;
    answer?: string;
    questionType?: string;
    isAnswering?: boolean;
  }>>([]);
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [timeLeft, setTimeLeft] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [questionCount, setQuestionCount] = useState(0); // 질문 개수 추적
  const [showStartPopup, setShowStartPopup] = useState(false); // 면접 시작 팝업
  const [showQuestionModal, setShowQuestionModal] = useState(false); // 질문 모달 표시
  const [modalQuestion, setModalQuestion] = useState<any>(null); // 모달에서 표시할 임시 질문

  
  // 📹 비디오 스트림 관리 상태
  const [isStreamCreating, setIsStreamCreating] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  
  // STT/TTS 관련 상태
  const [sttInstance, setSTTInstance] = useState<SpeechToText | null>(null);
  const [ttsInstance, setTTSInstance] = useState<TextToSpeech | null>(null);
  const [isSTTActive, setIsSTTActive] = useState(false);
  const [isTTSActive, setIsTTSActive] = useState(false);
  const [ttsType, setTtsType] = useState<'question' | 'ai_answer' | 'general'>('general');
  const [currentInterviewerType, setCurrentInterviewerType] = useState<'hr' | 'tech' | 'collaboration' | null>(null);
  const [interimText, setInterimText] = useState('');
  const [canAnswer, setCanAnswer] = useState(true); // TTS 끝나야 답변 가능
  const [showHistory, setShowHistory] = useState(false); // 히스토리 섹션 표시/숨김
  
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const answerRef = useRef<HTMLTextAreaElement>(null);
  const initializationRef = useRef<boolean>(false);  // 초기화 완료 여부
  const videoRef = useRef<HTMLVideoElement>(null);
  const isSettingUpRef = useRef<boolean>(false);  // 스트림 설정 중 플래그
  const lastTTSQuestionRef = useRef<string>('');  // 마지막 TTS 재생한 질문 추적
  const useEffectExecutedRef = useRef<boolean>(false); // React.StrictMode 중복 실행 방지

  // Initialize interview - simplified to always restart from localStorage
  useEffect(() => {
    // 페이지 레벨 중복 실행 방지 (최우선)
    if (pageInitialized) {
      console.log('⚠️ 페이지 이미 초기화됨 - 중복 실행 방지');
      return;
    }
    pageInitialized = true;
    
    // React.StrictMode 중복 실행 방지
    if (useEffectExecutedRef.current) {
      console.log('⚠️ useEffect 이미 실행됨 - StrictMode 중복 방지');
      return;
    }
    useEffectExecutedRef.current = true;

    // 🔍 카메라 스트림 상태 디버깅
    console.log('🔍 [DEBUG] InterviewActive 초기화 시작 - Context 상태:', {
      hasCameraStream: !!state.cameraStream,
      streamActive: state.cameraStream ? state.cameraStream.active : 'N/A',
      videoTracks: state.cameraStream ? state.cameraStream.getVideoTracks().length : 0,
      sessionId: state.sessionId,
      interviewStatus: state.interviewStatus
    });
    
    // 🚨 중요한 상태를 큰 글씨로 출력
    if (!state.cameraStream) {
      console.error('🚨 [CRITICAL] CAMERA STREAM이 NULL입니다!');
    } else if (!state.cameraStream.active) {
      console.error('🚨 [CRITICAL] CAMERA STREAM이 비활성화되어 있습니다!');
    } else if (state.cameraStream.getVideoTracks().length === 0) {
      console.error('🚨 [CRITICAL] VIDEO TRACKS가 없습니다!');
    } else {
      console.log('✅ [SUCCESS] CAMERA STREAM 기본 상태 정상');
    }
    
    if (state.cameraStream) {
      const videoTracks = state.cameraStream.getVideoTracks();
      if (videoTracks.length > 0) {
        const track = videoTracks[0];
        console.log('🔍 [DEBUG] 비디오 트랙 상세 정보:', {
          readyState: track.readyState,
          enabled: track.enabled,
          muted: track.muted,
          id: track.id,
          label: track.label,
          kind: track.kind
        });
        
        // 🚨 트랙 상태 확인
        if (track.readyState === 'ended') {
          console.error('🚨 [CRITICAL] VIDEO TRACK이 ENDED 상태입니다!');
        } else if (!track.enabled) {
          console.error('🚨 [CRITICAL] VIDEO TRACK이 DISABLED 상태입니다!');
        } else {
          console.log('✅ [SUCCESS] VIDEO TRACK 상태 정상');
        }
      }
    }

    if (!state.sessionId || !state.settings) {
      // localStorage 확인
      console.log('🔄 면접 상태가 없음 - localStorage 확인');
      const savedState = localStorage.getItem('interview_state');
      
      if (savedState) {
        try {
          const parsedState = JSON.parse(savedState);
          console.log('✅ localStorage에서 설정 발견:', parsedState);
          
          // 데이터 유효성 검증 (최소한만)
          if (!parsedState.settings) {
            console.error('❌ localStorage 데이터 불완전 - settings 누락');
            localStorage.removeItem('interview_state');
            navigate('/interview/setup');
            return;
          }
          
          // 면접 모드 유효성 검증
          const validModes = ['ai_competition', 'personalized', 'standard'];
          if (!validModes.includes(parsedState.settings.mode)) {
            console.error('❌ 유효하지 않은 면접 모드:', parsedState.settings.mode);
            localStorage.removeItem('interview_state');
            navigate('/interview/setup');
            return;
          }
          
          // Context 상태 업데이트 (기본 설정만)
          if (parsedState.jobPosting) {
            dispatch({ type: 'SET_JOB_POSTING', payload: parsedState.jobPosting });
          }
          if (parsedState.resume) {
            dispatch({ type: 'SET_RESUME', payload: parsedState.resume });
          }
          if (parsedState.interviewMode) {
            dispatch({ type: 'SET_INTERVIEW_MODE', payload: parsedState.interviewMode });
          }
          if (parsedState.aiSettings) {
            dispatch({ type: 'SET_AI_SETTINGS', payload: parsedState.aiSettings });
          }
          
          // 무조건 새로운 면접 재시작
          console.log('🚀 localStorage 설정으로 새로운 면접 재시작');
          handleInterviewRestartFromLocalStorage(parsedState.settings);
          return;
          
        } catch (error) {
          console.error('❌ localStorage 파싱 실패:', error);
          localStorage.removeItem('interview_state');
        }
      }
      
      // localStorage 없음 - 면접 설정 페이지로 이동
      console.log('❌ localStorage 없음 - 면접 설정 페이지로 이동');
      navigate('/interview/setup');
      return;
    }
    
    // 일반 초기화 로직 (기존 state가 있을 때만 실행)
    if (
      state.settings?.mode === 'ai_competition' &&
      !initializationRef.current
    ) {
      initializationRef.current = true;
      setHasInitialized(true);
      setComparisonMode(true);
      setShowStartPopup(true);
      handleNewInterviewStart(state.settings);
    } else if (state.settings?.mode !== 'ai_competition' && !initializationRef.current) {
      initializationRef.current = true;
      setHasInitialized(true);
      // 일반 모드 초기화
      if (state.questions.length === 0 && !isLoading) {
        loadFirstQuestion();
      } else if (state.questions.length > 0) {
        const currentQuestion = state.questions[state.currentQuestionIndex];
        if (currentQuestion) {
          setTimeLeft(currentQuestion.time_limit || 120);
        }
      }
      setShowStartPopup(true);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 빈 배열로 한 번만 실행

  // STT/TTS 초기화
  useEffect(() => {
    // STT 초기화
    const stt = createSTT({
      onResult: (transcript: string, isFinal: boolean) => {
        if (isFinal) {
          setCurrentAnswer(prev => prev + transcript);
          setInterimText('');
        } else {
          setInterimText(transcript);
        }
      },
      onError: (error: string) => {
        console.error('STT 오류:', error);
        setIsSTTActive(false);
        setInterimText('');
      },
      onStart: () => {
        setIsSTTActive(true);
        console.log('STT 시작');
      },
      onEnd: () => {
        setIsSTTActive(false);
        setInterimText('');
        console.log('STT 종료');
      }
    });

    // TTS 초기화
    const tts = createTTS();
    
    // TTS 지원 여부 확인
    const hasTTS = 'speechSynthesis' in window;
    console.log('🔊 TTS 지원 여부:', hasTTS);
    if (hasTTS) {
      console.log('🎵 사용 가능한 음성:', window.speechSynthesis.getVoices().length);
    }

    setSTTInstance(stt);
    setTTSInstance(tts);

    return () => {
      // 컴포넌트 언마운트 시 정리
      if (stt) {
        stt.stop();
      }
      if (tts) {
        tts.stop();
      }
    };
  }, []);

  // 비교 면접 모드에서는 타임라인의 마지막 미완료 질문 사용
  const currentQuestion = comparisonMode && timeline.length > 0
    ? (() => {
        // 타임라인에서 마지막 면접관 턴의 미완료 질문 찾기
        const lastInterviewerTurn = [...timeline].reverse().find(turn => 
          turn.type === 'interviewer' && (!turn.answer || turn.answer === '')
        );
        if (lastInterviewerTurn) {
          return {
            id: `timeline_${lastInterviewerTurn.id}`,
            question: lastInterviewerTurn.question,
            category: lastInterviewerTurn.questionType,
            time_limit: 120,
            keywords: []
          };
        }
        return null;
      })()
    : state.questions[state.currentQuestionIndex];



  // 📹 이전 스트림 완전 정리 함수
  const cleanupPreviousStream = (stream: MediaStream | null) => {
    if (stream) {
      console.log('🧹 이전 스트림 정리 중...');
      stream.getTracks().forEach(track => {
        track.stop();
        console.log(`🗑️ 트랙 정리: ${track.kind} - ${track.readyState}`);
      });
      
      // 비디오 요소에서 스트림 제거
      if (videoRef.current && videoRef.current.srcObject === stream) {
        videoRef.current.srcObject = null;
      }
    }
  };

  // 📹 개선된 카메라 스트림 생성 함수
  const createNewStream = async (retryCount: number = 0): Promise<boolean> => {
    const MAX_RETRIES = 3;
    
    if (isStreamCreating) {
      console.log('⏳ 이미 스트림 생성 중입니다...');
      return false;
    }
    
    if (retryCount >= MAX_RETRIES) {
      console.error('❌ 최대 재시도 횟수 초과');
      setStreamError('카메라 접근에 실패했습니다. 브라우저 설정을 확인해주세요.');
      return false;
    }
    
    try {
      setIsStreamCreating(true);
      setStreamError(null);
      
      console.log(`🔄 새로운 카메라 스트림 생성 중... (시도 ${retryCount + 1}/${MAX_RETRIES})`);
      
      // 이전 스트림 정리
      cleanupPreviousStream(state.cameraStream);
      
      const newStream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false  // 면접에서는 비디오만 필요
      });
      
      const videoTracks = newStream.getVideoTracks();
      console.log('✅ 새 카메라 스트림 생성 성공:', videoTracks.length, '개 트랙');
      
      // 트랙 상태 검증
      if (videoTracks.length === 0) {
        throw new Error('비디오 트랙을 찾을 수 없습니다');
      }
      
      // Context에 새 스트림 저장 (Promise로 변경 완료 대기)
      return new Promise<boolean>((resolve) => {
        dispatch({
          type: 'SET_CAMERA_STREAM',
          payload: newStream
        });
        
        // Context 업데이트 완료 대기
        setTimeout(() => {
          console.log('✅ 스트림 Context 업데이트 완료');
          resolve(true);
        }, 100);
      });
      
    } catch (error) {
      console.error(`❌ 카메라 스트림 생성 실패 (시도 ${retryCount + 1}):`, error);
      
      if (retryCount < MAX_RETRIES - 1) {
        console.log(`🔄 ${1000 * (retryCount + 1)}ms 후 재시도...`);
        setTimeout(() => {
          createNewStream(retryCount + 1);
        }, 1000 * (retryCount + 1));  // 점진적 지연
        return false;
      } else {
        setStreamError(error instanceof Error ? error.message : '알 수 없는 오류');
        return false;
      }
    } finally {
      setIsStreamCreating(false);
    }
  };

  // 📹 개선된 카메라 스트림 연결
  useEffect(() => {
    // 🔍 [DEBUG] 카메라 설정 useEffect 진입
    console.log('🔍 [DEBUG] 카메라 설정 useEffect 실행:', {
      isSettingUp: isSettingUpRef.current,
      hasCameraStream: !!state.cameraStream,
      streamActive: state.cameraStream?.active,
      hasVideoRef: !!videoRef.current
    });

    // 이미 설정 중이거나 스트림이 없으면 리턴
    if (isSettingUpRef.current || !state.cameraStream) {
      console.log('🔍 [DEBUG] 카메라 설정 중단:', {
        reason: isSettingUpRef.current ? '이미 설정 중' : '스트림 없음',
        isSettingUp: isSettingUpRef.current,
        hasCameraStream: !!state.cameraStream
      });
      return;
    }
    
    const setupCamera = async () => {
      // 중복 실행 방지
      if (isSettingUpRef.current) {
        console.log('⏳ 이미 카메라 설정 중입니다...');
        return;
      }
      
      console.log('🔍 [DEBUG] setupCamera 함수 시작');
      isSettingUpRef.current = true;
      
      try {
        // 🔒 스트림이 실행 중 변경될 수 있으므로 로컬 변수에 저장
        const currentStream = state.cameraStream;
        if (!currentStream) {
          console.warn('⚠️ 스트림이 없습니다 (setupCamera 내부)');
          return;
        }
        
        console.log('🎥 카메라 설정 시작...', {
          hasStream: !!currentStream,
          hasVideoRef: !!videoRef.current,
          tracksCount: currentStream.getVideoTracks().length || 0,
          streamId: currentStream.id,
          streamActive: currentStream.active
        });
        
        // 스트림 유효성 검증
        const videoTracks = currentStream.getVideoTracks();
        console.log('🔍 [DEBUG] 스트림 유효성 검증 시작:', {
          videoTracksCount: videoTracks.length,
          streamId: currentStream.id,
          streamActive: currentStream.active
        });
        
        if (videoTracks.length === 0) {
          console.warn('⚠️ 비디오 트랙이 없습니다');
          return;
        }
        
        const track = videoTracks[0];
        console.log('🔍 [DEBUG] 비디오 트랙 상세 검증:', {
          readyState: track.readyState,
          enabled: track.enabled,
          muted: track.muted,
          id: track.id,
          label: track.label,
          kind: track.kind,
          settings: track.getSettings ? track.getSettings() : 'N/A'
        });
        
        if (track.readyState === 'ended') {
          console.warn('⚠️ 비디오 트랙이 종료되었습니다. 새 스트림을 생성합니다...');
          const success = await createNewStream();
          if (!success) {
            console.error('❌ 새 스트림 생성 실패');
            return;
          }
          // 새 스트림이 생성되면 useEffect가 다시 실행되므로 여기서 리턴
          return;
        }
        
        console.log('✅ 스트림 유효성 검증 통과:', track.readyState);
        
        // videoRef가 준비될 때까지 대기 (최대 3초)
        let retries = 0;
        const MAX_WAIT_RETRIES = 30; // 100ms * 30 = 3초
        
        while (!videoRef.current && retries < MAX_WAIT_RETRIES) {
          await new Promise(resolve => setTimeout(resolve, 100));
          retries++;
        }
        
        if (!videoRef.current) {
          console.error('❌ 비디오 ref를 찾을 수 없습니다 (3초 대기 후)');
          return;
        }
        
        console.log('🎥 비디오 ref 준비 완료, 스트림 연결 중...');
        
        // 🔍 [DEBUG] 스트림 연결 전 상태
        console.log('🔍 [DEBUG] 스트림 연결 시작:', {
          currentVideoRef: !!videoRef.current,
          currentSrcObject: !!videoRef.current?.srcObject,
          streamToConnect: currentStream.id,
          streamActive: currentStream.active,
          videoTracks: currentStream.getVideoTracks().length
        });
        
        // 이전 스트림 정리
        if (videoRef.current.srcObject) {
          const prevStream = videoRef.current.srcObject as MediaStream;
          console.log('🔍 [DEBUG] 이전 스트림 정리:', {
            prevStreamId: prevStream.id,
            sameName: prevStream === currentStream
          });
          videoRef.current.srcObject = null;
          // 이전 스트림이 현재 스트림과 다른 경우에만 정리
          if (prevStream !== currentStream) {
            cleanupPreviousStream(prevStream);
          }
          await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        // 새 스트림 연결
        console.log('🔍 [DEBUG] 새 스트림 연결 시도...');
        videoRef.current.srcObject = currentStream;
        console.log('🔍 [DEBUG] srcObject 설정 완료:', {
          assignedStream: !!videoRef.current.srcObject,
          streamId: currentStream.id
        });
        
        // 🚨 srcObject 설정 검증
        if (!videoRef.current.srcObject) {
          console.error('🚨 [CRITICAL] srcObject 설정 실패!');
        } else if (videoRef.current.srcObject !== currentStream) {
          console.error('🚨 [CRITICAL] srcObject가 다른 스트림으로 설정됨!');
        } else {
          console.log('✅ [SUCCESS] srcObject 정상 설정됨');
        }
        
        // 📹 개선된 비디오 재생 설정
        const playVideo = () => {
          return new Promise<void>((resolve, reject) => {
            if (!videoRef.current) {
              console.log('🔍 [DEBUG] playVideo 실패: videoRef.current가 null');
              reject(new Error('Video ref is null'));
              return;
            }

            console.log('🔍 [DEBUG] playVideo 시작:', {
              videoRefReady: !!videoRef.current,
              srcObject: !!videoRef.current.srcObject,
              readyState: videoRef.current.readyState,
              videoWidth: videoRef.current.videoWidth,
              videoHeight: videoRef.current.videoHeight
            });
            
            const onLoadedData = async () => {
              try {
                console.log('🔍 [DEBUG] onLoadedData 이벤트 발생');
                await videoRef.current!.play();
                console.log('✅ 비디오 재생 시작됨');
                console.log('🔍 [DEBUG] 재생 후 상태:', {
                  paused: videoRef.current!.paused,
                  currentTime: videoRef.current!.currentTime,
                  videoWidth: videoRef.current!.videoWidth,
                  videoHeight: videoRef.current!.videoHeight
                });
                
                // 🚨 최종 비디오 상태 검증
                if (videoRef.current!.videoWidth === 0 || videoRef.current!.videoHeight === 0) {
                  console.error('🚨 [CRITICAL] 비디오 크기가 0입니다! (스트림 연결 실패)');
                } else if (videoRef.current!.paused) {
                  console.warn('⚠️ [WARNING] 비디오가 일시정지 상태입니다');
                } else {
                  console.log('✅ [SUCCESS] 비디오 재생 및 표시 정상!');
                }
                resolve();
              } catch (error) {
                if (error instanceof Error && error.name === 'AbortError') {
                  console.log('📹 play() 요청이 중단됨 (정상)');
                  resolve();
                } else {
                  console.warn('⚠️ 비디오 자동 재생 실패:', error);
                  resolve(); // 재생 실패해도 계속 진행
                }
              }
            };
            
            const onError = (error: any) => {
              console.error('📹 비디오 로드 에러:', error);
              resolve(); // 에러 발생해도 계속 진행
            };
            
            const videoElement = videoRef.current;
            if (videoElement) {
              videoElement.addEventListener('loadeddata', onLoadedData, { once: true });
              videoElement.addEventListener('error', onError, { once: true });
            }
            
            // 메타데이터 로드 이벤트
            if (videoElement) {
              videoElement.onloadedmetadata = () => {
                console.log('📹 비디오 메타데이터 로드됨 - 크기:', 
                  videoElement.videoWidth, 'x', videoElement.videoHeight);
              };
            }
          });
        };
        
        try {
          await playVideo();
          console.log('✅ 카메라 설정 완료');
        } catch (error) {
          console.error('📹 비디오 재생 설정 실패:', error);
        }
        
      } catch (error) {
        console.error('❌ 카메라 설정 중 오류:', error);
      } finally {
        isSettingUpRef.current = false;
      }
    };
    
    setupCamera();
    
    // 📹 정리 함수 - 컴포넌트 언마운트 시 리소스 정리
    return () => {
      console.log('🧹 카메라 설정 정리 중...');
      isSettingUpRef.current = false;
      
      const videoElement = videoRef.current;
      if (videoElement) {
        // 이벤트 리스너 정리
        videoElement.onloadedmetadata = null;
        videoElement.onerror = null;
        
        // 현재 재생 중인 비디오 정지
        if (!videoElement.paused) {
          videoElement.pause();
        }
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.cameraStream]); // 🔄 state.cameraStream 변경 시에만 재실행

  // 📹 컴포넌트 언마운트 시 전체 리소스 정리
  useEffect(() => {
    return () => {
      console.log('🧹 InterviewActive 컴포넌트 언마운트 - 전체 정리');
      
      // 모든 스트림 정리
      cleanupPreviousStream(state.cameraStream);
      
      // ref 플래그 리셋
      isSettingUpRef.current = false;
      initializationRef.current = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 빈 의존성 배열로 마운트/언마운트 시에만 실행

  // 페이지 새로고침/닫기 시 경고 및 정리
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      // 디버깅: 현재 상태 로깅
      console.log('🔍 beforeunload 이벤트 발생:', {
        interviewState,
        sessionId: state.sessionId,
        hasSettings: !!state.settings,
        questionsLength: state.questions.length
      });
      
      // 면접 관련 데이터가 있으면 경고 표시 (조건 완화)
      if (state.sessionId && state.settings) {
        console.log('⚠️ beforeunload - 면접 진행 중 감지, 경고 표시');
        e.preventDefault();
        e.returnValue = '면접이 진행 중입니다. 새로고침하면 현재 진행 상황이 모두 삭제되고 새로운 면접이 시작됩니다.';
        
        // TTS 강제 정리
        if (ttsInstance) {
          console.log('🔇 beforeunload - TTS 강제 정리');
          ttsInstance.forceStop();
        } else if (window.speechSynthesis && window.speechSynthesis.speaking) {
          console.log('🔇 beforeunload - 전역 speechSynthesis 정리');
          window.speechSynthesis.cancel();
        }
        
        // 현재 상태를 localStorage에 저장
        try {
          const currentState = {
            jobPosting: state.jobPosting,
            resume: state.resume,
            interviewMode: state.interviewMode,
            aiSettings: state.aiSettings,
            settings: state.settings,
            sessionId: state.sessionId,
            interviewStatus: state.interviewStatus
          };
          localStorage.setItem('interview_state', JSON.stringify(currentState));
          console.log('💾 beforeunload - 면접 상태 localStorage에 저장');
        } catch (error) {
          console.error('❌ beforeunload - localStorage 저장 실패:', error);
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [interviewState, ttsInstance, state.jobPosting, state.resume, state.interviewMode, state.aiSettings, state.settings, state.sessionId, state.interviewStatus]);

  // 추가 페이지 이탈 감지 이벤트들 (beforeunload 보완)
  useEffect(() => {
    const handlePageHide = (e: PageTransitionEvent) => {
      console.log('🔍 pagehide 이벤트 발생:', { persisted: e.persisted });
      
      if (state.sessionId && state.settings) {
        console.log('🔇 pagehide - TTS 강제 정리 및 상태 저장');
        
        // TTS 강제 정리
        if (ttsInstance) {
          ttsInstance.forceStop();
        } else if (window.speechSynthesis && window.speechSynthesis.speaking) {
          window.speechSynthesis.cancel();
        }
        
        // 상태 저장
        try {
          const currentState = {
            jobPosting: state.jobPosting,
            resume: state.resume,
            interviewMode: state.interviewMode,
            aiSettings: state.aiSettings,
            settings: state.settings,
            sessionId: state.sessionId,
            interviewStatus: state.interviewStatus
          };
          localStorage.setItem('interview_state', JSON.stringify(currentState));
          console.log('💾 pagehide - localStorage 저장 완료');
        } catch (error) {
          console.error('❌ pagehide - localStorage 저장 실패:', error);
        }
      }
    };

    const handleVisibilityChange = () => {
      console.log('🔍 visibilitychange 이벤트 발생:', { 
        hidden: document.hidden,
        visibilityState: document.visibilityState 
      });
      
      // 페이지가 숨겨질 때 (탭 변경, 최소화 등)
      if (document.hidden && state.sessionId && state.settings) {
        console.log('👁️ 페이지 숨김 감지 - 상태 저장');
        
        try {
          const currentState = {
            jobPosting: state.jobPosting,
            resume: state.resume,
            interviewMode: state.interviewMode,
            aiSettings: state.aiSettings,
            settings: state.settings,
            sessionId: state.sessionId,
            interviewStatus: state.interviewStatus
          };
          localStorage.setItem('interview_state', JSON.stringify(currentState));
          console.log('💾 visibilitychange - localStorage 저장 완료');
        } catch (error) {
          console.error('❌ visibilitychange - localStorage 저장 실패:', error);
        }
      }
    };

    // 이벤트 리스너 등록
    window.addEventListener('pagehide', handlePageHide);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      window.removeEventListener('pagehide', handlePageHide);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [ttsInstance, state.jobPosting, state.resume, state.interviewMode, state.aiSettings, state.settings, state.sessionId, state.interviewStatus]);

  // 상태 기반 자동 저장 (면접 진행 중 실시간 저장)
  useEffect(() => {
    // 면접 관련 데이터가 있고, 면접이 시작된 상태에서만 자동 저장
    if (state.sessionId && state.settings && (interviewState === 'active' || interviewState === 'ai_answering' || interviewState === 'ready')) {
      console.log('💾 상태 변경 감지 - 자동 저장:', { 
        interviewState, 
        questionsLength: state.questions.length,
        answersLength: state.answers.length
      });
      
      try {
        const currentState = {
          jobPosting: state.jobPosting,
          resume: state.resume,
          interviewMode: state.interviewMode,
          aiSettings: state.aiSettings,
          settings: state.settings,
          sessionId: state.sessionId,
          interviewStatus: state.interviewStatus,
          questions: state.questions,
          answers: state.answers,
          currentQuestionIndex: state.currentQuestionIndex,
          interviewState: interviewState,
          lastUpdated: new Date().toISOString()
        };
        localStorage.setItem('interview_state', JSON.stringify(currentState));
        console.log('✅ 자동 저장 완료');
      } catch (error) {
        console.error('❌ 자동 저장 실패:', error);
      }
    }
  }, [
    interviewState, 
    state.sessionId, 
    state.settings, 
    state.questions.length, 
    state.answers.length, 
    state.currentQuestionIndex,
    currentAnswer // 답변 입력 중에도 저장
  ]);

  // localStorage에서 복원된 설정으로 새로운 면접 시작
  const restartInterviewFromLocalStorage = async (settings: any) => {
    if (!settings) {
      console.error('❌ restartInterviewFromLocalStorage - settings가 없음');
      return;
    }

    try {
      console.log('🔄 새로운 면접 시작 중...', settings);
      
      // Context 상태 초기화
      dispatch({ type: 'RESET_INTERVIEW' });
      
      // 설정 다시 적용
      dispatch({ type: 'SET_SETTINGS', payload: settings });
      
      // 로딩 상태 설정
      setIsLoading(true);
      setInterviewState('ready');
      
      // 면접 모드에 따라 API 호출
      if (settings.mode === 'ai_competition') {
        // AI 경쟁 모드
        console.log('🤖 AI 경쟁 모드로 새 면접 시작');
        const response = await interviewApi.startAICompetition(settings);
        
        // 새로운 세션 정보 설정
        dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
        setComparisonSessionId(response.comparison_session_id);
        
        // 첫 번째 질문 추가
        if (response.question) {
          dispatch({ type: 'ADD_QUESTION', payload: response.question });
          setCurrentInterviewerType(mapQuestionCategoryToInterviewer(response.question.category));
        }
        
        // AI 경쟁 모드 상태 설정
        setComparisonMode(true);
        initializationRef.current = true;
        setHasInitialized(true);
        
        console.log('✅ AI 경쟁 모드 새 면접 시작 완료');
      } else {
        // 일반 모드
        console.log('👤 일반 모드로 새 면접 시작');
        const response = await interviewApi.startInterview(settings);
        
        // 새로운 세션 ID 설정
        dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
        
        // 첫 번째 질문 로드
        await loadFirstQuestion();
        
        console.log('✅ 일반 모드 새 면접 시작 완료');
      }
      
      // 면접 시작 팝업 표시
      setShowStartPopup(true);
      
      // localStorage 정리 (새로운 면접이므로)
      localStorage.removeItem('interview_state');
      
    } catch (error) {
      console.error('❌ 새로운 면접 시작 실패:', error);
      setIsLoading(false);
      
      // API 실패 시 면접 설정 페이지로 이동
      navigate('/interview/setup');
    } finally {
      setIsLoading(false);
    }
  };

  // localStorage 설정으로 새로운 면접 재시작 핸들러
  const handleInterviewRestartFromLocalStorage = async (settings: any) => {
    if (!settings) {
      console.error('❌ handleInterviewRestartFromLocalStorage - settings가 없음');
      navigate('/interview/setup');
      return;
    }

    try {
      console.log('🔄 localStorage 설정으로 새로운 면접 재시작 중...', settings);
      
      // 기존 localStorage 정리 - 새로운 면접이므로
      localStorage.removeItem('interview_state');
      
      // Context 상태 완전 초기화
      dispatch({ type: 'RESET_INTERVIEW' });
      dispatch({ type: 'SET_SETTINGS', payload: settings });
      
      setIsLoading(true);
      setInterviewState('ready');
      
      // Hook을 사용한 API 호출 (완전히 새로운 면접)
      const response = await startInterviewAPI(settings, 'restart');
      
      if (!response) {
        console.log('⚠️ API 호출이 차단됨 (중복 방지) - 잠시 후 다시 시도');
        setIsLoading(false);
        
        // 잠시 후 다시 시도하거나 설정 페이지로 이동
        setTimeout(() => {
          console.log('🔄 면접 설정 페이지로 이동');
          navigate('/interview/setup');
        }, 2000);
        return;
      }
      
      if (response) {
        console.log('✅ 새로운 면접 재시작 성공:', response);
        
        // 새로운 세션 정보 설정
        dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
        
        if (settings.mode === 'ai_competition') {
          // AI 경쟁 모드 설정
          setComparisonSessionId(response.comparison_session_id);
          setComparisonMode(true);
          setCurrentPhase('user_turn');
          
          // 첫 번째 질문 추가
          if (response.question) {
            dispatch({ type: 'ADD_QUESTION', payload: response.question });
            setCurrentInterviewerType(mapQuestionCategoryToInterviewer(response.question.category));
            
            // 타임라인 설정
            const firstTurn = {
              id: `interviewer_${Date.now()}`,
              type: 'interviewer' as const,
              question: response.question.question,
              questionType: response.question.category
            };
            setTimeline([firstTurn]);
          }
          
          // 면접 시작 팝업 표시
          setShowStartPopup(true);
          
          console.log('🤖 AI 경쟁 모드 재시작 완료');
        } else {
          // 일반 모드 설정
          if (response.question) {
            dispatch({ type: 'ADD_QUESTION', payload: response.question });
          }
          setShowStartPopup(true);
          
          console.log('👤 일반 모드 재시작 완료');
        }
        
        // 초기화 플래그 설정
        initializationRef.current = true;
        setHasInitialized(true);
      }
      
    } catch (error) {
      console.error('❌ localStorage 면접 재시작 실패:', error);
      setIsLoading(false);
      
      // 사용자에게 에러 메시지 표시
      const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류';
      alert(`면접 재시작 중 오류가 발생했습니다: ${errorMessage}\n\n면접 설정 페이지로 이동합니다.`);
      
      // 재시작 실패 시 면접 설정 페이지로 이동
      navigate('/interview/setup');
    } finally {
      setIsLoading(false);
    }
  };

  // EnvironmentCheck에서 온 새로운 면접 시작 핸들러
  const handleInterviewStartFromEnvironment = async (settings: any) => {
    if (!settings) {
      console.error('❌ handleInterviewStartFromEnvironment - settings가 없음');
      return;
    }

    try {
      console.log('🚀 EnvironmentCheck에서 새로운 면접 시작', settings);
      
      // Context 상태 초기화
      dispatch({ type: 'RESET_INTERVIEW' });
      dispatch({ type: 'SET_SETTINGS', payload: settings });
      
      setIsLoading(true);
      setInterviewState('ready');
      
      // Hook을 사용한 API 호출
      const response = await startInterviewAPI(settings, 'environment');
      
      if (response) {
        // 세션 정보 설정
        dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
        setComparisonSessionId(response.comparison_session_id);
        
        // 첫 번째 질문 추가
        if (response.question) {
          dispatch({ type: 'ADD_QUESTION', payload: response.question });
          setCurrentInterviewerType(mapQuestionCategoryToInterviewer(response.question.category));
        }
        
        // AI 경쟁 모드 상태 설정
        setComparisonMode(true);
        initializationRef.current = true;
        setHasInitialized(true);
        setShowStartPopup(true);
        
        // localStorage 상태 업데이트 (API 호출 완료됨을 표시)
        const updatedState = JSON.parse(localStorage.getItem('interview_state') || '{}');
        updatedState.needsApiCall = false;
        updatedState.sessionId = response.session_id;
        localStorage.setItem('interview_state', JSON.stringify(updatedState));
        
        console.log('✅ EnvironmentCheck 면접 시작 완료');
      }
      
    } catch (error) {
      console.error('❌ EnvironmentCheck 면접 시작 실패:', error);
      setIsLoading(false);
      navigate('/interview/setup');
    } finally {
      setIsLoading(false);
    }
  };

  // 일반적인 새로운 면접 시작 핸들러
  const handleNewInterviewStart = async (settings: any) => {
    if (!settings) {
      console.error('❌ handleNewInterviewStart - settings가 없음');
      return;
    }

    try {
      console.log('🆕 새로운 면접 시작', settings);
      
      setIsLoading(true);
      
      // Hook을 사용한 API 호출
      const response = await startInterviewAPI(settings, 'new');
      
      if (response) {
        // 세션 정보 설정
        dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
        setComparisonSessionId(response.comparison_session_id);
        
        // 첫 번째 질문 추가
        if (response.question) {
          dispatch({ type: 'ADD_QUESTION', payload: response.question });
          setCurrentInterviewerType(mapQuestionCategoryToInterviewer(response.question.category));
        }
        
        console.log('✅ 새로운 면접 시작 완료');
      }
      
    } catch (error) {
      console.error('❌ 새로운 면접 시작 실패:', error);
      alert(`면접 시작 실패: ${handleApiError(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  // STT/TTS 관련 함수들
  const handleStartSTT = () => {
    if (sttInstance && !isSTTActive) {
      sttInstance.start();
    }
  };

  const handleStopSTT = () => {
    if (sttInstance && isSTTActive) {
      sttInstance.stop();
    }
  };

  const handlePlayTTS = () => {
    const questionForTTS = modalQuestion || currentQuestion;
    
    console.log('🔊 TTS 재생 시도:', {
      currentQuestion: !!currentQuestion,
      modalQuestion: !!modalQuestion,
      questionForTTS: !!questionForTTS,
      ttsInstance: !!ttsInstance,
      isTTSActive,
      questionText: questionForTTS?.question?.substring(0, 50)
    });
    
    if (questionForTTS && ttsInstance && !isTTSActive) {
      const interviewerType = mapQuestionCategoryToInterviewer(questionForTTS.category || '');
      
      // 🔍 디버깅: 수동 TTS 재생 시 질문 정보 로깅
      console.log('🔍 현재 질문 디버깅 (수동 TTS):', {
        'questionForTTS.category': questionForTTS.category,
        'mapped interviewerType': interviewerType,
        'questionForTTS 전체': questionForTTS
      });
      
      console.log('🎯 TTS 재생 시작:', interviewerType);
      
      setIsTTSActive(true);
      setTtsType('question');
      setCurrentInterviewerType(interviewerType);
      ttsInstance.speakAsInterviewer(questionForTTS.question, interviewerType)
        .then(() => {
          console.log('✅ TTS 재생 완료');
          setIsTTSActive(false);
          setTtsType('general');
          setCurrentInterviewerType(null);
        })
        .catch(error => {
          console.error('❌ TTS 재생 실패:', error);
          setIsTTSActive(false);
          setTtsType('general');
          setCurrentInterviewerType(null);
        });
    } else {
      console.warn('⚠️ TTS 재생 조건 불충족:', {
        hasCurrentQuestion: !!currentQuestion,
        hasModalQuestion: !!modalQuestion,
        hasQuestionForTTS: !!questionForTTS,
        hasTTSInstance: !!ttsInstance,
        isTTSActive
      });
    }
  };

  const handleStopTTS = () => {
    if (ttsInstance && isTTSActive) {
      ttsInstance.stop();
      setIsTTSActive(false);
    }
  };


  // Timer management - 사용자 턴에서만 활성화
  useEffect(() => {
    if ((interviewState === 'active' || interviewState === 'comparison_mode') && currentPhase === 'user_turn') {
      console.log('⏱️ 타이머 시작 - 사용자 턴');
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
      console.log('⏸️ 타이머 정지 - AI 턴이거나 비활성 상태');
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interviewState, currentPhase]);

  const handleTimeUp = () => {
    // AI 턴 중이거나 타이머가 제대로 설정되지 않은 경우 무시
    if (currentPhase === 'ai_turn' || timeLeft <= 0) {
      console.log('🚫 시간 만료 무시 - AI 턴이거나 타이머 미설정');
      return;
    }
    
    console.log('⏰ 시간 만료!');
    setInterviewState('paused');
    alert('시간이 만료되었습니다!');
  };

  const initializeComparisonMode = async () => {
    if (!state.settings) return;
    
    // 이미 초기화 중이거나 완료된 경우 중단
    if (isStarting || isLoading || comparisonSessionId) {
      console.log('🚫 이미 초기화 중이거나 완료됨, 중단');
      return;
    }
    
    try {
      setIsLoading(true);
      console.log('🔄 AI 경쟁 면접 모드 초기화 시작 (Hook 사용)');
      
      // Hook을 사용한 AI 경쟁 면접 시작
      const response = await startInterviewAPI(state.settings, 'new');
      
      if (response) {
        console.log('✅ AI 경쟁 면접 응답:', response);
        
        // 상태 업데이트
        setComparisonSessionId(response.comparison_session_id);
        setCurrentPhase('user_turn');
        
        // 세션 ID 업데이트
        dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
        
        // 첫 번째 질문 처리
        if (response.question) {
          const questionData = response.question as any;
          const normalizedQuestion = {
            id: questionData.question_id || `q_${Date.now()}`,
            question: questionData.question_content || questionData.question || '질문을 불러올 수 없습니다',
            category: questionData.question_type || questionData.category || '일반',
            time_limit: questionData.time_limit || 120,
            keywords: questionData.keywords || []
          };
          
          dispatch({ type: 'ADD_QUESTION', payload: normalizedQuestion });
          setTimeLeft(normalizedQuestion.time_limit || 120);
          setInterviewState('comparison_mode');
          setQuestionCount(1); // 첫 번째 질문 카운트
          
          // 첫 번째 질문을 타임라인에 직접 추가
          const firstTurn = {
            id: `interviewer_${Date.now()}`,
            type: 'interviewer' as const,
            question: normalizedQuestion.question,
            questionType: normalizedQuestion.category
          };
          
          setTimeline([firstTurn]);
        }
      }
      
    } catch (error) {
      console.error('AI 경쟁 면접 초기화 실패:', error);
      alert(`AI 경쟁 면접 시작 실패: ${handleApiError(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  // 이 함수는 더 이상 사용되지 않습니다. submitComparisonAnswer에서 AI 답변을 처리합니다.
  const processAITurnWithSessionId = async (sessionId: string) => {
    console.warn('⚠️ processAITurnWithSessionId는 더 이상 사용되지 않습니다. submitComparisonAnswer를 사용하세요.');
  };

  const processAITurn = async () => {
    console.warn('⚠️ processAITurn은 더 이상 사용되지 않습니다. submitComparisonAnswer를 사용하세요.');
  };

  const loadFirstQuestion = async () => {
    if (!state.sessionId) return;
    if (isLoading) return;
    
    if (state.questions.length > 0) {
      console.log('🚫 이미 질문이 로드됨, 중복 방지');
      return;
    }
    
    try {
      setIsLoading(true);
      console.log('📝 첫 번째 질문 로드 시작');
      const response = await interviewApi.getNextQuestion(state.sessionId);
      
      if (response.question) {
        dispatch({ type: 'ADD_QUESTION', payload: response.question });
        setTimeLeft(response.question.time_limit || 120);
        console.log('✅ 첫 번째 질문 로드 완료:', response.question.category);
        
        // 일반 모드에서도 timeline에 첫 번째 질문 추가
        if (!comparisonMode) {
          const interviewerTurn = {
            id: `interviewer_${Date.now()}`,
            type: 'interviewer' as const,
            question: response.question.question,
            questionType: response.question.category
          };
          setTimeline(prev => [...prev, interviewerTurn]);
        }
      } else if (response.completed) {
        setInterviewState('completed');
      }
    } catch (error) {
      console.error('질문 로드 실패:', error);
      const errorMessage = handleApiError(error);
      
      // 404 에러인 경우 더 친화적인 메시지 제공
      if (errorMessage.includes('404') || errorMessage.includes('찾을 수 없습니다')) {
        alert('이 면접 모드는 지원되지 않는 기능을 사용하려고 합니다. 다른 면접 모드를 선택해주세요.');
        navigate('/interview/interview-mode-selection');
      } else {
        alert(`질문 로드 실패: ${errorMessage}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const startInterview = () => {
    setInterviewState('active');
    dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'active' });
    
    setTimeout(() => {
      answerRef.current?.focus();
    }, 100);
  };

  // 팝업 버튼 핸들러들
  const handleStartWithTTS = () => {
    setShowStartPopup(false);
    
    if (comparisonMode) {
      setInterviewState('comparison_mode');
      // 비교 모드에서 첫 질문 TTS 재생
      setTimeout(() => {
        const firstQuestion = timeline.find(t => t.type === 'interviewer');
        if (firstQuestion && ttsInstance) {
          const interviewerType = mapQuestionCategoryToInterviewer(firstQuestion.questionType || '일반');
          
          // 🔍 디버깅: 첫 질문 정보 로깅
          console.log('🔍 현재 질문 디버깅 (첫 질문):', {
            'currentQuestion?.category': currentQuestion?.category,
            'firstQuestion.questionType': firstQuestion.questionType,
            'mapped interviewerType': interviewerType,
            'currentQuestion 전체': currentQuestion,
            'firstQuestion 전체': firstQuestion
          });
          
          setIsTTSActive(true);
          setTtsType('question');
          setCurrentInterviewerType(interviewerType);
          ttsInstance.speakAsInterviewer(firstQuestion.question, interviewerType)
            .then(() => {
              setIsTTSActive(false);
              setTtsType('general');
              setCurrentInterviewerType(null);
            })
            .catch(error => {
              console.error('❌ 첫 질문 TTS 재생 실패:', error);
              setIsTTSActive(false);
              setTtsType('general');
              setCurrentInterviewerType(null);
            });
        }
      }, 500);
    } else {
      setInterviewState('active');
      // 일반 모드에서 질문 TTS 재생
      setTimeout(() => {
        if (currentQuestion && ttsInstance) {
          handlePlayTTS();
        }
        answerRef.current?.focus();
      }, 500);
    }
    
    dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'active' });
  };

  const handleStartWithoutTTS = () => {
    setShowStartPopup(false);
    
    if (comparisonMode) {
      setInterviewState('comparison_mode');
    } else {
      setInterviewState('active');
      setTimeout(() => {
        answerRef.current?.focus();
      }, 100);
    }
    
    dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'active' });
  };

  const handleCancel = () => {
    setShowStartPopup(false);
    navigate('/interview/setup');
  };

  const pauseInterview = () => {
    setInterviewState('paused');
    dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'paused' });
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
  };

  const resumeInterview = () => {
    setInterviewState('active');
    dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'active' });
    answerRef.current?.focus();
  };

  const submitAnswer = async () => {
    // 🐛 디버깅: 버튼 클릭 시 상태 확인
    console.log('🔘 submitAnswer 함수 호출됨');
    console.log('📋 현재 상태:', {
      sessionId: state.sessionId,
      currentAnswer: currentAnswer?.length || 0,
      currentAnswerTrim: currentAnswer?.trim() || '',
      isLoading,
      currentPhase,
      comparisonMode,
      canAnswer,
      comparisonSessionId
    });
    
    if (!state.sessionId) return;
    
    // 답변 제출 시 STT 자동 종료
    if (isSTTActive && sttInstance) {
      console.log('🎤 답변 제출 시 STT 자동 종료');
      sttInstance.stop();
      setIsSTTActive(false);
    }
    
    if (comparisonMode) {
      await submitComparisonAnswer();
    } else {
      await submitNormalAnswer();
    }
  };

  const submitComparisonAnswer = async () => {
    // 🐛 comparisonSessionId가 없으면 state.sessionId 사용
    const sessionIdToUse = comparisonSessionId || state.sessionId;
    if (!sessionIdToUse) {
      console.error('❌ sessionId가 없음:', { comparisonSessionId, sessionId: state.sessionId });
      return;
    }
    console.log('🎯 사용할 sessionId:', sessionIdToUse);
    
    try {
      setIsLoading(true);
      
      // 사용자 답변만 타임라인에 추가 (질문은 이미 handleNextQuestion에서 추가됨)
      const userAnswer = {
        id: `user_answer_${Date.now()}`,
        type: 'user' as const,
        question: currentQuestion?.question || '질문을 불러올 수 없습니다',
        questionType: currentQuestion?.category || '일반',
        answer: currentAnswer,
        isAnswering: false
      };
      
      // 중복 방지: 같은 질문에 대한 사용자 답변이 이미 있는지 확인
      setTimeline(prev => {
        const hasExistingUserAnswer = prev.some(turn => 
          turn.type === 'user' && 
          turn.question === userAnswer.question && 
          turn.answer
        );
        
        if (hasExistingUserAnswer) {
          console.log('⚠️ 같은 질문에 대한 사용자 답변이 이미 존재함, 추가하지 않음');
          return prev;
        }
        
        return [...prev, userAnswer];
      });
      
      // 사용자 답변 제출 (새로운 통합 API 사용)
      const response = await interviewApi.processCompetitionTurn(sessionIdToUse, currentAnswer);
      
      console.log('✅ 사용자 답변 제출 완료:', response);
      setCurrentAnswer('');
      
      // 면접 완료 확인
      if (response.interview_status === 'completed') {
        console.log('🎉 면접 완료');
        setInterviewState('completed');
        return;
      }
      
      // AI 답변이 응답에 포함되어 있으므로 바로 처리
      console.log('🤖 AI 답변 및 다음 질문 처리 시작...');
      setCurrentPhase('ai_turn');
      
      try {
        // AI 답변이 있는 경우 타임라인에 추가
        if (response.ai_answer?.content) {
          const aiTurnId = `ai_${Date.now()}`;
          const aiTurn = {
            id: aiTurnId,
            type: 'ai' as const,
            question: currentQuestion?.question || '질문을 불러올 수 없습니다',
            questionType: currentQuestion?.category || '일반',
            answer: response.ai_answer.content,
            isAnswering: false,
            persona_name: '춘식이'
          };
          
          // 중복 방지: 같은 질문에 대한 AI 답변이 이미 있는지 확인
          setTimeline(prev => {
            const hasExistingAIAnswer = prev.some(turn => 
              turn.type === 'ai' && 
              turn.question === aiTurn.question && 
              turn.answer
            );
            
            if (hasExistingAIAnswer) {
              console.log('⚠️ 같은 질문에 대한 AI 답변이 이미 존재함, 추가하지 않음');
              return prev;
            }
            
            return [...prev, aiTurn];
          });
        }
        
        // AI 답변 TTS 재생 후 다음 질문으로 전환
        if (response.ai_answer?.content) {
          console.log('✅ AI 답변 및 다음 질문 수신 완룼:', response.ai_answer.content);
          
          if (ttsInstance) {
            console.log('🤖 AI 답변 TTS 재생 시작');
            setIsTTSActive(true);
            setTtsType('ai_answer');
            ttsInstance.speakAsAICandidate(response.ai_answer.content)
              .then(() => {
                console.log('✅ AI 답변 TTS 재생 완료');
                setIsTTSActive(false);
                setTtsType('general');
                // TTS 완료 후 1초 딜레이를 두고 다음 질문으로 전환
                setTimeout(() => {
                  handleNextQuestion(response);
                }, 1000);
              })
              .catch(error => {
                console.error('❌ AI 답변 TTS 재생 실패:', error);
                setIsTTSActive(false);
                setTtsType('general');
                // TTS 실패 시에도 다음 질문으로 전환
                handleNextQuestion(response);
              });
          } else {
            // TTS 인스턴스가 없으면 바로 다음 질문으로 전환
            handleNextQuestion(response);
          }
          
        } else {
          console.error('❌ AI 답변이 응답에 포함되지 않음');
          // AI 답변이 없어도 다음 질문으로 진행
          handleNextQuestion(response);
        }
        
      } catch (error) {
        console.error('❌ AI 답변 생성 중 오류:', error);
        handleNextQuestion(response);
      }
      
    } catch (error) {
      console.error('답변 제출 실패:', error);
      alert(`답변 제출 실패: ${handleApiError(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  // 다음 질문 처리 함수 (첫 번째 질문 포함)
  const handleNextQuestion = (response: any) => {
    console.log('🔍 handleNextQuestion 응답 구조:', response);
    const nextQuestionData = response.next_user_question || response.next_question;
    console.log('🎯 추출된 다음 질문 데이터:', nextQuestionData);
    
    if (nextQuestionData) {
      // 백엔드의 is_final 플래그 또는 interview_status로 면접 종료 여부 결정
      if (nextQuestionData.is_final || response.interview_status === 'completed') {
        console.log('🎉 백엔드에서 면접 완료 신호 - 면접 종료');
        setInterviewState('completed');
        return;
      }
      
      const nextQuestionCount = questionCount + 1;
      console.log(`📊 질문 개수: ${questionCount} → ${nextQuestionCount} (백엔드에서 관리)`);
      console.log('🎯 다음 질문으로 이동:', nextQuestionData);
      
      // 타입 안전성을 위해 any로 캐스팅
      const questionData = nextQuestionData as any;
      
      // 면접관이 질문을 제시하는 방식 (InterviewerService 구조에 맞게)
      const interviewerTurn = {
        id: `interviewer_${Date.now()}`,
        type: 'interviewer' as const,
        question: questionData.question || '질문을 불러올 수 없습니다',
        questionType: questionData.interviewer_type || '일반'
      };
      
      // 서버 응답을 프론트엔드 형식으로 변환 (InterviewerService 구조에 맞게)
      const normalizedNextQuestion = {
        id: questionData.question_id || `q_${Date.now()}`,
        question: questionData.question || '질문을 불러올 수 없습니다',
        category: questionData.interviewer_type || '일반',
        time_limit: questionData.time_limit || 120,
        keywords: questionData.keywords || [],
        intent: questionData.intent || ''
      };
      
      // 중복 방지: 같은 질문이 이미 타임라인에 있는지 확인 (비교 모드와 일반 모드 모두)
      setTimeline(prev => {
        const hasExistingQuestion = prev.some(turn => 
          turn.question === interviewerTurn.question
        );
        
        if (hasExistingQuestion) {
          console.log('⚠️ 같은 질문이 이미 타임라인에 존재함, 추가하지 않음');
          return prev;
        }
        
        return [...prev, interviewerTurn];
      });
      dispatch({ type: 'ADD_QUESTION', payload: normalizedNextQuestion });
      setTimeLeft(questionData.time_limit || 120);
      setCurrentPhase('user_turn');
      setInterviewState('active');
      setQuestionCount(nextQuestionCount); // 질문 개수 증가
      
      // 새 질문에 대한 자동 TTS 재생 (1초 딜레이로 조정)
      setTimeout(() => {
        if (ttsInstance) {
          const interviewerType = mapQuestionCategoryToInterviewer(interviewerTurn.questionType || '일반');
          
          // 🔍 디버깅: 현재 질문 정보 전체 로깅
          console.log('🔍 현재 질문 디버깅 (새 질문):', {
            'currentQuestion?.category': currentQuestion?.category,
            'interviewerTurn.questionType': interviewerTurn.questionType,
            'mapped interviewerType': interviewerType,
            'currentQuestion 전체': currentQuestion,
            'interviewerTurn 전체': interviewerTurn
          });
          
          console.log('🔊 새 질문 자동 TTS 재생:', interviewerTurn.question.substring(0, 50));
          setIsTTSActive(true);
          setTtsType('question');
          setCurrentInterviewerType(interviewerType);
          ttsInstance.speakAsInterviewer(interviewerTurn.question, interviewerType)
            .then(() => {
              console.log('✅ 새 질문 TTS 재생 완료');
              setIsTTSActive(false);
              setTtsType('general');
              setCurrentInterviewerType(null);
            })
            .catch(error => {
              console.error('❌ 새 질문 TTS 재생 실패:', error);
              setIsTTSActive(false);
              setTtsType('general');
              setCurrentInterviewerType(null);
            });
        }
      }, 1000);
      
    } else {
      // 다음 질문이 없으면 면접 완료
      console.log('🎉 모든 질문 완료');
      setInterviewState('completed');
    }
  };

  const submitNormalAnswer = async () => {
    if (!state.sessionId) return;
    
    const currentQuestion = state.questions[state.currentQuestionIndex];
    if (!currentQuestion) return;

    try {
      setIsLoading(true);
      
      // 일반 모드에서도 사용자 답변을 timeline에 추가
      const userAnswer = {
        id: `user_answer_${Date.now()}`,
        type: 'user' as const,
        question: currentQuestion.question,
        questionType: currentQuestion.category,
        answer: currentAnswer,
        isAnswering: false
      };
      
      // 중복 방지: 같은 질문에 대한 사용자 답변이 이미 있는지 확인
      setTimeline(prev => {
        const hasExistingUserAnswer = prev.some(turn => 
          turn.type === 'user' && 
          turn.question === userAnswer.question && 
          turn.answer
        );
        
        if (hasExistingUserAnswer) {
          console.log('⚠️ 같은 질문에 대한 사용자 답변이 이미 존재함, 추가하지 않음');
          return prev;
        }
        
        return [...prev, userAnswer];
      });
      
      const answerData = {
        session_id: state.sessionId,
        question_id: currentQuestion.id,
        answer: currentAnswer,
        time_spent: (currentQuestion.time_limit || 120) - timeLeft
      };

      await interviewApi.submitAnswer(answerData);
      dispatch({ type: 'ADD_ANSWER', payload: answerData });
      setCurrentAnswer('');
      
      // AI 경쟁 모드인 경우 AI 답변 생성
      if (state.settings?.mode === 'ai_competition' && state.sessionId) {
        try {
          const aiResponse = await interviewApi.getAIAnswer(state.sessionId, currentQuestion.id);
          
          dispatch({ 
            type: 'ADD_AI_ANSWER', 
            payload: {
              question_id: currentQuestion.id,
              answer: aiResponse.answer,
              score: aiResponse.score,
              persona_name: aiResponse.persona_name,
              time_spent: aiResponse.time_spent
            }
          });
          
          setInterviewState('ai_answering');
          
          setTimeout(() => {
            proceedToNextQuestion();
          }, 3000);
        } catch (aiError) {
          console.error('AI 답변 생성 실패:', aiError);
          proceedToNextQuestion();
        }
      } else {
        proceedToNextQuestion();
      }
      
    } catch (error) {
      console.error('답변 제출 실패:', error);
      alert(`답변 제출 실패: ${handleApiError(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const proceedToNextQuestion = async () => {
    if (!state.sessionId) return;
    
    try {
      const nextResponse = await interviewApi.getNextQuestion(state.sessionId);
      
      if (nextResponse.question) {
        dispatch({ type: 'ADD_QUESTION', payload: nextResponse.question });
        dispatch({ type: 'SET_CURRENT_QUESTION_INDEX', payload: state.currentQuestionIndex + 1 });
        setTimeLeft(nextResponse.question.time_limit || 120);
        setInterviewState('active');
        
        setTimeout(() => {
          answerRef.current?.focus();
        }, 100);
      } else if (nextResponse.completed) {
        completeInterview();
      }
    } catch (error) {
      console.error('다음 질문 로드 실패:', error);
      alert(`다음 질문 로드 실패: ${handleApiError(error)}`);
    }
  };

  const completeInterview = () => {
    setInterviewState('completed');
    dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'completed' });
    
    setTimeout(() => {
      if (state.sessionId) {
        navigate(`/interview/results/${state.sessionId}`);
      } else {
        navigate('/interview/results');
      }
    }, 3000);
  };

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getTimerColor = (): string => {
    if (timeLeft > 60) return 'text-green-600';
    if (timeLeft > 30) return 'text-yellow-600';
    return 'text-red-600';
  };

  const progress = state.questions.length > 0 
    ? ((state.currentQuestionIndex + 1) / state.questions.length) * 100 
    : 0;

  // 면접 시작 팝업 컴포넌트
  const renderStartPopup = () => {
    if (!showStartPopup) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 p-8 transform transition-all duration-300">
          <div className="text-center">
            {/* 아이콘 */}
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="text-3xl">🎤</span>
            </div>
            
            {/* 제목 */}
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              면접을 시작하시겠습니까?
            </h2>
            
            {/* 면접 정보 */}
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <p className="text-lg font-semibold text-gray-800">
                {state.settings?.company || '쿠팡'} - {state.settings?.position || '개발자'}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {comparisonMode ? 'AI 경쟁 면접' : '일반 면접'}이 준비되었습니다.
              </p>
            </div>
            
            {/* 버튼들 */}
            <div className="space-y-4">
              <button
                onClick={() => handleStartWithTTS()}
                className="w-full py-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 text-lg"
              >
                <span>🔊</span>
                질문 듣고 시작하기
              </button>
              
              <button
                onClick={() => handleCancel()}
                className="w-full py-3 text-gray-600 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 질문 모달 컴포넌트
  const renderQuestionModal = () => {
    const questionToShow = modalQuestion || currentQuestion;
    if (!showQuestionModal || !questionToShow) return null;

    const getInterviewerInfo = (category: string) => {
      if (category === '자기소개' || category === '지원동기' || category === 'HR' || category === '인사') {
        return { icon: '👔', name: '인사 면접관', color: 'blue' };
      } else if (category === '협업' || category === 'COLLABORATION') {
        return { icon: '🤝', name: '협업 면접관', color: 'green' };
      } else if (category === '기술' || category === 'TECH') {
        return { icon: '💻', name: '기술 면접관', color: 'purple' };
      } else {
        return { icon: '❓', name: '면접관', color: 'gray' };
      }
    };

    const interviewer = getInterviewerInfo(questionToShow.category || '일반');

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden transform transition-all duration-300">
          {/* 헤더 */}
          <div className={`p-6 border-b border-gray-200 bg-${interviewer.color}-50`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className={`w-12 h-12 bg-${interviewer.color}-100 rounded-full flex items-center justify-center mr-4`}>
                  <span className="text-2xl">{interviewer.icon}</span>
                </div>
                <div>
                  <h2 className={`text-xl font-bold text-${interviewer.color}-900`}>
                    {interviewer.name}
                  </h2>
                  <p className={`text-sm text-${interviewer.color}-700`}>
                    {questionToShow.category || '일반'} 질문
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowQuestionModal(false);
                  setModalQuestion(null);
                }}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
          </div>

          {/* 질문 내용 */}
          <div className="p-6 overflow-y-auto max-h-60">
            <div className="text-lg text-gray-900 leading-relaxed">
              {questionToShow.question}
            </div>
            
            {/* 키워드 힌트 (있는 경우) */}
            {questionToShow.keywords && questionToShow.keywords.length > 0 && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <p className="text-sm font-medium text-gray-700 mb-2">💡 키워드 힌트:</p>
                <div className="flex flex-wrap gap-2">
                  {questionToShow.keywords.map((keyword: string, index: number) => (
                    <span
                      key={index}
                      className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 액션 버튼들 */}
          <div className="p-6 bg-gray-50 border-t border-gray-200">
            <div className="flex gap-3">
              <button
                onClick={handlePlayTTS}
                disabled={isTTSActive}
                className={`flex-1 py-3 px-4 bg-${interviewer.color}-600 text-white rounded-lg font-medium hover:bg-${interviewer.color}-700 transition-colors flex items-center justify-center gap-2 disabled:bg-gray-400`}
              >
                <span>{isTTSActive ? '🔊' : '🎵'}</span>
                {isTTSActive ? '재생 중...' : '질문 듣기'}
              </button>
              <button
                onClick={() => {
                  setShowQuestionModal(false);
                  setModalQuestion(null);
                }}
                className="flex-1 py-3 px-4 bg-gray-600 text-white rounded-lg font-medium hover:bg-gray-700 transition-colors"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Ready State
  if (interviewState === 'ready') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title={`${state.settings?.company || '쿠팡'} 면접`}
          subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
        />
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <div className="mb-8">
              <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h1 className="text-3xl font-bold text-gray-900 mb-4">면접 준비 완료</h1>
              <p className="text-lg text-gray-600">
                {comparisonMode ? '춘식이와의 경쟁 면접' : '일반 면접'}이 곧 시작됩니다.
              </p>
            </div>

            <div className="mb-8 p-6 bg-gray-50 rounded-xl">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">면접 정보</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">회사:</span>
                  <span className="ml-2 font-medium">{state.settings?.company}</span>
                </div>
                <div>
                  <span className="text-gray-500">직군:</span>
                  <span className="ml-2 font-medium">{state.settings?.position}</span>
                </div>
                <div>
                  <span className="text-gray-500">모드:</span>
                  <span className="ml-2 font-medium">
                    {comparisonMode ? 'AI 경쟁 면접' : '일반 면접'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">난이도:</span>
                  <span className="ml-2 font-medium">{state.settings?.difficulty}</span>
                </div>
              </div>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
                <span className="ml-3 text-gray-600">
                  {state.sessionId ? '면접 준비 중...' : '면접 재시작 중...'}
                </span>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-gray-600 mb-6">
                  준비가 되었으면 아래 버튼을 클릭해 면접을 시작하세요.
                </p>
                <button
                  onClick={() => setShowStartPopup(true)}
                  className="px-8 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
                >
                  면접 시작
                </button>
              </div>
            )}
          </div>
        </div>
        
        {/* 면접 시작 팝업 */}
        {renderStartPopup()}
        
        {/* 질문 모달 */}
        {renderQuestionModal()}
      </div>
    );
  }

  // Paused State
  if (interviewState === 'paused') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title={`${state.settings?.company || '쿠팡'} 면접`}
          subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
        />
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <div className="w-20 h-20 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">면접 일시정지</h1>
            <p className="text-lg text-gray-600 mb-8">
              면접이 일시정지되었습니다. 준비가 되면 계속 진행하세요.
            </p>
            <button
              onClick={resumeInterview}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              면접 재개
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Completed State
  if (interviewState === 'completed') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title={`${state.settings?.company || '쿠팡'} 면접`}
          subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
        />
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">면접 완료!</h1>
            <p className="text-lg text-gray-600 mb-8">
              수고하셨습니다. 곧 결과 페이지로 이동합니다.
            </p>
            <div className="flex items-center justify-center">
              <LoadingSpinner />
              <span className="ml-3 text-gray-600">결과 분석 중...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Comparison Mode State - 화상회의 스타일
  
  if (comparisonMode && hasInitialized) {
    return (
      <div className="min-h-screen bg-black">
        {/* 면접 시작 팝업 */}
        {renderStartPopup()}
        {/* 상단 면접관 3명 */}
        <div className="grid grid-cols-3 gap-4 p-4" style={{ height: '40vh' }}>
          {/* 인사 면접관 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // TTS 재생 중이고 인사 면접관일 때
            isTTSActive && currentInterviewerType === 'hr'
              ? 'border-blue-500 shadow-lg shadow-blue-500/50 animate-pulse'
            // 기본 상태
            : 'border-gray-700'
          }`}>
            <div className={`absolute top-4 left-4 font-semibold ${
              isTTSActive && currentInterviewerType === 'hr'
                ? 'text-blue-400' 
                : 'text-white'
            }`}>
              👔 인사 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_1.jpg"
                alt="인사 면접관"
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-4 left-4">
                <div className={`w-4 h-4 rounded-full animate-pulse ${
                  currentQuestion?.category === '자기소개' || currentQuestion?.category === '지원동기' || currentQuestion?.category === 'HR' || currentQuestion?.category === '인사'
                    ? 'bg-blue-500' 
                    : 'bg-red-500'
                }`}></div>
              </div>
              {/* 질문 중 표시 */}
              {(currentQuestion?.category === '자기소개' || currentQuestion?.category === '지원동기' || currentQuestion?.category === 'HR' || currentQuestion?.category === '인사') && (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-blue-400 font-semibold">
                  🎤 질문 중
                </div>
              )}
            </div>
          </div>

          {/* 협업 면접관 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // TTS 재생 중이고 협업 면접관일 때
            isTTSActive && currentInterviewerType === 'collaboration'
              ? 'border-green-500 shadow-lg shadow-green-500/50 animate-pulse'
            // 기본 상태
            : 'border-gray-700'
          }`}>
            <div className={`absolute top-4 left-4 font-semibold ${
              isTTSActive && currentInterviewerType === 'collaboration'
                ? 'text-green-400' 
                : 'text-white'
            }`}>
              🤝 협업 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_2.jpg"
                alt="협업 면접관"
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-4 left-4">
                <div className={`w-4 h-4 rounded-full animate-pulse ${
                  currentQuestion?.category === '협업' || currentQuestion?.category === 'COLLABORATION'
                    ? 'bg-green-500' 
                    : 'bg-red-500'
                }`}></div>
              </div>
              {/* 질문 중 표시 */}
              {(currentQuestion?.category === '협업' || currentQuestion?.category === 'COLLABORATION') && (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-green-400 font-semibold">
                  🎤 질문 중
                </div>
              )}
            </div>
          </div>

          {/* 기술 면접관 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // TTS 재생 중이고 기술 면접관일 때
            isTTSActive && currentInterviewerType === 'tech'
              ? 'border-purple-500 shadow-lg shadow-purple-500/50 animate-pulse'
            // 기본 상태
            : 'border-gray-700'
          }`}>
            <div className={`absolute top-4 left-4 font-semibold ${
              isTTSActive && currentInterviewerType === 'tech'
                ? 'text-purple-400' 
                : 'text-white'
            }`}>
              💻 기술 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_3.jpg"
                alt="기술 면접관"
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-4 left-4">
                <div className={`w-4 h-4 rounded-full animate-pulse ${
                  currentQuestion?.category === '기술' || currentQuestion?.category === 'TECH'
                    ? 'bg-purple-500' 
                    : 'bg-red-500'
                }`}></div>
              </div>
              {/* 질문 중 표시 */}
              {(currentQuestion?.category === '기술' || currentQuestion?.category === 'TECH') && (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-purple-400 font-semibold">
                  🎤 질문 중
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 하단 영역 */}
        <div className="grid gap-4 p-4" style={{ height: '60vh', gridTemplateColumns: '2fr 1fr 2fr' }}>
          {/* 사용자 영역 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // STT 활성화 시 (사용자가 말하는 중)
            isSTTActive
              ? 'border-red-500 shadow-lg shadow-red-500/50 animate-pulse'
            // 사용자 차례이지만 말하지 않는 중
            : currentPhase === 'user_turn'
              ? 'border-yellow-500 shadow-lg shadow-yellow-500/50'
            // 대기 상태
            : 'border-gray-600'
          }`}>
            <div className="absolute top-4 left-4 text-yellow-400 font-semibold z-10">
              사용자: {state.settings?.candidate_name || 'You'}
            </div>
            
            {/* 실제 사용자 비디오 - 항상 렌더링 */}
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
              style={{ transform: 'scaleX(-1)' }}
            />
            
            {/* 📹 카메라 연결 상태 오버레이 */}
            {!state.cameraStream && (
              <div className="absolute inset-0 h-full flex items-center justify-center bg-gray-800">
                <div className="text-white text-lg opacity-50">
                  {isStreamCreating ? '카메라 연결 중...' : '카메라 대기 중...'}
                </div>
              </div>
            )}
            
            {/* 📹 스트림 에러 표시 */}
            {streamError && (
              <div className="absolute inset-0 h-full flex flex-col items-center justify-center bg-red-900 bg-opacity-80">
                <div className="text-white text-center p-4">
                  <div className="text-lg font-semibold mb-2">📹 카메라 오류</div>
                  <div className="text-sm mb-4">{streamError}</div>
                  <button
                    onClick={() => {
                      setStreamError(null);
                      createNewStream();
                    }}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    다시 시도
                  </button>
                </div>
              </div>
            )}
            
            {/* 📹 스트림 생성 중 표시 */}
            {isStreamCreating && (
              <div className="absolute inset-0 h-full flex items-center justify-center bg-blue-900 bg-opacity-50">
                <div className="text-white text-center">
                  <div className="animate-spin w-8 h-8 border-4 border-white border-t-transparent rounded-full mx-auto mb-2"></div>
                  <div className="text-sm">카메라 연결 중...</div>
                </div>
              </div>
            )}
            
            {/* 라이브 표시 */}
            <div className="absolute top-4 right-4 bg-red-500 text-white px-2 py-1 rounded text-xs font-medium z-10">
              LIVE
            </div>

            {/* 답변 입력 오버레이 (사용자 턴일 때만) */}
            {currentPhase === 'user_turn' && (
              <div className="absolute bottom-0 left-0 right-0 bg-black/80 p-4">
                <textarea
                  ref={answerRef}
                  value={currentAnswer}
                  readOnly={true}
                  className="w-full h-20 p-2 bg-gray-800 text-white border border-gray-600 rounded-lg resize-none text-sm cursor-not-allowed"
                  placeholder="🎤 음성으로 답변해주세요. 마이크 버튼을 눌러 시작하세요."
                />
                <div className="flex items-center justify-between mt-2">
                  <div className="text-gray-400 text-xs">{currentAnswer.length}자</div>
                  <div className={`text-lg font-bold ${getTimerColor()}`}>
                    {formatTime(timeLeft)}
                  </div>
                </div>
              </div>
            )}
            
            {/* 대기 중 오버레이 */}
            {currentPhase === 'ai_turn' && (
              <div className="absolute bottom-0 left-0 right-0 bg-black/80 p-4 text-center">
                <div className="text-white opacity-75">대기 중...</div>
                <div className="text-xs text-gray-400 mt-1">AI 차례입니다</div>
              </div>
            )}
          </div>

          {/* 중앙 컨트롤 */}
          <div className="bg-gray-800 rounded-lg p-6 flex flex-col justify-center">
            {/* 현재 질문 표시 */}
            <div className="text-center mb-6">
              <div className="text-gray-400 text-sm mb-2">현재 질문</div>
              {currentQuestion ? (
                <>
                  <div className={`text-sm font-semibold mb-2 ${
                    currentQuestion.category === '자기소개' || currentQuestion.category === '지원동기' || currentQuestion.category === 'HR' || currentQuestion.category === '인사'
                      ? 'text-blue-400' 
                      : currentQuestion.category === '협업' || currentQuestion.category === 'COLLABORATION'
                      ? 'text-green-400'
                      : currentQuestion.category === '기술' || currentQuestion.category === 'TECH'
                      ? 'text-purple-400'
                      : 'text-gray-400'
                  }`}>
                    {currentQuestion.category === '자기소개' || currentQuestion.category === '지원동기' || currentQuestion.category === 'HR' || currentQuestion.category === '인사'
                      ? '👔 인사 면접관' 
                      : currentQuestion.category === '협업' || currentQuestion.category === 'COLLABORATION'
                      ? '🤝 협업 면접관'
                      : currentQuestion.category === '기술' || currentQuestion.category === 'TECH'
                      ? '💻 기술 면접관'
                      : '❓ 면접관'
                    }
                  </div>
                  <div className="text-white text-base leading-relaxed line-clamp-2 mb-3">
                    {currentQuestion.question && currentQuestion.question.length > 60 
                      ? `${currentQuestion.question.substring(0, 60)}...` 
                      : currentQuestion.question
                    }
                  </div>
                  <button
                    onClick={() => setShowQuestionModal(true)}
                    className="px-3 py-1 bg-white/20 hover:bg-white/30 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    📋 전체 질문 보기
                  </button>
                </>
              ) : (
                <div className="text-gray-500">질문을 불러오는 중...</div>
              )}
            </div>

            {/* 음성 컨트롤 */}
            <div className="mb-4">
              <VoiceControls
                onStartSTT={handleStartSTT}
                onStopSTT={handleStopSTT}
                onPlayTTS={handlePlayTTS}
                onStopTTS={handleStopTTS}
                isSTTActive={isSTTActive}
                isTTSActive={isTTSActive}
                disabled={currentPhase !== 'user_turn' && currentPhase !== 'interviewer_question'}
                className="justify-center"
              />
            </div>

            {/* 음성 상태 표시 */}
            {(isSTTActive || isTTSActive || interimText) && (
              <div className="mb-4">
                <SpeechIndicator
                  isListening={isSTTActive}
                  isSpeaking={isTTSActive}
                  interimText={interimText}
                />
              </div>
            )}

            {/* 컨트롤 버튼 */}
            <div className="space-y-3">
              {(() => {
                const hasAnswer = !!currentAnswer.trim();
                const isValidPhase = (currentPhase === 'user_turn' || currentPhase === 'interviewer_question');
                const isButtonDisabled = !hasAnswer || isLoading || !isValidPhase;
                
                // 🐛 디버깅: 버튼 상태 로깅
                console.log('🔘 버튼 상태 체크 (첫 번째 버튼):', {
                  hasAnswer,
                  isLoading,
                  currentPhase,
                  isValidPhase,
                  isButtonDisabled,
                  currentAnswerLength: currentAnswer?.length || 0
                });
                
                return (
                  <button 
                    className="w-full py-3 bg-green-600 text-white rounded-lg hover:bg-green-500 transition-colors font-semibold"
                    onClick={submitAnswer}
                    disabled={isButtonDisabled}
                  >
                    {isLoading ? '제출 중...' : currentPhase === 'user_turn' ? '🚀 답변 제출' : '대기 중...'}
                  </button>
                );
              })()}
            </div>

            {/* 진행 상황 */}
            <div className="mt-4 text-center">
              <div className="text-white text-sm mb-2">
                진행상황: {timeline.filter(t => t.answer).length} / {timeline.length}
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div 
                  className="bg-yellow-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${timeline.length > 0 ? (timeline.filter(t => t.answer).length / timeline.length) * 100 : 0}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* AI 지원자 춘식이 */}
          <div className={`bg-blue-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // AI 답변 TTS 재생 중일 때
            isTTSActive && ttsType === 'ai_answer'
              ? 'border-orange-500 shadow-lg shadow-orange-500/50 animate-pulse'
            // AI가 답변 생성 중일 때
            : currentPhase === 'ai_turn'
              ? 'border-green-500 shadow-lg shadow-green-500/50 animate-pulse'
            // 대기 상태
            : 'border-gray-600'
          }`}>
            <div className="absolute top-4 left-4 text-green-400 font-semibold z-10">
              AI 지원자 {getAICandidateName(state.aiSettings?.aiQualityLevel || 6)}
            </div>
            
            {/* AI 지원자 전체 이미지 */}
            <div className="h-full flex items-center justify-center relative">
              <img 
                src={getAICandidateImage(state.aiSettings?.aiQualityLevel || 6)}
                alt={getAICandidateName(state.aiSettings?.aiQualityLevel || 6)}
                className="w-full h-full object-cover"
              />
              
              {/* 상태 표시 오버레이 */}
              {currentPhase === 'ai_turn' ? (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center bg-black/70 rounded-lg p-4">
                  <div className="text-green-400 text-sm font-semibold mb-2">답변 중...</div>
                  <div className="w-6 h-6 border-2 border-green-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
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

        {/* 질문 모달 */}
        {renderQuestionModal()}
      </div>
    );
  }

  // Loading state for normal mode
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title={`${state.settings?.company || '쿠팡'} 면접`}
          subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
        />
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <LoadingSpinner />
            <p className="mt-4 text-gray-600">질문을 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  // Active Interview State
  if (!currentQuestion && !comparisonMode) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title={`${state.settings?.company || '쿠팡'} 면접`}
          subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
        />
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <p className="text-gray-600">질문을 불러올 수 없습니다.</p>
            <button
              onClick={() => navigate('/interview/setup')}
              className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              설정으로 돌아가기
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title={`${state.settings?.company || '쿠팡'} 면접`}
        subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
      />
      
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between items-center text-sm text-gray-600 mb-2">
            <span>질문 {state.currentQuestionIndex + 1} / {state.questions.length}</span>
            <span>{Math.round(progress)}% 완료</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        {/* 면접 진행 히스토리 (모든 모드) */}
        {timeline.length > 0 && (
          <div className="bg-white rounded-2xl shadow-xl mb-6">
            <div 
              className="p-4 cursor-pointer flex items-center justify-between hover:bg-gray-50 transition-colors rounded-t-2xl border-b"
              onClick={() => setShowHistory(!showHistory)}
            >
              <h3 className="text-lg font-bold text-gray-900 flex items-center">
                📋 면접 진행 히스토리 
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({timeline.filter(t => t.answer).length} / {timeline.length})
                </span>
              </h3>
              <span className="text-gray-500">
                {showHistory ? '▲' : '▼'}
              </span>
            </div>
            {showHistory && (
              <div className="p-6 pt-0">
                <div className="max-h-96 overflow-y-auto space-y-4 mt-4">
                  {timeline.map((turn, index) => (
                    <div 
                      key={turn.id} 
                      className={`p-4 rounded-lg border-l-4 ${
                        turn.type === 'user' 
                          ? 'bg-blue-50 border-blue-400' 
                          : turn.type === 'interviewer'
                          ? 'bg-purple-50 border-purple-400'
                          : 'bg-green-50 border-green-400'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-sm">
                          {turn.type === 'user' 
                            ? `👤 ${state.settings?.candidate_name || '사용자'}` 
                            : turn.type === 'interviewer'
                            ? '👔 면접관'
                            : '🤖 춘식이'
                          } - {turn.questionType}
                        </span>
                        <span className="text-xs text-gray-500">#{index + 1}</span>
                      </div>
                      <div 
                        className="mb-2 text-sm font-medium text-gray-700 cursor-pointer hover:text-blue-600 transition-colors"
                        onClick={() => {
                          // 임시로 질문 정보를 설정하여 모달 표시
                          const tempQuestion = {
                            id: turn.id,
                            question: turn.question,
                            category: turn.questionType || '일반',
                            time_limit: 120,
                            keywords: []
                          };
                          setModalQuestion(tempQuestion);
                          setShowQuestionModal(true);
                        }}
                      >
                        ❓ {turn.question.length > 100 ? `${turn.question.substring(0, 100)}...` : turn.question}
                      </div>
                      {turn.answer ? (
                        <div className="text-sm text-gray-600">
                          💬 {turn.answer}
                        </div>
                      ) : turn.isAnswering ? (
                        <div className="text-sm text-gray-500 italic">
                          ⏳ 답변 생성 중...
                        </div>
                      ) : (
                        <div className="text-sm text-gray-400">
                          ⏸️ 답변 대기중
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          {/* Question Section */}
          <div className="p-8 border-b border-gray-200">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center mr-4 ${
                  comparisonMode 
                    ? (currentPhase === 'user_turn' ? 'bg-blue-100' : 'bg-green-100')
                    : 'bg-blue-100'
                }`}>
                  <span className={`font-bold ${
                    comparisonMode 
                      ? (currentPhase === 'user_turn' ? 'text-blue-600' : 'text-green-600')
                      : 'text-blue-600'
                  }`}>
                    {comparisonMode 
                      ? (currentPhase === 'user_turn' ? '👤' : '🤖')
                      : `Q${state.currentQuestionIndex + 1}`
                    }
                  </span>
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    {comparisonMode 
                      ? (currentPhase === 'user_turn' 
                          ? `${state.settings?.candidate_name || '사용자'}님의 차례` 
                          : '춘식이의 차례'
                        )
                      : `${currentQuestion?.category || '일반'} 질문`
                    }
                  </h2>
                  <p className="text-gray-600">
                    {comparisonMode 
                      ? `${currentQuestion?.category || '일반'} 질문 - ${currentPhase === 'user_turn' ? '신중하게 답변해주세요' : 'AI가 답변 중입니다'}`
                      : '신중하게 답변해주세요'
                    }
                  </p>
                </div>
              </div>
              <div className={`text-3xl font-bold ${getTimerColor()}`}>
                {comparisonMode && currentPhase === 'ai_turn' ? '⏳' : formatTime(timeLeft)}
              </div>
            </div>
            
            <div className="bg-gray-50 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1 pr-4">
                  <p className="text-lg text-gray-900 leading-relaxed line-clamp-2">
                    {currentQuestion?.question && currentQuestion.question.length > 80 
                      ? `${currentQuestion.question.substring(0, 80)}...` 
                      : currentQuestion?.question
                    }
                  </p>
                </div>
                <button
                  onClick={() => setShowQuestionModal(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2 whitespace-nowrap"
                >
                  <span>📋</span>
                  질문 보기
                </button>
              </div>
            </div>
          </div>

          {/* Answer Section */}
          <div className="p-8">
            {comparisonMode && currentPhase === 'ai_turn' ? (
              /* AI 답변 중 표시 */
              <div className="text-center py-8">
                <div className="animate-pulse">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-2xl">🤖</span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">춘식이가 답변 중입니다</h3>
                  <p className="text-gray-600">잠시만 기다려주세요...</p>

                </div>
              </div>
            ) : (
              /* 사용자 답변 입력 */
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="answer" className="block text-sm font-medium text-gray-700">
                    {comparisonMode 
                      ? `${state.settings?.candidate_name || '사용자'}님의 답변을 입력해주세요 (최소 50자 이상 권장)`
                      : '답변을 입력해주세요 (최소 50자 이상 권장)'
                    }
                  </label>
                  
                </div>

                {/* 음성 컨트롤 */}
                <div className="mb-3">
                  <VoiceControls
                    onStartSTT={handleStartSTT}
                    onStopSTT={handleStopSTT}
                    onPlayTTS={handlePlayTTS}
                    onStopTTS={handleStopTTS}
                    isSTTActive={isSTTActive}
                    isTTSActive={isTTSActive}
                    disabled={comparisonMode && (currentPhase !== 'user_turn' && currentPhase !== 'interviewer_question')}
                  />
                </div>

                {/* 음성 상태 표시 */}
                {(isSTTActive || isTTSActive || interimText) && (
                  <div className="mb-3">
                    <SpeechIndicator
                      isListening={isSTTActive}
                      isSpeaking={isTTSActive}
                      interimText={interimText}
                      speakingType={ttsType}
                    />
                  </div>
                )}

                <textarea
                  ref={answerRef}
                  id="answer"
                  value={currentAnswer}
                  readOnly={true}
                  disabled={comparisonMode && (!canAnswer || currentPhase === 'ai_turn')}
                  className={`w-full h-64 p-4 border border-gray-300 rounded-lg resize-none cursor-not-allowed ${
                    comparisonMode && (!canAnswer || currentPhase === 'ai_turn') ? 'bg-gray-100' : 'bg-gray-50'
                  }`}
                  placeholder={comparisonMode 
                    ? "🎤 춘식이와 경쟁하세요! 음성으로 답변해주세요. 마이크 버튼을 눌러 시작하세요."
                    : "🎤 음성으로 답변해주세요. 마이크 버튼을 눌러 시작하세요."
                  }
                />
                <div className="mt-2 text-sm text-gray-500">
                  {currentAnswer.length}자 입력됨
                </div>
              </div>
            )}

            {comparisonMode && currentPhase === 'ai_turn' ? (
              /* AI 턴일 때는 버튼 없음 */
              null
            ) : (
              /* 사용자 턴일 때 답변 제출 버튼 */
              <div className="flex justify-end">
                {(() => {
                  const hasAnswer = !!currentAnswer.trim();
                  const isValidPhase = (currentPhase === 'user_turn' || currentPhase === 'interviewer_question');
                  const canAnswerCondition = comparisonMode ? canAnswer : true;
                  const isButtonDisabled = !hasAnswer || isLoading || (comparisonMode && (!canAnswerCondition || !isValidPhase));
                  
                  // 🐛 디버깅: 버튼 상태 로깅
                  console.log('🔘 버튼 상태 체크 (두 번째 버튼):', {
                    hasAnswer,
                    isLoading,
                    currentPhase,
                    isValidPhase,
                    comparisonMode,
                    canAnswer,
                    canAnswerCondition,
                    isButtonDisabled,
                    currentAnswerLength: currentAnswer?.length || 0
                  });
                  
                  return (
                    <button
                      onClick={submitAnswer}
                      disabled={isButtonDisabled}
                      className={`px-8 py-3 text-white rounded-lg font-medium transition-colors ${
                        comparisonMode 
                          ? 'bg-green-600 hover:bg-green-700' 
                          : 'bg-blue-600 hover:bg-blue-700'
                      } disabled:bg-gray-400 disabled:cursor-not-allowed`}
                    >
                      {isLoading 
                        ? '제출 중...' 
                        : comparisonMode 
                          ? (currentPhase === 'interviewer_question' ? '💬 답변 제출' : '🏃‍♂️ 춘식이와 경쟁!')
                          : '답변 제출'
                      }
                    </button>
                  );
                })()}
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* 질문 모달 */}
      {renderQuestionModal()}
    </div>
  );
};

export default InterviewActive;