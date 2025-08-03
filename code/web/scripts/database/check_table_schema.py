#!/usr/bin/env python3
"""
기존 Supabase 테이블 스키마 확인 스크립트
"""

import sys
import os
import asyncio

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import get_supabase_client

async def check_table_schemas():
    """기존 테이블 스키마 확인"""
    
    client = get_supabase_client()
    
    tables_to_check = [
        'company', 'position', 'User', 
        'user_resume', 'ai_resume', 'fix_question',
        'interview', 'history_detail', 'posting'
    ]
    
    print("🔍 기존 Supabase 테이블 스키마 분석")
    print("=" * 60)
    
    for table_name in tables_to_check:
        try:
            print(f"\n📋 테이블: {table_name}")
            
            # 테이블의 컬럼 정보 조회
            # PostgreSQL 시스템 테이블을 이용한 스키마 조회
            query = f"""
            SELECT 
                column_name, 
                data_type, 
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            AND table_schema = 'public'
            ORDER BY ordinal_position;
            """
            
            # RPC 함수를 사용하여 테이블 스키마 정보 조회
            try:
                # 테이블 컬럼 정보를 가져오는 SQL 쿼리를 RPC로 실행
                schema_result = client.rpc('get_table_schema', {'table_name_param': table_name}).execute()
                
                if schema_result.data:
                    print("  컬럼들:")
                    for column in schema_result.data:
                        print(f"    - {column['column_name']}: {column['data_type']} {'NOT NULL' if column['is_nullable'] == 'NO' else 'NULL'}")
                        if column['column_default']:
                            print(f"      기본값: {column['column_default']}")
                else:
                    # RPC 함수가 없으면 샘플 데이터로 대체
                    result = client.table(table_name).select('*').limit(1).execute()
                    
                    if result.data:
                        print("  컬럼들:")
                        sample_data = result.data[0]
                        for column_name, value in sample_data.items():
                            value_type = type(value).__name__
                            print(f"    - {column_name}: {value_type}")
                    else:
                        print("  ⚠️  데이터가 없어서 구조를 파악할 수 없음")
                        
            except Exception as rpc_error:
                # RPC 함수 실행 실패시 샘플 데이터로 대체
                result = client.table(table_name).select('*').limit(1).execute()
                
                if result.data:
                    print("  컬럼들:")
                    sample_data = result.data[0]
                    for column_name, value in sample_data.items():
                        value_type = type(value).__name__
                        print(f"    - {column_name}: {value_type}")
                else:
                    print("  ⚠️  데이터가 없어서 구조를 파악할 수 없음")
                    print(f"  (RPC 오류: {str(rpc_error)})")
                
        except Exception as e:
            print(f"  ❌ 오류: {str(e)}")
    
    print("\n" + "=" * 60)
    print("✅ 스키마 분석 완료")

if __name__ == "__main__":
    asyncio.run(check_table_schemas())