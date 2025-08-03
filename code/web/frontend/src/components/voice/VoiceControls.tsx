import React, { useState, useEffect } from 'react';
import { checkSpeechSupport } from '../../utils/speechUtils';

interface VoiceControlsProps {
  onStartSTT: () => void;
  onStopSTT: () => void;
  onPlayTTS: () => void;
  onStopTTS: () => void;
  isSTTActive: boolean;
  isTTSActive: boolean;
  disabled?: boolean;
  className?: string;
}

const VoiceControls: React.FC<VoiceControlsProps> = ({
  onStartSTT,
  onStopSTT,
  onPlayTTS,
  onStopTTS,
  isSTTActive,
  isTTSActive,
  disabled = false,
  className = ''
}) => {
  const [speechSupport, setSpeechSupport] = useState({ hasSTT: false, hasTTS: false });

  useEffect(() => {
    setSpeechSupport(checkSpeechSupport());
  }, []);

  const handleSTTToggle = () => {
    if (isSTTActive) {
      onStopSTT();
    } else {
      onStartSTT();
    }
  };

  const handleTTSToggle = () => {
    if (isTTSActive) {
      onStopTTS();
    } else {
      onPlayTTS();
    }
  };

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* STT 버튼 */}
      {speechSupport.hasSTT ? (
        <button
          onClick={handleSTTToggle}
          disabled={disabled}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
            isSTTActive
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-blue-500 text-white hover:bg-blue-600'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          title={isSTTActive ? '음성 인식 중지' : '음성 인식 시작'}
        >
          <span className="text-lg">
            {isSTTActive ? '🛑' : '🎤'}
          </span>
          <span className="text-sm">
            {isSTTActive ? '음성 중지' : '음성 입력'}
          </span>
        </button>
      ) : (
        <div className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-500 rounded-lg text-sm">
          <span>🎤</span>
          <span>음성 입력 불가</span>
        </div>
      )}

      {/* TTS 버튼 */}
      {speechSupport.hasTTS ? (
        <button
          onClick={handleTTSToggle}
          disabled={disabled}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
            isTTSActive
              ? 'bg-orange-500 text-white hover:bg-orange-600'
              : 'bg-green-500 text-white hover:bg-green-600'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          title={isTTSActive ? '음성 출력 중지' : '질문 다시 듣기'}
        >
          <span className="text-lg">
            {isTTSActive ? '🔇' : '🔊'}
          </span>
          <span className="text-sm">
            {isTTSActive ? '음성 중지' : '다시 듣기'}
          </span>
        </button>
      ) : (
        <div className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-500 rounded-lg text-sm">
          <span>🔊</span>
          <span>음성 출력 불가</span>
        </div>
      )}

      {/* 브라우저 호환성 안내 */}
      {(!speechSupport.hasSTT || !speechSupport.hasTTS) && (
        <div className="text-xs text-gray-500 max-w-48">
          {!speechSupport.hasSTT && !speechSupport.hasTTS
            ? 'Chrome 브라우저에서 음성 기능을 이용하세요'
            : !speechSupport.hasSTT
            ? '음성 입력은 Chrome에서만 지원됩니다'
            : '음성 출력 기능을 사용할 수 없습니다'
          }
        </div>
      )}
    </div>
  );
};

export default VoiceControls;