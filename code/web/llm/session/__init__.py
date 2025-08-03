#!/usr/bin/env python3
"""
🚫 DEPRECATED - 더 이상 사용하지 않음

이 모듈의 모든 기능은 backend/services/interview_service.py로 이관되었습니다.
새로운 Backend 중앙 관제 시스템을 사용하세요.

기존 설명: 세션 관리 모듈 - 면접 세션의 생성, 관리, 상태 추적을 담당
"""

# from .models import InterviewSession, ComparisonSession, SessionState
# from .manager import SessionManager
# from .comparison_session import ComparisonSessionManager

# 경고: 이 모듈을 import하려고 하면 에러가 발생합니다.
raise ImportError(
    "🚫 llm.session 모듈은 더 이상 사용되지 않습니다. "
    "backend.services.interview_service 의 새로운 중앙 관제 시스템을 사용하세요."
)

# __all__ = [
#     "InterviewSession",
#     "ComparisonSession", 
#     "SessionState",
#     "SessionManager",
#     "ComparisonSessionManager"
# ]