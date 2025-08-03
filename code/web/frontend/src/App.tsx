import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { InterviewProvider } from './contexts/InterviewContext';
import ErrorBoundary from './components/common/ErrorBoundary';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Pages
import MainPage from './pages/MainPage';
import InterviewSetup from './pages/InterviewSetup';
import InterviewActive from './pages/InterviewActive';
import InterviewActiveTemp from './pages/InterviewActive_temp';
import InterviewResults from './pages/InterviewResults';
import InterviewHistory from './pages/InterviewHistory';
import InterviewModeSelection from './pages/interview/InterviewModeSelection';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import SignUpPage from './pages/SignUpPage';

// New Interview Flow Pages
import JobPostingSelection from './pages/interview/JobPostingSelection';
import ResumeSelection from './pages/interview/ResumeSelection';
import AISetup from './pages/interview/AISetup';
import EnvironmentCheck from './pages/interview/EnvironmentCheck';

function App() {
  return (
    <ErrorBoundary>
      <InterviewProvider>
        <Router>
          <div className="App">
            <Routes>
              {/* Main Routes */}
              <Route path="/" element={<MainPage />} />
              <Route path="/history" element={
                <ProtectedRoute>
                  <InterviewHistory />
                </ProtectedRoute>
              } />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/profile" element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              } />
              <Route path="/signup" element={<SignUpPage />} />
              
              {/* New Interview Flow - 4 Steps */}
              <Route path="/interview/job-posting" element={
                <ProtectedRoute>
                  <JobPostingSelection />
                </ProtectedRoute>
              } />
              <Route path="/interview/resume-selection" element={
                <ProtectedRoute>
                  <ResumeSelection />
                </ProtectedRoute>
              } />
              <Route path="/interview/interview-mode-selection" element={
                <ProtectedRoute>
                  <InterviewModeSelection />
                </ProtectedRoute>
              } />
              <Route path="/interview/ai-setup" element={
                <ProtectedRoute>
                  <AISetup />
                </ProtectedRoute>
              } />
              <Route path="/interview/environment-check" element={
                <ProtectedRoute>
                  <EnvironmentCheck />
                </ProtectedRoute>
              } />
              
              {/* Interview Execution */}
              <Route path="/interview/active" element={
                <ProtectedRoute>
                  <InterviewActive />
                </ProtectedRoute>
              } />
              <Route path="/interview/active-temp" element={
                <ProtectedRoute>
                  <InterviewActiveTemp />
                </ProtectedRoute>
              } />
              <Route path="/interview/results" element={
                <ProtectedRoute>
                  <InterviewResults />
                </ProtectedRoute>
              } />
              <Route path="/interview/results/:sessionId" element={
                <ProtectedRoute>
                  <InterviewResults />
                </ProtectedRoute>
              } />
              
              {/* Legacy routes - redirect to new flow */}
              <Route path="/interview" element={<Navigate to="/interview/job-posting" replace />} />
              <Route path="/interview/setup" element={<Navigate to="/interview/job-posting" replace />} />
              
              {/* TODO: Implement these pages */}
              {/* <Route path="/profile" element={<ProfilePage />} /> */}
              
              {/* Demo routes for development */}
              <Route path="/demo" element={
                <div className="min-h-screen flex items-center justify-center bg-gray-50">
                  <div className="text-center">
                    <h1 className="text-3xl font-bold text-gray-900 mb-4">데모 페이지</h1>
                    <p className="text-gray-600 mb-6">곧 구현될 예정입니다.</p>
                    <button 
                      onClick={() => window.history.back()}
                      className="bg-primary text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors"
                    >
                      돌아가기
                    </button>
                  </div>
                </div>
              } />
              
              {/* 404 Route */}
              <Route path="*" element={
                <div className="min-h-screen flex items-center justify-center bg-gray-50">
                  <div className="text-center">
                    <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
                    <h2 className="text-2xl font-bold text-gray-900 mb-4">페이지를 찾을 수 없습니다</h2>
                    <p className="text-gray-600 mb-6">요청하신 페이지가 존재하지 않습니다.</p>
                    <button 
                      onClick={() => window.location.href = '/'}
                      className="bg-primary text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors"
                    >
                      홈으로 이동
                    </button>
                  </div>
                </div>
              } />
            </Routes>
          </div>
        </Router>
      </InterviewProvider>
    </ErrorBoundary>
  );
}

export default App;