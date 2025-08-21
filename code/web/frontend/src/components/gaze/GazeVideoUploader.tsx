import React, { useState, useRef, useCallback } from 'react';
import { interviewApi } from '../../services/api';

interface GazeVideoUploaderProps {
  sessionId: string;  // session_id를 props로 받도록 변경
  onUploadComplete: (s3Key: string) => void;
  onUploadProgress: (progress: number) => void;
  onError: (error: string) => void;
  disabled?: boolean;
  className?: string;
}

interface UploadState {
  isUploading: boolean;
  progress: number;
  error: string | null;
  completed: boolean;
}

const GazeVideoUploader: React.FC<GazeVideoUploaderProps> = ({
  sessionId,
  onUploadComplete,
  onUploadProgress,
  onError,
  disabled = false,
  className = ''
}) => {
  const [uploadState, setUploadState] = useState<UploadState>({
    isUploading: false,
    progress: 0,
    error: null,
    completed: false
  });
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 파일 크기를 인간이 읽기 쉬운 형태로 변환
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 파일 유효성 검증
  const validateFile = (file: File): string | null => {
    // 파일 타입 확인
    const allowedTypes = ['video/webm', 'video/mp4', 'video/quicktime'];
    if (!allowedTypes.includes(file.type)) {
      return '지원되지 않는 파일 형식입니다. WebM, MP4, MOV 파일만 업로드할 수 있습니다.';
    }

    // 파일 크기 확인 (100MB 제한)
    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
      return '파일 크기가 너무 큽니다. 100MB 이하의 파일만 업로드할 수 있습니다.';
    }

    // 파일명 길이 확인
    if (file.name.length > 200) {
      return '파일명이 너무 깁니다. 200자 이하로 줄여주세요.';
    }

    return null;
  };

  // 청크 업로드 함수
  const uploadInChunks = async (
    uploadUrl: string, 
    file: File, 
    onProgress: (progress: number) => void
  ): Promise<void> => {
    const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB 청크
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    
    // 파일이 작으면 통째로 업로드
    if (totalChunks === 1) {
      return uploadDirectly(uploadUrl, file, onProgress);
    }

    console.log(`📦 청크 업로드 시작: ${totalChunks}개 청크`);
    
    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      if (abortControllerRef.current?.signal.aborted) {
        throw new Error('업로드가 취소되었습니다.');
      }

      const start = chunkIndex * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);
      
      console.log(`📤 청크 ${chunkIndex + 1}/${totalChunks} 업로드 (${start}-${end})`);
      
      const response = await fetch(uploadUrl, {
        method: 'PUT',
        body: chunk,
        headers: {
          'Content-Type': file.type,
          'Content-Range': `bytes ${start}-${end - 1}/${file.size}`,
        },
        signal: abortControllerRef.current?.signal
      });

      if (!response.ok) {
        throw new Error(`청크 업로드 실패: ${response.status} ${response.statusText}`);
      }

      const progress = ((chunkIndex + 1) / totalChunks) * 100;
      onProgress(progress);
    }
  };

  // 직접 업로드 함수 (작은 파일용)
  const uploadDirectly = async (
    uploadUrl: string, 
    file: File, 
    onProgress: (progress: number) => void
  ): Promise<void> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = (event.loaded / event.total) * 100;
          onProgress(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          onProgress(100);
          resolve();
        } else {
          reject(new Error(`업로드 실패: ${xhr.status} ${xhr.statusText}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('네트워크 오류로 업로드에 실패했습니다.'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('업로드가 취소되었습니다.'));
      });

      if (abortControllerRef.current) {
        abortControllerRef.current.signal.addEventListener('abort', () => {
          xhr.abort();
        });
      }

      xhr.open('PUT', uploadUrl);
      xhr.setRequestHeader('Content-Type', file.type);
      xhr.send(file);
    });
  };

  // 파일 업로드 처리
  const handleFileUpload = useCallback(async (file: File) => {
    try {
      // 필수 데이터 검증
      if (!sessionId) {
        throw new Error('세션 ID를 찾을 수 없습니다. 면접을 다시 시작해주세요.');
      }

      setUploadState({
        isUploading: true,
        progress: 0,
        error: null,
        completed: false
      });

      console.log('🚀 시선 추적 비디오 업로드 시작:', file.name, formatFileSize(file.size));

      // 1. Presigned URL 요청 (session_id 기반으로 변경)
      console.log('📝 S3 업로드 URL 요청 중... (session_id:', sessionId, ')');
      const uploadResponse = await interviewApi.getGazeUploadUrl({
        session_id: sessionId,  // interview_id 대신 session_id 사용
        file_name: file.name,
        file_size: file.size,
        file_type: 'video'
      });

      console.log('✅ S3 업로드 URL 받음:', uploadResponse.media_id);

      // 2. S3에 직접 업로드
      console.log('📤 S3 직접 업로드 시작...');
      abortControllerRef.current = new AbortController();
      
      await uploadInChunks(uploadResponse.upload_url, file, (progress) => {
        setUploadState(prev => ({ ...prev, progress }));
        onUploadProgress(progress);
      });

      console.log('✅ S3 업로드 완료');

      // 3. 백엔드에서 받은 S3 키 사용
      const s3Key = uploadResponse.s3_key;

      setUploadState({
        isUploading: false,
        progress: 100,
        error: null,
        completed: true
      });

      console.log('🎉 시선 추적 비디오 업로드 완료:', s3Key);
      onUploadComplete(s3Key);

    } catch (error: any) {
      console.error('❌ 시선 추적 비디오 업로드 실패:', error);
      
      const errorMessage = error.name === 'AbortError' 
        ? '업로드가 취소되었습니다.'
        : error.message || '알 수 없는 오류가 발생했습니다.';

      setUploadState({
        isUploading: false,
        progress: 0,
        error: errorMessage,
        completed: false
      });

      onError(errorMessage);
    } finally {
      abortControllerRef.current = null;
    }
  }, [sessionId, onUploadComplete, onUploadProgress, onError]);

  // 파일 선택 처리
  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    console.log('📂 파일 선택됨:', file.name, file.type, formatFileSize(file.size));

    // 파일 유효성 검증
    const validationError = validateFile(file);
    if (validationError) {
      setUploadState(prev => ({ ...prev, error: validationError }));
      onError(validationError);
      return;
    }

    handleFileUpload(file);
  }, [handleFileUpload, onError]);

  // 드래그 앤 드롭 처리
  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();

    if (disabled || uploadState.isUploading) return;

    const files = Array.from(event.dataTransfer.files);
    const file = files[0];

    if (!file) return;

    console.log('📁 드래그 앤 드롭으로 파일 선택됨:', file.name);

    const validationError = validateFile(file);
    if (validationError) {
      setUploadState(prev => ({ ...prev, error: validationError }));
      onError(validationError);
      return;
    }

    handleFileUpload(file);
  }, [disabled, uploadState.isUploading, handleFileUpload, onError]);

  // 업로드 취소
  const handleCancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  // 다시 시도
  const handleRetry = useCallback(() => {
    setUploadState({
      isUploading: false,
      progress: 0,
      error: null,
      completed: false
    });
    
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, []);

  const isDisabled = disabled || uploadState.isUploading;

  return (
    <div className={`gaze-video-uploader ${className}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept="video/webm,video/mp4,video/quicktime"
        onChange={handleFileSelect}
        disabled={isDisabled}
        className="hidden"
      />
      
      {!uploadState.completed && !uploadState.error && (
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 ${
            isDisabled 
              ? 'border-gray-300 bg-gray-50 cursor-not-allowed' 
              : 'border-blue-300 bg-blue-50 hover:bg-blue-100 cursor-pointer'
          }`}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => !isDisabled && fileInputRef.current?.click()}
        >
          <div className="flex flex-col items-center gap-4">
            <div className="text-4xl">
              {uploadState.isUploading ? '⏳' : '📹'}
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {uploadState.isUploading ? '업로드 중...' : '시선 추적 비디오 업로드'}
              </h3>
              
              {uploadState.isUploading ? (
                <div className="space-y-3">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadState.progress}%` }}
                    />
                  </div>
                  <p className="text-sm text-gray-600">
                    {uploadState.progress.toFixed(1)}% 완료
                  </p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCancel();
                    }}
                    className="px-4 py-2 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                  >
                    취소
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-gray-600">
                    파일을 클릭하거나 드래그해서 업로드하세요
                  </p>
                  <p className="text-sm text-gray-500">
                    WebM, MP4, MOV 파일 지원 (최대 100MB)
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {uploadState.completed && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <div className="text-4xl mb-4">✅</div>
          <h3 className="text-lg font-semibold text-green-900 mb-2">
            업로드 완료!
          </h3>
          <p className="text-green-700">
            시선 추적 비디오가 성공적으로 업로드되었습니다.
          </p>
        </div>
      )}

      {uploadState.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <div className="text-4xl mb-4">❌</div>
          <h3 className="text-lg font-semibold text-red-900 mb-2">
            업로드 실패
          </h3>
          <p className="text-red-700 mb-4">
            {uploadState.error}
          </p>
          <button
            onClick={handleRetry}
            disabled={disabled}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            다시 시도
          </button>
        </div>
      )}
    </div>
  );
};

export default GazeVideoUploader;