import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import StepIndicator from '../components/interview/StepIndicator';
import NavigationButtons from '../components/interview/NavigationButtons';
import { useInterview } from '../contexts/InterviewContext';
import { ResumeResponse } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useResumes } from '../hooks/useResumes';
import { usePositions } from '../hooks/usePositions';

// Extended Resume interface combining backend data with user info
interface ExtendedResume extends ResumeResponse {
  name: string;
  email: string;
  phone: string;
  position_name?: string;
}


const ResumeSelection: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  const { user, isAuthenticated } = useAuth();
  const [selectedResume, setSelectedResume] = useState<number | null>(null);
  
  // 커스텀 훅 사용
  const { resumes: resumesData, loading: resumesLoading, error: resumesError } = useResumes();
  const { positions, loading: positionsLoading, error: positionsError } = usePositions();

  // 이력서 데이터에 사용자 정보와 직군명 추가
  const extendedResumes: ExtendedResume[] = useMemo(() => {
    if (!user || !resumesData || !positions) return [];
    
    return resumesData.map(resume => ({
      ...resume,
      name: user.name,
      email: user.email,
      phone: '', // 사용자 프로필에 전화번호가 없어서 빈 문자열
      position_name: positions.find(p => p.position_id === resume.position_id)?.position_name || '미지정'
    }));
  }, [resumesData, positions, user]);

  // 로딩 및 에러 상태 통합
  const loading = resumesLoading || positionsLoading;
  const error = resumesError || positionsError;

  const steps = ['공고 선택', '이력서 선택', '면접 모드 선택', 'AI 설정', '환경 체크'];

  const calculateCompletionRate = (resume: ExtendedResume): number => {
    const fields = ['academic_record', 'career', 'tech', 'activities'];
    const filledFields = fields.filter(field => {
      const value = resume[field as keyof ExtendedResume];
      return value && value.toString().trim() !== '';
    });
    return Math.round((filledFields.length / fields.length) * 100);
  };

  const formatDate = (dateString: string): string => {
    try {
      return new Date(dateString).toLocaleDateString('ko-KR');
    } catch {
      return '날짜 없음';
    }
  };

  const handleSelectResume = (resumeId: number) => {
    setSelectedResume(resumeId);
  };

  const handlePrevious = () => {
    navigate('/interview/job-posting');
  };

  const handleNext = () => {
    if (!selectedResume) return;
    
    const selectedResumeData = extendedResumes.find(resume => resume.user_resume_id === selectedResume);
    if (selectedResumeData) {
      // Context에 선택된 이력서 정보 저장 (기존 인터페이스에 맞게 변환)
      const resumeForContext = {
        id: selectedResumeData.user_resume_id.toString(),
        user_resume_id: selectedResumeData.user_resume_id, // ✅ 원본 numeric ID 보존
        name: selectedResumeData.name,
        email: selectedResumeData.email,
        phone: selectedResumeData.phone,
        academic_record: selectedResumeData.academic_record,
        career: selectedResumeData.career,
        tech: selectedResumeData.tech,
        activities: selectedResumeData.activities,
        certificate: selectedResumeData.certificate,
        awards: selectedResumeData.awards,
        created_at: selectedResumeData.created_date,
        updated_at: selectedResumeData.updated_date
      };
      
      dispatch({
        type: 'SET_RESUME',
        payload: resumeForContext
      });
      
      navigate('/interview/interview-mode-selection');
    }
  };

  const handleCreateResume = () => {
    navigate('/profile', { state: { activeTab: 'resume', action: 'create' } });
  };

  const selectedResumeData = extendedResumes.find(resume => resume.user_resume_id === selectedResume);

  // 로딩 상태 처리
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title="면접 준비"
          subtitle="사용할 이력서를 선택해주세요"
        />
        <main className="container mx-auto px-6 py-8">
          <StepIndicator currentStep={2} totalSteps={5} steps={steps} />
          <div className="max-w-6xl mx-auto">
            <div className="text-center py-16">
              <div className="text-8xl mb-6">🔄</div>
              <h3 className="text-xl font-bold text-slate-900 mb-2">이력서 로딩 중...</h3>
              <p className="text-slate-600">잠시만 기다려주세요.</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // 인증되지 않은 사용자 처리
  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title="면접 준비"
          subtitle="로그인이 필요합니다"
        />
        <main className="container mx-auto px-6 py-8">
          <div className="max-w-6xl mx-auto">
            <div className="text-center py-16">
              <div className="text-8xl mb-6">🔒</div>
              <h3 className="text-xl font-bold text-slate-900 mb-2">로그인이 필요합니다</h3>
              <p className="text-slate-600 mb-6">이력서를 보려면 먼저 로그인해주세요.</p>
              <button
                onClick={() => navigate('/login')}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-blue-700 transition-colors"
              >
                로그인하러 가기
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // 에러 상태 처리
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title="면접 준비"
          subtitle="이력서 로딩 오류"
        />
        <main className="container mx-auto px-6 py-8">
          <div className="max-w-6xl mx-auto">
            <div className="text-center py-16">
              <div className="text-8xl mb-6">⚠️</div>
              <h3 className="text-xl font-bold text-slate-900 mb-2">이력서를 불러올 수 없습니다</h3>
              <p className="text-slate-600 mb-6">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-blue-700 transition-colors mr-4"
              >
                다시 시도
              </button>
              <button
                onClick={() => navigate('/profile')}
                className="bg-slate-100 text-slate-600 px-6 py-3 rounded-lg text-lg hover:bg-slate-200 transition-colors"
              >
                마이페이지로 가기
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="면접 준비"
        subtitle="사용할 이력서를 선택해주세요"
      />
      
      <main className="container mx-auto px-6 py-8">
        <StepIndicator currentStep={2} totalSteps={5} steps={steps} />
        
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">
              어떤 이력서로 면접을 볼까요?
            </h2>
            <p className="text-slate-600">
              {state.jobPosting?.company} {state.jobPosting?.position} 포지션에 맞는 이력서를 선택해주세요.
            </p>
          </div>

          {extendedResumes.length === 0 ? (
            // 이력서가 없는 경우
            <div className="text-center py-16">
              <div className="text-8xl mb-6">📄</div>
              <h3 className="text-xl font-bold text-slate-900 mb-2">등록된 이력서가 없습니다</h3>
              <p className="text-slate-600 mb-6">
                면접을 시작하기 전에 마이페이지에서 이력서를 먼저 작성해주세요.
              </p>
              <button
                onClick={handleCreateResume}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-blue-700 transition-colors"
              >
                📝 이력서 작성하러 가기
              </button>
            </div>
          ) : (
            <>
              {/* 이력서 목록 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                {extendedResumes.map(resume => {
                  const completionRate = calculateCompletionRate(resume);
                  return (
                    <div
                      key={resume.user_resume_id}
                      onClick={() => handleSelectResume(resume.user_resume_id)}
                      className={`bg-white/80 backdrop-blur-sm rounded-2xl p-6 border-2 cursor-pointer transition-all duration-300 hover:shadow-lg ${selectedResume === resume.user_resume_id
                          ? 'border-blue-500 bg-gradient-to-r from-blue-50 to-purple-50 transform scale-105'
                          : 'border-slate-200 hover:border-slate-300'}`}
                    >
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-slate-900 truncate">
                          {resume.position_name || '미지정'} 이력서
                        </h3>
                        <span className="text-xs text-slate-500">{formatDate(resume.updated_date)}</span>
                      </div>
                      
                      <div className="mb-4">
                        <div className="text-sm text-slate-600 mb-2 flex items-center justify-between">
                          <span>작성 완료도</span>
                          <span className="font-medium">{completionRate}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full transition-all duration-500 ${completionRate === 100 ? 'bg-green-500' : 
                              completionRate >= 75 ? 'bg-blue-500' : 
                              completionRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{width: `${completionRate}%`}}
                          />
                        </div>
                      </div>
                      
                      <div className="text-sm text-slate-600 mb-4 space-y-1">
                        <div className="flex items-center gap-2">
                          <span>🎓</span>
                          <span className="truncate">{resume.academic_record || '학력 미입력'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span>💻</span>
                          <span className="truncate">{resume.tech || '기술스택 미입력'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span>💼</span>
                          <span className="truncate">
                            {resume.career ? resume.career.split('\n')[0] : '경력 미입력'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span>🏆</span>
                          <span className="truncate">
                            {resume.position_name ? `${resume.position_name} 직군` : '직군 미지정'}
                          </span>
                        </div>
                      </div>

                      {selectedResume === resume.user_resume_id && (
                        <div className="mt-4 pt-4 border-t border-slate-200">
                          <div className="flex items-center gap-2 text-blue-600">
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            <span className="font-medium">선택됨</span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* 이력서 추가 버튼 */}
              <div className="text-center mb-8">
                <button
                  onClick={handleCreateResume}
                  className="bg-slate-100 text-slate-600 px-4 py-2 rounded-lg hover:bg-slate-200 transition-colors"
                >
                  ➕ 새 이력서 만들기
                </button>
              </div>

              {/* 선택된 이력서 미리보기 */}
              {selectedResumeData && (
                <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 mb-8">
                  <h3 className="text-xl font-bold text-slate-900 mb-4">선택된 이력서 미리보기</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <h4 className="font-medium text-slate-700 mb-2">기본 정보</h4>
                      <div className="space-y-1 text-sm text-slate-600">
                        <div>이름: {selectedResumeData.name}</div>
                        <div>이메일: {selectedResumeData.email}</div>
                        <div>직군: {selectedResumeData.position_name || '미지정'}</div>
                        <div>작성일: {formatDate(selectedResumeData.created_date)}</div>
                      </div>
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-700 mb-2">주요 기술스택</h4>
                      <div className="flex flex-wrap gap-1">
                        {selectedResumeData.tech ? selectedResumeData.tech.split(',').slice(0, 5).map((tech, idx) => (
                          <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                            {tech.trim()}
                          </span>
                        )) : (
                          <span className="text-slate-400 text-xs">기술스택 미입력</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="mt-4">
                    <h4 className="font-medium text-slate-700 mb-2">주요 경력</h4>
                    <p className="text-sm text-slate-600 line-clamp-2">
                      {selectedResumeData.career ? selectedResumeData.career.split('\n')[0] : '경력 정보가 없습니다.'}
                    </p>
                  </div>
                </div>
              )}
            </>
          )}

          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200">
            <NavigationButtons
              onPrevious={handlePrevious}
              onNext={handleNext}
              previousLabel="공고 다시 선택"
              nextLabel="면접 모드 선택하기"
              canGoNext={!!selectedResume}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default ResumeSelection;
