import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { supabase } from '../lib/supabase';
import { tokenManager } from '../services/api';

// API Base URL 설정
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const OAuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const { checkAuthStatus } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('');
  const isProcessing = useRef(false);

  const handleOAuthCallback = useCallback(async () => {
    // 중복 실행 방지 체크
    if (isProcessing.current) {
      console.log('🚫 OAuth 콜백이 이미 처리 중입니다. 중복 실행을 방지합니다.');
      return;
    }

    isProcessing.current = true;
    
    try {
      // Supabase에서 OAuth 세션 확인
      const { data: { session }, error } = await supabase.auth.getSession();
      
      if (error) {
        throw new Error(`OAuth 세션 확인 실패: ${error.message}`);
      }

      if (!session) {
        throw new Error('OAuth 세션을 찾을 수 없습니다.');
      }

      // 백엔드에 사용자 동기화 요청
      const response = await fetch(`${API_BASE_URL}/auth/oauth/complete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`사용자 동기화 실패: ${response.status}`);
      }

      const userData = await response.json();

      // tokenManager에 토큰과 사용자 정보 저장
      if (userData.access_token && userData.user) {
        tokenManager.setToken(userData.access_token);
        tokenManager.setUser(userData.user);
      } else {
        throw new Error('백엔드에서 토큰 또는 사용자 정보를 받지 못했습니다.');
      }

      // 인증 상태 업데이트
      await checkAuthStatus();
      setStatus('success');

      // 성공 후 홈으로 이동
      setTimeout(() => {
        navigate('/');
      }, 1500);

    } catch (error: any) {
      setErrorMessage(error.message || 'OAuth 로그인 처리 중 오류가 발생했습니다.');
      setStatus('error');

      // 실패 시 로그인 페이지로 이동
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } finally {
      // 성공/실패와 관계없이 처리 완료 표시 유지 (재실행 방지)
      // isProcessing.current = false; // 의도적으로 리셋하지 않음 (재실행 완전 방지)
    }
  }, [navigate, checkAuthStatus]);

  useEffect(() => {
    handleOAuthCallback();
  }, [handleOAuthCallback]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 flex items-center justify-center">
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 border border-slate-200 shadow-lg text-center max-w-md w-full">
        {status === 'loading' && (
          <>
            <LoadingSpinner size="lg" color="primary" />
            <h2 className="text-xl font-bold text-slate-900 mt-4 mb-2">
              로그인 처리 중...
            </h2>
            <p className="text-slate-600">
              소셜 로그인을 완료하고 있습니다.
            </p>
          </>
        )}
        
        {status === 'success' && (
          <>
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-slate-900 mb-2">
              로그인 완료!
            </h2>
            <p className="text-slate-600">
              메인 페이지로 이동합니다...
            </p>
          </>
        )}
        
        {status === 'error' && (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-slate-900 mb-2">
              로그인 실패
            </h2>
            <p className="text-slate-600 mb-4">
              {errorMessage}
            </p>
            <p className="text-sm text-slate-500">
              로그인 페이지로 돌아갑니다...
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default OAuthCallbackPage;