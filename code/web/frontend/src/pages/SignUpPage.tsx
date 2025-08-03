import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { authApi, handleApiError } from '../services/api';
import { useAuth } from '../hooks/useAuth';

// 비밀번호 유효성 검사 함수 (백엔드와 동일한 로직)
interface PasswordValidation {
  isValid: boolean;
  errors: string[];
  checks: {
    length: boolean;
    uppercase: boolean;
    lowercase: boolean;
    special: boolean;
  };
}

const validatePassword = (password: string): PasswordValidation => {
  const checks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
  };

  const errors: string[] = [];
  if (!checks.length) errors.push('비밀번호는 8자 이상이어야 합니다.');
  if (!checks.uppercase) errors.push('비밀번호에 대문자가 포함되어야 합니다.');
  if (!checks.lowercase) errors.push('비밀번호에 소문자가 포함되어야 합니다.');
  if (!checks.special) errors.push('비밀번호에 특수문자가 포함되어야 합니다.');

  return {
    isValid: Object.values(checks).every(check => check),
    errors,
    checks
  };
};

const SignUpPage: React.FC = () => {
  const navigate = useNavigate();
  const { signup } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    code: '',
    password: '',
    passwordConfirm: '',
    name: ''
  });
  const [error, setError] = useState('');
  const [emailSent, setEmailSent] = useState(false);
  const [codeVerified, setCodeVerified] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [infoMessage, setInfoMessage] = useState('');
  const [verifyMessage, setVerifyMessage] = useState('');
  const [passwordValidation, setPasswordValidation] = useState<PasswordValidation>({
    isValid: false,
    errors: [],
    checks: { length: false, uppercase: false, lowercase: false, special: false }
  });
  const [showPasswordRequirements, setShowPasswordRequirements] = useState(false);

  // 입력 변경 핸들러
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError('');
    if (name === 'email') setEmailError('');
    if (name === 'code') setVerifyMessage(''); // Remove setCodeError('');
    if (name === 'password') {
      const validation = validatePassword(value);
      setPasswordValidation(validation);
      setShowPasswordRequirements(value.length > 0);
    }
    setInfoMessage('');
    setVerifyMessage('');
  };

  // 인증받기 클릭 - 실제 OTP 발송
  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(formData.email)) {
      setEmailError('올바른 이메일을 입력하세요.');
      setInfoMessage('');
      return;
    }
    
    setIsLoading(true);
    setEmailError('');
    setInfoMessage('');
    
    try {
      // 실제 OTP 발송 API 호출
      const result = await authApi.sendOtp(formData.email);
      if (result.success) {
        setEmailSent(true);
        setInfoMessage('인증번호가 이메일로 발송되었습니다. 이메일을 확인해주세요.');
      }
    } catch (error: any) {
      const errorMessage = handleApiError(error);
      setEmailError(errorMessage);
      console.error('OTP 발송 실패:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // 인증확인 클릭 - 실제 OTP 검증
  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.code || formData.code.length < 4) {
      setVerifyMessage('인증번호를 입력해주세요.');
      return;
    }
    
    setIsLoading(true);
    setVerifyMessage('');
    
    try {
      // 실제 OTP 검증 API 호출
      const result = await authApi.verifyOtp(formData.email, formData.code);
      if (result.success && result.verified) {
        setCodeVerified(true);
        setVerifyMessage('인증이 완료되었습니다!');
      }
    } catch (error: any) {
      const errorMessage = handleApiError(error);
      setVerifyMessage(errorMessage);
      console.error('OTP 검증 실패:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // 회원가입 클릭
  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // 유효성 검사
    if (!codeVerified) {
      setError('이메일 인증을 완료해주세요.');
      return;
    }
    if (!passwordValidation.isValid) {
      setError('비밀번호 조건을 모두 충족해주세요.');
      return;
    }
    if (formData.password !== formData.passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }
    if (!formData.name.trim()) {
      setError('이름을 입력하세요.');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // useAuth의 signup 함수 사용
      const result = await signup(formData.name, formData.email, formData.password);

      if (result.success) {
        // 회원가입 성공 처리
        if (result.response?.access_token) {
          // 토큰이 있으면 자동 로그인 처리되었으므로 홈으로 이동
          navigate('/');
        } else {
          // 이메일 인증이 필요한 경우
          setInfoMessage('이메일로 인증 링크가 전송되었습니다. 이메일을 확인하여 인증을 완료해주세요.');
          setTimeout(() => {
            navigate('/login');
          }, 3000);
        }
      } else {
        // 에러 처리
        setError(result.error || '회원가입에 실패했습니다.');
      }
      
    } catch (error: any) {
      // 예상치 못한 에러 처리
      const errorMessage = handleApiError(error);
      setError(errorMessage);
      console.error('회원가입 실패:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header title="회원가입" subtitle="Beta-GO Interview에 오신 것을 환영합니다" />
      <main className="container mx-auto px-6 py-12">
        <div className="max-w-md mx-auto">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 border border-slate-200 shadow-lg">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold text-slate-900 mb-2">회원가입</h1>
              <p className="text-slate-600">이메일 인증 후 정보를 입력하세요</p>
            </div>
            <form className="space-y-6" onSubmit={handleSignUp}>
              {/* 이메일 + 인증받기 */}
              <div className="flex gap-2">
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                  placeholder="이메일을 입력하세요"
                  required
                  disabled={codeVerified}
                />
                <button
                  type="button"
                  onClick={handleSendCode}
                  disabled={isLoading || codeVerified}
                  className="px-4 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition-all disabled:opacity-50"
                >
                  {isLoading && !codeVerified ? <LoadingSpinner size="sm" color="white" /> : '인증받기'}
                </button>
              </div>
              {emailError && <div className="mb-2 text-center text-red-600 font-semibold text-sm">{emailError}</div>}
              {infoMessage && <div className="mb-2 text-center text-blue-600 font-semibold text-sm">{infoMessage}</div>}

              {/* 인증번호 + 인증확인 */}
              <div className="flex gap-2">
                <input
                  type="text"
                  name="code"
                  value={formData.code}
                  onChange={handleInputChange}
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                  placeholder="인증번호 입력"
                  required
                  disabled={!emailSent || codeVerified}
                />
                <button
                  type="button"
                  onClick={handleVerifyCode}
                  disabled={!emailSent || codeVerified}
                  className="px-4 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition-all disabled:opacity-50"
                >
                  인증확인
                </button>
              </div>
              {verifyMessage && (
                <div className={`mb-2 text-center font-semibold text-sm ${verifyMessage.includes('완료') ? 'text-green-600' : 'text-red-600'}`}>{verifyMessage}</div>
              )}

              {/* PW, PW 확인, 이름 */}
              <div>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                  placeholder="패스워드 (8자 이상, 대문자, 소문자, 특수문자 포함)"
                  required
                  disabled={!codeVerified}
                />
                {/* 비밀번호 요구사항 체크리스트 */}
                {showPasswordRequirements && (
                  <div className="mt-2 p-3 bg-gray-50 rounded-lg border">
                    <p className="text-sm font-medium text-gray-700 mb-2">비밀번호 요구사항:</p>
                    <div className="grid grid-cols-1 gap-1 text-sm">
                      <div className={`flex items-center gap-2 ${passwordValidation.checks.length ? 'text-green-600' : 'text-red-500'}`}>
                        <span className="text-xs">{passwordValidation.checks.length ? '✓' : '✗'}</span>
                        <span>8자 이상</span>
                      </div>
                      <div className={`flex items-center gap-2 ${passwordValidation.checks.uppercase ? 'text-green-600' : 'text-red-500'}`}>
                        <span className="text-xs">{passwordValidation.checks.uppercase ? '✓' : '✗'}</span>
                        <span>대문자 포함 (A-Z)</span>
                      </div>
                      <div className={`flex items-center gap-2 ${passwordValidation.checks.lowercase ? 'text-green-600' : 'text-red-500'}`}>
                        <span className="text-xs">{passwordValidation.checks.lowercase ? '✓' : '✗'}</span>
                        <span>소문자 포함 (a-z)</span>
                      </div>
                      <div className={`flex items-center gap-2 ${passwordValidation.checks.special ? 'text-green-600' : 'text-red-500'}`}>
                        <span className="text-xs">{passwordValidation.checks.special ? '✓' : '✗'}</span>
                        <span>특수문자 포함 (!@#$%^&* 등)</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div>
                <input
                  type="password"
                  name="passwordConfirm"
                  value={formData.passwordConfirm}
                  onChange={handleInputChange}
                  className={`w-full px-4 py-3 rounded-xl border ${
                    formData.passwordConfirm && formData.password !== formData.passwordConfirm 
                      ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                      : formData.passwordConfirm && formData.password === formData.passwordConfirm 
                      ? 'border-green-300 focus:border-green-500 focus:ring-green-500'
                      : 'border-slate-300 focus:border-blue-500 focus:ring-blue-500'
                  } bg-white focus:ring-2 focus:outline-none transition-all`}
                  placeholder="패스워드 확인"
                  required
                  disabled={!codeVerified}
                />
                {formData.passwordConfirm && (
                  <div className={`mt-1 text-sm ${
                    formData.password === formData.passwordConfirm 
                      ? 'text-green-600' 
                      : 'text-red-500'
                  }`}>
                    {formData.password === formData.passwordConfirm ? '✓ 비밀번호가 일치합니다' : '✗ 비밀번호가 일치하지 않습니다'}
                  </div>
                )}
              </div>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                placeholder="이름"
                required
                disabled={!codeVerified}
              />
              {error && <div className="mb-2 text-center text-red-600 font-semibold text-sm">{error}</div>}
              <button
                type="submit"
                disabled={!codeVerified || isLoading || !passwordValidation.isValid || formData.password !== formData.passwordConfirm || !formData.name.trim()}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 rounded-xl font-bold text-lg hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center gap-2">
                    <LoadingSpinner size="sm" color="white" /> 회원가입 중...
                  </div>
                ) : (
                  '회원가입'
                )}
              </button>
            </form>
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

export default SignUpPage; 