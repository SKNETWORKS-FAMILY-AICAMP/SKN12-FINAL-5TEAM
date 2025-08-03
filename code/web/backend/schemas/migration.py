"""
데이터 마이그레이션 API 엔드포인트
웹 인터페이스에서 마이그레이션 실행 가능
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging

logger = logging.getLogger(__name__)

# ===================
# 요청/응답 모델
# ===================

class MigrationRequest(BaseModel):
    task: str  # 'all', 'companies', 'questions', 'candidates'
    dry_run: bool = False

class MigrationStatus(BaseModel):
    status: str
    message: str
    results: Optional[Dict[str, Any]] = None

# 마이그레이션 상태 저장
migration_status = {
    "is_running": False,
    "current_task": None,
    "progress": 0,
    "last_result": None
}
