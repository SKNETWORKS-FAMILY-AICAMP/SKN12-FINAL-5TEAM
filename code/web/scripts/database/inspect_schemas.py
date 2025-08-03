#!/usr/bin/env python3
"""
Supabase 테이블 스키마 검사 (REST API 활용)
"""

import sys
import os
import requests
import json

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import get_supabase_client

def inspect_table_schema(table_name: str):
    """테이블 스키마 검사"""
    client = get_supabase_client()
    
    print(f"\n📋 테이블: {table_name}")
    
    try:
        # 빈 insert 시도로 필수 컬럼 확인
        try:
            result = client.table(table_name).insert({}).execute()
        except Exception as insert_error:
            error_msg = str(insert_error)
            if "null value in column" in error_msg.lower():
                # NOT NULL 제약조건 위반에서 컬럼명 추출
                import re
                null_columns = re.findall(r'null value in column "([^"]+)"', error_msg)
                if null_columns:
                    print(f"  필수 컬럼들: {', '.join(null_columns)}")
            elif "duplicate key" in error_msg.lower():
                print("  ✅ 테이블 접근 가능 (중복키 오류)")
            else:
                print(f"  ⚠️ INSERT 오류: {error_msg}")
        
        # 빈 쿼리로 컬럼 정보 확인
        try:
            result = client.table(table_name).select('*').limit(0).execute()
            print("  ✅ SELECT 쿼리 성공")
        except Exception as select_error:
            print(f"  ❌ SELECT 오류: {str(select_error)}")
        
        # 샘플 데이터가 있으면 구조 확인
        try:
            sample = client.table(table_name).select('*').limit(1).execute()
            if sample.data:
                print("  컬럼 구조 (샘플 기반):")
                for col, val in sample.data[0].items():
                    print(f"    - {col}: {type(val).__name__}")
            else:
                print("  📝 테이블이 비어있음")
        except Exception as e:
            print(f"  ❌ 샘플 조회 실패: {str(e)}")
            
    except Exception as e:
        print(f"  ❌ 전체 검사 실패: {str(e)}")

def main():
    print("🔍 Supabase 테이블 스키마 검사")
    print("=" * 60)
    
    tables = [
        'company', 'position', 'User', 
        'user_resume', 'ai_resume', 'fix_question',
        'interview', 'history_detail', 'posting'
    ]
    
    for table in tables:
        inspect_table_schema(table)
    
    print("\n" + "=" * 60)
    print("✅ 스키마 검사 완료")

if __name__ == "__main__":
    main()