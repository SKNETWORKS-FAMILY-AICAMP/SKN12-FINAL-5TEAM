# === 김원우 작성 시작 ===
"""
S3 미디어 파일 관리 라우터

이 모듈은 S3에 저장되는 미디어 파일의 업로드, 재생, 관리 API를 제공합니다.
기존 test/video_api.py의 기능을 표준 라우터 구조로 이전했습니다.

주요 기능:
- S3 Presigned URL 기반 업로드
- 동영상/오디오 재생 URL 생성
- 업로드 완료 처리
- 파일 목록 및 통계 조회

작성자: 김원우
작성일: 2025-08-12
"""

import os
import sys
import boto3
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from typing import List, Optional

# 백엔드 서비스 import를 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from services.auth_service import AuthService, security
from services.supabase_client import get_supabase_client, get_user_supabase_client
from schemas.media import (
    UploadRequest, TestUploadRequest, GazeUploadRequest, UploadResponse, PlayResponse,
    UploadCompleteRequest, UploadCompleteResponse, MediaFileInfo,
    MediaListResponse, MediaStatsResponse, ErrorResponse
)
import uuid
from models.media import MediaFileType, UploadStatus

# 라우터 초기화
router = APIRouter(prefix="/media", tags=["Media Management"])
auth_service = AuthService()

# AWS S3 클라이언트 설정
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


@router.post("/upload-url", response_model=UploadResponse)
async def get_upload_url(
    request: UploadRequest, 
    current_user=Depends(auth_service.get_current_user)
):
    """
    일반 업로드용 Presigned URL 생성
    
    면접 동영상/오디오 업로드를 위한 S3 Presigned URL을 생성합니다.
    클라이언트는 이 URL을 사용하여 S3에 직접 업로드할 수 있습니다.
    """
    try:
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
        
        # DB에 미디어 파일 레코드 생성
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
        
        return UploadResponse(
            upload_url=upload_url,
            media_id=result.data[0]['media_id'],
            expires_in=3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 URL 생성 실패: {str(e)}")


@router.post("/test/upload-url", response_model=UploadResponse)
async def get_test_upload_url(
    request: TestUploadRequest, 
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    테스트용 업로드 Presigned URL 생성
    
    시선 분석 등 테스트 목적의 동영상 업로드를 위한 URL을 생성합니다.
    사용자별 권한이 적용된 Supabase 클라이언트를 사용합니다.
    """
    try:
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
        
        return UploadResponse(
            upload_url=upload_url,
            media_id=result.data[0]['media_id'],
            expires_in=3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 업로드 URL 생성 실패: {str(e)}")


@router.post("/gaze/upload-url", response_model=UploadResponse)
async def get_gaze_upload_url(
    request: GazeUploadRequest, 
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    시선 추적 영상 업로드용 Presigned URL 생성
    
    시선 추적 분석을 위한 영상 파일의 S3 직접 업로드 URL을 생성합니다.
    gaze-videos/{user_id}/{session_id}/ 경로 구조를 사용합니다.
    DB 삽입은 면접 완료 후 interview_id가 확정된 시점에 처리됩니다.
    """
    try:
        print(f"[DEBUG] 시선 영상 업로드 URL 요청: user_id={current_user.user_id}, session_id={request.session_id}")
        
        # 시선 전용 S3 키 생성 (gaze-videos/{user_id}/{session_id}/{file_name})
        s3_key = f"gaze-videos/{current_user.user_id}/{request.session_id}/{request.file_name}"
        print(f"[DEBUG] 시선 영상 S3 키: {s3_key}")
        
        # Presigned URL 생성 (1시간 유효)
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME, 
                'Key': s3_key,
                'ContentType': request.content_type or 'video/webm'  # 실제 파일 타입 사용
            },
            ExpiresIn=3600
        )
        
        print(f"[DEBUG] 시선 영상 Presigned URL 생성 완료: {upload_url[:100]}...")
        
        # 임시 media_id 생성 (DB에 저장하지 않음)
        temp_media_id = str(uuid.uuid4())
        print(f"[DEBUG] 임시 media_id 생성: {temp_media_id}")
        
        # ❌ DB 삽입 제거 - interview_id가 확정된 후 지연 삽입됨
        print(f"[INFO] media_files 테이블 삽입을 지연 처리로 변경. 면접 완료 후 interview_id와 함께 삽입될 예정.")
        
        return UploadResponse(
            upload_url=upload_url,
            media_id=temp_media_id,
            s3_key=s3_key,
            expires_in=3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 시선 영상 업로드 URL 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시선 영상 업로드 URL 생성 실패: {str(e)}")


@router.get("/play/{test_id}", response_model=PlayResponse)
async def get_play_url(
    test_id: str, 
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    재생용 Presigned URL 생성
    
    업로드된 동영상/오디오 파일의 재생 URL을 생성합니다.
    test_id는 media_id와 동일합니다.
    """
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
            
        s3_key = file_info['s3_key']
        
        # Presigned URL 생성 (1시간 유효)  
        play_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        print(f"[DEBUG] 생성된 Presigned URL: {play_url[:100]}...")
        print(f"[DEBUG] S3 버킷: {BUCKET_NAME}, S3 키: {s3_key}")
        
        response_data = PlayResponse(
            play_url=play_url,
            file_name=file_info['file_name'],
            file_type=file_info['file_type'],
            test_id=test_id
        )
        print(f"[DEBUG] 재생 API 응답: {response_data}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재생 URL 생성 오류: {str(e)}")


@router.patch("/complete/{media_id}", response_model=UploadCompleteResponse)
async def complete_upload(
    media_id: str, 
    request: Optional[UploadCompleteRequest] = None,
    file_size: Optional[int] = None, 
    duration: Optional[int] = None,
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    업로드 완료 처리
    
    S3 업로드 완료 후 DB에서 파일 정보를 업데이트합니다.
    실제 파일 크기와 재생 시간을 기록합니다.
    """
    print(f"[DEBUG] 완료 API 호출: media_id={media_id}, file_size={file_size}, user_id={current_user.user_id}")
    
    try:
        # 사용자 토큰을 사용한 Supabase 클라이언트로 RLS 정책 통과
        user_token = credentials.credentials
        supabase = get_user_supabase_client(user_token)
        print(f"[DEBUG] Using user token for DB access: {user_token[:50]}...")
        
        update_data = {'updated_at': 'now()'}
        
        # 요청 데이터에서 값 추출 (쿼리 파라미터 우선)
        actual_file_size = file_size or (request.file_size if request else None)
        actual_duration = duration or (request.duration if request else None)
        
        if actual_file_size:
            update_data['file_size'] = actual_file_size
        if actual_duration:
            update_data['duration'] = actual_duration
            
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
        if actual_file_size and existing_record.get('file_size') != actual_file_size:
            update_data['file_size'] = actual_file_size
            needs_update = True
        if actual_duration and existing_record.get('duration') != actual_duration:
            update_data['duration'] = actual_duration  
            needs_update = True
            
        if needs_update:
            print(f"[DEBUG] DB 업데이트 데이터: {update_data}")
            result = supabase.table('media_files').update(update_data).eq('media_id', media_id).eq('user_id', current_user.user_id).execute()
            print(f"[DEBUG] DB 업데이트 결과: {result.data}")
        else:
            print(f"[DEBUG] 업데이트 필요 없음 - 이미 최신 상태")
            result = check_result  # 기존 레코드를 결과로 사용
            
        print(f"[✅] 완료 API 성공: media_id={media_id}")
        return UploadCompleteResponse(
            message='업로드 완료', 
            media_id=media_id,
            status='completed'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 완료 처리 오류: {str(e)}")


@router.get("/list", response_model=MediaListResponse)
async def get_media_list(
    page: int = 1,
    page_size: int = 20,
    file_type: Optional[str] = None,
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    미디어 파일 목록 조회
    
    사용자의 미디어 파일 목록을 페이지네이션으로 조회합니다.
    파일 타입별 필터링을 지원합니다.
    """
    try:
        user_token = credentials.credentials
        supabase = get_user_supabase_client(user_token)
        
        # 쿼리 빌더 생성
        query = supabase.table('media_files').select('*').eq('user_id', current_user.user_id)
        
        # 파일 타입 필터링
        if file_type:
            query = query.eq('file_type', file_type)
        
        # 전체 개수 조회
        count_result = query.execute()
        total_count = len(count_result.data) if count_result.data else 0
        
        # 페이지네이션 적용
        offset = (page - 1) * page_size
        result = query.order('created_at', desc=True).range(offset, offset + page_size - 1).execute()
        
        media_files = []
        for item in result.data if result.data else []:
            media_files.append(MediaFileInfo(
                media_id=item['media_id'],
                file_name=item['file_name'],
                file_type=item['file_type'],
                file_size=item.get('file_size'),
                duration=item.get('duration'),
                created_at=item['created_at'],
                updated_at=item['updated_at'],
                s3_url=item.get('s3_url')
            ))
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return MediaListResponse(
            media_files=media_files,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"미디어 목록 조회 실패: {str(e)}")


@router.get("/stats", response_model=MediaStatsResponse)
async def get_media_stats(
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    미디어 파일 통계 조회
    
    사용자의 미디어 파일 사용 통계를 제공합니다.
    """
    try:
        user_token = credentials.credentials
        supabase = get_user_supabase_client(user_token)
        
        result = supabase.table('media_files').select('*').eq('user_id', current_user.user_id).execute()
        
        if not result.data:
            return MediaStatsResponse(
                total_files=0,
                total_size_mb=0.0,
                video_count=0,
                audio_count=0,
                avg_file_size_mb=0.0,
                latest_upload=None
            )
        
        files = result.data
        total_files = len(files)
        video_count = len([f for f in files if f['file_type'] == 'video'])
        audio_count = len([f for f in files if f['file_type'] == 'audio'])
        
        # 파일 크기 계산 (None 값 제외)
        file_sizes = [f['file_size'] for f in files if f.get('file_size')]
        total_size_mb = sum(file_sizes) / (1024 * 1024) if file_sizes else 0.0
        avg_file_size_mb = total_size_mb / len(file_sizes) if file_sizes else 0.0
        
        # 최근 업로드 시간
        latest_upload = None
        if files:
            latest_file = max(files, key=lambda f: f['created_at'])
            latest_upload = latest_file['created_at']
        
        return MediaStatsResponse(
            total_files=total_files,
            total_size_mb=round(total_size_mb, 2),
            video_count=video_count,
            audio_count=audio_count,
            avg_file_size_mb=round(avg_file_size_mb, 2),
            latest_upload=latest_upload
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@router.delete("/{media_id}")
async def delete_media_file(
    media_id: str,
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    미디어 파일 삭제
    
    S3에서 파일을 삭제하고 DB 레코드도 제거합니다.
    """
    try:
        user_token = credentials.credentials
        supabase = get_user_supabase_client(user_token)
        
        # 파일 정보 조회
        result = supabase.table('media_files').select('s3_key').eq('media_id', media_id).eq('user_id', current_user.user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="미디어 파일을 찾을 수 없습니다")
        
        s3_key = result.data[0]['s3_key']
        
        # S3에서 파일 삭제
        try:
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
            print(f"[DEBUG] S3 파일 삭제 완료: {s3_key}")
        except Exception as e:
            print(f"[WARNING] S3 파일 삭제 실패: {e}")
            # S3 삭제 실패해도 DB 레코드는 삭제
        
        # DB 레코드 삭제
        supabase.table('media_files').delete().eq('media_id', media_id).eq('user_id', current_user.user_id).execute()
        
        return {"message": "미디어 파일이 삭제되었습니다", "media_id": media_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 삭제 실패: {str(e)}")


# 라우터 내보내기
media_router = router
# === 김원우 작성 끝 ===