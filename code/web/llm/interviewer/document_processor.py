#!/usr/bin/env python3
"""
사용자 문서 처리 시스템
자소서, 이력서, 포트폴리오를 분석하여 개인 프로필을 생성
코드 정리 및 구조 개선 버전
"""

import openai
import json
import re
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import PyPDF2
import docx
from io import BytesIO
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

from ..shared.constants import GPT_MODEL, MAX_TOKENS, TEMPERATURE
from ..shared.utils import format_timestamp, extract_question_and_intent

@dataclass
class UserProfile:
    """사용자 프로필 데이터 클래스"""
    name: str
    background: Dict[str, Any]  # 학력, 경력
    technical_skills: List[str]  # 기술 스택
    projects: List[Dict[str, str]]  # 프로젝트 경험
    experiences: List[Dict[str, str]]  # 업무/활동 경험
    strengths: List[str]  # 강점
    keywords: List[str]  # 핵심 키워드
    career_goal: str  # 커리어 목표
    unique_points: List[str]  # 차별화 포인트

class DocumentProcessor:
    """문서 처리 및 분석 클래스"""
    
    def __init__(self, api_key: str = None):
        # API 키 자동 로드
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OpenAI API 키가 필요합니다. .env 파일에 OPENAI_API_KEY를 설정하거나 직접 전달하세요.")
        
        self.client = openai.OpenAI(api_key=api_key)
    
    def extract_text_from_file(self, file_content: bytes, file_type: str) -> str:
        """파일에서 텍스트 추출"""
        try:
            if file_type.lower() == 'pdf':
                return self._extract_from_pdf(file_content)
            elif file_type.lower() in ['docx', 'doc']:
                return self._extract_from_docx(file_content)
            elif file_type.lower() == 'txt':
                return file_content.decode('utf-8')
            else:
                raise ValueError(f"지원하지 않는 파일 형식: {file_type}")
        except Exception as e:
            print(f"파일 텍스트 추출 오류: {e}")
            return ""
    
    def _extract_from_pdf(self, file_content: bytes) -> str:
        """PDF에서 텍스트 추출"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"PDF 추출 오류: {e}")
            return ""
    
    def _extract_from_docx(self, file_content: bytes) -> str:
        """DOCX에서 텍스트 추출"""
        try:
            doc = docx.Document(BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"DOCX 추출 오류: {e}")
            return ""
    
    def analyze_document(self, text: str, document_type: str) -> Dict[str, Any]:
        """문서 내용 분석"""
        
        prompt = f"""
다음 {document_type} 문서를 분석하여 주요 정보를 추출해주세요.

=== 문서 내용 ===
{text}

=== 추출할 정보 ===
1. 기본 정보 (이름, 학력, 경력)
2. 기술 스택 및 역량
3. 프로젝트 경험
4. 업무 경험
5. 주요 성과 및 강점
6. 핵심 키워드
7. 커리어 목표
8. 차별화 포인트

JSON 형식으로 응답해주세요:
{{
  "basic_info": {{
    "name": "이름",
    "education": ["학력 정보"],
    "career_years": "경력 년수 (숫자나 '없음', '신입' 등으로 표기)",
    "current_position": "현재 직책 (신입의 경우 '신입' 또는 '지원자')"
  }},
  "technical_skills": ["기술1", "기술2", "기술3"],
  "projects": [
    {{
      "name": "프로젝트명",
      "description": "설명",
      "tech_stack": ["사용기술"],
      "role": "역할",
      "period": "기간"
    }}
  ],
  "experiences": [
    {{
      "company": "회사명",
      "position": "직책",
      "period": "기간", 
      "achievements": ["성과1", "성과2"]
    }}
  ],
  "strengths": ["강점1", "강점2", "강점3"],
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "career_goal": "커리어 목표",
  "unique_points": ["차별화포인트1", "차별화포인트2"]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 HR 전문가로서 이력서와 자기소개서를 정확하게 분석합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.2
            )
            
            result = response.choices[0].message.content.strip()
            
            # JSON 파싱
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return self._get_default_analysis()
                
        except Exception as e:
            print(f"문서 분석 중 오류: {e}")
            return self._get_default_analysis()
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """기본 분석 결과"""
        return {
            "basic_info": {
                "name": "사용자",
                "education": [],
                "career_years": "없음",
                "current_position": "신입"
            },
            "technical_skills": [],
            "projects": [],
            "experiences": [],
            "strengths": ["학습 의지", "성장 잠재력"],
            "keywords": ["신입", "잠재력"],
            "career_goal": "전문성을 갖춘 개발자로 성장",
            "unique_points": ["새로운 관점", "배움에 대한 열정"]
        }
    
    def create_user_profile(self, documents: Dict[str, str]) -> UserProfile:
        """여러 문서를 통합하여 사용자 프로필 생성"""
        
        # 각 문서별 분석
        analyses = {}
        for doc_type, text in documents.items():
            if text.strip():
                analyses[doc_type] = self.analyze_document(text, doc_type)
        
        # 통합 분석
        integrated_profile = self._integrate_analyses(analyses)
        
        return UserProfile(
            name=integrated_profile["basic_info"]["name"],
            background=integrated_profile["basic_info"],
            technical_skills=integrated_profile["technical_skills"],
            projects=integrated_profile["projects"],
            experiences=integrated_profile["experiences"],
            strengths=integrated_profile["strengths"],
            keywords=integrated_profile["keywords"],
            career_goal=integrated_profile["career_goal"],
            unique_points=integrated_profile["unique_points"]
        )
    
    def _integrate_analyses(self, analyses: Dict[str, Dict]) -> Dict[str, Any]:
        """여러 분석 결과를 통합"""
        
        if not analyses:
            return self._get_default_analysis()
        
        # 첫 번째 분석 결과를 베이스로 사용
        base_analysis = list(analyses.values())[0]
        
        # 다른 분석 결과들과 병합
        for doc_type, analysis in analyses.items():
            if doc_type == "포트폴리오":
                # 포트폴리오에서 프로젝트 정보 강화
                base_analysis["projects"].extend(analysis.get("projects", []))
                base_analysis["technical_skills"].extend(analysis.get("technical_skills", []))
            
            elif doc_type == "이력서":
                # 이력서에서 경력 정보 강화
                base_analysis["experiences"].extend(analysis.get("experiences", []))
                base_analysis["basic_info"].update(analysis.get("basic_info", {}))
            
            elif doc_type == "자기소개서":
                # 자소서에서 강점과 목표 강화
                base_analysis["strengths"].extend(analysis.get("strengths", []))
                base_analysis["career_goal"] = analysis.get("career_goal", base_analysis.get("career_goal", ""))
                base_analysis["unique_points"].extend(analysis.get("unique_points", []))
        
        # 중복 제거
        base_analysis["technical_skills"] = list(set(base_analysis["technical_skills"]))
        base_analysis["strengths"] = list(set(base_analysis["strengths"]))
        base_analysis["keywords"] = list(set(base_analysis["keywords"]))
        base_analysis["unique_points"] = list(set(base_analysis["unique_points"]))
        
        return base_analysis

if __name__ == "__main__":
    print("📄 문서 처리 시스템 테스트")
    
    # 자동으로 .env에서 API 키 로드
    processor = DocumentProcessor()
    
    # 샘플 텍스트로 테스트
    sample_text = """
    이름: 김개발
    학력: 컴퓨터공학과 졸업
    경력: Python, React 개발 3년
    프로젝트: 
    - 이커머스 플랫폼 개발 (Python, Django, PostgreSQL)
    - 실시간 채팅 앱 (Node.js, Socket.io, Redis)
    강점: 문제 해결 능력, 팀워크, 빠른 학습력
    목표: 풀스택 개발자로 성장하여 기술 리더가 되고 싶습니다.
    """
    
    print("\n🔍 문서 분석 중...")
    analysis = processor.analyze_document(sample_text, "이력서")
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    
    print("\n👤 사용자 프로필 생성 중...")
    profile = processor.create_user_profile({"이력서": sample_text})
    print(f"이름: {profile.name}")
    print(f"기술 스택: {profile.technical_skills}")
    print(f"강점: {profile.strengths}")
    print(f"목표: {profile.career_goal}")