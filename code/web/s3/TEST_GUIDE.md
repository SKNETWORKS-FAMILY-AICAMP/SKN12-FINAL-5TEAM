# S3 비디오 시스템 테스트 가이드

## 🚀 테스트 준비

### 1. 환경 변수 설정
`.env` 파일을 프로젝트 루트에 생성하고 다음 내용을 채워주세요:

```env
# AWS S3 설정
AWS_ACCESS_KEY_ID=your_actual_aws_access_key
AWS_SECRET_ACCESS_KEY=your_actual_aws_secret_key
AWS_REGION=ap-northeast-2

# 기타 설정들 (기존 것 그대로 사용)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
JWT_SECRET_KEY=your_jwt_secret_key
```

### 2. AWS S3 버킷 확인
- S3 콘솔에서 `betago-s3` 버킷이 존재하는지 확인
- 버킷 정책에서 업로드 권한 확인

### 3. 백엔드 서버 시작
```bash
cd backend
python main.py
```

## 🧪 테스트 실행

### 방법 1: HTML 테스트 페이지 사용
1. 브라우저에서 `s3/test_video.html` 열기
2. 개발자 도구 콘솔 열기 (F12)
3. 테스트 실행:
   - 🔴 녹화 시작 → 3-5초 녹화 → ⏹️ 녹화 정지
   - 📤 업로드하기 클릭
   - 🎬 비디오 로드 클릭하여 재생 확인

### 방법 2: React 컴포넌트 테스트
React 앱에서 `InterviewRecorder` 컴포넌트를 임포트하여 테스트

## ✅ 확인 사항

### 1. S3 버킷 확인
- AWS S3 콘솔에서 파일이 업로드되었는지 확인
- 파일 경로: `interviews/{user_id}/{interview_id}/파일명.webm`

### 2. Supabase 데이터 확인
```sql
SELECT * FROM media_files ORDER BY created_at DESC LIMIT 5;
```

다음 필드들이 올바르게 저장되는지 확인:
- `media_id`, `user_id`, `interview_id`
- `file_name`, `file_type`, `s3_key`, `s3_url`
- `file_size`, `created_at`, `updated_at`

### 3. API 엔드포인트 테스트
- `POST /video/upload-url` - Presigned URL 생성
- `GET /video/play/{interview_id}` - 재생 URL 생성
- `PATCH /video/complete/{media_id}` - 업로드 완료 처리

## 🐛 문제 해결

### 자주 발생하는 오류들:
1. **AWS 권한 오류**: IAM 사용자에 S3 권한 부여 확인
2. **CORS 오류**: S3 버킷의 CORS 정책 확인
3. **인증 오류**: JWT 토큰이 localStorage에 있는지 확인
4. **브라우저 권한**: 카메라/마이크 접근 권한 허용

### 로그 확인:
- 브라우저 개발자 도구 콘솔
- 백엔드 서버 로그
- S3 CloudTrail 로그 (필요시)

## 🎯 성공 기준

✅ 모든 테스트가 성공하면:
1. 비디오 녹화 완료
2. S3에 파일 업로드 완료
3. Supabase에 메타데이터 저장 완료
4. 업로드된 비디오 재생 가능

이후 실제 면접 시스템에 통합 진행 가능합니다!