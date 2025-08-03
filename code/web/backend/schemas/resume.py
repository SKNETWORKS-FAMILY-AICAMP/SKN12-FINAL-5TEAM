# backend/schemas/resume.py
from pydantic import BaseModel
from datetime import datetime

# 생성 시, 수정 시, 응답 시 전부 BaseModel 하나씩
class ResumeCreate(BaseModel):
    academic_record: str
    position_id: int
    career: str
    tech: str
    activities: str
    certificate: str
    awards: str

class ResumeUpdate(BaseModel):
    academic_record: str
    position_id: int
    career: str
    tech: str
    activities: str
    certificate: str
    awards: str

class ResumeResponse(BaseModel):
    user_resume_id: int
    user_id: int
    academic_record: str
    position_id: int
    created_date: datetime
    updated_date: datetime
    career: str
    tech: str
    activities: str
    certificate: str
    awards: str

