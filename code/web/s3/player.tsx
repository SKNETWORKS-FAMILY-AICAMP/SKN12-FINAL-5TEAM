import React, { useState, useEffect } from 'react';

interface PlayerProps {
  interviewId: number;
}

const VideoPlayer: React.FC<PlayerProps> = ({ interviewId }) => {
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadVideo();
  }, [interviewId]);

  const loadVideo = async () => {
    try {
      const response = await fetch(`/video/play/${interviewId}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      if (response.ok) {
        const { play_url } = await response.json();
        setVideoUrl(play_url);
      } else {
        setError('비디오를 찾을 수 없습니다');
      }
    } catch (err) {
      setError('비디오 로드 실패');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">로딩 중...</div>;
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-600">
        {error}
      </div>
    );
  }

  if (!videoUrl) {
    return (
      <div className="text-center py-8 text-gray-500">
        업로드된 비디오가 없습니다
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-900 mb-4">면접 영상</h3>
      <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
        <video
          src={videoUrl}
          controls
          className="w-full h-full"
        />
      </div>
      <button className="w-full mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium">
        영상 저장
      </button>
    </div>
  );
};

export default VideoPlayer;