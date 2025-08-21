import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import StepIndicator from '../components/interview/StepIndicator';
import NavigationButtons from '../components/interview/NavigationButtons';
import { useInterview } from '../contexts/InterviewContext';

interface InterviewMode {
  id: string;
  title: string;
  description: string;
  features: string[];
  color: string;
}

interface Interviewer {
  id: string;
  name: string;
  role: string;
  description: string;
  icon: string;
  color: string;
}

const AISetup: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  const [aiQualityLevel, setAiQualityLevel] = useState(5); // Default to intermediate

  const steps = ['공고 선택', '이력서 선택', '면접 모드 선택', 'AI 설정', '환경 체크'];
  
  const selectedMode = state.interviewMode || 'personalized';

  const getAICandidateImage = (level: number): string => {
    if (level <= 3) return '/img/nano-banana_____.png';
    if (level <= 7) return '/img/nano-banana__Create_an_image_of_.png';
    return '/img/nano-banana______2.png';
  };

  const getAICandidateName = (level: number): string => {
    if (level <= 3) return '춘식이 (초급)';
    if (level <= 7) return '춘식이 (중급)';
    return '춘식이 (고급)';
  };

  const getDifficultyName = (level: number): string => {
    if (level <= 3) return '초급';
    if (level <= 7) return '중급';
    return '고급';
  };

  const interviewers: Interviewer[] = [
    {
      id: 'hr',
      name: '',
      role: '인사 담당자',
      description: '지원동기, 성격, 조직 적합성을 평가합니다.',
      icon: '👔',
      color: 'from-blue-500 to-blue-600'
    },
    {
      id: 'tech1',
      name: '',
      role: '기술 담당자',
      description: '기술 역량, 문제 해결 능력을 평가합니다.',
      icon: '💻',
      color: 'from-green-500 to-green-600'
    },
    {
      id: 'collabo1',
      name: '',
      role: '협업 담당자',
      description: '소통 능력, 팀워크, 리더십을 평가합니다.',
      icon: '🤝',
      color: 'from-purple-500 to-purple-600'
    }
  ];

  const handlePrevious = () => {
    navigate('/interview/interview-mode-selection');
  };

  const handleNext = () => {
    dispatch({ 
      type: 'SET_AI_SETTINGS', 
      payload: {
        mode: selectedMode,
        aiQualityLevel,
        interviewers: interviewers.map(interviewer => ({
          id: interviewer.id,
          name: interviewer.name,
          role: interviewer.role
        }))
      }
    });
    
    navigate('/interview/environment-check');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="면접 준비"
        subtitle="AI 면접관과 설정을 선택해주세요"
      />
      
      <main className="container mx-auto px-6 py-8">
        <StepIndicator currentStep={4} totalSteps={5} steps={steps} />
        
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">
              AI 면접관 설정
            </h2>
            <p className="text-slate-600">
              {state.jobPosting?.company} {state.jobPosting?.position} 면접을 위한 AI 설정을 구성합니다.
            </p>
          </div>

          {/* AI 면접관 소개 */}
          <div>
            <h3 className="text-2xl font-bold text-slate-900 text-center mb-8">
              AI 면접관 3명이 다각도로 평가합니다
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {interviewers.map((interviewer, index) => (
                <div
                  key={interviewer.id}
                  className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 text-center hover:shadow-lg transition-all duration-300"
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <div className={`w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-r ${interviewer.color} flex items-center justify-center overflow-hidden border-2 border-white shadow-lg`}>
                    <img 
                      src={interviewer.id === 'hr' ? '/img/nano-banana_A_front-facing_port_1.png' : interviewer.id === 'tech1' ? '/img/nano-banana_Change_only_the_back.png' : interviewer.id === 'collabo1' ? '/img/flux-1-kontext-pro__k-tech___.png' : `/img/${interviewer.id}_interviewer.png`}
                      alt={interviewer.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <h4 className="text-lg font-bold text-slate-900 mb-2">
                    {interviewer.name}
                  </h4>
                  <p className="text-sm text-blue-600 font-medium mb-3">
                    {interviewer.role}
                  </p>
                  <p className="text-sm text-slate-600">
                    {interviewer.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* AI 경쟁 모드 설정 */}
          {(selectedMode === 'ai_competition' || selectedMode === 'text_competition') && (
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 border border-slate-200">
              <h3 className="text-xl font-bold text-slate-900 mb-6 text-center">
                AI 지원자 설정
              </h3>
              
              {/* AI 지원자 소개 */}
              <div className="mb-8 p-6 bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl border border-purple-200">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center overflow-hidden border-2 border-white shadow-lg">
                    <img 
                      src={getAICandidateImage(aiQualityLevel)}
                      alt={getAICandidateName(aiQualityLevel)}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div>
                    <h4 className="text-lg font-bold text-purple-900">{getAICandidateName(aiQualityLevel)}</h4>
                    <p className="text-purple-700">AI 면접 지원자</p>
                  </div>
                </div>
                <p className="text-sm text-purple-700">
                  AI 지원자 '춘식이'와 동시에 면접을 진행하며 실력을 비교해보세요. 
                  난이도가 높을수록 더 우수한 답변을 제공합니다.
                </p>
              </div>

              {/* AI 난이도 선택 */}
              <div>
                <label className="block text-lg font-bold text-slate-900 mb-6">
                  AI 지원자 난이도 선택
                </label>
                
                {/* 난이도 설명 카드들 */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div 
                    className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      aiQualityLevel <= 3 
                        ? 'border-purple-500 bg-purple-50' 
                        : 'border-slate-200 bg-slate-50 hover:border-purple-300'
                    }`}
                    onClick={() => setAiQualityLevel(2)}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`w-3 h-3 rounded-full ${
                        aiQualityLevel <= 3 ? 'bg-green-500' : 'bg-slate-300'
                      }`}></div>
                      <h5 className="font-medium text-slate-900">초급자</h5>
                    </div>
                    <p className="text-sm text-slate-600">
                      기본적인 답변 수준으로, 면접 초보자와 비슷한 수준입니다.
                    </p>
                  </div>
                  
                  <div 
                    className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      aiQualityLevel >= 4 && aiQualityLevel <= 7
                        ? 'border-purple-500 bg-purple-50' 
                        : 'border-slate-200 bg-slate-50 hover:border-purple-300'
                    }`}
                    onClick={() => setAiQualityLevel(5)}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`w-3 h-3 rounded-full ${
                        aiQualityLevel >= 4 && aiQualityLevel <= 7 ? 'bg-yellow-500' : 'bg-slate-300'
                      }`}></div>
                      <h5 className="font-medium text-slate-900">중급자</h5>
                    </div>
                    <p className="text-sm text-slate-600">
                      실무 경험이 있는 개발자 수준의 답변을 제공합니다.
                    </p>
                  </div>
                  
                  <div 
                    className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      aiQualityLevel >= 8
                        ? 'border-purple-500 bg-purple-50' 
                        : 'border-slate-200 bg-slate-50 hover:border-purple-300'
                    }`}
                    onClick={() => setAiQualityLevel(9)}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`w-3 h-3 rounded-full ${
                        aiQualityLevel >= 8 ? 'bg-red-500' : 'bg-slate-300'
                      }`}></div>
                      <h5 className="font-medium text-slate-900">고급자</h5>
                    </div>
                    <p className="text-sm text-slate-600">
                      시니어 개발자 수준의 깊이 있는 답변을 제공합니다.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 설정 요약 */}
          <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 border border-slate-200">
            <h3 className="text-xl font-bold text-slate-900 mb-4">설정 요약</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium text-slate-700 mb-2">선택된 공고</h4>
                <p className="text-sm text-slate-600">
                  {state.jobPosting?.company} - {state.jobPosting?.position}
                </p>
              </div>
              <div>
                <h4 className="font-medium text-slate-700 mb-2">사용할 이력서</h4>
                <p className="text-sm text-slate-600">
                  {state.resume?.name}_이력서
                </p>
              </div>
              <div>
                <h4 className="font-medium text-slate-700 mb-2">면접 모드</h4>
                <p className="text-sm text-slate-600">
                  {selectedMode === 'personalized' && '개인화 면접'}
                  {selectedMode === 'standard' && '표준 면접'}
                  {selectedMode === 'ai_competition' && 'AI 경쟁 면접'}
                </p>
              </div>
              <div>
                <h4 className="font-medium text-slate-700 mb-2">AI 면접관</h4>
                <p className="text-sm text-slate-600">
                  인사/기술/협업 담당자 3명
                  {selectedMode === 'ai_competition' && ` + AI 지원자 (${getDifficultyName(aiQualityLevel)})`}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200">
            <NavigationButtons
              onPrevious={handlePrevious}
              onNext={handleNext}
              previousLabel="이전 단계로"
              nextLabel="환경 체크하기"
              canGoNext={true}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default AISetup;
