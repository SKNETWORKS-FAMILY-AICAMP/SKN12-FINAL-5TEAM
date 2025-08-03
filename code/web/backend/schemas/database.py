"""
기존 Supabase 테이블과 현재 시스템 연동
기존 구조를 건드리지 않고 데이터베이스 기능 추가
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.existing_tables_service import existing_tables_service

# ===================
# 요청/응답 모델
# ===================

class CreateUserRequest(BaseModel):
    name: str
    email: str
    pw: str

class CreateInterviewRequest(BaseModel):
    user_id: int
    company_id: int
    position_id: int
    posting_id: Optional[int] = None

class SaveInterviewDetailRequest(BaseModel):
    interview_id: int
    who: str  # 'user' 또는 'ai'
    question_index: int
    question_id: int
    question_content: str
    question_intent: str
    question_level: str
    answer: str
    feedback: str
    sequence: int
    duration: int

class SaveResumeRequest(BaseModel):
    user_id: int
    title: str
    content: str
