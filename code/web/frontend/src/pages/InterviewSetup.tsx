import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useInterview } from '../contexts/InterviewContext';
import { interviewApi, handleApiError, validateFileSize, validateFileExtension } from '../services/api';
import { saveInterviewState, InterviewState, markApiCallCompleted } from '../utils/interviewStateManager';

const InterviewSetup: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  
  const [selectedMode, setSelectedMode] = useState('personalized');
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);
  const [selectedPosition, setSelectedPosition] = useState('');
  const [userName, setUserName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [aiQualityLevel, setAiQualityLevel] = useState(6);

  const interviewModes = [
    {
      id: 'personalized',
      title: '📄 개인화 면접',
      description: '문서 업로드 기반 맞춤형 질문',
      features: ['이력서/자소서 분석', '맞춤형 질문 생성', '개인화된 피드백'],
      color: 'from-blue-500 to-cyan-500'
    },
    {
      id: 'standard',
      title: '📝 표준 면접',
      description: '기본 질문으로 진행',
      features: ['일반적인 면접 질문', '빠른 시작', '기본 평가'],
      color: 'from-green-500 to-emerald-500'
    },
    {
      id: 'text_competition',
      title: '⌨️ 텍스트 AI 경쟁',
      description: 'AI와 텍스트로 경쟁하는 면접',
      features: ['고품질 턴제 면접', 'AI 페르소나 경쟁', '텍스트 기반 진행'],
      color: 'from-orange-500 to-red-500'
    },
    {
      id: 'ai_competition',
      title: '🤖 AI 경쟁 면접',
      description: 'AI 지원자와 경쟁',
      features: ['실시간 AI 대결', '비교 분석', '경쟁력 평가'],
      color: 'from-purple-500 to-pink-500'
    }
  ];

  const companies = [
    {
      id: 'naver',
      name: '네이버',
      logo: '🔵',
      description: '검색, AI, 클라우드 전문',
      techStack: ['Java', 'Spring', 'MySQL', 'Redis'],
      positions: ['백엔드 개발', '프론트엔드 개발', '인공지능', '데이터 사이언스', '기획']
    },
    {
      id: 'kakao',
      name: '카카오',
      logo: '💛',
      description: '플랫폼, 메시징 전문',
      techStack: ['Kotlin', 'Spring Boot', 'MongoDB', 'Kafka'],
      positions: ['백엔드 개발', '프론트엔드 개발', '인공지능', '데이터 사이언스', '기획']
    },
    {
      id: 'line',
      name: '라인',
      logo: '💚',
      description: '글로벌 메시징 전문',
      techStack: ['Java', 'Go', 'MySQL', 'Redis'],
      positions: ['백엔드 개발', '프론트엔드 개발', '인공지능', '데이터 사이언스', '기획']
    },
    {
      id: 'coupang',
      name: '쿠팡',
      logo: '🔴',
      description: '이커머스, 물류 전문',
      techStack: ['Java', 'Python', 'AWS', 'Docker'],
      positions: ['백엔드 개발', '프론트엔드 개발', '인공지능', '데이터 사이언스', '기획']
    },
    {
      id: 'baemin',
      name: '배달의민족',
      logo: '🍔',
      description: '푸드테크, 배달 서비스 전문',
      techStack: ['Kotlin', 'Spring', 'MySQL', 'Redis'],
      positions: ['백엔드 개발', '프론트엔드 개발', '인공지능', '데이터 사이언스', '기획']
    },
    {
      id: 'daangn',
      name: '당근마켓',
      logo: '🥕',
      description: '중고거래, 동네 커뮤니티 전문',
      techStack: ['Ruby', 'Rails', 'React', 'PostgreSQL'],
      positions: ['백엔드 개발', '프론트엔드 개발', '인공지능', '데이터 사이언스', '기획']
    },
    {
      id: 'toss',
      name: '토스',
      logo: '💳',
      description: '핀테크, 금융 서비스 전문',
      techStack: ['Java', 'Kotlin', 'Spring', 'AWS'],
      positions: ['백엔드 개발', '프론트엔드 개발', '인공지능', '데이터 사이언스', '기획']
    }
  ];

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    
    for (const file of files) {
      // 파일 검증
      if (!validateFileSize(file)) {
        alert(`파일 크기가 너무 큽니다: ${file.name} (최대 16MB)`);
        continue;
      }
      
      if (!validateFileExtension(file)) {
        alert(`지원하지 않는 파일 형식입니다: ${file.name}`);
        continue;
      }
      
      try {
        setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));
        
        // 파일 업로드
        const result = await interviewApi.uploadDocument(file);
        
        setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
        setUploadedFiles(prev => [...prev, file]);
        
        console.log('파일 업로드 성공:', result);
        
      } catch (error) {
        console.error('파일 업로드 실패:', error);
        alert(`파일 업로드 실패: ${handleApiError(error)}`);
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[file.name];
          return newProgress;
        });
      }
    }
  };

  const handleStartInterview = async () => {
    if (!selectedCompany || !selectedPosition || !userName) {
      alert('모든 정보를 입력해주세요!');
      return;
    }

    setIsLoading(true);

    try {
      const selectedCompanyData = companies.find(c => c.id === selectedCompany);
      
      // 먼저 기본 설정 생성
      const baseSettings = {
        company: selectedCompanyData!.name,
        position: selectedPosition,
        mode: selectedMode,
        difficulty: '중간',
        candidate_name: userName,
        documents: uploadedFiles.map(file => file.name)
      };

      // InterviewerService 플래그 명시적 추가
      const useInterviewerService = selectedMode === 'ai_competition';
      const settings = {
        ...baseSettings,
        use_interviewer_service: useInterviewerService  // 🎯 명시적으로 플래그 설정
      };

      // 🐛 디버깅: 생성된 설정값 로깅
      console.log('🐛 DEBUG: selectedMode:', selectedMode);
      console.log('🐛 DEBUG: useInterviewerService 계산값:', useInterviewerService);
      console.log('🐛 DEBUG: InterviewSetup에서 생성한 전체 설정값:', settings);
      console.log('🐛 DEBUG: settings.use_interviewer_service:', settings.use_interviewer_service);
      console.log('🐛 DEBUG: JSON.stringify 결과:', JSON.stringify(settings));

      let response;
      if (selectedMode === 'ai_competition') {
        // AI 경쟁 면접 시작 - 백그라운드로 처리
        console.log('🚀 AI 경쟁 면접 시작 (백그라운드 처리)');
        
        // 설정 저장
        dispatch({ type: 'SET_SETTINGS', payload: settings });
        
        // 즉시 InterviewGO로 이동하기 위해 임시 응답 생성
        response = {
          session_id: `temp_${Date.now()}`, // 임시 세션 ID
          status: 'waiting_for_user',
          content: { content: "면접을 시작합니다. 첫 번째 질문을 기다려주세요." }
        };

        // 임시 상태를 localStorage에 저장 (needsApiCall 플래그 포함)
        const tempState: InterviewState = {
          sessionId: response.session_id,
          settings: settings,
          interviewStatus: 'setup',
          timestamp: Date.now(),
          jobPosting: selectedCompanyData,
          resume: state.resume,
          interviewMode: selectedMode,
          aiSettings: {
            mode: 'ai_competition',
            persona: 'professional'
          },
          interviewStartResponse: response,
          needsApiCall: true,        // API 호출 필요 플래그
          apiCallCompleted: false    // API 호출 완료 상태
        };
        saveInterviewState(tempState);
        console.log('💾 임시 상태로 localStorage 저장 (needsApiCall: true):', tempState);
        
        // 백그라운드에서 실제 API 호출
        interviewApi.startAICompetition(settings).then(realResponse => {
          console.log('✅ 백그라운드 면접 시작 완료:', realResponse);
          // 유틸리티 함수를 사용하여 API 호출 완료 상태로 업데이트
          markApiCallCompleted(realResponse);
        }).catch(error => {
          console.error('❌ 백그라운드 면접 시작 실패:', error);
          // 유틸리티 함수를 사용하여 에러 상태로 업데이트
          markApiCallCompleted(undefined, error.message);
        });
        
      } else if (selectedMode === 'text_competition') {
        // 🆕 텍스트 기반 AI 경쟁 면접 시작
        console.log('🔍 텍스트 경쟁 모드 - Context 상태 확인:');
        console.log('📄 state.resume:', state.resume);
        console.log('📋 전체 state:', state);
        
        // 이력서 데이터 확인 및 포함
        if (!state.resume) {
          console.log('⚠️ 이력서 데이터 없음 - 이력서 선택 페이지로 이동');
          alert('이력서를 먼저 선택해주세요. 이력서 선택 페이지로 이동합니다.');
          navigate('/interview/resume-selection');
          return;
        }

        // 이력서 데이터를 포함한 설정 생성
        const settingsWithResume = {
          ...settings,
          resume: state.resume
        };

        console.log('✅ 이력서 데이터가 포함된 설정:');
        console.log('📤 settingsWithResume:', settingsWithResume);

        response = await interviewApi.startTextCompetition(settingsWithResume);
        
        // 설정 저장 (텍스트 모드 표시)
        dispatch({ type: 'SET_SETTINGS', payload: { ...settingsWithResume, mode: 'text_competition' } });
        
        // 텍스트 경쟁 모드 전용 데이터 저장
        if (response.question) {
          dispatch({ type: 'SET_TEXT_COMPETITION_DATA', payload: {
            initialQuestion: response.question,
            aiPersona: response.ai_persona,
            progress: response.progress
          }});
        }
      } else {
        // 일반 면접 시작
        response = await interviewApi.startInterview(settings);
        dispatch({ type: 'SET_SETTINGS', payload: settings });
      }
      
      // Context 업데이트
      if (response.session_id) {
        dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
        dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'setup' });

        // localStorage에 면접 상태 저장 (InterviewActive가 기대하는 구조로)
        const interviewState = {
          sessionId: response.session_id,
          settings: settings,
          interviewStatus: 'setup',
          timestamp: Date.now(),
          // InterviewActive가 추가로 기대하는 필드들
          jobPosting: selectedCompanyData,
          resume: state.resume,
          interviewMode: selectedMode,
          aiSettings: selectedMode === 'ai_competition' ? {
            mode: 'ai_competition',
            persona: 'professional'
          } : null,
          // 🆕 면접 시작 응답 저장 (턴 정보 포함)
          interviewStartResponse: response
        };
        localStorage.setItem('interview_state', JSON.stringify(interviewState));
        console.log('💾 면접 상태 localStorage에 저장:', interviewState);

        // 모드에 따라 다른 면접 페이지로 이동
        if (selectedMode === 'text_competition') {
          navigate('/interview/active-temp');  // 텍스트 경쟁 모드
        } else if (selectedMode === 'ai_competition') {
          navigate('/interview/ai/start');  // AI 경쟁 모드 전용 경로
        } else {
          navigate('/interview/active');  // 기타 모드
        }
      } else {
        console.error('❌ 응답에서 session_id를 찾을 수 없음:', response);
        throw new Error('세션 ID를 받지 못했습니다.');
      }
      
    } catch (error) {
      console.error('면접 시작 실패:', error);
      alert(`면접 시작 실패: ${handleApiError(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const selectedCompanyData = companies.find(c => c.id === selectedCompany);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="면접 설정"
        subtitle="맞춤형 AI 면접을 위한 정보를 설정해주세요"
      />
      
      <main className="container mx-auto px-6 py-12">
        <div className="max-w-6xl mx-auto space-y-12">
          
          {/* 면접 모드 선택 */}
          <div className="animate-fadeIn">
            <h2 className="text-3xl font-bold text-slate-900 text-center mb-8">
              면접 모드를 선택하세요
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {interviewModes.map((mode, index) => (
                <div
                  key={mode.id}
                  onClick={() => setSelectedMode(mode.id)}
                  className={`interview-card cursor-pointer rounded-2xl p-6 border-2 transition-all ${
                    selectedMode === mode.id
                      ? 'border-blue-500 bg-gradient-to-r from-blue-50 to-purple-50'
                      : 'border-slate-200 bg-white/80 hover:border-slate-300'
                  }`}
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <div className="text-center">
                    <div className={`w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-r ${mode.color} flex items-center justify-center text-2xl`}>
                      {mode.title.split(' ')[0]}
                    </div>
                    <h3 className={`text-lg font-bold mb-2 ${
                      selectedMode === mode.id ? 'text-blue-900' : 'text-slate-900'
                    }`}>
                      {mode.title}
                    </h3>
                    <p className={`text-sm mb-4 ${
                      selectedMode === mode.id ? 'text-blue-700' : 'text-slate-600'
                    }`}>
                      {mode.description}
                    </p>
                    <ul className="space-y-1">
                      {mode.features.map((feature, idx) => (
                        <li key={idx} className={`text-xs ${
                          selectedMode === mode.id ? 'text-blue-600' : 'text-slate-500'
                        }`}>
                          ✓ {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 회사 선택 */}
          <div className="animate-slideUp">
            <h2 className="text-3xl font-bold text-slate-900 text-center mb-8">
              지원할 회사를 선택하세요
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {companies.map((company, index) => (
                <div
                  key={company.id}
                  onClick={() => setSelectedCompany(company.id)}
                  className={`interview-card cursor-pointer rounded-2xl p-6 border-2 transition-all ${
                    selectedCompany === company.id
                      ? 'border-blue-500 bg-gradient-to-r from-blue-50 to-purple-50'
                      : 'border-slate-200 bg-white/80 hover:border-slate-300'
                  }`}
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <div className="text-center">
                    <div className="text-4xl mb-3">{company.logo}</div>
                    <h3 className={`text-xl font-bold mb-2 ${
                      selectedCompany === company.id ? 'text-blue-900' : 'text-slate-900'
                    }`}>
                      {company.name}
                    </h3>
                    <p className={`text-sm mb-4 ${
                      selectedCompany === company.id ? 'text-blue-700' : 'text-slate-600'
                    }`}>
                      {company.description}
                    </p>
                    <div className="flex flex-wrap gap-1 justify-center mb-4">
                      {company.techStack.slice(0, 3).map((tech, idx) => (
                        <span key={idx} className={`px-2 py-1 rounded-full text-xs ${
                          selectedCompany === company.id
                            ? 'bg-blue-200 text-blue-800'
                            : 'bg-slate-200 text-slate-600'
                        }`}>
                          {tech}
                        </span>
                      ))}
                    </div>
                    <div className={`text-xs ${
                      selectedCompany === company.id ? 'text-blue-600' : 'text-slate-500'
                    }`}>
                      {company.positions.length}개 포지션 가능
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 상세 정보 입력 */}
          {selectedCompany && (
            <div className="animate-slideUp bg-white/80 backdrop-blur-sm rounded-2xl p-8 border border-slate-200">
              <h3 className="text-2xl font-bold text-slate-900 mb-6 text-center">
                상세 정보 입력
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    지원자 이름
                  </label>
                  <input
                    type="text"
                    value={userName}
                    onChange={(e) => setUserName(e.target.value)}
                    placeholder="이름을 입력하세요"
                    className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    지원 직군
                  </label>
                  <select
                    value={selectedPosition}
                    onChange={(e) => setSelectedPosition(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                  >
                    <option value="">직군을 선택하세요</option>
                    {selectedCompanyData?.positions.map((position, idx) => (
                      <option key={idx} value={position}>{position}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* 문서 업로드 */}
              {selectedMode === 'personalized' && (
                <div className="mb-6">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    문서 업로드 (선택사항)
                  </label>
                  <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:border-blue-400 transition-colors">
                    <div className="text-4xl mb-2">📄</div>
                    <p className="text-slate-600 mb-2">이력서, 자기소개서를 드래그하거나 클릭하여 업로드</p>
                    <p className="text-sm text-slate-500 mb-4">PDF, DOCX, DOC 파일 지원 (최대 16MB)</p>
                    
                    <input
                      type="file"
                      multiple
                      accept=".pdf,.doc,.docx"
                      onChange={handleFileUpload}
                      className="hidden"
                      id="file-upload"
                    />
                    
                    <label
                      htmlFor="file-upload"
                      className="inline-block bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors cursor-pointer"
                    >
                      파일 선택
                    </label>
                    
                    {/* 업로드된 파일 목록 */}
                    {uploadedFiles.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {uploadedFiles.map((file, index) => (
                          <div key={index} className="flex items-center justify-between bg-green-50 p-2 rounded">
                            <span className="text-sm text-green-800">{file.name}</span>
                            <span className="text-xs text-green-600">✓ 업로드 완료</span>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* 업로드 진행률 */}
                    {Object.entries(uploadProgress).map(([fileName, progress]) => (
                      progress < 100 && (
                        <div key={fileName} className="mt-2">
                          <div className="text-sm text-blue-600 mb-1">{fileName}</div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                        </div>
                      )
                    ))}
                  </div>
                </div>
              )}

              {/* AI 경쟁 모드 설정 */}
              {selectedMode === 'ai_competition' && (
                <div className="mb-6">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    AI 지원자 난이도 선택
                  </label>
                  <div className="grid grid-cols-5 gap-2">
                    {[...Array(10)].map((_, index) => {
                      const level = index + 1;
                      return (
                        <button
                          key={level}
                          type="button"
                          onClick={() => setAiQualityLevel(level)}
                          className={`p-2 rounded-lg text-sm font-medium transition-all ${
                            aiQualityLevel === level
                              ? 'bg-purple-600 text-white shadow-lg'
                              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                          }`}
                        >
                          Lv.{level}
                        </button>
                      );
                    })}
                  </div>
                  <div className="mt-2 text-xs text-slate-500 text-center">
                    현재 선택: <span className="font-medium text-purple-600">레벨 {aiQualityLevel}</span>
                    {aiQualityLevel <= 3 && ' (초급)'}
                    {aiQualityLevel >= 4 && aiQualityLevel <= 7 && ' (중급)'}
                    {aiQualityLevel >= 8 && ' (고급)'}
                  </div>
                  
                  <div className="mt-4 p-4 bg-purple-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-2xl">🤖</span>
                      <span className="font-medium text-purple-900">춘식이와 경쟁하기</span>
                    </div>
                    <p className="text-sm text-purple-700">
                      AI 지원자 '춘식이'와 동시에 면접을 진행하며 실력을 비교해보세요. 
                      레벨이 높을수록 더 우수한 답변을 제공합니다.
                    </p>
                  </div>
                </div>
              )}

              <div className="text-center">
                <button
                  onClick={handleStartInterview}
                  disabled={!selectedCompany || !selectedPosition || !userName || isLoading}
                  className={`px-8 py-4 rounded-full text-lg font-bold transition-all ${
                    selectedCompany && selectedPosition && userName && !isLoading
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:shadow-lg hover:scale-105'
                      : 'bg-slate-300 text-slate-500 cursor-not-allowed'
                  }`}
                >
                  {isLoading ? (
                    <div className="flex items-center gap-2">
                      <LoadingSpinner size="sm" color="white" />
                      면접 준비 중...
                    </div>
                  ) : (
                    '면접 시작하기'
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default InterviewSetup;