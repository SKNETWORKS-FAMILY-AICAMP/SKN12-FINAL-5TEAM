import React, { useState } from 'react';
import VideoTestRecorder from './VideoTestRecorder';
import VideoTestUploader from './VideoTestUploader';
import VideoTestPlayer from './VideoTestPlayer';
import VideoCalibration from './VideoCalibration';
import VideoGazeAnalysis from './VideoGazeAnalysis';
import VideoGazeResult from './VideoGazeResult';
import { TestSessionState, GazeAnalysisResult } from './types';

interface VideoTestModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const VideoTestModal: React.FC<VideoTestModalProps> = ({ isOpen, onClose }) => {
  const [sessionState, setSessionState] = useState<TestSessionState>({
    step: 'calibration',
    isRecording: false,
    isUploading: false,
    uploadProgress: 0,
    error: null,
    recordedBlob: null,
    testId: null,
    mediaId: null,
    // 시선 분석 관련 상태
    calibrationSessionId: null,
    isCalibrating: false,
    calibrationPhase: 'ready',
    isAnalyzing: false,
    analysisTaskId: null,
    gazeResult: null,
  });

  const resetSession = () => {
    console.log('🔄 세션 초기화 - 캘리브레이션 단계로 리셋');
    setSessionState({
      step: 'calibration',
      isRecording: false,
      isUploading: false,
      uploadProgress: 0,
      error: null,
      recordedBlob: null,
      testId: null,
      mediaId: null,
      // 시선 분석 관련 상태 초기화
      calibrationSessionId: null,
      isCalibrating: false,
      calibrationPhase: 'ready',
      isAnalyzing: false,
      analysisTaskId: null,
      gazeResult: null,
    });
  };

  const handleRecordingComplete = (blob: Blob) => {
    console.log('🎬 녹화 완료 - Modal에서 업로드 단계로 전환:', {
      blobSize: blob.size,
      blobType: blob.type,
      currentStep: sessionState.step
    });
    
    setSessionState(prev => ({
      ...prev,
      step: 'upload',
      recordedBlob: blob,
      error: null
    }));
  };

  const handleUploadComplete = (testId: string, mediaId: string) => {
    setSessionState(prev => ({
      ...prev,
      step: 'analyze',
      testId,
      mediaId,
      error: null
    }));
  };

  const handleUploadProgress = (progress: number) => {
    setSessionState(prev => ({
      ...prev,
      uploadProgress: progress
    }));
  };

  const handleError = (error: string) => {
    setSessionState(prev => ({
      ...prev,
      error
    }));
  };

  const handleClose = () => {
    resetSession();
    onClose();
  };

  // 새로운 핸들러 함수들
  const handleCalibrationComplete = (sessionId: string) => {
    console.log('🎯 캘리브레이션 완료 - 녹화 단계로 전환:', sessionId);
    setSessionState(prev => ({
      ...prev,
      step: 'record',
      calibrationSessionId: sessionId,
      error: null
    }));
  };

  const handleAnalysisComplete = (result: GazeAnalysisResult) => {
    console.log('🔍 시선 분석 완료 - 결과 단계로 전환:', result);
    setSessionState(prev => ({
      ...prev,
      step: 'result',
      gazeResult: result,
      isAnalyzing: false,
      error: null
    }));
  };

  const handleAnalysisProgress = (progress: number) => {
    setSessionState(prev => ({
      ...prev,
      uploadProgress: Math.round(progress * 100)
    }));
  };

  const goBackToRecord = () => {
    setSessionState(prev => ({
      ...prev,
      step: 'record',
      recordedBlob: null,
      testId: null,
      mediaId: null,
      error: null,
      uploadProgress: 0,
      isAnalyzing: false,
      analysisTaskId: null,
      gazeResult: null
    }));
  };

  const goBackToCalibration = () => {
    setSessionState(prev => ({
      ...prev,
      step: 'calibration',
      recordedBlob: null,
      testId: null,
      mediaId: null,
      error: null,
      uploadProgress: 0,
      calibrationSessionId: null,
      isAnalyzing: false,
      analysisTaskId: null,
      gazeResult: null
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* 헤더 */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">👁️ 시선 분석 테스트</h2>
              <p className="text-gray-600 text-sm mt-1">4포인트 캘리브레이션 → 면접 녹화 → 시선 분석</p>
            </div>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
            >
              ×
            </button>
          </div>
          
          {/* 진행 단계 표시 */}
          <div className="flex justify-center mt-6">
            <div className="flex items-center space-x-2 overflow-x-auto">
              {[
                { step: 'calibration', label: '캘리브레이션', icon: '🎯' },
                { step: 'record', label: '녹화', icon: '🎬' },
                { step: 'upload', label: '업로드', icon: '📤' },
                { step: 'analyze', label: '분석', icon: '🔍' },
                { step: 'result', label: '결과', icon: '📊' }
              ].map((item, index) => {
                const isActive = sessionState.step === item.step;
                const isCompleted = ['calibration', 'record', 'upload', 'analyze', 'result'].indexOf(sessionState.step) > index;
                
                return (
                  <React.Fragment key={item.step}>
                    <div className={`flex items-center space-x-1 ${
                      isActive ? 'text-blue-600' : 
                      isCompleted ? 'text-green-600' : 
                      'text-gray-400'
                    }`}>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                        isActive ? 'bg-blue-100' : 
                        isCompleted ? 'bg-green-100' : 
                        'bg-gray-100'
                      }`}>
                        {isCompleted ? '✓' : index + 1}
                      </div>
                      <span className="text-xs font-medium hidden sm:block">{item.label}</span>
                      <span className="text-sm sm:hidden">{item.icon}</span>
                    </div>
                    {index < 4 && <div className="w-4 h-0.5 bg-gray-300"></div>}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="p-6">
          {/* 에러 메시지 */}
          {sessionState.error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start">
                <span className="text-red-500 text-xl mr-3">❌</span>
                <div>
                  <h4 className="text-red-800 font-medium">오류가 발생했습니다</h4>
                  <p className="text-red-700 text-sm mt-1">{sessionState.error}</p>
                </div>
              </div>
            </div>
          )}

          {/* 단계별 컴포넌트 */}
          {sessionState.step === 'calibration' && (
            <>
              <div className="text-center text-sm text-blue-600 mb-4">
                🎯 1단계: 시선 캘리브레이션
              </div>
              <VideoCalibration
                onCalibrationComplete={handleCalibrationComplete}
                onError={handleError}
              />
            </>
          )}

          {sessionState.step === 'record' && (
            <>
              <div className="text-center text-sm text-blue-600 mb-4">
                🎬 2단계: 면접 동영상 녹화
              </div>
              <VideoTestRecorder
                onRecordingComplete={handleRecordingComplete}
                onError={handleError}
              />
            </>
          )}

          {sessionState.step === 'upload' && sessionState.recordedBlob && (
            <>
              <div className="text-center text-sm text-blue-600 mb-4">
                📤 3단계: S3에 업로드 중... (크기: {(sessionState.recordedBlob.size / (1024 * 1024)).toFixed(2)} MB)
              </div>
              <VideoTestUploader
                blob={sessionState.recordedBlob}
                onUploadComplete={handleUploadComplete}
                onUploadProgress={handleUploadProgress}
                onError={handleError}
              />
            </>
          )}

          {sessionState.step === 'analyze' && sessionState.testId && sessionState.calibrationSessionId && (
            <>
              <div className="text-center text-sm text-blue-600 mb-4">
                🔍 4단계: 시선 분석 진행 중
              </div>
              <VideoGazeAnalysis
                videoUrl={`/video/play/${sessionState.testId}`}
                calibrationSessionId={sessionState.calibrationSessionId}
                onAnalysisComplete={handleAnalysisComplete}
                onProgress={handleAnalysisProgress}
                onError={handleError}
              />
            </>
          )}

          {sessionState.step === 'result' && sessionState.gazeResult && (
            <>
              <div className="text-center text-sm text-blue-600 mb-4">
                📊 5단계: 시선 분석 결과
              </div>
              <VideoGazeResult
                result={sessionState.gazeResult}
                onRestart={resetSession}
              />
            </>
          )}
        </div>

        {/* 푸터 */}
        <div className="border-t border-gray-200 p-6">
          <div className="flex justify-between">
            <div className="flex space-x-3">
              {sessionState.step === 'record' && (
                <button
                  onClick={goBackToCalibration}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  🎯 캘리브레이션 다시하기
                </button>
              )}
              {(sessionState.step === 'upload' || sessionState.step === 'analyze') && (
                <button
                  onClick={goBackToRecord}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  🔄 다시 녹화
                </button>
              )}
              {sessionState.step === 'result' && (
                <button
                  onClick={resetSession}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  🔄 처음부터 다시
                </button>
              )}
            </div>

            <div className="flex space-x-3">
              <button
                onClick={handleClose}
                className="px-6 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoTestModal;