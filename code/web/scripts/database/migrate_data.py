#!/usr/bin/env python3
"""
로컬 JSON 데이터를 Supabase로 마이그레이션하는 스크립트
"""

import sys
import os
import asyncio
import argparse

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.services.data_migration_service import migration_service

async def main():
    parser = argparse.ArgumentParser(description='데이터 마이그레이션 도구')
    parser.add_argument('--task', choices=['all', 'companies', 'questions', 'candidates', 'validate'], 
                       default='all', help='실행할 마이그레이션 작업')
    parser.add_argument('--dry-run', action='store_true', help='실제 실행하지 않고 미리보기만')
    
    args = parser.parse_args()
    
    print("🎯 AI 면접 시스템 데이터 마이그레이션 도구")
    print("=" * 60)
    
    if args.dry_run:
        print("📋 DRY RUN 모드 - 실제 데이터는 변경되지 않습니다.")
        print("=" * 60)
        
        # 현재 로컬 데이터 확인
        print("📁 로컬 데이터 확인:")
        companies_data = migration_service.load_json_file('companies_data.json')
        questions_data = migration_service.load_json_file('fixed_questions.json')
        personas_data = migration_service.load_json_file('candidate_personas.json')
        
        print(f"  - 회사 데이터: {len(companies_data.get('companies', []))}개")
        print(f"  - 고정 질문: {sum(len(questions) for questions in questions_data.values() if isinstance(questions, list))}개")
        print(f"  - AI 후보자: {len(personas_data.get('personas', {}))}개")
        
        # 현재 DB 상태 확인
        await migration_service.validate_migration()
        return
    
    try:
        if args.task == 'all':
            print("🚀 전체 마이그레이션 실행...")
            results = await migration_service.run_full_migration()
            
        elif args.task == 'companies':
            print("🏢 회사 데이터 마이그레이션...")
            success = await migration_service.migrate_companies()
            results = {'companies': success}
            
        elif args.task == 'questions':
            print("❓ 고정 질문 마이그레이션...")
            success = await migration_service.migrate_fixed_questions()
            results = {'fixed_questions': success}
            
        elif args.task == 'candidates':
            print("🤖 AI 후보자 마이그레이션...")
            success = await migration_service.migrate_ai_candidates()
            results = {'ai_candidates': success}
            
        elif args.task == 'validate':
            print("🔍 데이터 검증만 실행...")
            await migration_service.validate_migration()
            return
        
        # 마이그레이션 후 검증
        if any(results.values()):
            print("\n🔍 마이그레이션 후 데이터 검증...")
            await migration_service.validate_migration()
            
    except KeyboardInterrupt:
        print("\n⏸️  마이그레이션이 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())