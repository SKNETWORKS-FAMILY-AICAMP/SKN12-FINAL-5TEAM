#!/usr/bin/env python3
"""
간단한 마이그레이션 테스트
"""

import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.services.data_migration_service import migration_service

async def test_simple_migration():
    """간단한 테스트"""
    print("🧪 간단한 마이그레이션 테스트")
    print("=" * 50)
    
    # 1. 기본 포지션들 생성 테스트
    print("\n1️⃣ 기본 포지션 생성 테스트")
    await migration_service._create_default_positions(1, "테스트회사")
    
    # 2. 현재 상태 확인
    print("\n2️⃣ 현재 데이터베이스 상태 확인")
    await migration_service.validate_migration()
    
    print("\n✅ 테스트 완료")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_simple_migration())