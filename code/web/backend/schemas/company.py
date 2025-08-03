from pydantic import BaseModel
from typing import Optional

class CompanyResponse(BaseModel):
    company_id: int
    name: str
    talent_profile: Optional[str]
    core_competencies: Optional[str]
    tech_focus: Optional[str]
    interview_keywords: Optional[str]
    question_direction: Optional[str]
    company_culture: Optional[str]
    technical_challenges: Optional[str]
