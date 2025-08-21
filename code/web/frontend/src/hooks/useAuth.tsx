import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi, tokenManager, UserProfile, handleApiError } from '../services/api';
import { supabase } from '../lib/supabase';

interface AuthState {
  isAuthenticated: boolean;
  user: UserProfile | null;
  isLoading: boolean;
}

export const useAuth = () => {
  const navigate = useNavigate();
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    isLoading: true
  });

  // 인증 상태 확인 함수
  const checkAuthStatus = () => {
    const token = tokenManager.getToken();
    const user = tokenManager.getUser();
    
    if (token && user) {
      setAuthState({
        isAuthenticated: true,
        user: user,
        isLoading: false
      });
    } else {
      setAuthState({
        isAuthenticated: false,
        user: null,
        isLoading: false
      });
    }
  };

  // 컴포넌트 마운트 시 인증 상태 확인
  useEffect(() => {
    checkAuthStatus();
    
    // Supabase 세션 상태 변화 감지
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('🔄 Supabase Auth 상태 변화:', event, session?.user?.email);
        
        if (event === 'SIGNED_IN' && session) {
          // OAuth 로그인 완료 시 백엔드 동기화는 OAuthCallbackPage에서 처리
          console.log('✅ Supabase 로그인 세션 감지');
        } else if (event === 'SIGNED_OUT') {
          // 로그아웃 시 로컬 상태 정리
          tokenManager.clearAuth();
          setAuthState({
            isAuthenticated: false,
            user: null,
            isLoading: false
          });
        }
      }
    );

    // 정리 함수
    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // 로그인 함수 (리다이렉트 지원)
  const login = async (email: string, password: string, redirectPath?: string) => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }));
      
      const response = await authApi.login({ email, pw: password });
      
      // 토큰과 사용자 정보 저장
      tokenManager.setToken(response.access_token);
      tokenManager.setUser(response.user);
      
      // 상태 업데이트
      setAuthState({
        isAuthenticated: true,
        user: response.user,
        isLoading: false
      });

      // 로그인 성공 후 리다이렉트 처리
      if (redirectPath && redirectPath !== '/login') {
        navigate(redirectPath);
      } else {
        navigate('/');
      }

      return { success: true };
    } catch (error: any) {
      setAuthState(prev => ({ ...prev, isLoading: false }));
      
      // 에러를 완전히 잡아서 절대 다시 throw하지 않음
      console.error('Login error:', error);
      const errorMessage = handleApiError(error);
      return { success: false, error: errorMessage };
    }
  };

  // 로그아웃 함수
  const logout = async () => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }));
      
      // 서버에 로그아웃 요청 (토큰이 있는 경우)
      if (tokenManager.getToken()) {
        try {
          await authApi.logout();
        } catch (error) {
          // 서버 로그아웃 실패해도 로컬 로그아웃 진행
          console.warn('서버 로그아웃 실패, 로컬 로그아웃 진행:', error);
        }
      }
      
      // 로컬 토큰 및 사용자 정보 삭제
      tokenManager.clearAuth();
      
      // 상태 업데이트
      setAuthState({
        isAuthenticated: false,
        user: null,
        isLoading: false
      });

      // 로그인 페이지로 이동
      navigate('/login');
      
      return { success: true };
    } catch (error: any) {
      setAuthState(prev => ({ ...prev, isLoading: false }));
      const errorMessage = handleApiError(error);
      return { success: false, error: errorMessage };
    }
  };

  // 회원가입 함수
  const signup = async (name: string, email: string, password: string) => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }));
      
      const response = await authApi.signup({ name, email, pw: password });
      
      // 회원가입 후 자동 로그인 처리
      if (response.access_token) {
        tokenManager.setToken(response.access_token);
        tokenManager.setUser(response.user);
        
        setAuthState({
          isAuthenticated: true,
          user: response.user,
          isLoading: false
        });
      } else {
        setAuthState(prev => ({ ...prev, isLoading: false }));
      }

      return { success: true, response };
    } catch (error: any) {
      setAuthState(prev => ({ ...prev, isLoading: false }));
      const errorMessage = handleApiError(error);
      return { success: false, error: errorMessage };
    }
  };

  // 인증 상태 새로고침 (토큰 검증)
  const refreshAuthStatus = async () => {
    try {
      const token = tokenManager.getToken();
      if (!token) {
        setAuthState({
          isAuthenticated: false,
          user: null,
          isLoading: false
        });
        return;
      }

      const response = await authApi.verifyToken();
      if (response.valid) {
        const user = tokenManager.getUser();
        setAuthState({
          isAuthenticated: true,
          user: user,
          isLoading: false
        });
      } else {
        // 토큰이 유효하지 않으면 로그아웃 처리
        tokenManager.clearAuth();
        setAuthState({
          isAuthenticated: false,
          user: null,
          isLoading: false
        });
      }
    } catch (error) {
      // 토큰 검증 실패 시 로그아웃 처리
      tokenManager.clearAuth();
      setAuthState({
        isAuthenticated: false,
        user: null,
        isLoading: false
      });
    }
  };


  return {
    ...authState,
    login,
    logout,
    signup,
    refreshAuthStatus,
    checkAuthStatus
  };
};