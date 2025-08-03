import React from 'react';

interface StepIndicatorProps {
  currentStep: number;
  totalSteps: number;
  steps: string[];
}

const StepIndicator: React.FC<StepIndicatorProps> = ({ currentStep, totalSteps, steps }) => {
  return (
    <div className="w-full max-w-4xl mx-auto mb-8">
      {/* 진행률 바 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex-1 relative">
          <div className="w-full bg-slate-200 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${(currentStep / totalSteps) * 100}%` }}
            />
          </div>
        </div>
        <div className="ml-4 text-sm font-medium text-slate-600">
          {currentStep} / {totalSteps}
        </div>
      </div>

      {/* 단계 표시 */}
      <div className="flex justify-between">
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const isActive = stepNumber === currentStep;
          const isCompleted = stepNumber < currentStep;
          
          return (
            <div key={index} className="flex flex-col items-center">
              <div 
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300 ${
                  isCompleted 
                    ? 'bg-green-500 text-white' 
                    : isActive 
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white' 
                      : 'bg-slate-200 text-slate-500'
                }`}
              >
                {isCompleted ? '✓' : stepNumber}
              </div>
              <div 
                className={`text-xs mt-2 text-center max-w-16 ${
                  isActive ? 'text-blue-600 font-medium' : 'text-slate-500'
                }`}
              >
                {step}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default StepIndicator;