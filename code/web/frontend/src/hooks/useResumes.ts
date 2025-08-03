import { useState, useEffect, useCallback } from 'react';
import { resumeApi, ResumeResponse, ResumeCreate, handleApiError } from '../services/api';
import { useAuth } from './useAuth';

interface UseResumesReturn {
  resumes: ResumeResponse[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  createResume: (data: ResumeCreate) => Promise<ResumeResponse | null>;
  updateResume: (id: number, data: ResumeCreate) => Promise<ResumeResponse | null>;
  deleteResume: (id: number) => Promise<boolean>;
}

// 전역 캐싱을 위한 변수들
let cachedResumes: ResumeResponse[] | null = null;
let cacheTimestamp: number | null = null;
let cachedUserId: number | null = null; // 사용자별 캐싱을 위해
const CACHE_DURATION = 5 * 60 * 1000; // 5분 캐시

export const useResumes = (): UseResumesReturn => {
  const { isAuthenticated, user } = useAuth();
  const [resumes, setResumes] = useState<ResumeResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchResumes = useCallback(async () => {
    if (!isAuthenticated || !user) {
      setResumes([]);
      setLoading(false);
      return;
    }

    try {
      setError(null);
      
      // 캐시된 데이터가 있고 유효한 경우 사용
      const now = Date.now();
      if (cachedResumes && 
          cacheTimestamp && 
          cachedUserId === user.user_id && 
          (now - cacheTimestamp) < CACHE_DURATION) {
        setResumes(cachedResumes);
        setLoading(false);
        return;
      }

      setLoading(true);
      const resumesData = await resumeApi.getResumes();
      
      // 데이터 캐싱
      cachedResumes = resumesData;
      cacheTimestamp = now;
      cachedUserId = user.user_id;
      
      setResumes(resumesData);
    } catch (err) {
      console.error('이력서 데이터 로딩 실패:', err);
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      
      // 에러 발생 시 빈 배열로 설정
      setResumes([]);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, user]);

  const refetch = useCallback(async () => {
    // 캐시 무효화 후 재요청
    cachedResumes = null;
    cacheTimestamp = null;
    cachedUserId = null;
    await fetchResumes();
  }, [fetchResumes]);

  const createResume = useCallback(async (data: ResumeCreate): Promise<ResumeResponse | null> => {
    try {
      setError(null);
      const newResume = await resumeApi.createResume(data);
      
      // 로컬 상태 업데이트
      setResumes(prev => {
        const updated = [...prev, newResume];
        // 캐시도 업데이트
        cachedResumes = updated;
        cacheTimestamp = Date.now();
        return updated;
      });
      
      return newResume;
    } catch (err) {
      console.error('이력서 생성 실패:', err);
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      return null;
    }
  }, []);

  const updateResume = useCallback(async (id: number, data: ResumeCreate): Promise<ResumeResponse | null> => {
    try {
      setError(null);
      const updatedResume = await resumeApi.updateResume(id, data);
      
      // 로컬 상태 업데이트
      setResumes(prev => {
        const updated = prev.map(resume => 
          resume.user_resume_id === id ? updatedResume : resume
        );
        // 캐시도 업데이트
        cachedResumes = updated;
        cacheTimestamp = Date.now();
        return updated;
      });
      
      return updatedResume;
    } catch (err) {
      console.error('이력서 수정 실패:', err);
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      return null;
    }
  }, []);

  const deleteResume = useCallback(async (id: number): Promise<boolean> => {
    try {
      setError(null);
      await resumeApi.deleteResume(id);
      
      // 로컬 상태 업데이트
      setResumes(prev => {
        const updated = prev.filter(resume => resume.user_resume_id !== id);
        // 캐시도 업데이트
        cachedResumes = updated;
        cacheTimestamp = Date.now();
        return updated;
      });
      
      return true;
    } catch (err) {
      console.error('이력서 삭제 실패:', err);
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      return false;
    }
  }, []);

  useEffect(() => {
    fetchResumes();
  }, [fetchResumes]);

  return {
    resumes,
    loading,
    error,
    refetch,
    createResume,
    updateResume,
    deleteResume,
  };
};