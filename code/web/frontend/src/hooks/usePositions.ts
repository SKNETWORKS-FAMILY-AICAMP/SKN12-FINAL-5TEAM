import { useState, useEffect, useCallback } from 'react';
import { positionApi, Position, handleApiError } from '../services/api';

interface UsePositionsReturn {
  positions: Position[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// 전역 캐싱을 위한 변수들
let cachedPositions: Position[] | null = null;
let cacheTimestamp: number | null = null;
let isPositionsFetching = false; // 중복 요청 방지 플래그
const CACHE_DURATION = 5 * 60 * 1000; // 5분 캐시

export const usePositions = (): UsePositionsReturn => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPositions = useCallback(async () => {
    try {
      setError(null);
      
      // 캐시된 데이터가 있고 유효한 경우 즉시 반환
      const now = Date.now();
      if (cachedPositions && cacheTimestamp && (now - cacheTimestamp) < CACHE_DURATION) {
        setPositions(cachedPositions);
        setLoading(false);
        return; // API 호출 없이 즉시 반환
      }

      // 이미 요청 중인 경우 중복 요청 방지
      if (isPositionsFetching) {
        return;
      }

      isPositionsFetching = true;
      setLoading(true);
      
      const positionsData = await positionApi.getPositions();
      
      // 데이터 캐싱
      cachedPositions = positionsData;
      cacheTimestamp = now;
      
      setPositions(positionsData);
    } catch (err) {
      console.error('직군 데이터 로딩 실패:', err);
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      
      // 에러 발생 시 빈 배열로 설정
      setPositions([]);
    } finally {
      setLoading(false);
      isPositionsFetching = false; // 요청 완료 후 플래그 해제
    }
  }, []);

  const refetch = useCallback(async () => {
    // 캐시 무효화 후 재요청
    cachedPositions = null;
    cacheTimestamp = null;
    isPositionsFetching = false; // 플래그도 초기화
    await fetchPositions();
  }, [fetchPositions]);

  useEffect(() => {
    fetchPositions();
  }, [fetchPositions]);

  return {
    positions,
    loading,
    error,
    refetch,
  };
};