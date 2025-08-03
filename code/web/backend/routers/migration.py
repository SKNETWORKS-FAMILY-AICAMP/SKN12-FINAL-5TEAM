import sys
import os
import logging
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.schemas.company import CompanyResponse
# from database.services.data_migration_service import migration_service
from schemas.migration import MigrationRequest, MigrationStatus, migration_status
from typing import List

logger = logging.getLogger(__name__)

# 라우터 생성
migration_router = APIRouter(prefix="/migration", tags=["Migration"])

# ===================
# 마이그레이션 엔드포인트
# ===================

@migration_router.get("/status")
async def get_migration_status():
    """마이그레이션 상태 조회"""
    return {
        "success": True,
        "data": migration_status
    }

@migration_router.get("/validate")
async def validate_data():
    """현재 데이터베이스 상태 검증"""
    try:
        validation_result = await migration_service.validate_migration()
        return {
            "success": True,
            "data": validation_result,
            "message": "데이터 검증 완료"
        }
    except Exception as e:
        logger.error(f"데이터 검증 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터 검증 실패: {str(e)}")

@migration_router.get("/preview")
async def preview_migration():
    """마이그레이션 미리보기 (dry-run)"""
    try:
        # 로컬 데이터 확인
        companies_data = migration_service.load_json_file('companies_data.json')
        questions_data = migration_service.load_json_file('fixed_questions.json')
        personas_data = migration_service.load_json_file('candidate_personas.json')
        
        # 현재 DB 상태
        current_data = await migration_service.validate_migration()
        
        preview_data = {
            "local_data": {
                "companies": len(companies_data.get('companies', [])),
                "fixed_questions": sum(len(questions) for questions in questions_data.values() if isinstance(questions, list)),
                "ai_candidates": len(personas_data.get('personas', {}))
            },
            "current_db": current_data,
            "migration_plan": {
                "companies": "회사 데이터 → company 테이블",
                "questions": "고정 질문 → fix_question 테이블", 
                "candidates": "AI 후보자 → ai_resume 테이블"
            }
        }
        
        return {
            "success": True,
            "data": preview_data,
            "message": "마이그레이션 미리보기 완료"
        }
        
    except Exception as e:
        logger.error(f"마이그레이션 미리보기 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"마이그레이션 미리보기 실패: {str(e)}")

@migration_router.post("/run")
async def run_migration(request: MigrationRequest, background_tasks: BackgroundTasks):
    """마이그레이션 실행"""
    global migration_status
    
    if migration_status["is_running"]:
        raise HTTPException(status_code=409, detail="이미 마이그레이션이 진행 중입니다")
    
    if request.dry_run:
        # dry-run은 즉시 실행
        return await preview_migration()
    
    # 백그라운드에서 마이그레이션 실행
    background_tasks.add_task(execute_migration, request.task)
    
    migration_status["is_running"] = True
    migration_status["current_task"] = request.task
    migration_status["progress"] = 0
    
    return {
        "success": True,
        "message": f"마이그레이션이 백그라운드에서 시작되었습니다 (작업: {request.task})",
        "task_id": request.task
    }

async def execute_migration(task: str):
    """백그라운드 마이그레이션 실행"""
    global migration_status
    
    try:
        migration_status["current_task"] = task
        migration_status["progress"] = 10
        
        if task == 'all':
            migration_status["progress"] = 20
            results = await migration_service.run_full_migration()
            migration_status["progress"] = 90
            
        elif task == 'companies':
            migration_status["progress"] = 30
            success = await migration_service.migrate_companies()
            results = {'companies': success}
            migration_status["progress"] = 80
            
        elif task == 'questions':
            migration_status["progress"] = 30
            success = await migration_service.migrate_fixed_questions()
            results = {'fixed_questions': success}
            migration_status["progress"] = 80
            
        elif task == 'candidates':
            migration_status["progress"] = 30
            success = await migration_service.migrate_ai_candidates()
            results = {'ai_candidates': success}
            migration_status["progress"] = 80
        else:
            results = {'error': f'Unknown task: {task}'}
        
        # 마이그레이션 후 검증
        migration_status["progress"] = 95
        validation_result = await migration_service.validate_migration()
        
        migration_status["last_result"] = {
            "migration_results": results,
            "validation": validation_result,
            "completed_at": str(datetime.now())
        }
        migration_status["progress"] = 100
        
    except Exception as e:
        logger.error(f"마이그레이션 실행 실패: {str(e)}")
        migration_status["last_result"] = {
            "error": str(e),
            "failed_at": str(datetime.now())
        }
    finally:
        migration_status["is_running"] = False
        migration_status["current_task"] = None

# ===================
# 데이터 관리 엔드포인트
# ===================

@migration_router.post("/companies/{company_id}/positions")
async def create_company_positions(company_id: int):
    """특정 회사의 기본 포지션 생성"""
    try:
        # 회사 정보 확인
        company_result = migration_service.client.table('company').select('name').eq('company_id', company_id).single().execute()
        
        if not company_result.data:
            raise HTTPException(status_code=404, detail="회사를 찾을 수 없습니다")
        
        company_name = company_result.data['name']
        
        # 기본 포지션 생성
        await migration_service._create_default_positions(company_id, company_name)
        
        return {
            "success": True,
            "message": f"{company_name}의 기본 포지션이 생성되었습니다"
        }
        
    except Exception as e:
        logger.error(f"포지션 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"포지션 생성 실패: {str(e)}")

@migration_router.delete("/reset/{table_name}")
async def reset_table_data(table_name: str):
    """특정 테이블 데이터 초기화 (주의: 위험한 작업)"""
    
    allowed_tables = ['company', 'position', 'fix_question', 'ai_resume']
    
    if table_name not in allowed_tables:
        raise HTTPException(status_code=400, detail=f"허용되지 않은 테이블입니다. 허용 테이블: {allowed_tables}")
    
    try:
        # 데이터 삭제 (주의: 실제 데이터가 삭제됩니다!)
        result = migration_service.client.table(table_name).delete().neq('id', 0).execute()  # 모든 데이터 삭제
        
        return {
            "success": True,
            "message": f"{table_name} 테이블 데이터가 초기화되었습니다",
            "deleted_count": len(result.data) if result.data else 0
        }
        
    except Exception as e:
        logger.error(f"테이블 초기화 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"테이블 초기화 실패: {str(e)}")

# ===================
# 헬스체크
# ===================

@migration_router.get("/health")
async def migration_health_check():
    """마이그레이션 서비스 상태 확인"""
    try:
        # 기본 연결 테스트
        validation_result = await migration_service.validate_migration()
        
        return {
            "success": True,
            "message": "마이그레이션 서비스 정상",
            "data": validation_result,
            "migration_status": migration_status
        }
    except Exception as e:
        logger.error(f"마이그레이션 헬스체크 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="마이그레이션 서비스에 문제가 있습니다")