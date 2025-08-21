import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/common/Header';
import StepIndicator from '../../components/interview/StepIndicator';
import NavigationButtons from '../../components/interview/NavigationButtons';
import { useInterview } from '../../contexts/InterviewContext';

interface InterviewMode {
  id: string;
  title: string;
  description: string;
  features: string[];
  color: string;
  icon: string;
}

const InterviewModeSelection: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  const [selectedMode, setSelectedMode] = useState<string | null>(null);

  const steps = ['공고 선택', '이력서 선택', '면접 모드 선택', 'AI 설정', '환경 체크'];

  const interviewModes: InterviewMode[] = [
    {
      id: 'ai_competition',
      title: 'AI 경쟁 면접',
      description: 'AI 지원자와 경쟁',
      features: ['실시간 AI 대결', '비교 분석', '경쟁력 평가'],
      color: 'from-purple-500 to-pink-500',
      icon: '🤖'
    },
    {
      id: 'coming_soon',
      title: 'Coming Soon',
      description: '새로운 기능이 곧 출시됩니다',
      features: ['더 많은 면접 모드', '향상된 기능', '기대해 주세요'],
      color: 'from-gray-400 to-gray-500',
      icon: '⏳'
    }
  ];

  const handlePrevious = () => {
    navigate('/interview/resume-selection');
  };

  const handleNext = () => {
    if (!selectedMode) return;
    
    // Context에 면접 모드 저장
    dispatch({ 
      type: 'SET_INTERVIEW_MODE', 
      payload: selectedMode
    });
    
    navigate('/interview/ai-setup');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="면접 준비"
        subtitle="면접 모드를 선택해주세요"
      />
      
      <main className="container mx-auto px-6 py-8">
        <StepIndicator currentStep={3} totalSteps={5} steps={steps} />
        
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">
              어떤 방식으로 면접을 진행하시겠습니까?
            </h2>
            <p className="text-slate-600">
              {state.jobPosting?.company} {state.jobPosting?.position} 면접을 위한 모드를 선택해주세요.
            </p>
          </div>

          {/* 면접 모드 선택 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
            {interviewModes.map((mode, index) => (
              <div
                key={mode.id}
                onClick={() => mode.id !== 'coming_soon' ? setSelectedMode(mode.id) : undefined}
                className={`interview-card rounded-2xl p-8 border-2 transition-all duration-300 ${
                  mode.id === 'coming_soon'
                    ? 'border-gray-300 bg-gray-100/80 cursor-not-allowed opacity-60'
                    : selectedMode === mode.id
                      ? 'border-blue-500 bg-gradient-to-r from-blue-50 to-purple-50 transform scale-105 shadow-xl cursor-pointer'
                      : 'border-slate-200 bg-white/80 hover:border-slate-300 hover:shadow-lg cursor-pointer'
                }`}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className="text-center">
                  <div className={`w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-r ${mode.color} flex items-center justify-center text-3xl`}>
                    {mode.icon}
                  </div>
                  <h3 className={`text-xl font-bold mb-3 ${
                    selectedMode === mode.id ? 'text-blue-900' : 'text-slate-900'
                  }`}>
                    {mode.title}
                  </h3>
                  <p className={`text-sm mb-6 ${
                    selectedMode === mode.id ? 'text-blue-700' : 'text-slate-600'
                  }`}>
                    {mode.description}
                  </p>
                  <ul className="space-y-2">
                    {mode.features.map((feature, idx) => (
                      <li key={idx} className={`text-sm ${
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

          {/* 선택된 모드 상세 설명 */}
          {selectedMode && (
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-8 border border-slate-200 mb-8">
              <h3 className="text-xl font-bold text-slate-900 mb-4 text-center">
                선택된 면접 모드
              </h3>
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
                <div className="md:col-span-2">
                  <h4 className="font-medium text-slate-700 mb-2">선택된 면접 모드</h4>
                  <p className="text-sm text-slate-600">
                    {interviewModes.find(mode => mode.id === selectedMode)?.title} - {interviewModes.find(mode => mode.id === selectedMode)?.description}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200">
            <NavigationButtons
              onPrevious={handlePrevious}
              onNext={handleNext}
              previousLabel="이력서 다시 선택"
              nextLabel="AI 설정하기"
              canGoNext={!!selectedMode}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default InterviewModeSelection; 