import React from 'react';

interface SpeechIndicatorProps {
  isListening: boolean;
  isSpeaking: boolean;
  interimText?: string;
  className?: string;
  speakingType?: 'question' | 'ai_answer' | 'general';
}

const SpeechIndicator: React.FC<SpeechIndicatorProps> = ({
  isListening,
  isSpeaking,
  interimText,
  className = '',
  speakingType = 'general'
}) => {
  if (!isListening && !isSpeaking && !interimText) {
    return null;
  }

  const getSpeakingText = () => {
    switch (speakingType) {
      case 'question':
        return '질문 읽는 중...';
      case 'ai_answer':
        return 'AI 답변 중...';
      default:
        return '음성 출력 중...';
    }
  };

  return (
    <div className={`bg-white/90 backdrop-blur-sm rounded-lg border border-slate-200 p-4 ${className}`}>
      {/* 음성 인식 상태 */}
      {isListening && (
        <div className="flex items-center gap-3 mb-3">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
          </div>
          <span className="text-sm font-medium text-red-600">음성 인식 중...</span>
        </div>
      )}

      {/* 음성 출력 상태 */}
      {isSpeaking && (
        <div className="flex items-center gap-3 mb-3">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-bounce"></div>
            <div className="w-3 h-3 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-3 h-3 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
          <span className="text-sm font-medium text-green-600">{getSpeakingText()}</span>
        </div>
      )}

      {/* 임시 인식 텍스트 */}
      {interimText && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="text-xs text-blue-600 font-medium mb-1">인식된 음성:</div>
          <div className="text-sm text-blue-800 italic">
            "{interimText}"
          </div>
        </div>
      )}
    </div>
  );
};

export default SpeechIndicator;