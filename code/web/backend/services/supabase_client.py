"""
Supabase 클라이언트 설정 및 관리
"""

import os
from supabase import create_client, Client
from typing import Optional
import logging

# 로거 설정
logger = logging.getLogger(__name__)

class SupabaseClient:
    """Supabase 클라이언트 싱글톤"""
    
    _instance: Optional['SupabaseClient'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Supabase 클라이언트 초기화"""
        try:
            # 환경변수에서 설정 로드
            supabase_url = os.getenv('SUPABASE_URL', 'https://neephzhkioahjrjmawlp.supabase.co')
            supabase_key = os.getenv(
                'SUPABASE_ANON_KEY', 
                'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5lZXBoemhraW9haGpyam1hd2xwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIyMTIwODcsImV4cCI6MjA2Nzc4ODA4N30.o4uLLdGxFclnRi-FEBeaEVCUklstLPIF6JRVM1pNLBc'
            )
            
            if not supabase_url or not supabase_key:
                raise ValueError("Supabase URL 또는 API 키가 설정되지 않았습니다.")
            
            self._client = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase 클라이언트 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ Supabase 클라이언트 초기화 실패: {str(e)}")
            raise
    
    @property
    def client(self) -> Client:
        """Supabase 클라이언트 반환"""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def health_check(self) -> bool:
        """Supabase 연결 상태 확인"""
        try:
            # 간단한 쿼리로 연결 테스트
            result = self.client.table('interviews').select('count').limit(1).execute()
            logger.info("✅ Supabase 연결 상태 양호")
            return True
        except Exception as e:
            logger.error(f"❌ Supabase 연결 실패: {str(e)}")
            return False

# 전역 클라이언트 인스턴스
supabase_client = SupabaseClient()

def get_supabase_client() -> Client:
    """Supabase 클라이언트 의존성 주입용 함수"""
    return supabase_client.client