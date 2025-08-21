import React, { useState, useEffect, useRef, useCallback } from 'react';
import { PlayerProps, TestPlayResponse } from './types';
import apiClient, { handleApiError } from '../../services/api';
import { GAZE_ERROR_MESSAGES } from '../../constants/gazeConstants';

const VideoTestPlayer: React.FC<PlayerProps> = ({ testId, onError }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoInfo, setVideoInfo] = useState<TestPlayResponse | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const loadVideo = useCallback(async () => {
    setIsLoading(true);
    
    try {
      console.log('🎥 비디오 로드 시작:', { testId });

      const response = await apiClient.get(`/video/play/${testId}`);
      const data = response.data as TestPlayResponse;
      console.log('✅ 비디오 데이터 받음:', {
        play_url: data.play_url ? `${data.play_url.substring(0, 100)}...` : 'null',
        file_name: data.file_name,
        file_type: data.file_type,
        test_id: data.test_id
      });
      setVideoInfo(data);
      setVideoUrl(data.play_url);
      
      // Presigned URL 유효성 체크
      if (data.play_url) {
        console.log('🔗 Presigned URL 유효성 체크 시작...');
        try {
          const urlCheck = await fetch(data.play_url, { method: 'HEAD' });
          console.log('🔗 Presigned URL 체크 결과:', {
            status: urlCheck.status,
            statusText: urlCheck.statusText,
            headers: {
              'content-type': urlCheck.headers.get('content-type'),
              'content-length': urlCheck.headers.get('content-length')
            }
          });
          if (!urlCheck.ok) {
            console.error('❌ Presigned URL이 유효하지 않음:', urlCheck.status);
          }
        } catch (urlError) {
          console.error('❌ Presigned URL 체크 실패:', urlError);
        }
      } else {
        console.error('❌ play_url이 null이거나 비어있음');
      }

    } catch (error) {
      const errorMessage = handleApiError(error);
      console.error('❌ 비디오 로드 실패:', { error, testId, errorMessage });
      onError(`${GAZE_ERROR_MESSAGES.SERVER_ERROR}: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  }, [testId, onError]); // testId와 onError를 의존성으로 추가

  useEffect(() => {
    if (testId) {
      loadVideo();
    }
  }, [testId, loadVideo]); // loadVideo를 의존성 배열에 추가

  const handlePlay = () => {
    if (videoRef.current) {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handlePause = () => {
    if (videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleVideoEnded = () => {
    setIsPlaying(false);
  };

  const downloadVideo = () => {
    if (videoUrl && videoInfo) {
      const link = document.createElement('a');
      link.href = videoUrl;
      link.download = videoInfo.file_name || 'test-video.webm';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">비디오를 로드하는 중...</p>
        </div>
      </div>
    );
  }

  if (!videoUrl || !videoInfo) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600 mb-4">비디오를 로드할 수 없습니다.</p>
        <button
          onClick={loadVideo}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 비디오 정보 */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-2">🎬 비디오 정보</h4>
        <div className="text-sm text-gray-600 space-y-1">
          <p>파일명: {videoInfo.file_name}</p>
          <p>형식: {videoInfo.file_type}</p>
          <p>테스트 ID: {videoInfo.test_id}</p>
        </div>
      </div>

      {/* 비디오 플레이어 */}
      <div className="relative">
        <video
          ref={videoRef}
          src={videoUrl}
          controls
          className="w-full max-w-md mx-auto rounded-lg bg-gray-900"
          onPlay={() => {
            console.log('🎬 비디오 재생 시작');
            setIsPlaying(true);
          }}
          onPause={() => {
            console.log('⏸️ 비디오 일시정지');
            setIsPlaying(false);
          }}
          onEnded={handleVideoEnded}
          onLoadStart={() => console.log('📂 비디오 로드 시작')}
          onLoadedMetadata={(e) => {
            const video = e.target as HTMLVideoElement;
            console.log('📋 비디오 메타데이터 로드됨:', {
              duration: video.duration,
              videoWidth: video.videoWidth,
              videoHeight: video.videoHeight,
              readyState: video.readyState
            });
          }}
          onLoadedData={() => console.log('📊 비디오 데이터 로드됨')}
          onCanPlay={() => console.log('▶️ 비디오 재생 가능')}
          onCanPlayThrough={() => console.log('🎯 비디오 끊김없이 재생 가능')}
          onError={(e) => {
            const video = e.target as HTMLVideoElement;
            console.error('❌ 비디오 재생 오류:', {
              error: video.error,
              networkState: video.networkState,
              readyState: video.readyState,
              src: videoUrl?.substring(0, 100) + '...'
            });
          }}
          onStalled={() => console.warn('⚠️ 비디오 로딩 지연')}
          onSuspend={() => console.log('⏸️ 비디오 로딩 중단')}
          onAbort={() => console.log('❌ 비디오 로딩 중단됨')}
          onEmptied={() => console.log('🗑️ 비디오 소스 비워짐')}
          preload="metadata"
        >
          Your browser does not support the video tag.
        </video>
      </div>

      {/* 제어 버튼들 */}
      <div className="flex justify-center space-x-4">
        <button
          onClick={isPlaying ? handlePause : handlePlay}
          className="bg-gradient-to-r from-green-500 to-green-600 text-white px-4 py-2 rounded-full font-bold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2"
        >
          <span>{isPlaying ? '⏸️' : '▶️'}</span>
          <span>{isPlaying ? '일시정지' : '재생'}</span>
        </button>

        <button
          onClick={downloadVideo}
          className="bg-gradient-to-r from-gray-500 to-gray-600 text-white px-4 py-2 rounded-full font-bold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2"
        >
          <span>⬇️</span>
          <span>다운로드</span>
        </button>
      </div>

      {/* 재생 상태 */}
      <div className="text-center text-sm text-gray-600">
        {isPlaying ? (
          <p className="text-green-600 font-medium">🎬 재생 중...</p>
        ) : (
          <p>📱 재생 버튼을 눌러 비디오를 시청하세요</p>
        )}
      </div>
    </div>
  );
};

export default VideoTestPlayer;