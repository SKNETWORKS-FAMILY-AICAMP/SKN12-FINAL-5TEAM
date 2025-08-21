import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { InterviewProvider } from './contexts/InterviewContext';
import ErrorBoundary from './components/common/ErrorBoundary';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Pages
import MainPage from './pages/MainPage';
import InterviewSetup from './pages/InterviewSetup';
import InterviewActive from './pages/InterviewActive';
import InterviewGO from './pages/InterviewGO';
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
import OAuthCallbackPage from './pages/OAuthCallbackPage';

function App() {
  return (
    <ErrorBoundary>
      <InterviewProvider>
        <Router>
          <div className="App">
            <Routes>
              {/* Main Routes */}
              <Route path="/" element={<MainPage />} />
              <Route path="/app" element={<MainPage />} />
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
              
              {/* OAuth 통합 콜백 라우트 */}
              <Route path="/auth/callback" element={<OAuthCallbackPage />} />
              
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
                  <InterviewGO />
                </ProtectedRoute>
              } />
              <Route path="/interview/active-temp" element={
                <ProtectedRoute>
                  <InterviewActiveTemp />
                </ProtectedRoute>
              } />
              <Route path="/interview/results/:interviewId" element={
                <ProtectedRoute>
                  <InterviewResults />
                </ProtectedRoute>
              } />
              
              {/* AI Interview Start Route */}
              <Route path="/interview/ai/start" element={
                <ProtectedRoute>
                  <InterviewGO />
                </ProtectedRoute>
              } />
              
              {/* Legacy routes - redirect to new flow */}
              <Route path="/interview" element={<Navigate to="/interview/job-posting" replace />} />
              
              {/* TODO: Implement these pages */}
              <Route path="/interview/setup" element={<InterviewSetup />} />
              
              {/* Catch all route */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </Router>
      </InterviewProvider>
    </ErrorBoundary>
  );
}

export default App;