#!/usr/bin/env python3
"""
유틸리티 함수 모듈
프로젝트 전체에서 사용되는 공통 함수들
"""

import re
import json
import logging
import os
import sys
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from pathlib import Path

from .constants import CAREER_LEVELS, QUESTION_DIFFICULTIES

# Supabase 클라이언트 임포트
sys.path.append(str(Path(__file__).parent.parent.parent))
from backend.services.supabase_client import get_supabase_client

# 세션 매니저 임포트 (레거시 코드 제거)
create_session_manager = None

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_career_years(career_years_str: Union[str, int]) -> int:
    """경력 년수 문자열을 정수로 파싱"""
    if isinstance(career_years_str, int):
        return career_years_str
    
    career_str = str(career_years_str).strip()
    
    # 신입/경력없음 케이스
    if career_str.lower() in ["없음", "경력 없음", "신입", "0", "0년", "경력없음"]:
        return 0
    
    # 숫자만 있는 경우
    if career_str.isdigit():
        return int(career_str)
    
    # 숫자 추출 시도 (예: "3년", "2-3년")
    numbers = re.findall(r'\d+', career_str)
    return int(numbers[0]) if numbers else 0


def get_career_level(career_years: int) -> str:
    """경력 년수에 따른 레벨 반환"""
    for level, info in CAREER_LEVELS.items():
        if info['min'] <= career_years <= info['max']:
            return level
    return 'SENIOR'  # 기본값


def get_difficulty_level(career_years: int) -> int:
    """경력에 따른 질문 난이도 결정"""
    if career_years >= 3:
        return QUESTION_DIFFICULTIES['HARD']
    elif career_years >= 1:
        return QUESTION_DIFFICULTIES['MEDIUM']
    else:
        return QUESTION_DIFFICULTIES['EASY']


def safe_json_load(file_path: str, default: Any = None) -> Any:
    """안전한 JSON 파일 로드 (레거시 지원)"""
    try:
        # 상대 경로를 절대 경로로 변환
        if not os.path.isabs(file_path):
            # 프로젝트 루트 기준으로 절대 경로 생성
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            file_path = os.path.join(project_root, file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"파일을 찾을 수 없습니다: {file_path}")
        return default or {}
    except json.JSONDecodeError:
        logger.error(f"JSON 파싱 오류: {file_path}")
        return default or {}


def load_fixed_questions_from_supabase() -> Dict[str, Any]:
    """Supabase에서 고정 질문을 로드합니다"""
    try:
        client = get_supabase_client()
        result = client.from_('fix_question').select('*').execute()
        questions_raw = result.data if result.data else []
        
        # JSON 구조로 변환 (기존 JSON 파일 형식과 호환)
        hr_questions = []
        for question in questions_raw:
            hr_question = {
                "question_id": question['question_id'],
                "position_id": 1,  # 기본값 (모든 직무 공통)
                "question_section": "hr",
                "content": question['question_content'],
                "intent": question['question_intent'],
                "level": int(question['question_level']) if question['question_level'] else 1
            }
            hr_questions.append(hr_question)
        
        return {"hr_questions": hr_questions}
        
    except Exception as e:
        logger.error(f"Supabase에서 고정 질문 로드 실패: {str(e)}")
        return {"hr_questions": []}


def get_fixed_questions() -> Dict[str, Any]:
    """고정 질문 데이터를 가져옵니다 (Supabase 우선, 실패시 JSON 파일)"""
    # 먼저 Supabase에서 시도
    supabase_data = load_fixed_questions_from_supabase()
    if supabase_data.get("hr_questions"):
        logger.info("Supabase에서 고정 질문 로드 완료")
        return supabase_data
    
    # Supabase 실패시 기존 JSON 파일 로드
    logger.info("Supabase 실패, JSON 파일에서 고정 질문 로드 시도")
    return safe_json_load("llm/data/fixed_questions.json", {"hr_questions": []})


def load_ai_resumes_from_supabase() -> Dict[str, Any]:
    """Supabase에서 AI 후보자 이력서를 로드합니다"""
    try:
        client = get_supabase_client()
        result = client.table('ai_resume').select('*, position(position_name)').execute()
        resumes_raw = result.data if result.data else []
        
        # JSON 구조로 변환 (기존 JSON 파일 형식과 호환)
        personas = {}
        for resume in resumes_raw:
            position_name = resume['position']['position_name'] if resume.get('position') else 'unknown'
            company_key = f"{position_name}_{resume['ai_resume_id']}"
            
            persona = {
                "name": f"AI후보자{resume['ai_resume_id']}",
                "background": {
                    "career_years": "5",  # 기본값
                    "current_position": position_name,
                    "education": resume.get('academic_record', ''),
                    "total_experience": resume.get('career', '')
                },
                "technical_skills": resume.get('tech', '').split(', ') if resume.get('tech') else [],
                "activities": resume.get('activities', ''),
                "certificate": resume.get('certificate', ''),
                "awards": resume.get('awards', '')
            }
            personas[company_key] = persona
        
        return {"personas": personas}
        
    except Exception as e:
        logger.error(f"Supabase에서 AI 이력서 로드 실패: {str(e)}")
        return {"personas": {}}


def sanitize_filename(filename: str) -> str:
    """파일명 안전성 검증 및 정리"""
    # 위험한 문자 제거
    safe_filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 길이 제한
    return safe_filename[:255] if safe_filename else 'unnamed_file'


def format_timestamp() -> str:
    """현재 시간을 포맷된 문자열로 반환"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def extract_question_and_intent(response_text: str) -> tuple[str, str]:
    """AI 응답에서 질문과 의도를 분리"""
    if "의도:" in response_text:
        parts = response_text.split("의도:")
        question = parts[0].strip()
        intent = parts[1].strip() if len(parts) > 1 else ""
    else:
        question = response_text.strip()
        intent = "면접 역량 평가"
    
    return question, intent


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """텍스트를 지정된 길이로 자르기"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> list:
    """필수 필드 검증"""
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    return missing_fields


def deep_get(dictionary: Dict[str, Any], keys: str, default: Any = None) -> Any:
    """중첩된 딕셔너리에서 안전하게 값 가져오기"""
    keys_list = keys.split('.')
    value = dictionary
    
    try:
        for key in keys_list:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default


def save_session_state(plan_content: str = None, todos: list = None, session_info: Dict[str, Any] = None):
    """현재 세션 상태 저장"""
    if create_session_manager is None:
        logger.warning("세션 매니저를 사용할 수 없습니다.")
        return
    
    try:
        manager = create_session_manager()
        
        if plan_content:
            manager.save_plan_state(plan_content, "active")
        
        if todos:
            manager.save_todo_state(todos)
        
        if session_info:
            manager.save_session_info(session_info)
        
        logger.info("세션 상태 저장 완료")
        
    except Exception as e:
        logger.error(f"세션 상태 저장 실패: {e}")


def load_session_state() -> Dict[str, Any]:
    """이전 세션 상태 로드"""
    if create_session_manager is None:
        return {"has_previous_session": False}
    
    try:
        manager = create_session_manager()
        return manager.check_previous_session()
        
    except Exception as e:
        logger.error(f"세션 상태 로드 실패: {e}")
        return {"has_previous_session": False}


def check_and_restore_session() -> bool:
    """세션 복원 확인"""
    if create_session_manager is None:
        return False
    
    try:
        from .claude_state.session_manager import check_and_restore_session
        return check_and_restore_session()
        
    except Exception as e:
        logger.error(f"세션 복원 확인 실패: {e}")
        return False