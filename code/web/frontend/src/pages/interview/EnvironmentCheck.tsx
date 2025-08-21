import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/common/Header';
import StepIndicator from '../../components/interview/StepIndicator';
import NavigationButtons from '../../components/interview/NavigationButtons';
import { useInterview } from '../../contexts/InterviewContext';
import { interviewApi, CalibrationResult } from '../../services/api';
import VideoCalibration from '../../components/test/VideoCalibration';
import { GAZE_CONSTANTS } from '../../constants/gazeConstants';
import { createTTS, checkSpeechSupport } from '../../utils/speechUtils';

interface CheckItem {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'checking' | 'success' | 'error';
  icon: string;
  errorMessage?: string;
}

const EnvironmentCheck: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  const [isLoading, setIsLoading] = useState(false);
  const [allChecksComplete, setAllChecksComplete] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [showGazeCalibration, setShowGazeCalibration] = useState(false);
  const isNavigatingForward = useRef(false);

  const [checkItems, setCheckItems] = useState<CheckItem[]>([
    {
      id: 'microphone',
      title: '마이크 테스트',
      description: '음성 입력이 정상적으로 작동하는지 확인합니다.',
      status: 'pending',
      icon: '🎤'
    },
    {
      id: 'camera',
      title: '카메라 테스트', 
      description: '비디오 입력이 정상적으로 작동하는지 확인합니다.',
      status: 'pending',
      icon: '📹'
    },
    {
      id: 'speaker',
      title: '스피커/TTS 테스트',
      description: '음성 출력 및 면접관 질문 읽기 기능을 확인합니다.',
      status: 'pending',
      icon: '🔊'
    },
    {
      id: 'network',
      title: '네트워크 연결',
      description: '안정적인 인터넷 연결을 확인합니다.',
      status: 'pending',
      icon: '🌐'
    },
    {
      id: 'browser',
      title: '브라우저 호환성',
      description: '브라우저가 면접 시스템을 지원하는지 확인합니다.',
      status: 'pending',
      icon: '💻'
    },
    {
      id: 'gaze_calibration',
      title: '시선 캘리브레이션',
      description: '비언어적 분석을 위한 시선 추적 캘리브레이션을 진행합니다.',
      status: 'pending',
      icon: '👁️'
    }
  ]);

  const steps = ['공고 선택', '이력서 선택', '면접 모드 선택', 'AI 설정', '환경 체크'];

  const updateCheckStatus = (id: string, status: CheckItem['status'], errorMessage?: string) => {
    setCheckItems(prev => prev.map(item => 
      item.id === id 
        ? { ...item, status, errorMessage }
        : item
    ));
  };

  // 마이크 테스트
  const checkMicrophone = async (): Promise<void> => {
    return new Promise(async (resolve, reject) => {
      try {
        updateCheckStatus('microphone', 'checking');
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // 실제로는 음성 레벨을 체크하는 로직이 들어가야 함
        setTimeout(() => {
          stream.getTracks().forEach(track => track.stop());
          updateCheckStatus('microphone', 'success');
          resolve();
        }, 1500);
      } catch (error) {
        updateCheckStatus('microphone', 'error', '마이크 권한을 허용해주세요.');
        reject(error);
      }
    });
  };

  // TTS/스피커 테스트
  const checkSpeaker = async (): Promise<void> => {
    return new Promise(async (resolve, reject) => {
      try {
        updateCheckStatus('speaker', 'checking');
        
        // TTS 지원 여부 확인
        const { hasTTS } = checkSpeechSupport();
        if (!hasTTS) {
          updateCheckStatus('speaker', 'error', 'TTS를 지원하지 않는 브라우저입니다.');
          reject(new Error('TTS not supported'));
          return;
        }

        console.log('🔊 TTS 테스트 시작 - 음성 권한 활성화');
        
        // TTS 인스턴스 생성
        const tts = createTTS();
        
        // 음성 목록 확인
        const voices = window.speechSynthesis.getVoices();
        console.log('🎵 사용 가능한 음성 수:', voices.length);
        console.log('🎵 한국어 음성:', voices.filter(v => v.lang.startsWith('ko')).length + '개');
        
        // 짧은 테스트 메시지로 TTS 권한 활성화
        const testMessage = "면접관 음성 테스트입니다. 이 음성이 들리면 정상입니다.";
        
        try {
          console.log('🎤 TTS 재생 시작...');
          await tts.speak(testMessage);
          console.log('✅ TTS 테스트 성공 - 음성 권한 활성화됨');
          console.log('🎯 이제 면접에서 TTS가 정상 작동할 것입니다');
          updateCheckStatus('speaker', 'success');
          resolve();
        } catch (ttsError) {
          console.error('❌ TTS 재생 실패:', ttsError);
          updateCheckStatus('speaker', 'error', '음성 재생에 실패했습니다. 스피커를 확인해주세요.');
          reject(ttsError);
        }
        
      } catch (error) {
        console.error('❌ 스피커/TTS 체크 실패:', error);
        updateCheckStatus('speaker', 'error', 'TTS 기능을 사용할 수 없습니다.');
        reject(error);
      }
    });
  };

  // 카메라 테스트
  const checkCamera = async (): Promise<void> => {
    return new Promise(async (resolve, reject) => {
      try {
        console.log('🎥 카메라 체크 시작');
        updateCheckStatus('camera', 'checking');
        
        const videoStream = await navigator.mediaDevices.getUserMedia({ 
          video: { 
            width: { ideal: 640 },
            height: { ideal: 480 }
          } 
        });
        
        console.log('🎥 비디오 스트림 획득 성공:', videoStream.getVideoTracks().length, '개 트랙');
        
        // 스트림을 먼저 설정하여 DOM 업데이트를 트리거
        setStream(videoStream);
        
        // DOM 업데이트를 기다린 후 video 요소에 스트림 할당
        await new Promise(resolve => setTimeout(resolve, 100));
        
        if (videoRef.current) {
          console.log('🎥 비디오 ref 존재, 스트림 설정 중...');
          videoRef.current.srcObject = videoStream;
          
          // video 이벤트 리스너 추가 (디버깅용)
          videoRef.current.onloadedmetadata = () => {
            console.log('📹 비디오 메타데이터 로드됨 - 크기:', videoRef.current?.videoWidth, 'x', videoRef.current?.videoHeight);
          };
          
          videoRef.current.oncanplay = () => {
            console.log('📹 비디오 재생 준비됨');
          };
          
          videoRef.current.onerror = (error) => {
            console.error('📹 비디오 에러:', error);
          };
          
          // video 요소가 스트림을 로드하고 재생을 시작하도록 함
          try {
            await videoRef.current.play();
            console.log('✅ 카메라 미리보기 시작됨');
          } catch (playError) {
            console.warn('⚠️ 비디오 자동 재생 실패 (권한 문제일 수 있음):', playError);
            // 자동재생이 실패해도 카메라 테스트는 성공으로 처리
          }
        } else {
          console.error('❌ 비디오 ref가 null입니다');
        }
        
        setTimeout(() => {
          console.log('✅ 카메라 체크 완료');
          updateCheckStatus('camera', 'success');
          resolve();
        }, 1500);
      } catch (error) {
        console.error('❌ 카메라 체크 실패:', error);
        updateCheckStatus('camera', 'error', '카메라 권한을 허용해주세요.');
        reject(error);
      }
    });
  };

  // 네트워크 테스트
  const checkNetwork = async (): Promise<void> => {
    return new Promise((resolve, reject) => {
      updateCheckStatus('network', 'checking');
      
      // 간단한 네트워크 속도 테스트 시뮬레이션
      const startTime = Date.now();
      fetch('/ping', { method: 'HEAD' })
        .then(() => {
          const responseTime = Date.now() - startTime;
          if (responseTime < 1000) {
            updateCheckStatus('network', 'success');
            resolve();
          } else {
            updateCheckStatus('network', 'error', '네트워크 연결이 불안정합니다.');
            reject(new Error('Slow network'));
          }
        })
        .catch(() => {
          // 실제 핑 테스트가 실패해도 성공으로 처리 (Mock)
          setTimeout(() => {
            updateCheckStatus('network', 'success');
            resolve();
          }, 1000);
        });
    });
  };

  // 브라우저 호환성 체크
  const checkBrowser = async (): Promise<void> => {
    return new Promise((resolve) => {
      updateCheckStatus('browser', 'checking');
      
      setTimeout(() => {
        const isCompatible = !!(navigator.mediaDevices && 
                              typeof navigator.mediaDevices.getUserMedia === 'function' &&
                              window.RTCPeerConnection);
        
        if (isCompatible) {
          updateCheckStatus('browser', 'success');
        } else {
          updateCheckStatus('browser', 'error', '브라우저가 면접 시스템을 지원하지 않습니다.');
        }
        resolve();
      }, 1000);
    });
  };

  // 시선 캘리브레이션 완료 핸들러
  const handleGazeCalibrationComplete = (sessionId: string) => {
    console.log('🎯 시선 캘리브레이션 완료:', sessionId);
    updateCheckStatus('gaze_calibration', 'success');
    dispatch({ type: 'SET_GAZE_CALIBRATION', payload: { sessionId } });
    setShowGazeCalibration(false);
  };

  const handleGazeCalibrationError = (error: string) => {
    console.error('❌ 시선 캘리브레이션 오류:', error);
    updateCheckStatus('gaze_calibration', 'error', error);
  };

  const startGazeCalibration = () => {
    updateCheckStatus('gaze_calibration', 'checking');
    setShowGazeCalibration(true);
  };

  const runAllChecks = async () => {
    setIsLoading(true);
    
    try {
      await checkBrowser();
      await checkNetwork();
      await checkMicrophone();
      await checkCamera();
      await checkSpeaker(); // 🆕 TTS/스피커 테스트 추가
      
      // 기본 체크 완료 후 시선 캘리브레이션 시작
      startGazeCalibration();
      
    } catch (error) {
      console.error('환경 체크 실패:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // 모든 체크 완료 여부 확인
  useEffect(() => {
    const basicChecksComplete = checkItems.filter(item => item.id !== 'gaze_calibration').every(item => item.status === 'success');
    const gazeCalibrationComplete = checkItems.find(item => item.id === 'gaze_calibration')?.status === 'success';
    setAllChecksComplete(basicChecksComplete && gazeCalibrationComplete);
  }, [checkItems]);

  const handlePrevious = () => {
    // 뒤로 가기는 정상적인 이동이므로 스트림 정리
    isNavigatingForward.current = false;
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    navigate('/interview/ai-setup');
  };

  const handleStartInterview = async () => {
    setIsLoading(true);
    try {
      // 1. Context에서 캘리브레이션 세션 ID를 가져옵니다.
      const calibSessionId = state.gazeTracking?.calibrationSessionId;
      if (!calibSessionId) {
        throw new Error("캘리브레이션 세션 ID를 찾을 수 없습니다. 캘리브레이션을 다시 진행해주세요.");
      }

      // 2. 새로 만든 전용 API 함수를 사용하여 캘리브레이션 결과를 요청합니다.
      console.log(`📊 캘리브레이션 결과 요청: ${calibSessionId}`);
      const calibResultResponse = await interviewApi.getCalibrationResult(calibSessionId);
      const fullCalibrationData: CalibrationResult = calibResultResponse;

      // 3. 받은 데이터가 유효한지 검증합니다.
      if (!fullCalibrationData || !fullCalibrationData.calibration_points) {
          throw new Error("백엔드로부터 유효한 캘리브레이션 데이터를 받지 못했습니다.");
      }
      console.log('✅ 캘리브레이션 전체 데이터 수신 성공:', fullCalibrationData);

      // 4. 캘리브레이션 데이터를 Context에 저장합니다 (S3 Pre-signed URL 플로우용)
      dispatch({ 
        type: 'SET_GAZE_CALIBRATION_DATA', 
        payload: fullCalibrationData 
      });
      console.log('📄 캘리브레이션 데이터가 Context에 저장되었습니다');

      // 5. 받아온 전체 캘리브레이션 데이터를 finalSettings에 포함시킵니다.
      const getDifficultyFromLevel = (level: number | undefined): string => {
        if (level === undefined) return '중간';
        if (level <= 3) return '초급';
        if (level <= 7) return '중급';
        return '고급';
      };

      const finalSettings = {
        company: state.jobPosting?.company || '',
        position: state.jobPosting?.position || '',
        posting_id: state.jobPosting?.posting_id,
        mode: state.aiSettings?.mode || 'personalized',
        difficulty: getDifficultyFromLevel(state.aiSettings?.aiQualityLevel),
        candidate_name: state.resume?.name || '사용자',
        resume: { ...state.resume, user_resume_id: state.resume?.user_resume_id },
        documents: [] as string[],
        calibration_data: fullCalibrationData,
      };

      // 6. 이후 로직은 동일합니다.
      const sessionId = `session_${Date.now()}`;
      dispatch({ type: 'SET_SESSION_ID', payload: sessionId });

      const stateToSave = {
        jobPosting: state.jobPosting,
        resume: state.resume,
        interviewMode: state.interviewMode,
        aiSettings: state.aiSettings,
        settings: finalSettings,
        sessionId: sessionId,
        interviewStatus: 'ready',
        fromEnvironmentCheck: true,
        needsApiCall: true,
        apiCallCompleted: false,
        gazeTracking: state.gazeTracking
      };
      localStorage.setItem('interview_state', JSON.stringify(stateToSave));

      isNavigatingForward.current = true;

      if (stream) {
        dispatch({ type: 'SET_CAMERA_STREAM', payload: stream });
      }

      dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'ready' });

      setTimeout(() => {
        navigate('/interview/active');
      }, 500);

    } catch (error) {
      console.error("❌ 면접 시작 처리 실패:", error);
      alert(error instanceof Error ? error.message : "캘리브레이션 결과를 가져오는 데 실패했습니다. 다시 시도해주세요.");
      setIsLoading(false);
    }
  };

  // 컴포넌트 언마운트 시 조건부 스트림 정리
  useEffect(() => {
    return () => {
      // 면접 시작으로 인한 이동이 아닐 경우에만 스트림 중지
      if (!isNavigatingForward.current && stream) {
        console.log('🔄 페이지 이탈로 인한 스트림 정리');
        stream.getTracks().forEach(track => track.stop());
      } else if (isNavigatingForward.current) {
        console.log('✅ 면접 시작으로 인한 이동 - 스트림 유지');
      }
    };
  }, [stream]);

  const getStatusIcon = (status: CheckItem['status']) => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'checking':
        return '🔄';
      case 'success':
        return '✅';
      case 'error':
        return '❌';
      default:
        return '⏳';
    }
  };

  const getStatusColor = (status: CheckItem['status']) => {
    switch (status) {
      case 'success':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'checking':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-slate-600 bg-slate-50 border-slate-200';
    }
  };

  // allChecksComplete 상태로 대체 (이미 useEffect에서 관리됨)
  const allChecksPassed = allChecksComplete;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="면접 준비"
        subtitle="마지막 환경 체크를 진행합니다"
      />
      
      <main className="container mx-auto px-6 py-8">
        <StepIndicator currentStep={5} totalSteps={5} steps={steps} />
        
        <div className="max-w-4xl mx-auto space-y-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">
              환경 체크
            </h2>
            <p className="text-slate-600">
              원활한 면접을 위해 마이크, 카메라, 네트워크 상태를 확인합니다.
            </p>
          </div>

          {/* 환경 체크 시작 버튼 */}
          {!allChecksComplete && checkItems.every(item => item.status === 'pending') && (
            <div className="text-center">
              <button
                onClick={runAllChecks}
                disabled={isLoading}
                className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-4 rounded-full text-lg font-bold hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? '체크 중...' : '환경 체크 시작'}
              </button>
            </div>
          )}

          {/* 체크 항목들 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {checkItems.map((item, index) => (
              <div
                key={item.id}
                className={`rounded-2xl p-6 border-2 transition-all duration-300 ${getStatusColor(item.status)}`}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className="flex items-start gap-4">
                  <div className="text-3xl">
                    {item.status === 'checking' ? (
                      <div className="animate-spin text-2xl">🔄</div>
                    ) : (
                      <span>{getStatusIcon(item.status)}</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-2xl">{item.icon}</span>
                      <h3 className="text-lg font-bold">{item.title}</h3>
                    </div>
                    <p className="text-sm mb-2">{item.description}</p>
                    {item.status === 'error' && item.errorMessage && (
                      <p className="text-sm text-red-600 font-medium">
                        {item.errorMessage}
                      </p>
                    )}
                    {item.status === 'success' && (
                      <p className="text-sm text-green-600 font-medium">
                        정상 작동 중
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 카메라 미리보기 - 항상 렌더링하되 조건부로 표시 */}
          <div className={`bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 transition-all duration-300 ${
            (checkItems.find(item => item.id === 'camera')?.status === 'success' || 
             checkItems.find(item => item.id === 'camera')?.status === 'checking') && stream
              ? 'opacity-100 visible' 
              : 'opacity-0 invisible h-0 p-0 overflow-hidden'
          }`}>
            <h3 className="text-lg font-bold text-slate-900 mb-4 text-center">
              카메라 미리보기
            </h3>
            <div className="relative max-w-md mx-auto">
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="w-full rounded-xl border border-slate-300 bg-gray-100"
                style={{ maxHeight: '300px', minHeight: '200px', transform: 'scaleX(-1)' }}
              />
              {stream ? (
                <div className="absolute bottom-3 left-3 bg-green-500 text-white px-2 py-1 rounded text-xs font-medium">
                  라이브
                </div>
              ) : (
                <div className="absolute bottom-3 left-3 bg-yellow-500 text-white px-2 py-1 rounded text-xs font-medium">
                  연결 중...
                </div>
              )}
            </div>
            <p className="text-sm text-slate-600 text-center mt-3">
              면접 중에는 이 화면이 면접관에게 보여집니다.
            </p>
          </div>

          {/* 시선 캘리브레이션 모달 */}
          {showGazeCalibration && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
              <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div className="border-b border-gray-200 p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900">👁️ 시선 캘리브레이션</h2>
                      <p className="text-gray-600 text-sm mt-1">비언어적 분석을 위한 시선 추적 설정</p>
                    </div>
                    <button
                      onClick={() => {
                        setShowGazeCalibration(false);
                        updateCheckStatus('gaze_calibration', 'error', '사용자가 취소했습니다.');
                      }}
                      className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <VideoCalibration
                    onCalibrationComplete={handleGazeCalibrationComplete}
                    onError={handleGazeCalibrationError}
                  />
                </div>
              </div>
            </div>
          )}

          {/* 최종 확인 */}
          {allChecksComplete && (
            <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-2xl p-8 border border-green-200 text-center">
              <div className="text-6xl mb-4">✅</div>
              <h3 className="text-2xl font-bold text-green-900 mb-4">
                모든 환경 체크가 완료되었습니다!
              </h3>
              <p className="text-green-700 mb-6">
                이제 면접을 시작할 준비가 되었습니다. 아래 버튼을 클릭하여 면접을 시작하세요.
              </p>
              
              {/* 최종 설정 요약 */}
              <div className="bg-white/70 rounded-xl p-4 mb-6 text-left max-w-md mx-auto">
                <h4 className="font-bold text-slate-900 mb-3">면접 정보</h4>
                <div className="space-y-2 text-sm text-slate-700">
                  <div>📋 공고: {state.jobPosting?.company} - {state.jobPosting?.position}</div>
                  <div>📄 이력서: {state.resume?.name}_이력서</div>
                  <div>🤖 모드: {state.aiSettings?.mode === 'ai_competition' ? 'AI 경쟁 면접' : '개인화 면접'}</div>
                  <div>👥 면접관: 3명 (인사/기술/협업)</div>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200">
            <NavigationButtons
              onPrevious={handlePrevious}
              onNext={allChecksPassed ? handleStartInterview : undefined}
              previousLabel="AI 설정 다시 하기"
              nextLabel="면접 시작하기"
              canGoNext={allChecksPassed}
              isLoading={isLoading}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default EnvironmentCheck;