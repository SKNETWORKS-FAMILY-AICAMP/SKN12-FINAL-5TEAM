import React from 'react';

interface TextCompetitionHeaderProps {
  aiPersona: {
    name: string;
    summary: string;
  };
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
}

const TextCompetitionHeader: React.FC<TextCompetitionHeaderProps> = ({
  aiPersona,
  progress
}) => {
  return (
    <div className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700 p-4">
      <div className="max-w-6xl mx-auto flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
            <span className="text-white font-bold text-lg">🤖</span>
          </div>
          <div>
            <h2 className="text-white font-bold text-lg">AI 경쟁자: {aiPersona.name}</h2>
            <p className="text-gray-400 text-sm">{aiPersona.summary}</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-white font-semibold">
            {progress.current} / {progress.total} 질문
          </div>
          <div className="w-32 bg-gray-700 rounded-full h-2 mt-1">
            <div 
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress.percentage}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TextCompetitionHeader;