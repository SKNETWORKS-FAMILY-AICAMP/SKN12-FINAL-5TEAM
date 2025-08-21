import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

interface HeaderProps {
  title?: string;
  subtitle?: string;
  showBackButton?: boolean;
  actions?: React.ReactNode;
  actionButton?: React.ReactNode;
}

const Header: React.FC<HeaderProps> = ({ 
  title = "Beta-GO Interview", 
  subtitle,
  showBackButton = false,
  actions,
  actionButton
}) => {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout, isLoading } = useAuth();

  // 로그아웃 핸들러
  const handleLogout = async () => {
    const result = await logout();
    if (!result.success) {
      console.error('로그아웃 실패:', result.error);
      // 에러가 있어도 로그인 페이지로 이동 (이미 logout 함수에서 처리됨)
    }
  };

  return (
    <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {showBackButton && (
              <button
                onClick={() => navigate(-1)}
                className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >
                <svg fill="currentColor" height="20px" viewBox="0 0 256 256" width="20px">
                  <path d="M224,128a8,8,0,0,1-8,8H59.31l58.35,58.34a8,8,0,0,1-11.32,11.32l-72-72a8,8,0,0,1,0-11.32l72-72a8,8,0,0,1,11.32,11.32L59.31,120H216A8,8,0,0,1,224,128Z"/>
                </svg>
              </button>
            )}
            
            <img 
              src="/img/beta_go.png" 
              alt="Beta-GO Interview 로고" 
              className="h-8 w-8 rounded"
            />
            
            <div>
              <h1 className="text-xl font-bold text-slate-900">{title}</h1>
              {subtitle && <p className="text-sm text-slate-600">{subtitle}</p>}
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {actionButton}
            {actions}
            
            <nav className="hidden md:flex items-center gap-8">
              <button 
                onClick={() => navigate('/')}
                className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
              >
                홈
              </button>
              {/* 면접 시작은 로그인 여부와 관계없이 표시 (ProtectedRoute에서 처리됨) */}
              <button 
                onClick={() => navigate('/interview/job-posting')}
                className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
              >
                면접 시작
              </button>
              
              {/* 로그인 상태에 따른 조건부 렌더링 */}
              {isAuthenticated ? (
                <>
                  {/* 로그인된 사용자: 사용자명 표시 (선택사항) */}
                  {user && (
                    <span className="text-sm font-medium text-slate-700">
                      {user.name}님
                    </span>
                  )}
                  <button 
                    onClick={handleLogout}
                    disabled={isLoading}
                    className="text-sm font-medium text-slate-600 hover:text-primary transition-colors disabled:opacity-50"
                  >
                    {isLoading ? '로그아웃 중...' : '로그아웃'}
                  </button>
                  <button 
                    onClick={() => navigate('/profile')}
                    className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
                  >
                    마이페이지
                  </button>
                </>
              ) : (
                <>
                  <button 
                    onClick={() => navigate('/login')}
                    className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
                  >
                    로그인
                  </button>
                  <button 
                    onClick={() => navigate('/signup')}
                    className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
                  >
                    회원가입
                  </button>
                </>
              )}
            </nav>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;