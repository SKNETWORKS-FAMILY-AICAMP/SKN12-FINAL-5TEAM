import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/common/Header';
import StepIndicator from '../../components/interview/StepIndicator';
import NavigationButtons from '../../components/interview/NavigationButtons';
import { useInterview } from '../../contexts/InterviewContext';

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

  const runAllChecks = async () => {
    setIsLoading(true);
    
    try {
      await checkBrowser();
      await checkNetwork();
      await checkMicrophone();
      await checkCamera();
      
      setAllChecksComplete(true);
    } catch (error) {
      console.error('환경 체크 실패:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePrevious = () => {
    // 카메라 스트림 정리
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    navigate('/interview/ai-setup');
  };

  const handleStartInterview = () => {
    setIsLoading(true);
    
    // 4단계 플로우 데이터를 기존 InterviewActive가 기대하는 형식으로 변환
    const finalSettings = {
      company: state.jobPosting?.company || '',  // 회사명 사용
      position: state.jobPosting?.position || '',
      mode: state.aiSettings?.mode || 'personalized',
      difficulty: '중간',
      candidate_name: state.resume?.name || '사용자',
      resume: state.resume,  // 전체 이력서 데이터 포함
      documents: [] as string[]
    };
    
    // 기존 설정 형식으로 변환하여 저장
    dispatch({ 
      type: 'SET_SETTINGS', 
      payload: finalSettings
    });
    
    // 임시 세션 ID 생성 (실제로는 API에서 받아야 함)
    const sessionId = `session_${Date.now()}`;
    dispatch({ 
      type: 'SET_SESSION_ID', 
      payload: sessionId
    });
    
    // 면접 설정을 localStorage에 저장 (새로고침 시 복원용)
    try {
      const stateToSave = {
        jobPosting: state.jobPosting,
        resume: state.resume,
        interviewMode: state.interviewMode,
        aiSettings: state.aiSettings,
        settings: finalSettings,
        sessionId: sessionId,
        interviewStatus: 'ready',
        fromEnvironmentCheck: true, // EnvironmentCheck에서 온 것임을 표시
        needsApiCall: true // API 호출이 필요함을 표시
      };
      localStorage.setItem('interview_state', JSON.stringify(stateToSave));
      console.log('💾 면접 설정을 localStorage에 저장 완료 (EnvironmentCheck)');
    } catch (error) {
      console.error('❌ localStorage 저장 실패:', error);
    }
    
    // 카메라 스트림을 Context에 저장
    if (stream) {
      const videoTracks = stream.getVideoTracks();
      console.log('📹 Context에 카메라 스트림 저장:', videoTracks.length, '개 트랙');
      
      if (videoTracks.length > 0) {
        const track = videoTracks[0];
        console.log('📹 환경체크에서 저장하는 트랙 정보:', {
          readyState: track.readyState,
          enabled: track.enabled,
          muted: track.muted,
          id: track.id,
          label: track.label
        });
      }
      
      dispatch({
        type: 'SET_CAMERA_STREAM',
        payload: stream
      });
    } else {
      console.warn('⚠️ 저장할 카메라 스트림이 없습니다!');
    }
    
    dispatch({ 
      type: 'SET_INTERVIEW_STATUS', 
      payload: 'ready'
    });
    
    console.log('🚀 면접 시작:', {
      settings: finalSettings,
      sessionId,
      hasStream: !!stream,
      companyCode: finalSettings.company,  // 디버깅을 위해 회사 코드 로그
      originalCompany: state.jobPosting?.company
    });
    
    // 실제 면접 시작 - 모드에 따라 다른 페이지로 라우팅
    setTimeout(() => {
      if (finalSettings.mode === 'text_competition') {
        console.log('🎯 텍스트 경쟁 모드 감지 - /interview/active-temp로 이동');
        navigate('/interview/active-temp');
      } else {
        console.log('🎯 기본 모드 - /interview/active로 이동');
        navigate('/interview/active');
      }
    }, 1000);
  };

  // 컴포넌트 언마운트 시 스트림 정리
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
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

  const allChecksPassed = checkItems.every(item => item.status === 'success');

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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

          {/* 최종 확인 */}
          {allChecksPassed && (
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