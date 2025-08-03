import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { handleApiError } from '../services/api';
import { useAuth } from '../hooks/useAuth';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  
  // URL에서 redirect 파라미터 가져오기
  const redirectPath = searchParams.get('redirect') || '/';
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [error, setError] = useState('');

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    setError(''); // 입력 변경 시 에러 메시지 초기화
  };

  // 폼 유효성 검증 함수
  const validateForm = () => {
    const { email, password } = formData;
    
    if (!email.trim()) {
      setError('이메일을 입력해주세요.');
      return false;
    }
    
    if (!email.includes('@') || !email.includes('.')) {
      setError('올바른 이메일 주소를 입력해주세요.');
      return false;
    }
    
    if (!password.trim()) {
      setError('비밀번호를 입력해주세요.');
      return false;
    }
    
    if (password.length < 6) {
      setError('비밀번호는 6자 이상 입력해주세요.');
      return false;
    }
    
    return true;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // 서버 요청 전 미리 검증
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const { email, password } = formData;
      const result = await login(email, password, redirectPath);

      if (!result.success) {
        // 에러 메시지를 사용자 친화적으로 변환
        const userFriendlyError = result.error?.includes('validation')
          ? '이메일 형식이 올바르지 않거나 비밀번호가 너무 짧습니다.'
          : result.error || '로그인에 실패했습니다.';
        
        setError(userFriendlyError);
      }
    } catch (error: any) {
      // 혹시 모를 예외도 완전히 차단
      console.error('Unexpected login error:', error);
      setError('로그인 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialLogin = (provider: string) => {
    alert(`${provider} 로그인 기능은 준비 중입니다.`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="로그인"
        subtitle="Beta-GO Interview에 오신 것을 환영합니다"
      />
      
      <main className="container mx-auto px-6 py-12">
        <div className="max-w-md mx-auto">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 border border-slate-200 shadow-lg">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold text-slate-900 mb-2">로그인</h1>
              <p className="text-slate-600">
                {redirectPath !== '/' ? 
                  '로그인 후 요청하신 페이지로 이동합니다' : 
                  '계정에 로그인하여 면접을 시작하세요'
                }
              </p>
              {redirectPath !== '/' && (
                <p className="text-sm text-blue-600 mt-1">
                  이동할 페이지: {redirectPath}
                </p>
              )}
            </div>

            <form onSubmit={handleLogin} className="space-y-6">
              {/* 에러 메시지 */}
              {error && (
                <div className="mb-2 text-center text-red-600 font-semibold text-sm">
                  {error}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  이메일
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                  placeholder="이메일을 입력하세요"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  비밀번호
                </label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                  placeholder="비밀번호를 입력하세요"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 rounded-xl font-bold text-lg hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center gap-2">
                    <LoadingSpinner size="sm" color="white" />
                    로그인 중...
                  </div>
                ) : (
                  '로그인'
                )}
              </button>
            </form>

            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-300"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-slate-500">또는</span>
                </div>
              </div>

              <div className="mt-6 space-y-3">
                <button
                  onClick={() => handleSocialLogin('Google')}
                  className="w-full flex items-center justify-center gap-3 py-3 px-4 border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Google로 로그인
                </button>

                <button
                  onClick={() => handleSocialLogin('Kakao')}
                  className="w-full flex items-center justify-center gap-3 py-3 px-4 bg-yellow-400 text-black rounded-xl hover:bg-yellow-500 transition-colors"
                >
                  <span className="text-lg">💬</span>
                  카카오로 로그인
                </button>
              </div>
            </div>

            <div className="mt-8 text-center">
              <p className="text-sm text-slate-600">
                계정이 없으신가요?{' '}
                <button 
                  onClick={() => navigate('/signup')}
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  회원가입
                </button>
              </p>
            </div>
          </div>

          <div className="mt-8 text-center">
            <button
              onClick={() => navigate('/')}
              className="text-slate-600 hover:text-slate-800 text-sm"
            >
              홈으로 돌아가기
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default LoginPage;