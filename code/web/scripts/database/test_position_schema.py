#!/usr/bin/env python3
"""
Position 테이블 스키마 테스트
"""

import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import get_supabase_client

def test_position_schema():
    """Position 테이블에 어떤 컬럼들이 있는지 테스트"""
    client = get_supabase_client()
    
    print("🧪 Position 테이블 스키마 테스트")
    print("=" * 50)
    
    # 테스트 1: 최소 필수 컬럼만
    print("\n1️⃣ 최소 필수 컬럼 테스트")
    try:
        result = client.table('position').insert({
            'position_name': 'TEST_POSITION_TO_DELETE'
        }).execute()
        
        if result.data:
            print("✅ position_name만으로 삽입 성공")
            position_id = result.data[0].get('position_id')
            print(f"생성된 데이터: {result.data[0]}")
            
            # 즉시 삭제
            client.table('position').delete().eq('position_id', position_id).execute()
            print("🗑️ 테스트 데이터 삭제 완료")
        else:
            print("❌ 삽입 실패")
    except Exception as e:
        print(f"❌ 오류: {str(e)}")
    
    # 테스트 2: company_id 포함
    print("\n2️⃣ company_id 포함 테스트")
    try:
        # 먼저 실제 company_id 가져오기
        companies = client.table('company').select('company_id').limit(1).execute()
        if companies.data:
            company_id = companies.data[0]['company_id']
            print(f"사용할 company_id: {company_id}")
            
            result = client.table('position').insert({
                'position_name': 'TEST_POSITION_WITH_COMPANY',
                'company_id': company_id
            }).execute()
            
            if result.data:
                print("✅ company_id 포함 삽입 성공")
                position_id = result.data[0].get('position_id')
                print(f"생성된 데이터: {result.data[0]}")
                
                # 즉시 삭제
                client.table('position').delete().eq('position_id', position_id).execute()
                print("🗑️ 테스트 데이터 삭제 완료")
            else:
                print("❌ 삽입 실패")
        else:
            print("❌ company 데이터가 없어서 테스트 불가")
    except Exception as e:
        print(f"❌ 오류: {str(e)}")
    
    # 테스트 3: 다른 가능한 컬럼들
    print("\n3️⃣ 추가 컬럼 테스트")
    test_columns = [
        'description',
        'requirements',
        'salary_range',
        'location',
        'department'
    ]
    
    for col in test_columns:
        try:
            result = client.table('position').insert({
                'position_name': f'TEST_{col.upper()}',
                col: 'test_value'
            }).execute()
            
            if result.data:
                print(f"✅ {col} 컬럼 존재")
                position_id = result.data[0].get('position_id')
                # 즉시 삭제
                client.table('position').delete().eq('position_id', position_id).execute()
            else:
                print(f"❌ {col} 컬럼 삽입 실패")
        except Exception as e:
            if "column" in str(e).lower() and "does not exist" in str(e).lower():
                print(f"❌ {col} 컬럼 존재하지 않음")
            else:
                print(f"❌ {col} 테스트 오류: {str(e)}")

if __name__ == "__main__":
    test_position_schema()