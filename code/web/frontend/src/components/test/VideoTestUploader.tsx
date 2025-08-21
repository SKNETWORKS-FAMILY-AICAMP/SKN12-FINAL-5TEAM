import React, { useState, useEffect, useRef, useCallback } from 'react';
import { UploaderProps, TestUploadResponse } from './types';
import apiClient, { handleApiError } from '../../services/api';
import { GAZE_CONSTANTS, GAZE_ERROR_MESSAGES } from '../../constants/gazeConstants';
import { tokenManager } from '../../services/api';

// 다양한 완료 API 패턴 시도 함수
const tryCompleteUpload = async (mediaId: string, fileSize: number): Promise<void> => {
  const completeEndpoints = [
    // ⭐ 기존 구현된 API 경로 (video_api.py에서 확인)
    { method: 'PATCH', url: `/video/complete/${mediaId}?file_size=${fileSize}` },
    { method: 'POST', url: `/video/complete/${mediaId}?file_size=${fileSize}` },
    { method: 'PUT', url: `/video/complete/${mediaId}?file_size=${fileSize}` },
    // body에 file_size 포함하는 버전 (기존 API에 맞음)
    { method: 'PATCH', url: `/video/complete/${mediaId}`, body: { file_size: fileSize } },
    { method: 'POST', url: `/video/complete/${mediaId}`, body: { file_size: fileSize } },
    { method: 'PUT', url: `/video/complete/${mediaId}`, body: { file_size: fileSize } },
    
    // 추가 시도 패턴들
    { method: 'PATCH', url: `/media/complete/${mediaId}?file_size=${fileSize}` },
    { method: 'POST', url: `/media/complete/${mediaId}?file_size=${fileSize}` },
    { method: 'PUT', url: `/media/complete/${mediaId}?file_size=${fileSize}` },
    { method: 'PATCH', url: `/media/${mediaId}/complete?file_size=${fileSize}` },
    { method: 'POST', url: `/media/${mediaId}/complete?file_size=${fileSize}` },
    { method: 'PUT', url: `/media/${mediaId}/complete?file_size=${fileSize}` },
    { method: 'PATCH', url: `/media/test/${mediaId}/complete?file_size=${fileSize}` },
    { method: 'POST', url: `/media/test/${mediaId}/complete?file_size=${fileSize}` }
  ];

  const token = tokenManager.getToken();

  for (const endpoint of completeEndpoints) {
    try {
      console.log(`🔄 완료 API 시도: ${endpoint.method} ${endpoint.url}`);
      
      const requestOptions: RequestInit = {
        method: endpoint.method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      };
      
      if (endpoint.body) {
        requestOptions.body = JSON.stringify(endpoint.body);
      }
      
      const response = await apiClient.request({
        method: endpoint.method as any,
        url: endpoint.url,
        data: endpoint.body,
        timeout: GAZE_CONSTANTS.API_TIMEOUT
      });
      
      console.log(`📨 API 응답: ${endpoint.method} ${endpoint.url} -> ${response.status} ${response.statusText}`);
      
      console.log(`✅ 완료 API 성공: ${endpoint.method} ${endpoint.url}`);
      return; // 성공시 종료
    } catch (error) {
      console.warn(`⚠️ API 호출 실패: ${endpoint.method} ${endpoint.url}:`, error);
    }
  }
  
  console.warn('⚠️ 모든 완료 API 패턴 시도 실패 - S3 업로드는 성공했지만 DB 상태 업데이트 못함');
};

const VideoTestUploader: React.FC<UploaderProps> = ({ 
  blob, 
  onUploadComplete, 
  onUploadProgress, 
  onError 
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const useEffectExecutedRef = useRef<boolean>(false); // React.StrictMode 중복 실행 방지

  const startUpload = useCallback(async () => {
    console.log('🚀 startUpload 함수 호출됨:', { hasBlob: !!blob, blobSize: blob?.size, isUploading });
    
    if (!blob) {
      console.log('❌ startUpload: blob이 없음');
      return;
    }

    // 파일 크기 검증
    if (blob.size === 0) {
      console.error('❌ 업로드 실패: 파일 크기가 0바이트');
      onError('녹화된 비디오가 없습니다. 다시 녹화해주세요.');
      return;
    }

    if (blob.size < 1024) { // 1KB 미만
      console.warn('⚠️ 업로드 경고: 파일 크기가 너무 작음 (' + blob.size + ' bytes)');
      onError('녹화된 비디오가 너무 작습니다. 더 오래 녹화해주세요.');
      return;
    }

    console.log('✅ 파일 크기 검증 통과:', blob.size, 'bytes');

    setIsUploading(true);
    setProgress(0);
    setUploadStatus('업로드 준비 중...');

    // 파일 정보 준비 (try 블록 밖에서 선언)
    const originalContentType = blob.type;
    const normalizeContentType = (blobType: string): string => {
      if (blobType.includes('webm')) {
        return 'video/webm';  // codecs=vp9,opus 등 파라미터 제거
      } else if (blobType.includes('mp4')) {
        return 'video/mp4';   // 기타 codecs 파라미터 제거
      }
      return blobType.split(';')[0]; // 세미콜론 이후 파라미터 모두 제거
    };
    const normalizedContentType = normalizeContentType(originalContentType);

    try {
      // 실제 면접 ID를 Context에서 가져오기
      const interviewState = localStorage.getItem('interview_state');
      const interviewId = interviewState ? JSON.parse(interviewState).sessionId || '999' : '999';

      // 파일 확장자와 이름 준비
      const fileExtension = normalizedContentType.includes('webm') ? 'webm' : 'mp4';
      const fileName = `test-video-${Date.now()}.${fileExtension}`;
      
      console.log('📁 파일 정보 (Content-Type 정규화):', {
        size: blob.size,
        originalType: originalContentType,
        normalizedType: normalizedContentType,
        fileName,
        fileExtension
      });

      // 1. 업로드 URL 요청
      setProgress(10);
      setUploadStatus('업로드 URL 요청 중...');
      onUploadProgress(10);

      const token = tokenManager.getToken();
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      };
      console.log('🔍 Request headers:', headers);
      
      const response = await apiClient.post('/media/test/upload-url', {
        interview_id: interviewId,  // 실제 면접 ID 사용
        file_name: fileName,
        file_type: 'video',
        file_size: blob.size,
        content_type: normalizedContentType
      });

      const { upload_url, media_id, test_id } = response.data as TestUploadResponse;
      
      console.log('✅ Presigned URL 받음:', {
        upload_url: upload_url.substring(0, 100) + '...',
        media_id,
        test_id
      });

      // 2. S3에 직접 업로드
      setProgress(30);
      setUploadStatus('S3에 업로드 중...');
      onUploadProgress(30);

      console.log('📤 S3 업로드 시작 (정규화된 Content-Type):', {
        method: 'PUT',
        originalBlobType: originalContentType,
        normalizedContentType: normalizedContentType,
        size: blob.size,
        url: upload_url.split('?')[0] + '...'
      });

      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        headers: {
          'Content-Type': normalizedContentType  // AWS 서명과 일치하는 정규화된 Content-Type
        },
        body: blob
      });
      
      console.log('📤 S3 응답:', {
        status: uploadResponse.status,
        statusText: uploadResponse.statusText,
        headers: Object.fromEntries(uploadResponse.headers.entries())
      });

      if (!uploadResponse.ok) {
        const errorText = await uploadResponse.text().catch(() => 'No response body');
        console.error('❌ S3 업로드 실패:', {
          status: uploadResponse.status,
          statusText: uploadResponse.statusText,
          errorText,
          url: upload_url.split('?')[0]  // query params 제거하고 base URL만
        });
        
        // 에러 유형별 구체적인 메시지
        if (uploadResponse.status === 403) {
          if (errorText.includes('SignatureDoesNotMatch')) {
            throw new Error(`S3 서명 불일치 오류 (403): Content-Type 정규화 필요 - 원본: ${originalContentType}, 정규화: ${normalizedContentType}. ${errorText}`);
          } else {
            throw new Error(`S3 업로드 권한 오류 (403): CORS 설정 또는 IAM 권한을 확인하세요. ${errorText}`);
          }
        } else {
          throw new Error(`S3 업로드 실패 (${uploadResponse.status}): ${uploadResponse.statusText} - ${errorText}`);
        }
      }

      // 3. 업로드 완료 처리 (다양한 API 패턴 시도)
      setProgress(90);
      setUploadStatus('업로드 완료 처리 중...');
      onUploadProgress(90);

      await tryCompleteUpload(media_id, blob.size);

      // 4. 완료
      setProgress(100);
      setUploadStatus('업로드 완료!');
      onUploadProgress(100);
      onUploadComplete(media_id, test_id); // media_id를 첫 번째 인자로 전달

    } catch (error) {
      const errorMessage = handleApiError(error);
      console.error('❌ Upload failed:', {
        error,
        message: errorMessage,
        blob: {
          size: blob.size,
          type: originalContentType,
          normalized: normalizedContentType
        }
      });
      onError(`${GAZE_ERROR_MESSAGES.UPLOAD_FAILED}: ${errorMessage}`);
    } finally {
      setIsUploading(false);
    }
  }, [onUploadComplete, onUploadProgress, onError]); // blob 의존성 제거

  useEffect(() => {
    console.log('📋 VideoTestUploader useEffect 실행:', {
      hasBlob: !!blob,
      isUploading,
      alreadyExecuted: useEffectExecutedRef.current,
      blobSize: blob?.size,
      blobType: blob?.type
    });

    // React.StrictMode 중복 실행 방지
    if (useEffectExecutedRef.current) {
      console.log('⚠️ useEffect 이미 실행됨 - StrictMode 중복 방지');
      return;
    }
    
    // blob이 있고 업로드 중이 아니며 아직 실행되지 않았을 때만 실행
    if (blob && !isUploading) {
      console.log('✅ 업로드 시작 조건 충족 - startUpload 호출');
      useEffectExecutedRef.current = true; // 실행 전에 플래그 설정
      startUpload();
    } else {
      console.log('❌ 업로드 시작 조건 불충족:', { hasBlob: !!blob, isUploading });
    }
  }, [blob, isUploading, startUpload]);

  return (
    <div className="space-y-4">
      {/* 파일 정보 */}
      {blob && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">📁 파일 정보</h4>
          <div className="text-sm text-gray-600 space-y-1">
            <p>크기: {(blob.size / (1024 * 1024)).toFixed(2)} MB</p>
            <p>형식: {blob.type}</p>
          </div>
        </div>
      )}

      {/* 업로드 진행상황 */}
      {isUploading && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-blue-600 font-medium">📤 {uploadStatus}</span>
            <span className="text-blue-600 font-bold">{progress}%</span>
          </div>
          
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div 
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          
          <div className="text-center text-sm text-gray-500">
            {progress < 100 ? '업로드가 진행 중입니다...' : '업로드가 완료되었습니다!'}
          </div>
        </div>
      )}

      {/* 완료 상태 */}
      {!isUploading && progress === 100 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
          <div className="text-green-600 font-bold text-lg mb-2">
            ✅ 업로드 성공!
          </div>
          <div className="text-green-700 text-sm">
            S3에 성공적으로 업로드되었습니다.
          </div>
        </div>
      )}

      {/* 수동 재시도 버튼 (에러 시) */}
      {!isUploading && progress === 0 && blob && (
        <button
          onClick={startUpload}
          className="w-full bg-gradient-to-r from-blue-500 to-purple-500 text-white py-3 rounded-lg font-bold hover:shadow-lg hover:scale-105 transition-all"
        >
          📤 업로드 시작
        </button>
      )}
    </div>
  );
};

export default VideoTestUploader;