#!/usr/bin/env python3
"""
AWS S3 권한 테스트 스크립트
"""

import os
import boto3
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def test_s3_permissions():
    """S3 권한 테스트"""
    
    # AWS 자격증명 확인
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_REGION', 'ap-northeast-2')
    bucket_name = 'betago-s3'
    
    print(f"[INFO] AWS_ACCESS_KEY_ID: {access_key[:10]}...")
    print(f"[INFO] AWS_SECRET_ACCESS_KEY: {'*' * 10}")
    print(f"[INFO] AWS_REGION: {region}")
    print(f"[INFO] BUCKET_NAME: {bucket_name}")
    print()
    
    # S3 클라이언트 생성
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        print("✅ S3 클라이언트 생성 성공")
    except Exception as e:
        print(f"❌ S3 클라이언트 생성 실패: {e}")
        return False
    
    # 1. 버킷 존재 확인
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print("✅ 버킷 존재 확인")
    except Exception as e:
        print(f"❌ 버킷 접근 실패: {e}")
        return False
    
    # 2. 버킷 리스트 권한 테스트
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        print("✅ 버킷 리스트 권한 확인")
    except Exception as e:
        print(f"❌ 버킷 리스트 권한 없음: {e}")
    
    # 3. Presigned URL 생성 테스트
    test_key = "test-uploads/permission-test.txt"
    try:
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': test_key,
                'ContentType': 'text/plain'
            },
            ExpiresIn=300  # 5분
        )
        print("✅ Presigned URL 생성 성공")
        print(f"[INFO] URL: {upload_url[:80]}...")
        return upload_url
    except Exception as e:
        print(f"❌ Presigned URL 생성 실패: {e}")
        return False

if __name__ == "__main__":
    print("=== AWS S3 권한 테스트 시작 ===")
    print()
    result = test_s3_permissions()
    print()
    print("=== 테스트 완료 ===")
    
    if result:
        print("✅ 기본 S3 권한은 정상입니다.")
        print("✅ Presigned URL이 생성되었습니다.")
        print()
        print("다음 단계:")
        print("1. 생성된 Presigned URL로 실제 파일 업로드 테스트")
        print("2. CORS 정책 확인")
        print("3. 브라우저에서의 PUT 요청 테스트")
    else:
        print("❌ S3 권한에 문제가 있습니다.")
        print("AWS IAM 사용자 권한을 확인해주세요.")