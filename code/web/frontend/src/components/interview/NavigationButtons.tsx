import React from 'react';
import LoadingSpinner from '../common/LoadingSpinner';

interface NavigationButtonsProps {
  onPrevious?: () => void;
  onNext?: () => void;
  previousLabel?: string;
  nextLabel?: string;
  canGoNext: boolean;
  isLoading?: boolean;
  showPrevious?: boolean;
}

const NavigationButtons: React.FC<NavigationButtonsProps> = ({
  onPrevious,
  onNext,
  previousLabel = "이전",
  nextLabel = "다음",
  canGoNext,
  isLoading = false,
  showPrevious = true
}) => {
  return (
    <div className="flex justify-between items-center pt-8 border-t border-slate-200">
      <div>
        {showPrevious && onPrevious && (
          <button
            onClick={onPrevious}
            className="flex items-center gap-2 px-6 py-3 text-slate-600 hover:text-slate-800 transition-colors"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
            </svg>
            {previousLabel}
          </button>
        )}
      </div>
      
      <div>
        {onNext && (
          <button
            onClick={onNext}
            disabled={!canGoNext || isLoading}
            className={`flex items-center gap-2 px-8 py-3 rounded-full font-medium transition-all ${
              canGoNext && !isLoading
                ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:shadow-lg hover:scale-105'
                : 'bg-slate-300 text-slate-500 cursor-not-allowed'
            }`}
          >
          {isLoading ? (
            <>
              <LoadingSpinner size="sm" color="white" />
              처리 중...
            </>
          ) : (
            <>
              {nextLabel}
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8.59 16.59L10 18l6-6-6-6-1.41 1.41L13.17 12z"/>
              </svg>
            </>
          )}
          </button>
        )}
      </div>
    </div>
  );
};

export default NavigationButtons;