from backend.services.existing_tables_service import existing_tables_service
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Depends
from backend.services.supabase_client import supabase_client
from backend.schemas.company import CompanyResponse
from typing import List

company_router = APIRouter(prefix="/company", tags=["Company"])

# 🟢 GET /company – 회사 정보 조회
@company_router.get("/", response_model=List[CompanyResponse])
def get_company_info():
    res = supabase_client.client.from_("company").select("*").execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No companies found")
    return res.data

# 🟢 GET /company/{company_id} – 기업 상세 요구사항 조회
@company_router.get("/{company_id}", response_model=CompanyResponse)
def get_company_detail(company_id: int):
    res = supabase_client.client.from_("company").select("*").eq("company_id", company_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No company found")
    return res.data