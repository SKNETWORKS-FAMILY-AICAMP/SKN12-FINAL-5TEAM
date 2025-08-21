import React, { useState, useRef } from 'react';

interface RecorderProps {
  interviewId: number;
  onUploadComplete?: () => void;
}

interface UploadResponse {
  upload_url: string;
  media_id: string;
}

interface PlayResponse {
  play_url: string;
  file_name?: string;
  file_type?: string;
}

// MediaRecorder 타입 확장 (TypeScript 타입 문제 해결용)
declare global {
  interface MediaRecorder {
    readonly mimeType: string;
  }
}

const InterviewRecorder: React.FC<RecorderProps> = ({ interviewId, onUploadComplete }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // 녹화 시작
  const startRecording = async () => {
    try {
      setError(null);
      
      // 브라우저 지원 확인
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('이 브라우저는 미디어 녹화를 지원하지 않습니다');
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true 
      });
      
      // MediaRecorder 지원 확인
      const options: MediaRecorderOptions = {};
      if (MediaRecorder.isTypeSupported('video/webm')) {
        options.mimeType = 'video/webm';
      } else if (MediaRecorder.isTypeSupported('video/mp4')) {
        options.mimeType = 'video/mp4';
      } else {
        console.warn('WebM과 MP4 형식을 모두 지원하지 않음, 기본 형식 사용');
      }
      
      const mediaRecorder = new MediaRecorder(stream, options);
      
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const mimeType = mediaRecorder.mimeType || 'video/webm';
        const blob = new Blob(chunksRef.current, { type: mimeType });
        await uploadVideo(blob);
        
        // 스트림 정리
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.onerror = (event) => {
        setError('녹화 중 오류가 발생했습니다');
        console.error('MediaRecorder error:', event);
      };

      mediaRecorder.start(1000); // 1초마다 데이터 수집
      setIsRecording(true);
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '녹화를 시작할 수 없습니다';
      setError(errorMessage);
      console.error('Recording start error:', error);
    }
  };

  // 녹화 정지
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // 비디오 업로드
  const uploadVideo = async (blob: Blob) => {
    setIsUploading(true);
    setUploadProgress(0);
    setError(null);
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('로그인이 필요합니다');
      }

      // 파일 정보 준비
      const fileExtension = blob.type.includes('webm') ? 'webm' : 'mp4';
      const fileName = `interview-${interviewId}-${Date.now()}.${fileExtension}`;
      
      // 1. 업로드 URL 요청
      setUploadProgress(10);
      const response = await fetch('/video/upload-url', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          interview_id: interviewId,
          file_name: fileName,
          file_type: 'video',
          file_size: blob.size
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: null }));
        throw new Error((errorData as any).detail || `업로드 URL 요청 실패: ${response.status}`);
      }
      
      const { upload_url, media_id }: UploadResponse = await response.json();
      
      // 2. S3에 직접 업로드
      setUploadProgress(30);
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        headers: {
          'Content-Type': blob.type
        },
        body: blob
      });
      
      if (!uploadResponse.ok) {
        throw new Error(`S3 업로드 실패: ${uploadResponse.status}`);
      }
      
      // 3. 업로드 완료 처리
      setUploadProgress(90);
      const completeResponse = await fetch(`/video/complete/${media_id}?file_size=${blob.size}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!completeResponse.ok) {
        console.warn('업로드 완료 처리 실패, 하지만 파일은 업로드됨');
      }
      
      setUploadProgress(100);
      onUploadComplete?.();
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '업로드 중 오류가 발생했습니다';
      setError(errorMessage);
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
      setTimeout(() => setUploadProgress(0), 2000); // 2초 후 프로그레스 바 초기화
    }
  };

  return (
    <div className="p-4 border rounded-lg">
      <h3 className="font-bold mb-4">면접 녹화</h3>
      
      {/* 에러 메시지 */}
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          ❌ {error}
        </div>
      )}
      
      {/* 녹화 상태 */}
      <div className="mb-4">
        {!isRecording && !isUploading && (
          <button 
            onClick={startRecording}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
            disabled={isUploading}
          >
            🔴 녹화 시작
          </button>
        )}
        
        {isRecording && (
          <button 
            onClick={stopRecording}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors animate-pulse"
          >
            ⏹️ 녹화 정지
          </button>
        )}
        
        {isUploading && (
          <div className="space-y-2">
            <div className="text-blue-600 font-medium">
              📤 업로드 중... {uploadProgress}%
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` } as React.CSSProperties}
              ></div>
            </div>
          </div>
        )}
      </div>
      
      {/* 상태 정보 */}
      <div className="text-sm text-gray-600">
        {isRecording && "🔴 녹화 진행 중..."}
        {isUploading && "📤 S3 업로드 진행 중..."}
        {!isRecording && !isUploading && !error && "📱 녹화 준비 완료"}
        {uploadProgress === 100 && "✅ 업로드 완료!"}
      </div>
    </div>
  );
};

export default InterviewRecorder;