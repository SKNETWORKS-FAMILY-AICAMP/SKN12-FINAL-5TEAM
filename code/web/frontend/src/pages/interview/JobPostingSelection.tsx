import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/common/Header';
import StepIndicator from '../../components/interview/StepIndicator';
import NavigationButtons from '../../components/interview/NavigationButtons';
import { useInterview } from '../../contexts/InterviewContext';
import { postingAPI, JobPosting } from '../../services/api';

const JobPostingSelection: React.FC = () => {
  const navigate = useNavigate();
  const { dispatch } = useInterview();
  const [selectedPosting, setSelectedPosting] = useState<number | null>(null);
  const [jobPostings, setJobPostings] = useState<JobPosting[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasInitialized = useRef(false);

  // 회사 로고 매핑 함수
  const getCompanyLogo = (companyName: string): string => {
    const logoMap: Record<string, string> = {
      '네이버': '/img/naver.png',
      '카카오': '/img/kakao.svg',
      '라인플러스': '/img/line.svg',
      '쿠팡': '/img/coupang.svg',
      '배달의민족': '/img/baemin.svg',
      '배민': '/img/baemin.svg',
      '당근': '/img/daangn.png',
      '당근마켓': '/img/daangn.png',
      '토스': '/img/toss.png'
    };
    
    return logoMap[companyName] || '/img/default-company.png'; // fallback 이미지
  };

  // 🆕 API에서 채용공고 데이터 로딩 (React Strict Mode 중복 방지)
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;
    
    const loadJobPostings = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const postings = await postingAPI.getAllPostings();
        console.log('📋 채용공고 데이터 로드 완료:', postings.length, '개');
        
        if (postings.length === 0) {
          console.warn('⚠️ DB에서 채용공고를 찾을 수 없음 - fallback 데이터 사용');
          // fallback: 더미 데이터 사용
          setJobPostings(getFallbackPostings());
        } else {
          setJobPostings(postings);
        }
        
      } catch (error) {
        console.error('❌ 채용공고 로딩 실패:', error);
        setError('채용공고를 불러오는데 실패했습니다.');
        // fallback: 더미 데이터 사용
        setJobPostings(getFallbackPostings());
      } finally {
        setIsLoading(false);
      }
    };

    loadJobPostings();
  }, []);

  // fallback 더미 데이터 (DB 연결 실패 시 사용) - 단순화된 구조
  const getFallbackPostings = (): JobPosting[] => [
    {
      posting_id: 1,
      company_id: 1,
      position_id: 1,
      company: '네이버',
      position: '프론트엔드 개발자',
      content: '네이버 메인 서비스의 프론트엔드 개발을 담당할 인재를 모집합니다.'
    },
    {
      posting_id: 2,
      company_id: 2,
      position_id: 2,
      company: '카카오',
      position: '백엔드 개발자',
      content: '카카오톡 메시징 시스템의 백엔드 개발을 담당할 개발자를 찾습니다.'
    },
    {
      posting_id: 3,
      company_id: 3,
      position_id: 3,
      company: '배달의민족',
      position: '모바일 개발자 (Android)',
      content: '배민 앱의 안드로이드 개발을 담당할 모바일 개발자를 찾습니다.'
    }
  ];

  const steps = ['공고 선택', '이력서 선택', '면접 모드 선택', 'AI 설정', '환경 체크'];

  const handleSelectPosting = (postingId: number) => {
    setSelectedPosting(postingId);
  };

  const handleNext = () => {
    if (!selectedPosting) return;
    
    const selectedPostingData = jobPostings.find(posting => posting.posting_id === selectedPosting);
    if (selectedPostingData) {
      // Context에 선택된 공고 정보 저장 (Supabase 구조에 맞게 수정)
      dispatch({ 
        type: 'SET_JOB_POSTING', 
        payload: {
          posting_id: selectedPostingData.posting_id,
          company_id: selectedPostingData.company_id,
          position_id: selectedPostingData.position_id,
          company: selectedPostingData.company,
          position: selectedPostingData.position,
          content: selectedPostingData.content
        }
      });
      
      navigate('/interview/resume-selection');
    }
  };

  const selectedPostingData = jobPostings.find(posting => posting.posting_id === selectedPosting);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="면접 준비"
        subtitle="지원하고 싶은 공고를 선택해주세요"
      />
      
      <main className="container mx-auto px-6 py-8">
        <StepIndicator currentStep={1} totalSteps={5} steps={steps} />
        
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">
              어떤 공고에 지원하시나요?
            </h2>
            <p className="text-slate-600">
              관심있는 공고를 선택하면 해당 기업에 맞는 맞춤형 면접을 준비해드립니다.
            </p>
          </div>

          {/* 로딩 상태 */}
          {isLoading && (
            <div className="flex justify-center items-center py-16">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
              <span className="ml-3 text-slate-600">채용공고를 불러오는 중...</span>
            </div>
          )}

          {/* 에러 상태 */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p className="text-red-600">{error}</p>
              <p className="text-red-500 text-sm mt-1">fallback 데이터를 사용합니다.</p>
            </div>
          )}

          {/* 채용공고 목록 */}
          {!isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
              {jobPostings.map((posting) => (
                <div
                  key={posting.posting_id}
                  onClick={() => handleSelectPosting(posting.posting_id)}
                  className={`bg-white/80 backdrop-blur-sm rounded-2xl p-6 border-2 cursor-pointer transition-all duration-300 hover:shadow-lg ${
                    selectedPosting === posting.posting_id
                      ? 'border-blue-500 bg-gradient-to-r from-blue-50 to-purple-50 transform scale-105'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="border-2 border-gray-300 rounded-2xl p-2">
                      {/* 실제 회사 로고 이미지 */}
                      <img 
                        src={getCompanyLogo(posting.company)} 
                        alt={posting.company}
                        className="w-8 h-8 rounded-lg object-contain"
                        onError={(e) => {
                          // 이미지 로드 실패 시 fallback
                          const img = e.currentTarget;
                          const fallbackDiv = img.nextElementSibling as HTMLElement;
                          if (fallbackDiv) {
                            img.style.display = 'none';
                            fallbackDiv.style.display = 'flex';
                          }
                        }}
                      />
                      {/* fallback 아이콘 */}
                      <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center" style={{display: 'none'}}>
                        <span className="text-white font-bold text-sm">
                          {posting.company.charAt(0)}
                        </span>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-slate-900">{posting.company}</h3>
                      <p className="text-blue-600 font-medium">{posting.position}</p>
                    </div>
                  </div>

                  <p className="text-sm text-slate-600 mb-4 line-clamp-2">
                    {posting.content}
                  </p>
                </div>
            ))}
          </div>
          )}

          {/* 선택된 공고 정보 표시 */}
          {selectedPostingData && !isLoading && (
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 mb-8">
              <h3 className="text-xl font-bold text-slate-900 mb-4">선택된 공고</h3>
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <img 
                    src={getCompanyLogo(selectedPostingData.company)} 
                    alt={selectedPostingData.company}
                    className="w-12 h-12 rounded-xl object-contain"
                    onError={(e) => {
                      const img = e.currentTarget;
                      const fallbackDiv = img.nextElementSibling as HTMLElement;
                      if (fallbackDiv) {
                        img.style.display = 'none';
                        fallbackDiv.style.display = 'flex';
                      }
                    }}
                  />
                  <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl flex items-center justify-center" style={{display: 'none'}}>
                    <span className="text-white font-bold">
                      {selectedPostingData.company.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <h4 className="text-lg font-bold text-slate-900">{selectedPostingData.company}</h4>
                    <p className="text-blue-600 font-medium">{selectedPostingData.position}</p>
                  </div>
                </div>
                
                <div>
                  <h4 className="font-medium text-slate-700 mb-2">채용공고 내용</h4>
                  <p className="text-sm text-slate-600 leading-relaxed">{selectedPostingData.content}</p>
                </div>
              </div>
              
              {/* DB 정보 표시 (디버깅용) */}
              <div className="mt-4 pt-4 border-t border-slate-200">
                <p className="text-xs text-slate-400">
                  DB ID: posting_id={selectedPostingData.posting_id}, company_id={selectedPostingData.company_id}, position_id={selectedPostingData.position_id}
                </p>
              </div>
            </div>
          )}

          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200">
            <NavigationButtons
              onNext={handleNext}
              nextLabel="이력서 선택하기"
              canGoNext={!!selectedPosting}
              showPrevious={false}
            />
          </div>
        </div>
      </main>
    </div>
  )
  ;
};

export default JobPostingSelection;