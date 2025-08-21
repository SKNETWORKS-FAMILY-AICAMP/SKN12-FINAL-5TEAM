# S3 비디오 시스템

화상 면접 녹화 → S3 업로드 → 피드백 재생의 간단한 구현

## 📁 파일 구성 (4개만!)

1. `video_api.py` - 백엔드 API (업로드/재생 URL 생성)
2. `recorder.tsx` - 면접 중 녹화 컴포넌트
3. `player.tsx` - 피드백 페이지 영상 플레이어  
4. `README.md` - 사용법

## 🔧 연결 방법

### 1. Backend 연결
`backend/main.py`에 추가:
```python
from s3.video_api import router as video_router
app.include_router(video_router)
```

### 2. 면접 페이지에 녹화 추가
```tsx
import InterviewRecorder from '../s3/recorder';

<InterviewRecorder 
  interviewId={면접ID} 
  onUploadComplete={() => console.log('업로드 완료')}
/>
```

### 3. 피드백 페이지에 플레이어 추가
`InterviewResults.tsx` 227-242라인 교체:
```tsx
import VideoPlayer from '../s3/player';

<VideoPlayer interviewId={sessionId} />
```

## 📋 필수 설정

`.env` 파일:
```
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret  
AWS_REGION=ap-northeast-2
```

DB에 `media_files` 테이블 생성:
```sql  
-- database/video/video_tables.sql 참고
```

## 🎯 동작 방식

1. **녹화**: MediaRecorder로 화면+음성 캡처
2. **업로드**: Presigned URL로 S3 직접 업로드  
3. **재생**: Presigned URL로 비디오 스트리밍

간단하죠! 🚀