#!/usr/bin/env python3
"""
회사 데이터 로더
7개 회사 정보를 Supabase에서 로드하고 관리하는 클래스
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# 상위 디렉토리의 database 모듈 임포트를 위한 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))
from backend.services.supabase_client import get_supabase_client

class CompanyDataLoader:
    """회사 데이터 로딩 및 관리 클래스 (Supabase 연동)"""
    
    def __init__(self):
        """
        CompanyDataLoader 초기화 (Supabase 클라이언트 사용)
        """
        self.client = get_supabase_client()
        self._companies_data = None
        self._companies_dict = None
        self._load_companies_data()
    
    def _load_companies_data(self) -> None:
        """Supabase에서 회사 데이터를 로드합니다"""
        try:
            # Supabase에서 회사 데이터 조회
            result = self.client.table('company').select('*').execute()
            companies_raw = result.data if result.data else []
            
            # JSON 구조로 변환
            companies = []
            company_id_mapping = {
                '네이버': 'naver',
                '카카오': 'kakao', 
                '라인': 'line',
                '라인플러스': '라인플러스',  # Supabase DB 호환성
                '쿠팡': 'coupang',
                '배달의민족': 'baemin',
                '당근마켓': 'daangn',
                '토스': 'toss'
            }
            
            for company_raw in companies_raw:
                # JSON 문자열을 파싱
                core_competencies = json.loads(company_raw['core_competencies']) if company_raw['core_competencies'] else []
                tech_focus = json.loads(company_raw['tech_focus']) if company_raw['tech_focus'] else []
                interview_keywords = json.loads(company_raw['interview_keywords']) if company_raw['interview_keywords'] else []
                company_culture = json.loads(company_raw['company_culture']) if company_raw['company_culture'] else {}
                technical_challenges = json.loads(company_raw['technical_challenges']) if company_raw['technical_challenges'] else []
                
                company = {
                    "id": company_id_mapping.get(company_raw['name'], company_raw['name'].lower()),
                    "name": company_raw['name'],
                    "talent_profile": company_raw['talent_profile'],
                    "core_competencies": core_competencies,
                    "tech_focus": tech_focus,
                    "interview_keywords": interview_keywords,
                    "question_direction": company_raw['question_direction'],
                    "company_culture": company_culture,
                    "technical_challenges": technical_challenges
                }
                companies.append(company)
            
            self._companies_data = {"companies": companies}
            
            # 빠른 검색을 위한 딕셔너리 생성
            self._companies_dict = {
                company["id"]: company 
                for company in companies
            }
            
            print(f"회사 데이터 로드 완료 (Supabase): {len(self._companies_dict)}개 회사")
            
        except Exception as e:
            print(f"Supabase에서 회사 데이터 로드 실패: {str(e)}")
            self._companies_data = {"companies": []}
            self._companies_dict = {}
    
    def get_company_data(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 회사의 데이터를 가져옵니다
        
        Args:
            company_id: 회사 ID (예: 'naver', 'kakao', 'line', 'coupang', 'baemin', 'daangn', 'toss')
            
        Returns:
            회사 데이터 딕셔너리 또는 None
        """
        return self._companies_dict.get(company_id)
    
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """모든 회사 데이터를 반환합니다"""
        return self._companies_data.get("companies", [])
    
    def get_company_list(self) -> List[Dict[str, str]]:
        """회사 ID와 이름 목록을 반환합니다"""
        return [
            {"id": company["id"], "name": company["name"]} 
            for company in self._companies_data.get("companies", [])
        ]
    
    def get_company_culture(self, company_id: str) -> Optional[Dict[str, Any]]:
        """회사의 문화 정보를 가져옵니다"""
        company = self.get_company_data(company_id)
        return company.get("company_culture") if company else None
    
    def get_interviewer_personas(self, company_id: str) -> Optional[Dict[str, Any]]:
        """회사의 면접관 페르소나를 가져옵니다"""
        company = self.get_company_data(company_id)
        return company.get("interviewer_personas") if company else None
    
    def get_tech_focus(self, company_id: str) -> Optional[List[str]]:
        """회사의 기술 포커스 영역을 가져옵니다"""
        company = self.get_company_data(company_id)
        return company.get("tech_focus") if company else None
    
    def get_interview_keywords(self, company_id: str) -> Optional[List[str]]:
        """회사의 면접 키워드를 가져옵니다"""
        company = self.get_company_data(company_id)
        return company.get("interview_keywords") if company else None
    
    def get_technical_challenges(self, company_id: str) -> Optional[List[str]]:
        """회사의 기술적 도전과제를 가져옵니다"""
        company = self.get_company_data(company_id)
        return company.get("technical_challenges") if company else None
    
    def is_valid_company(self, company_id: str) -> bool:
        """유효한 회사 ID인지 확인합니다"""
        return company_id in self._companies_dict
    
    def get_supported_companies(self) -> List[str]:
        """지원되는 회사 ID 목록을 반환합니다"""
        return list(self._companies_dict.keys())

# 전역 인스턴스 (싱글톤 패턴)
_company_loader_instance = None

def get_company_loader() -> CompanyDataLoader:
    """CompanyDataLoader 싱글톤 인스턴스를 반환합니다"""
    global _company_loader_instance
    if _company_loader_instance is None:
        _company_loader_instance = CompanyDataLoader()
    return _company_loader_instance

# 편의 함수들
def get_company_data(company_id: str) -> Optional[Dict[str, Any]]:
    """회사 데이터를 가져오는 편의 함수"""
    return get_company_loader().get_company_data(company_id)

def get_all_companies() -> List[Dict[str, Any]]:
    """모든 회사 데이터를 가져오는 편의 함수"""
    return get_company_loader().get_all_companies()

def is_valid_company(company_id: str) -> bool:
    """유효한 회사인지 확인하는 편의 함수"""
    return get_company_loader().is_valid_company(company_id)