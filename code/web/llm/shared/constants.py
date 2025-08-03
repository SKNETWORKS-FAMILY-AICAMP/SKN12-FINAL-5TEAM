#!/usr/bin/env python3
"""
상수 정의 모듈
프로젝트 전체에서 사용되는 상수들을 중앙 관리
Config 모듈에서 환경변수 기반 설정을 가져와 사용
"""

from .config import config

# 파일 관련 상수 (Config에서 가져옴)
ALLOWED_FILE_EXTENSIONS = config.ALLOWED_EXTENSIONS
MAX_FILE_SIZE = config.MAX_FILE_SIZE
UPLOAD_FOLDER = config.UPLOAD_FOLDER

# 면접 관련 상수 (Config에서 가져옴)
DEFAULT_TOTAL_QUESTIONS = config.DEFAULT_TOTAL_QUESTIONS
PROGRESS_UPDATE_INTERVAL = 1

# API 관련 상수 (Config에서 가져옴)
GPT_MODEL = config.GPT_MODEL
MAX_TOKENS = config.MAX_TOKENS
TEMPERATURE = config.TEMPERATURE

# 경력 단계 구분 (Config에서 가져옴)
CAREER_LEVELS = config.CAREER_LEVELS

# 질문 난이도 (고정값 유지)
QUESTION_DIFFICULTIES = {
    'EASY': 1,
    'MEDIUM': 2,
    'HARD': 3
}

# 회사 목록 (Config에서 가져옴)
SUPPORTED_COMPANIES = config.SUPPORTED_COMPANIES

# 질문 섹션 매핑 (Config에서 가져옴)
QUESTION_SECTIONS = config.QUESTION_TYPE_MAPPING

# 추가 상수들
SIMILARITY_THRESHOLD = config.QUESTION_SIMILARITY_THRESHOLD
API_RETRY_COUNT = config.API_RETRY_COUNT
API_RETRY_DELAY = config.API_RETRY_DELAY
RATE_LIMIT_PER_MINUTE = config.RATE_LIMIT_PER_MINUTE