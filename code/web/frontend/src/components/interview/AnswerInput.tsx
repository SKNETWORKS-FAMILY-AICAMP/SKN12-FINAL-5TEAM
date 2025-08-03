import React, { useRef } from 'react';

interface AnswerInputProps {
  currentAnswer: string;
  setCurrentAnswer: (answer: string) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  isCompleted: boolean;
}

const AnswerInput: React.FC<AnswerInputProps> = ({
  currentAnswer,
  setCurrentAnswer,
  onSubmit,
  isSubmitting,
  isCompleted
}) => {
  const answerRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (!currentAnswer.trim() || isSubmitting) {
      return;
    }
    onSubmit();
  };

  if (isCompleted) {
    return null;
  }

  return (
    <div className="bg-gray-800/50 rounded-2xl p-6">
      <div className="mb-4">
        <label className="block text-white font-semibold mb-2">
          답변을 입력하세요:
        </label>
        <textarea
          ref={answerRef}
          value={currentAnswer}
          onChange={(e) => setCurrentAnswer(e.target.value)}
          placeholder="여기에 답변을 작성해주세요..."
          className="w-full h-32 p-4 bg-gray-700 text-white rounded-xl border border-gray-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none"
          disabled={isSubmitting}
          maxLength={500}
        />
      </div>
      
      <div className="flex justify-between items-center">
        <div className="text-gray-400 text-sm">
          {currentAnswer.length}/500자
        </div>
        <button
          onClick={handleSubmit}
          disabled={!currentAnswer.trim() || isSubmitting}
          className={`px-8 py-3 rounded-xl font-semibold transition-all ${
            !currentAnswer.trim() || isSubmitting
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:shadow-lg hover:scale-105'
          }`}
        >
          {isSubmitting ? (
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>제출 중...</span>
            </div>
          ) : (
            '답변 제출'
          )}
        </button>
      </div>
    </div>
  );
};

export default AnswerInput;