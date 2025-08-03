import React from 'react';

interface ChatMessage {
  type: 'question' | 'user' | 'ai';
  content: string;
  timestamp: Date;
}

interface ChatHistoryProps {
  chatHistory: ChatMessage[];
  aiPersona: {
    name: string;
    summary: string;
  };
  candidateName: string;
  isCompleted: boolean;
}

const ChatHistory: React.FC<ChatHistoryProps> = ({
  chatHistory,
  aiPersona,
  candidateName,
  isCompleted
}) => {
  return (
    <div className="flex-1 overflow-y-auto mb-6 space-y-4 bg-gray-800/30 rounded-2xl p-6">
      {chatHistory.map((message, index) => (
        <div key={index} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
          {message.type === 'question' && (
            <div className="w-full">
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-4 text-white">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xl">👨‍💼</span>
                  <span className="font-semibold">면접관</span>
                </div>
                <p className="text-lg leading-relaxed">{message.content}</p>
              </div>
            </div>
          )}
          {message.type === 'user' && (
            <div className="max-w-2xl">
              <div className="bg-green-600 rounded-2xl p-4 text-white">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xl">👤</span>
                  <span className="font-semibold">{candidateName}</span>
                </div>
                <p className="leading-relaxed">{message.content}</p>
              </div>
            </div>
          )}
          {message.type === 'ai' && (
            <div className="max-w-2xl">
              <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-2xl p-4 text-white">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xl">🤖</span>
                  <span className="font-semibold">{aiPersona.name}</span>
                </div>
                <p className="leading-relaxed">{message.content}</p>
              </div>
            </div>
          )}
        </div>
      ))}
      
      {isCompleted && (
        <div className="w-full text-center">
          <div className="bg-gradient-to-r from-yellow-500 to-orange-500 rounded-2xl p-6 text-white">
            <h3 className="text-2xl font-bold mb-2">🎉 면접 완료!</h3>
            <p className="text-lg">텍스트 기반 AI 경쟁 면접이 모두 끝났습니다.</p>
            <p className="text-sm mt-2 opacity-90">잠시 후 결과 페이지로 이동합니다...</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatHistory;