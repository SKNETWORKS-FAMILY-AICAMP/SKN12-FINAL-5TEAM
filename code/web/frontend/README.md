# 🎨 AI 면접 시스템 - 프론트엔드

React + TypeScript로 구현된 AI 면접 시스템의 사용자 인터페이스입니다.

## 🚀 기술 스택

- **React**: 19.1.0
- **TypeScript**: 5.x
- **Styling**: Tailwind CSS 3.x
- **HTTP Client**: Fetch API
- **State Management**: React Context + Custom Hooks
- **Build Tool**: Create React App (CRA)

## 📁 프로젝트 구조

```
src/
├── components/           # 재사용 가능한 컴포넌트
│   ├── auth/            # 인증 관련 컴포넌트
│   │   └── ProtectedRoute.tsx
│   ├── common/          # 공통 컴포넌트
│   │   ├── Header.tsx
│   │   ├── LoadingSpinner.tsx
│   │   └── ErrorBoundary.tsx
│   ├── interview/       # 면접 관련 컴포넌트
│   │   ├── AnswerInput.tsx
│   │   ├── ChatHistory.tsx
│   │   ├── NavigationButtons.tsx
│   │   ├── StepIndicator.tsx
│   │   └── TextCompetitionHeader.tsx
│   └── voice/           # 음성 관련 컴포넌트
│       ├── SpeechIndicator.tsx
│       └── VoiceControls.tsx
├── pages/               # 페이지 컴포넌트
│   ├── LoginPage.tsx    # 로그인 페이지
│   ├── MainPage.tsx     # 메인 페이지
│   ├── InterviewSetup.tsx   # 면접 설정
│   ├── InterviewActive.tsx  # 면접 진행
│   ├── InterviewResults.tsx # 면접 결과
│   ├── InterviewHistory.tsx # 면접 기록
│   └── interview/       # 면접 하위 페이지
│       ├── AISetup.tsx
│       ├── EnvironmentCheck.tsx
│       ├── InterviewModeSelection.tsx
│       ├── JobPostingSelection.tsx
│       └── ResumeSelection.tsx
├── hooks/               # Custom React Hooks
│   ├── useAuth.tsx      # 인증 관련 훅
│   ├── useInterviewHistory.ts
│   ├── useInterviewStart.ts
│   ├── usePositions.ts
│   ├── useResumes.ts
│   ├── useTextCompetitionInit.ts
│   └── useTextCompetitionState.ts
├── contexts/            # React Context
│   └── InterviewContext.tsx
├── services/            # API 서비스
│   ├── api.ts           # 기본 API 서비스
│   └── textCompetitionApi.ts
├── types/               # TypeScript 타입 정의
│   └── speech.d.ts
└── utils/               # 유틸리티 함수
    └── speechUtils.ts
```

## 🏃‍♂️ 개발 서버 실행

```bash
# 의존성 설치
npm install

# 개발 서버 시작 (http://localhost:3000)
npm start
```

## 📦 빌드 및 배포

```bash
# 프로덕션 빌드
npm run build

# 빌드 파일은 build/ 폴더에 생성됩니다
```

## 🎯 주요 기능

### 1. 면접 모드 선택
- **AI 경쟁 면접**: 사용자 vs AI "춘식이" 턴제 경쟁
- **개인화 면접**: 문서 기반 맞춤형 질문
- **표준 면접**: 기본 질문으로 연습

### 2. 실시간 면접 UI
- **턴제 진행**: 사용자와 AI가 교대로 답변
- **타임라인 표시**: 모든 질문/답변 시간순 표시
- **동적 면접관**: 질문 유형별 면접관 변경
- **실시간 피드백**: 답변별 즉시 평가

### 3. 지원 기업
- **7개 주요 IT 기업**: 네이버, 카카오, 라인, 쿠팡, 배민, 당근, 토스
- **기업별 특화**: 각 회사의 면접 스타일과 기술 스택 반영

## 🔗 백엔드 연동

프론트엔드는 FastAPI 백엔드와 REST API로 통신합니다:

- **Base URL**: `http://localhost:8000`
- **주요 엔드포인트**:
  - `POST /start_comparison_interview`: AI 경쟁 면접 시작
  - `POST /user_turn_submit`: 사용자 답변 제출
  - `POST /ai_turn_process`: AI 턴 처리
  - `POST /evaluate_comparison_interview`: 면접 평가

## 🎨 스타일링

- **Tailwind CSS**: 유틸리티 우선 CSS 프레임워크
- **반응형 디자인**: 모바일, 태블릿, 데스크톱 지원
- **다크 모드**: 추후 지원 예정

## 🧪 테스트

```bash
# 테스트 실행
npm test

# 커버리지 확인
npm test -- --coverage
```

## 📝 코드 스타일

- **TypeScript**: 엄격한 타입 체크 활성화
- **ESLint**: 코드 품질 검사
- **Prettier**: 코드 포맷팅

## 🔧 환경 변수

```env
# .env.local 파일 생성
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development
```

## 📚 참고 자료

- [React 공식 문서](https://reactjs.org/)
- [TypeScript 가이드](https://www.typescriptlang.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [프로젝트 메인 README](../README.md)