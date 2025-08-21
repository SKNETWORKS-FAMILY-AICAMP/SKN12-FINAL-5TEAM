import React, { useState, useRef, useEffect, useCallback } from 'react';
import { RecorderProps } from './types';

// MediaRecorder state type definition
type RecordingState = 'inactive' | 'recording' | 'paused';

const VideoTestRecorder: React.FC<RecorderProps> = ({ onRecordingComplete, onError }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const recordingStartTimeRef = useRef<number | null>(null);
  const isInitializingRef = useRef<boolean>(false);

  const stopRecording = useCallback(() => {
    const mediaRecorder = mediaRecorderRef.current;
    if (mediaRecorder && (mediaRecorder.state as RecordingState) === 'recording') {
      const recordingDuration = recordingStartTimeRef.current ? Date.now() - recordingStartTimeRef.current : 0;
      if (recordingDuration < 500) return;
      mediaRecorder.stop();
      setIsRecording(false);
      recordingStartTimeRef.current = null;
      isInitializingRef.current = false;
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, [isRecording]);

  useEffect(() => {
    checkMediaSupport();
    return () => {
      if (mediaRecorderRef.current && (mediaRecorderRef.current.state as RecordingState) === 'recording' && !isInitializingRef.current) {
        try { mediaRecorderRef.current.stop(); } catch (error) { console.error('❌ cleanup 중 MediaRecorder 중단 실패:', error); }
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => { if (track.readyState === 'live') track.stop(); });
        streamRef.current = null;
      }
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const checkMediaSupport = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setPermissionError('이 브라우저는 미디어 녹화를 지원하지 않습니다');
        return;
      }
      if (navigator.permissions) {
        try {
          const cameraPermission = await navigator.permissions.query({ name: 'camera' as PermissionName });
          const microphonePermission = await navigator.permissions.query({ name: 'microphone' as PermissionName });
          if (cameraPermission.state === 'denied' || microphonePermission.state === 'denied') {
            setPermissionError('카메라 또는 마이크 권한이 거부되었습니다. 브라우저 설정에서 권한을 허용해주세요.');
          }
        } catch (permError) { console.log('권한 조회 실패:', permError); }
      }
      setIsInitialized(true);
    } catch (error) {
      setPermissionError('미디어 장치 확인 중 오류가 발생했습니다');
    }
  };

  const startRecording = async () => {
    try {
      isInitializingRef.current = true;
      setIsLoading(true);
      setPermissionError(null);
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error('이 브라우저는 미디어 녹화를 지원하지 않습니다');
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      const options: MediaRecorderOptions = {};
      if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) options.mimeType = 'video/webm;codecs=vp8';
      else if (MediaRecorder.isTypeSupported('video/webm')) options.mimeType = 'video/webm';
      else if (MediaRecorder.isTypeSupported('video/mp4')) options.mimeType = 'video/mp4';
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];
      mediaRecorder.ondataavailable = (event) => { if (event.data.size > 0) chunksRef.current.push(event.data); };
      mediaRecorder.onstop = () => {
        const mimeType = mediaRecorder.mimeType || 'video/webm';
        const blob = new Blob(chunksRef.current, { type: mimeType });
        if (blob.size === 0) { onError('녹화에 실패했습니다. 다시 시도해주세요.'); return; }
        if (recordingTime < 1) { onError('최소 1초 이상 녹화해주세요.'); return; }
        onRecordingComplete(blob);
        if (streamRef.current) { streamRef.current.getTracks().forEach(track => track.stop()); streamRef.current = null; }
        if (videoRef.current) videoRef.current.srcObject = null;
      };
      mediaRecorder.onerror = (event) => { onError('녹화 중 오류가 발생했습니다'); };
      if ((mediaRecorder.state as RecordingState) !== 'inactive') throw new Error('MediaRecorder 상태가 올바르지 않습니다');
      setIsRecording(true);
      setRecordingTime(0);
      setIsLoading(false);
      recordingStartTimeRef.current = Date.now();
      mediaRecorder.start(1000);
      await new Promise(resolve => setTimeout(resolve, 100));
      if ((mediaRecorder.state as RecordingState) !== 'recording') {
        setIsRecording(false);
        recordingStartTimeRef.current = null;
        isInitializingRef.current = false;
        throw new Error('녹화를 시작할 수 없습니다. 브라우저 호환성을 확인하세요.');
      }
      isInitializingRef.current = false;
      timerRef.current = setInterval(() => { setRecordingTime(prev => prev + 1); }, 1000);
    } catch (error) {
      setIsLoading(false);
      isInitializingRef.current = false;
      const errorMessage = error instanceof Error ? error.message : '녹화를 시작할 수 없습니다';
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError' || error.message.includes('Permission denied')) setPermissionError('카메라와 마이크 접근 권한이 필요합니다. 브라우저에서 권한을 허용해주세요.');
        else if (error.name === 'NotFoundError') setPermissionError('카메라나 마이크를 찾을 수 없습니다. 장치가 연결되어 있는지 확인해주세요.');
        else setPermissionError(errorMessage);
      } else setPermissionError(errorMessage);
      onError(errorMessage);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isInitialized) return <div className="space-y-4"><div className="text-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div><p className="text-gray-600">미디어 장치 확인 중...</p></div></div>;

  if (permissionError) return <div className="space-y-4"><div className="bg-red-50 border border-red-200 rounded-lg p-6"><div className="text-center"><div className="text-red-500 text-4xl mb-4">🚫</div><h3 className="text-red-800 font-medium text-lg mb-2">미디어 접근 오류</h3><p className="text-red-700 text-sm mb-4">{permissionError}</p><div className="space-y-2 text-xs text-red-600"><p>💡 해결 방법:</p><p>1. 브라우저 주소창 옆의 카메라/마이크 아이콘 클릭</p><p>2. "허용"으로 설정 후 페이지 새로고침</p><p>3. 또는 브라우저 설정에서 카메라/마이크 권한 허용</p></div><button onClick={() => { setPermissionError(null); checkMediaSupport(); }} className="mt-4 bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 transition-colors">🔄 다시 시도</button></div></div></div>;

  return (
    <div className="space-y-4">
      <div className="relative">
        <video ref={videoRef} autoPlay muted playsInline className="w-full max-w-md mx-auto rounded-lg bg-gray-900" style={{ transform: 'scaleX(-1)' }} />
        {isRecording && <div className="absolute top-2 left-2 bg-red-500 text-white px-2 py-1 rounded text-sm font-bold animate-pulse">🔴 REC {formatTime(recordingTime)}</div>}
      </div>

      {/* 🚀 추가된 중요 안내 문구 */}
      {!isRecording && !isLoading && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 text-yellow-800 p-4" role="alert">
          <p className="font-bold">⚠️ 중요</p>
          <p className="text-sm">캘리브레이션과 <strong>동일한 자세와 거리</strong>를 유지하고, 카메라 렌즈를 응시하며 답변해주세요.</p>
        </div>
      )}

      <div className="flex justify-center space-x-4">
        {!isRecording ? (
          <button onClick={startRecording} disabled={isLoading} className="bg-gradient-to-r from-red-500 to-red-600 text-white px-6 py-3 rounded-full font-bold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed">
            {isLoading ? (<><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div><span>권한 요청 중...</span></>) : (<><span>🔴</span><span>녹화 시작</span></>)}
          </button>
        ) : (
          <button onClick={stopRecording} className="bg-gradient-to-r from-gray-500 to-gray-600 text-white px-6 py-3 rounded-full font-bold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2 animate-pulse">
            <span>⏹️</span><span>녹화 정지</span>
          </button>
        )}
      </div>

      <div className="text-center text-sm text-gray-600">
        {!isRecording && !isLoading && <p>📱 카메라와 마이크 권한을 허용한 후 녹화를 시작하세요</p>}
        {isLoading && <p className="text-blue-600 font-medium">🔄 미디어 권한 요청 중...</p>}
        {isRecording && <p className="text-red-600 font-medium">🔴 녹화 중... ({formatTime(recordingTime)})</p>}
      </div>
    </div>
  );
};

export default VideoTestRecorder;