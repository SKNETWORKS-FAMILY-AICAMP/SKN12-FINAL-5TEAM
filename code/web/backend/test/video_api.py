"""
간단한 비디오 업로드/재생 API
"""

import os
import sys
import boto3
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

# 백엔드 서비스 import를 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))
from services.auth_service import AuthService, security
from services.supabase_client import get_supabase_client, get_user_supabase_client

router = APIRouter(prefix="/video", tags=["Video"])
auth_service = AuthService()

# AWS S3 클라이언트
print(f"[DEBUG] AWS_ACCESS_KEY_ID: {os.getenv('AWS_ACCESS_KEY_ID', 'NOT SET')[:10]}...")
print(f"[DEBUG] AWS_SECRET_ACCESS_KEY: {'SET' if os.getenv('AWS_SECRET_ACCESS_KEY') else 'NOT SET'}")
print(f"[DEBUG] AWS_REGION: {os.getenv('AWS_REGION', 'ap-northeast-2')}")

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'ap-northeast-2')
)

BUCKET_NAME = 'betago-s3'

class UploadRequest(BaseModel):
    interview_id: int
    file_name: str
    file_type: str = "video"  # video 또는 audio
    file_size: int = None
    duration: int = None

class TestUploadRequest(BaseModel):
    interview_id: int
    file_name: str
    file_type: str = "video"  # video 또는 audio
    file_size: int = None

@router.post("/upload-url")
async def get_upload_url(request: UploadRequest, current_user=Depends(auth_service.get_current_user)):
    """업로드용 Presigned URL 생성"""
    
    # S3 키 생성
    s3_key = f"interviews/{current_user.user_id}/{request.interview_id}/{request.file_name}"
    
    # Presigned URL 생성 (1시간 유효)
    upload_url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': BUCKET_NAME, 
            'Key': s3_key,
            'ContentType': 'video/webm' if request.file_type == 'video' else 'audio/webm'
        },
        ExpiresIn=3600
    )
    
    # DB에 레코드 생성
    supabase = get_supabase_client()
    try:
        result = supabase.table('media_files').insert({
            'user_id': current_user.user_id,
            'interview_id': request.interview_id,
            'file_name': request.file_name,
            'file_type': request.file_type,
            's3_key': s3_key,
            's3_url': f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{s3_key}",
            'file_size': request.file_size,
            'duration': request.duration
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="DB 레코드 생성 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")
    
    return {
        'upload_url': upload_url,
        'media_id': result.data[0]['media_id']
    }

@router.post("/test/upload-url")
async def get_test_upload_url(
    request: TestUploadRequest, 
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """테스트용 업로드 Presigned URL 생성"""
    
    # S3 키 생성 (테스트용)
    print(f"[DEBUG] Current user info: {current_user}")
    s3_key = f"test-videos/{current_user.user_id}/{request.interview_id}/{request.file_name}"
    
    # Presigned URL 생성 (1시간 유효)
    print(f"[DEBUG] Generating presigned URL for: {s3_key}")
    print(f"[DEBUG] Bucket: {BUCKET_NAME}")
    
    upload_url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': BUCKET_NAME, 
            'Key': s3_key,
            'ContentType': 'video/webm' if request.file_type == 'video' else 'audio/webm'
        },
        ExpiresIn=3600
    )
    
    print(f"[DEBUG] Generated presigned URL: {upload_url[:100]}...")
    
    # 사용자 토큰을 사용한 테스트용 DB 레코드 생성
    user_token = credentials.credentials
    supabase = get_user_supabase_client(user_token)
    print(f"[DEBUG] Using user token for DB access: {user_token[:50]}...")
    
    try:
        insert_data = {
            'user_id': current_user.user_id,
            'interview_id': 175,  # 테스트용으로 기존 interview_id 사용
            'file_name': request.file_name,
            'file_type': request.file_type,
            's3_key': s3_key,
            's3_url': f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{s3_key}",
            'file_size': request.file_size,
            'duration': None
        }
        print(f"[DEBUG] DB 삽입할 데이터: {insert_data}")
        
        result = supabase.table('media_files').insert(insert_data).execute()
        print(f"[DEBUG] DB 삽입 결과: {result}")
        print(f"[DEBUG] 삽입된 데이터: {result.data}")
        
        if not result.data:
            print(f"[ERROR] DB 레코드 생성 실패 - result.data가 비어있음")
            raise HTTPException(status_code=500, detail="DB 레코드 생성 실패")
            
        media_id = result.data[0]['media_id']
        print(f"[DEBUG] 생성된 media_id: {media_id}")
        
        # 삽입 후 바로 조회해서 확인
        verification = supabase.table('media_files').select('*').eq('media_id', media_id).execute()
        print(f"[DEBUG] 삽입 직후 확인 조회: {verification.data}")
            
    except Exception as e:
        print(f"[ERROR] DB insertion error: {str(e)}")
        print(f"[ERROR] 삽입 시도한 데이터: {insert_data}")
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")
    
    return {
        'upload_url': upload_url,
        'media_id': result.data[0]['media_id'],
        'test_id': result.data[0]['media_id']  # 일관성을 위해 test_id도 추가
    }

@router.get("/play/{test_id}")
async def get_play_url(
    test_id: str, 
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """재생용 Presigned URL 생성 (test_id = media_id)"""
    
    try:
        print(f"[DEBUG] 재생 API 호출: test_id={test_id}, user_id={current_user.user_id}")
        print(f"[DEBUG] 현재 사용자 정보: {current_user}")
        
        # 사용자 토큰을 사용한 Supabase 클라이언트 (업로드/완료 API와 동일)
        user_token = credentials.credentials
        supabase = get_user_supabase_client(user_token)
        print(f"[DEBUG] 재생 API에서 user token 사용: {user_token[:50]}...")
        
        # user token을 사용하여 DB에서 파일 정보 조회
        print(f"[DEBUG] media_id={test_id}, user_id={current_user.user_id}로 파일 조회")
        result = supabase.table('media_files').select('s3_key, file_name, file_type, media_id').eq('media_id', test_id).eq('user_id', current_user.user_id).execute()
        print(f"[DEBUG] 조회 결과: {len(result.data)}개 발견")
        
        if not result.data:
            print(f"[DEBUG] 파일을 찾을 수 없음: media_id={test_id}, user_id={current_user.user_id}")
            raise HTTPException(status_code=404, detail=f"미디어 파일을 찾을 수 없습니다 (ID: {test_id})")
        
        # 파일 정보 가져오기
        file_info = result.data[0]
        print(f"[DEBUG] 파일 정보 찾음: {file_info}")
        
        # 권한 확인: 해당 사용자의 파일인지 확인 (선택적)
        # 테스트 환경에서는 일단 생략하고 나중에 필요시 추가
            
        s3_key = file_info['s3_key']
        
        # Presigned URL 생성 (1시간 유효)  
        play_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        print(f"[DEBUG] 생성된 Presigned URL: {play_url[:100]}...")
        print(f"[DEBUG] S3 버킷: {BUCKET_NAME}, S3 키: {s3_key}")
        
        response_data = {
            'play_url': play_url,
            'file_name': file_info['file_name'],
            'file_type': file_info['file_type'],
            'test_id': test_id
        }
        print(f"[DEBUG] 재생 API 응답: {response_data}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재생 URL 생성 오류: {str(e)}")

@router.patch("/complete/{media_id}")
async def complete_upload(
    media_id: str, 
    file_size: int = None, 
    duration: int = None,
    current_user=Depends(auth_service.get_current_user),  # 인증 의존성 추가
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """업로드 완료 처리 - 파일 크기와 지속시간 업데이트"""
    
    print(f"[DEBUG] 완료 API 호출: media_id={media_id}, file_size={file_size}, user_id={current_user.user_id}")
    
    try:
        # 사용자 토큰을 사용한 Supabase 클라이언트로 RLS 정책 통과
        user_token = credentials.credentials
        supabase = get_user_supabase_client(user_token)
        print(f"[DEBUG] Using user token for DB access: {user_token[:50]}...")
        update_data = {'updated_at': 'now()'}
        
        if file_size:
            update_data['file_size'] = file_size
        if duration:
            update_data['duration'] = duration
            
        # 먼저 레코드가 존재하는지 확인
        print(f"[DEBUG] 완료 API에서 레코드 존재 확인: media_id={media_id}, user_id={current_user.user_id}")
        check_result = supabase.table('media_files').select('*').eq('media_id', media_id).eq('user_id', current_user.user_id).execute()
        print(f"[DEBUG] 완료 API 레코드 존재 확인: {len(check_result.data)}개 발견")
        print(f"[DEBUG] 완료 API 조회된 레코드: {check_result.data}")
        
        if not check_result.data:
            print(f"[DEBUG] 완료 API에서 미디어 파일 찾을 수 없음: media_id={media_id}, user_id={current_user.user_id}")
            # 전체 조회로 실제 존재하는지 확인
            all_check = supabase.table('media_files').select('*').eq('media_id', media_id).execute()
            print(f"[DEBUG] 완료 API 전체 조회 결과: {all_check.data}")
            raise HTTPException(status_code=404, detail=f"미디어 파일을 찾을 수 없습니다 (ID: {media_id})")
        
        existing_record = check_result.data[0]
        print(f"[DEBUG] 기존 레코드: file_size={existing_record.get('file_size')}, duration={existing_record.get('duration')}")
        
        # 실제로 업데이트가 필요한 필드만 업데이트
        needs_update = False
        if file_size and existing_record.get('file_size') != file_size:
            update_data['file_size'] = file_size
            needs_update = True
        if duration and existing_record.get('duration') != duration:
            update_data['duration'] = duration  
            needs_update = True
            
        if needs_update:
            print(f"[DEBUG] DB 업데이트 데이터: {update_data}")
            result = supabase.table('media_files').update(update_data).eq('media_id', media_id).eq('user_id', current_user.user_id).execute()
            print(f"[DEBUG] DB 업데이트 결과: {result.data}")
        else:
            print(f"[DEBUG] 업데이트 필요 없음 - 이미 최신 상태")
            result = check_result  # 기존 레코드를 결과로 사용
            
        print(f"[✅] 완료 API 성공: media_id={media_id}")
        return {'message': '업로드 완료', 'media_id': media_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 완료 처리 오류: {str(e)}")