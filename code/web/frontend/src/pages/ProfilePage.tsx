import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useAuth } from '../hooks/useAuth';
import { usePositions } from '../hooks/usePositions';
import { useResumes } from '../hooks/useResumes';
import { useInterviewHistory } from '../hooks/useInterviewHistory';
import { Position, ResumeResponse, ResumeCreate } from '../services/api';


// UserResume 인터페이스를 백엔드 스키마와 일치하도록 수정
interface UserResume extends ResumeResponse {
  // 추가 UI용 필드들
  position_name?: string; // 직군명 (매핑용)
  displayName?: string;   // 표시용 이력서 제목
}

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading: authLoading, refreshAuthStatus } = useAuth();
  const [activeTab, setActiveTab] = useState('resume');
  const [currentView, setCurrentView] = useState<'list' | 'create' | 'edit' | 'view'>('list');
  const [editingResumeId, setEditingResumeId] = useState<number | null>(null);
  
  // 커스텀 훅들 사용
  const { positions, loading: positionsLoading } = usePositions();
  const { resumes: resumesData, loading: resumesLoading, error: resumesError, createResume, updateResume, deleteResume } = useResumes();
  const { interviews: interviewHistory, stats: interviewStats, isLoading: historyLoading, error: historyError, refreshHistory } = useInterviewHistory();
  const [userInfo, setUserInfo] = useState({
    name: user?.name || '',
    email: user?.email || '',
    profileImage: null as string | null
  });



  const [currentResume, setCurrentResume] = useState<UserResume>({
    user_resume_id: 0,
    user_id: user?.user_id || 0,
    academic_record: '',
    position_id: 0,
    created_date: '',
    updated_date: '',
    career: '',
    tech: '',
    activities: '',
    certificate: '',
    awards: '',
    // UI용 추가 필드
    position_name: '',
    displayName: ''
  });

  const sidebarMenus = [
    { id: 'resume', label: '이력서 관리', icon: '📄', color: 'text-blue-600' },
    { id: 'interview-history', label: '면접 히스토리', icon: '📊', color: 'text-purple-600' },
    { id: 'personal-info', label: '개인정보 관리', icon: '👤', color: 'text-orange-600' }
  ];

  // 🆕 이력서 제목 생성 함수
  const generateResumeTitle = (resume: ResumeResponse, positions: Position[]): string => {
    const position = positions.find(p => p.position_id === resume.position_id);
    const positionName = position?.position_name || '일반';
    return `${user?.name || '사용자'}_${positionName}_이력서`;
  };

  // 이력서 목록을 positions와 함께 계산된 값으로 처리
  const resumeList: UserResume[] = resumesData.map(resume => ({
    ...resume,
    position_name: positions.find(p => p.position_id === resume.position_id)?.position_name || '직군 미정',
    displayName: generateResumeTitle(resume, positions)
  }));

  // 로딩 상태 통합
  const isLoading = resumesLoading || positionsLoading;

  // 사용자 정보가 로드되면 상태 업데이트 및 데이터 로딩
  useEffect(() => {
    if (user) {
      setUserInfo({
        name: user.name,
        email: user.email,
        profileImage: null
      });
      
      // currentResume도 업데이트 (기본값 설정용)
      setCurrentResume(prev => ({
        ...prev,
        user_id: user.user_id
      }));
    }
  }, [user]);



  // 이력서 관련 유틸리티 함수들
  const calculateCompletionRate = (resume: UserResume): number => {
    // 필수 필드만 체크 (position_id, academic_record, career, tech)
    const fields = ['position_id', 'academic_record', 'career', 'tech'];
    const filledFields = fields.filter(field => {
      const value = resume[field as keyof UserResume];
      return field === 'position_id' ? value && value !== 0 : value?.toString().trim();
    });
    return Math.round((filledFields.length / fields.length) * 100);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('ko-KR');
  };

  // 이력서 네비게이션 함수들
  const handleCreateResume = () => {
    setCurrentResume({
      user_resume_id: 0,
      user_id: user?.user_id || 0,
      academic_record: '',
      position_id: 0, // 사용자가 선택해야 함
      created_date: '',
      updated_date: '',
      career: '',
      tech: '',
      activities: '',
      certificate: '',
      awards: '',
      // UI용 추가 필드
      position_name: '',
      displayName: ''
    });
    setCurrentView('create');
  };

  const handleViewResume = (resume: UserResume) => {
    setCurrentResume(resume);
    setEditingResumeId(resume.user_resume_id);
    setCurrentView('view');
  };

  const handleEditResume = (resume: UserResume) => {
    setCurrentResume(resume);
    setEditingResumeId(resume.user_resume_id);
    setCurrentView('edit');
  };

  const handleBackToList = () => {
    setCurrentView('list');
    setEditingResumeId(null);
  };

  const handleEditFromView = () => {
    setCurrentView('edit');
  };

  const handleResumeUpdate = (field: keyof UserResume, value: string | number) => {
    setCurrentResume(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleResumeSave = async () => {
    // 📝 필수 필드 검증
    if (!currentResume.position_id || currentResume.position_id === 0) {
      alert('직군을 선택해주세요.');
      return;
    }
    if (!currentResume.academic_record.trim()) {
      alert('학력을 입력해주세요.');
      return;
    }
    if (!currentResume.career.trim()) {
      alert('경력을 입력해주세요.');
      return;
    }
    if (!currentResume.tech.trim()) {
      alert('기술스택을 입력해주세요.');
      return;
    }

    try {
      // API 요청용 데이터 준비 (UI용 필드 제외)
      const resumeData: ResumeCreate = {
        academic_record: currentResume.academic_record,
        position_id: currentResume.position_id,
        career: currentResume.career,
        tech: currentResume.tech,
        activities: currentResume.activities || '',
        certificate: currentResume.certificate || '',
        awards: currentResume.awards || ''
      };

      if (currentView === 'create') {
        // 🆕 새 이력서 생성
        const createdResume = await createResume(resumeData);
        if (createdResume) {
          alert('이력서가 생성되었습니다.');
        }
      } else if (currentView === 'edit' && editingResumeId) {
        // ✏️ 기존 이력서 수정
        const updatedResume = await updateResume(editingResumeId, resumeData);
        if (updatedResume) {
          alert('이력서가 수정되었습니다.');
        }
      }
      
      handleBackToList();
    } catch (error: any) {
      console.error('이력서 저장 실패:', error);
      const errorMessage = error.response?.data?.detail || '이력서 저장에 실패했습니다.';
      alert(errorMessage);
    }
  };

  const handleDeleteResume = async (resumeId: number) => {
    if (window.confirm('정말로 이 이력서를 삭제하시겠습니까?')) {
      try {
        // 🗑️ 이력서 삭제
        const success = await deleteResume(resumeId);
        if (success) {
          alert('이력서가 삭제되었습니다.');
        }
      } catch (error: any) {
        console.error('이력서 삭제 실패:', error);
        const errorMessage = error.response?.data?.detail || '이력서 삭제에 실패했습니다.';
        alert(errorMessage);
      }
    }
  };

  const handleCopyResume = async (resume: UserResume) => {
    try {
      // 📋 이력서 복사용 데이터 준비 (ID 관련 필드 제외)
      const copyData: ResumeCreate = {
        academic_record: resume.academic_record,
        position_id: resume.position_id,
        career: resume.career,
        tech: resume.tech,
        activities: resume.activities,
        certificate: resume.certificate,
        awards: resume.awards
      };
      
      // 새 이력서 생성
      const copiedResume = await createResume(copyData);
      if (copiedResume) {
        alert('이력서가 복사되었습니다.');
      }
    } catch (error: any) {
      console.error('이력서 복사 실패:', error);
      const errorMessage = error.response?.data?.detail || '이력서 복사에 실패했습니다.';
      alert(errorMessage);
    }
  };

  const handleUserInfoUpdate = (field: string, value: string) => {
    setUserInfo(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleUserInfoSave = async () => {
    // 이름과 이메일 검증
    if (!userInfo.name.trim()) {
      alert('이름을 입력해주세요.');
      return;
    }
    if (!userInfo.email.trim()) {
      alert('이메일을 입력해주세요.');
      return;
    }
    
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        alert('인증이 필요합니다. 다시 로그인해주세요.');
        return;
      }

      const response = await fetch('/user/me', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: userInfo.name.trim(),
          email: userInfo.email.trim()
        }),
      });

      if (response.ok) {
        const updatedUser = await response.json();
        
        // localStorage의 사용자 정보도 업데이트
        const existingUser = localStorage.getItem('user_profile');
        if (existingUser) {
          const userData = JSON.parse(existingUser);
          userData.name = updatedUser.name;
          userData.email = updatedUser.email;
          localStorage.setItem('user_profile', JSON.stringify(userData));
        }
        
        // 로컬 상태도 즉시 업데이트
        setUserInfo({
          name: updatedUser.name,
          email: updatedUser.email,
          profileImage: userInfo.profileImage
        });
        
        alert('정보가 성공적으로 저장되었습니다.');
        
        // 인증 상태 새로고침으로 사용자 정보 갱신
        await refreshAuthStatus();
        
        // 잠깐 기다린 후 페이지 새로고침 (모든 컴포넌트 확실히 갱신)
        setTimeout(() => {
          window.location.reload();
        }, 100);
      } else {
        const errorData = await response.json();
        alert(`저장에 실패했습니다: ${errorData.detail || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('정보 저장 오류:', error);
      alert('네트워크 오류가 발생했습니다. 다시 시도해주세요.');
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 80) return 'text-blue-600 bg-blue-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getStatusBadge = (status: string) => {
    switch(status) {
      case 'completed':
        return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">완료</span>;
      case 'in_progress':
        return <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">진행중</span>;
      case 'failed':
        return <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">실패</span>;
      default:
        return null;
    }
  };

  const renderContent = () => {
    switch(activeTab) {
      case 'resume':
        if (currentView === 'list') {
          return (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-slate-900">이력서 관리</h2>
                {resumeList.length > 0 && (
                  <button
                    onClick={handleCreateResume}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    ➕ 새 이력서 만들기
                  </button>
                )}
              </div>

              {resumesError ? (
                // 에러 상태
                <div className="text-center py-16">
                  <div className="text-8xl mb-6">⚠️</div>
                  <h3 className="text-xl font-bold text-slate-900 mb-2">데이터 로딩에 실패했습니다</h3>
                  <p className="text-slate-600 mb-6">{resumesError}</p>
                  <button
                    onClick={handleCreateResume}
                    className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-blue-700 transition-colors"
                  >
                    📝 새 이력서 만들기
                  </button>
                </div>
              ) : resumeList.length === 0 ? (
                // 빈 상태
                <div className="text-center py-16">
                  <div className="text-8xl mb-6">📄</div>
                  <h3 className="text-xl font-bold text-slate-900 mb-2">첫 이력서를 만들어보세요!</h3>
                  <p className="text-slate-600 mb-6">AI 맞춤형 면접을 위한 이력서를 작성해주세요</p>
                  <button
                    onClick={handleCreateResume}
                    className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-blue-700 transition-colors"
                  >
                    📝 이력서 만들기
                  </button>
                </div>
              ) : (
                // 이력서 목록
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {resumeList.map(resume => {
                    const completionRate = calculateCompletionRate(resume);
                    return (
                      <div key={resume.user_resume_id} className="bg-white rounded-lg border border-slate-200 p-6 hover:shadow-md transition-all duration-300 hover:border-blue-300 cursor-pointer" onClick={() => handleViewResume(resume)}>
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="font-semibold text-slate-900 truncate">{resume.displayName || `${user?.name}_${resume.position_name}_이력서`}</h3>
                          <span className="text-xs text-slate-500">{formatDate(resume.updated_date)}</span>
                        </div>
                        
                        <div className="mb-4">
                          <div className="text-sm text-slate-600 mb-2 flex items-center justify-between">
                            <span>작성 완료도</span>
                            <span className="font-medium">{completionRate}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full transition-all duration-500 ${
                                completionRate === 100 ? 'bg-green-500' : 
                                completionRate >= 75 ? 'bg-blue-500' : 
                                completionRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}
                              style={{width: `${completionRate}%`}}
                            />
                          </div>
                        </div>
                        
                        <div className="text-sm text-slate-600 mb-4 space-y-1">
                          <div className="flex items-center gap-2">
                            <span>💼</span>
                            <span className="truncate">{resume.position_name || '직군 미선택'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span>🎓</span>
                            <span className="truncate">{resume.academic_record || '학력 미입력'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span>💻</span>
                            <span className="truncate">{resume.tech || '기술스택 미입력'}</span>
                          </div>
                        </div>
                        
                        <div className="flex gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleViewResume(resume);
                            }}
                            className="flex-1 bg-slate-50 text-slate-600 py-2 px-2 rounded text-xs font-medium hover:bg-slate-100 transition-colors whitespace-nowrap"
                          >
                            👁️ 보기
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditResume(resume);
                            }}
                            className="flex-1 bg-blue-50 text-blue-600 py-2 px-2 rounded text-xs font-medium hover:bg-blue-100 transition-colors whitespace-nowrap"
                          >
                            ✏️ 수정
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopyResume(resume);
                            }}
                            className="flex-1 bg-green-50 text-green-600 py-2 px-2 rounded text-xs font-medium hover:bg-green-100 transition-colors whitespace-nowrap"
                          >
                            📋 복사
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteResume(resume.user_resume_id);
                            }}
                            className="flex-1 bg-red-50 text-red-600 py-2 px-2 rounded text-xs font-medium hover:bg-red-100 transition-colors whitespace-nowrap"
                          >
                            🗑️ 삭제
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        } else if (currentView === 'view') {
          return (
            <div className="space-y-6">
              <div className="flex items-center gap-4">
                <button
                  onClick={handleBackToList}
                  className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                >
                  ←
                </button>
                <h2 className="text-2xl font-bold text-slate-900">이력서 상세</h2>
                <div className="flex-1" />
                <button
                  onClick={handleEditFromView}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  ✏️ 수정하기
                </button>
              </div>

              <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-6">
                {/* 기본 정보 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    👤 기본 정보
                  </h3>
                  
                  {/* 지원 직군 */}
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-slate-700 mb-2">지원 직군</label>
                    <input
                      type="text"
                      value={positions.find(p => p.position_id === currentResume.position_id)?.position_name || '직군 미선택'}
                      disabled
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-gray-50 text-gray-700"
                    />
                  </div>
                  
                  {/* 지원자명 */}
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">지원자명</label>
                    <input
                      type="text"
                      value={user?.name || ''}
                      disabled
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-gray-50 text-gray-700"
                    />
                  </div>
                </div>

                {/* 학력 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🎓 학력
                  </h3>
                  <textarea
                    value={currentResume.academic_record}
                    disabled
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-gray-50 text-gray-700 resize-none h-24"
                  />
                </div>

                {/* 경력 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    💼 경력
                  </h3>
                  <textarea
                    value={currentResume.career}
                    disabled
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-gray-50 text-gray-700 resize-none h-32"
                  />
                </div>

                {/* 기술스택 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    💻 기술스택
                  </h3>
                  <textarea
                    value={currentResume.tech}
                    disabled
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-gray-50 text-gray-700 resize-none h-24"
                  />
                </div>

                {/* 활동/경험 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🚀 활동/경험
                  </h3>
                  <textarea
                    value={currentResume.activities}
                    disabled
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-gray-50 text-gray-700 resize-none h-32"
                  />
                </div>

                {/* 자격증 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🏆 자격증
                  </h3>
                  <textarea
                    value={currentResume.certificate}
                    disabled
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-gray-50 text-gray-700 resize-none h-24"
                  />
                </div>

                {/* 수상경력 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🥇 수상경력
                  </h3>
                  <textarea
                    value={currentResume.awards}
                    disabled
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-gray-50 text-gray-700 resize-none h-24"
                  />
                </div>
              </div>
            </div>
          );
        } else if (currentView === 'create' || currentView === 'edit') {
          return (
            <div className="space-y-6">
              <div className="flex items-center gap-4">
                <button
                  onClick={handleBackToList}
                  className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                >
                  ←
                </button>
                <h2 className="text-2xl font-bold text-slate-900">
                  {currentView === 'create' ? '이력서 작성' : '이력서 수정'}
                </h2>
              </div>

              <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-6">
                {/* 기본 정보 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    👤 기본 정보
                  </h3>
                  
                  {/* 지원 직군 선택 */}
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-slate-700 mb-2">지원 직군 *</label>
                    {positionsLoading ? (
                      <div className="flex items-center justify-center py-3 border border-slate-300 rounded-lg">
                        <LoadingSpinner size="sm" />
                        <span className="ml-2 text-slate-500">직군 목록 로딩 중...</span>
                      </div>
                    ) : (
                      <select
                        value={currentResume.position_id || 0}
                        onChange={(e) => handleResumeUpdate('position_id', parseInt(e.target.value))}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value={0} disabled>직군을 선택해주세요</option>
                        {positions.map(position => (
                          <option key={position.position_id} value={position.position_id}>
                            {position.position_name}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                  
                  {/* 이름은 로그인된 사용자 이름 표시 */}
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">지원자명</label>
                    <input
                      type="text"
                      value={user?.name || ''}
                      disabled
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed"
                      placeholder="로그인된 사용자명"
                    />
                  </div>
                </div>

                {/* 학력 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🎓 학력 *
                  </h3>
                  <textarea
                    value={currentResume.academic_record}
                    onChange={(e) => handleResumeUpdate('academic_record', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-24"
                    placeholder="예: 2020년 서울대학교 컴퓨터공학과 졸업 (학점: 3.8/4.5)"
                  />
                </div>

                {/* 경력 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    💼 경력 *
                  </h3>
                  <textarea
                    value={currentResume.career}
                    onChange={(e) => handleResumeUpdate('career', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-32"
                    placeholder="예: 2021-2023 네이버 - 프론트엔드 개발자&#10;• React 기반 웹 서비스 개발&#10;• 사용자 경험 개선으로 전환율 20% 향상"
                  />
                </div>

                {/* 기술스택 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    💻 기술스택 *
                  </h3>
                  <textarea
                    value={currentResume.tech}
                    onChange={(e) => handleResumeUpdate('tech', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-24"
                    placeholder="예: JavaScript, React, TypeScript, Node.js, Python, Docker"
                  />
                </div>

                {/* 활동/경험 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🚀 활동/경험
                  </h3>
                  <textarea
                    value={currentResume.activities}
                    onChange={(e) => handleResumeUpdate('activities', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-32"
                    placeholder="예: 오픈소스 프로젝트 기여, 개발 동아리 활동, 사이드 프로젝트 등"
                  />
                </div>

                {/* 자격증 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🏆 자격증
                  </h3>
                  <textarea
                    value={currentResume.certificate}
                    onChange={(e) => handleResumeUpdate('certificate', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-24"
                    placeholder="예: 정보처리기사 (2021.05), AWS SAA (2022.03)"
                  />
                </div>

                {/* 수상경력 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🥇 수상경력
                  </h3>
                  <textarea
                    value={currentResume.awards}
                    onChange={(e) => handleResumeUpdate('awards', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-24"
                    placeholder="예: 2022 해커톤 대상, 2021 프로그래밍 경진대회 우수상"
                  />
                </div>
              </div>

              <div className="text-sm text-slate-500 text-center">
                * 표시된 항목은 필수 입력 사항입니다.
              </div>

              {/* 저장 버튼 */}
              <div className="flex justify-center pt-6">
                <button
                  onClick={handleResumeSave}
                  disabled={resumesLoading}
                  className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-lg font-medium"
                >
                  {resumesLoading ? (
                    <div className="flex items-center gap-2">
                      <LoadingSpinner size="sm" color="white" />
                      저장 중...
                    </div>
                  ) : (
                    '💾 저장하기'
                  )}
                </button>
              </div>
            </div>
          );
        }
        break;


      case 'interview-history':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-slate-900">면접 히스토리</h2>
              <div className="flex gap-2">
                <button 
                  onClick={() => refreshHistory()}
                  disabled={historyLoading}
                  className="bg-slate-100 text-slate-600 px-3 py-2 rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  {historyLoading ? (
                    <>
                      <LoadingSpinner size="sm" />
                      새로고침 중...
                    </>
                  ) : (
                    <>
                      🔄 새로고침
                    </>
                  )}
                </button>
                <button 
                  onClick={() => navigate('/interview/job-posting')}
                  className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors"
                >
                  🚀 새 면접 시작
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">면접 통계</h3>
              {historyLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner size="sm" />
                  <span className="ml-2 text-slate-500">통계 로딩 중...</span>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">{interviewStats.totalInterviews}</div>
                    <div className="text-sm text-slate-600">총 면접 횟수</div>
                  </div>
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">
                      {interviewStats.averageScore}
                    </div>
                    <div className="text-sm text-slate-600">평균 점수</div>
                  </div>
                  <div className="text-center p-4 bg-purple-50 rounded-lg">
                    <div className="text-2xl font-bold text-purple-600">
                      {interviewHistory.filter(interview => interview.score >= 80).length}
                    </div>
                    <div className="text-sm text-slate-600">80점 이상</div>
                  </div>
                </div>
              )}
            </div>

            {historyLoading ? (
              <div className="flex justify-center py-12">
                <LoadingSpinner size="lg" />
                <span className="ml-3 text-slate-600">면접 기록을 불러오는 중...</span>
              </div>
            ) : historyError ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">⚠️</div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">면접 기록을 불러올 수 없습니다</h3>
                <p className="text-slate-600 mb-4">{historyError}</p>
                <button 
                  onClick={() => refreshHistory()}
                  disabled={historyLoading}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {historyLoading ? '다시 시도 중...' : '다시 시도'}
                </button>
              </div>
            ) : interviewHistory.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">📊</div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">아직 면접 기록이 없습니다</h3>
                <p className="text-slate-600 mb-6">첫 면접을 시작해보세요!</p>
                <button 
                  onClick={() => navigate('/interview/job-posting')}
                  className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors"
                >
                  🚀 면접 시작하기
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {interviewHistory.map(interview => (
                  <div key={interview.session_id} className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center text-white font-bold">
                          {interview.company.charAt(0)}
                        </div>
                        <div>
                          <h3 className="font-semibold text-slate-900">{interview.company}</h3>
                          <p className="text-slate-600">{interview.position}</p>
                          <p className="text-sm text-slate-500">{interview.date} {interview.time}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className={`px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(interview.score)}`}>
                          {interview.score}점
                        </div>
                        {getStatusBadge(interview.status)}
                        <button 
                          onClick={() => {
                            console.log('🔍 ProfilePage 결과 보기 클릭:', interview.session_id);
                            if (!interview.session_id) {
                              console.error('❌ session_id가 없습니다:', interview);
                              alert('면접 결과를 불러올 수 없습니다. 데이터가 손상되었을 수 있습니다.');
                              return;
                            }
                            navigate(`/interview/results/${interview.session_id}`);
                          }}
                          className="text-blue-600 hover:text-blue-700 px-3 py-1 rounded text-sm"
                        >
                          결과 보기
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case 'personal-info':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-slate-900">개인정보 관리</h2>
            
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              <div className="flex items-center space-x-6 mb-6">
                <div className="w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center">
                  {userInfo.profileImage ? (
                    <img src={userInfo.profileImage} alt="프로필" className="w-20 h-20 rounded-full object-cover" />
                  ) : (
                    <span className="text-gray-500 text-2xl">👤</span>
                  )}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">{userInfo.name}</h3>
                  <p className="text-slate-600">{userInfo.email}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">이름</label>
                  <input
                    type="text"
                    value={userInfo.name}
                    onChange={(e) => handleUserInfoUpdate('name', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">이메일</label>
                  <input
                    type="email"
                    value={userInfo.email}
                    onChange={(e) => handleUserInfoUpdate('email', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-slate-200">
                <h4 className="text-lg font-semibold text-slate-900 mb-4">계정 설정</h4>
                <div className="space-y-4">
                  <button 
                    onClick={handleUserInfoSave}
                    disabled={authLoading}
                    className="w-full md:w-auto bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {authLoading ? '저장 중...' : '정보 저장'}
                  </button>
                </div>
              </div>

            </div>
          </div>
        );

      default:
        return null;
    }
  };

  // 인증 로딩 중이거나 사용자 정보가 없으면 로딩 표시
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header title="마이페이지" subtitle="내 프로필과 면접 기록을 관리하세요" />
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="lg" />
          <p className="ml-4 text-gray-600">사용자 정보를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header title="마이페이지" subtitle="내 프로필과 면접 기록을 관리하세요" />
        <div className="flex items-center justify-center h-96">
          <p className="text-gray-600">사용자 정보를 찾을 수 없습니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="마이페이지"
        subtitle="내 프로필과 면접 기록을 관리하세요"
      />
      
      <main className="container mx-auto px-6 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* 사이드바 */}
          <div className="lg:w-80 flex-shrink-0">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-6 sticky top-24">
              <div className="text-center mb-6">
                <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-3">
                  {user.name.charAt(0)}
                </div>
                <h3 className="font-bold text-slate-900">{user.name}</h3>
              </div>

              <nav className="space-y-2">
                {sidebarMenus.map(menu => (
                  <button
                    key={menu.id}
                    onClick={() => setActiveTab(menu.id)}
                    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                      activeTab === menu.id
                        ? 'bg-blue-50 border-2 border-blue-200 text-blue-700'
                        : 'hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <span className="text-lg">{menu.icon}</span>
                    <span className="font-medium">{menu.label}</span>
                  </button>
                ))}
              </nav>

            </div>
          </div>

          {/* 메인 콘텐츠 */}
          <div className="flex-1">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-8 min-h-[600px]">
              {isLoading ? (
                <div className="flex items-center justify-center h-96">
                  <LoadingSpinner size="lg" message="로딩 중..." />
                </div>
              ) : (
                renderContent()
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ProfilePage;