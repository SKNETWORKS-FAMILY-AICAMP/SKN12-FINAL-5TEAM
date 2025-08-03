# 🔧 API 레퍼런스

AI 면접 시스템의 모든 API 엔드포인트에 대한 상세 문서입니다.

## 📋 목차
- [기본 정보](#기본-정보)
- [인증](#인증)
- [에러 응답](#에러-응답)
- [문서 관리 API](#문서-관리-api)
- [면접 시스템 API](#면접-시스템-api)
- [AI 경쟁 면접 API](#ai-경쟁-면접-api)
- [평가 시스템 API](#평가-시스템-api)

## 🌐 기본 정보

### Base URL
```
http://localhost:8888
```

### Content-Type
```
application/json
```

### 응답 형식
모든 API는 다음 형식으로 응답합니다:
```json
{
  "success": boolean,
  "data": object,      // 성공 시 데이터
  "error": string,     // 실패 시 에러 메시지
  "timestamp": string  // ISO 8601 형식
}
```

## 🔐 인증

현재 버전에서는 별도의 인증이 필요하지 않습니다. OpenAI API 키는 서버 측에서 관리됩니다.

## ❌ 에러 응답

### 공통 에러 코드
| 코드 | 설명 |
|------|------|
| 400 | 잘못된 요청 (Bad Request) |
| 404 | 리소스를 찾을 수 없음 (Not Found) |
| 413 | 파일 크기 초과 (Payload Too Large) |
| 429 | 요청 제한 초과 (Too Many Requests) |
| 500 | 서버 내부 오류 (Internal Server Error) |

### 에러 응답 예시
```json
{
  "success": false,
  "error": "파일 크기가 16MB를 초과합니다",
  "error_code": "FILE_TOO_LARGE",
  "timestamp": "2025-01-16T10:30:00Z"
}
```

---

## 📄 문서 관리 API

### 📤 파일 업로드

**엔드포인트**: `POST /upload`

사용자의 지원 문서(자기소개서, 이력서, 포트폴리오)를 업로드합니다.

#### 요청
```http
POST /upload
Content-Type: multipart/form-data

file: [File]                    # 업로드할 파일
document_type: string           # 문서 타입: "자기소개서" | "이력서" | "포트폴리오"
```

#### 지원 파일 형식
- PDF (.pdf)
- Microsoft Word (.docx, .doc)
- 텍스트 파일 (.txt)
- 최대 크기: 16MB

#### 응답
```json
{
  "success": true,
  "document_type": "자기소개서",
  "text": "추출된 전체 텍스트...",
  "text_preview": "첫 200자 미리보기...",
  "file_size": 1234567,
  "processed_at": "2025-01-16T10:30:00Z"
}
```

#### 에러 응답
```json
{
  "success": false,
  "error": "지원하지 않는 파일 형식입니다",
  "supported_formats": ["pdf", "docx", "doc", "txt"]
}
```

### 📊 문서 분석

**엔드포인트**: `POST /analyze`

업로드된 문서들을 분석하여 사용자 프로필을 생성합니다.

#### 요청
```json
{
  "documents": {
    "자기소개서": "자기소개서 텍스트 내용...",
    "이력서": "이력서 텍스트 내용...",
    "포트폴리오": "포트폴리오 텍스트 내용..."
  }
}
```

#### 응답
```json
{
  "success": true,
  "profile": {
    "name": "홍길동",
    "background": {
      "career_years": "3",
      "current_position": "백엔드 개발자",
      "education": "컴퓨터공학과 학사"
    },
    "technical_skills": [
      "Python", "Java", "Spring Boot", "MySQL", "Docker"
    ],
    "projects": [
      {
        "name": "이커머스 플랫폼",
        "description": "MSA 기반 쇼핑몰 백엔드 개발",
        "technologies": ["Spring Boot", "MySQL", "Redis"],
        "role": "백엔드 개발"
      }
    ],
    "experiences": [
      {
        "company": "ABC 테크",
        "position": "백엔드 개발자",
        "duration": "2년",
        "achievements": ["API 성능 30% 개선", "코드 리뷰 프로세스 도입"]
      }
    ],
    "strengths": ["문제 해결 능력", "팀워크", "학습 능력"],
    "keywords": ["백엔드", "API", "데이터베이스", "성능 최적화"],
    "career_goal": "시니어 백엔드 개발자로 성장",
    "unique_points": ["다양한 프로젝트 경험", "성능 최적화 전문성"]
  },
  "analysis_metadata": {
    "processing_time": 2.5,
    "confidence_score": 0.87,
    "extracted_entities": 15
  }
}
```

---

## 🎯 면접 시스템 API

### 🚀 개인화 면접 시작

**엔드포인트**: `POST /start_personalized`

사용자 프로필을 기반으로 개인화된 면접을 시작합니다.

#### 요청
```json
{
  "company": "naver",
  "position": "백엔드 개발자",
  "user_profile": {
    // /analyze API 응답의 profile 객체
  }
}
```

#### 응답
```json
{
  "success": true,
  "session_id": "personalized_naver_backend_1705398600",
  "question": {
    "question_id": "intro_1",
    "question_type": "자기소개",
    "question_content": "간단하게 자기소개를 해주세요.",
    "question_intent": "지원자의 기본 배경과 커뮤니케이션 능력 파악",
    "progress": "1/20",
    "personalized": false,
    "estimated_time": "2-3분"
  },
  "session_info": {
    "total_questions": 20,
    "company": "naver",
    "position": "백엔드 개발자",
    "interview_mode": "personalized"
  }
}
```

### 📝 표준 면접 시작

**엔드포인트**: `POST /start_standard`

문서 없이 기본 질문으로 면접을 시작합니다.

#### 요청
```json
{
  "company": "naver",
  "position": "백엔드 개발자",
  "name": "홍길동"
}
```

#### 응답
```json
{
  "success": true,
  "session_id": "standard_naver_backend_1705398600",
  "question": {
    "question_id": "intro_1",
    "question_type": "자기소개",
    "question_content": "간단하게 자기소개를 해주세요.",
    "progress": "1/20",
    "personalized": false
  }
}
```

### 💬 답변 제출

**엔드포인트**: `POST /answer`

현재 질문에 대한 답변을 제출하고 다음 질문을 받습니다.

#### 요청
```json
{
  "session_id": "personalized_naver_backend_1705398600",
  "answer": "안녕하세요. 3년차 백엔드 개발자 홍길동입니다..."
}
```

#### 응답 (면접 진행 중)
```json
{
  "success": true,
  "result": {
    "status": "in_progress",
    "question": {
      "question_id": "motivation_1",
      "question_type": "지원동기",
      "question_content": "네이버에 지원하게 된 동기는 무엇인가요?",
      "progress": "2/20",
      "personalized": true,
      "personalization_reason": "지원자의 검색 엔진 관심사를 반영"
    },
    "previous_answer_saved": true
  }
}
```

#### 응답 (면접 완료)
```json
{
  "success": true,
  "result": {
    "status": "interview_complete",
    "message": "모든 질문이 완료되었습니다",
    "total_answers": 20,
    "interview_duration": "45분"
  }
}
```

---

## 🤖 AI 경쟁 면접 API

### 🚀 AI 경쟁 면접 시작

**엔드포인트**: `POST /start_comparison_interview`

사용자와 AI 지원자가 경쟁하는 턴제 면접을 시작합니다.

#### 요청
```json
{
  "company": "naver",
  "position": "백엔드 개발자",
  "name": "홍길동"
}
```

#### 응답 (사용자 먼저 시작)
```json
{
  "success": true,
  "comparison_session_id": "comp_user_session_123",
  "user_session_id": "user_session_123",
  "ai_session_id": "ai_session_456",
  "question": {
    "question_type": "자기소개",
    "question_content": "간단하게 자기소개를 해주세요.",
    "progress": "1/20"
  },
  "current_phase": "user_turn",
  "current_respondent": "홍길동",
  "question_index": 1,
  "total_questions": 20,
  "ai_name": "춘식이",
  "starts_with_user": true,
  "message": "홍길동님부터 시작합니다"
}
```

#### 응답 (AI 먼저 시작)
```json
{
  "success": true,
  "comparison_session_id": "comp_user_session_123",
  "current_phase": "ai_turn",
  "current_respondent": "춘식이",
  "ai_name": "춘식이",
  "user_name": "홍길동",
  "starts_with_user": false,
  "message": "춘식이부터 시작합니다"
}
```

### 💬 사용자 턴 답변 제출

**엔드포인트**: `POST /user_turn_submit`

사용자 턴에서 답변을 제출합니다.

#### 요청
```json
{
  "comparison_session_id": "comp_user_session_123",
  "answer": "안녕하세요. 3년차 백엔드 개발자 홍길동입니다..."
}
```

#### 응답
```json
{
  "success": true,
  "message": "답변이 제출되었습니다",
  "next_phase": "ai_turn",
  "ai_name": "춘식이"
}
```

### 🤖 AI 턴 처리

**엔드포인트**: `POST /ai_turn_process`

AI 턴에서 질문 생성 및 답변을 처리합니다.

#### 요청 (1단계: 질문 생성)
```json
{
  "comparison_session_id": "comp_user_session_123",
  "step": "question"
}
```

#### 응답 (1단계: 질문만 생성됨)
```json
{
  "success": true,
  "step": "question_generated",
  "ai_question": {
    "question_type": "기술",
    "question_content": "대용량 트래픽을 처리하는 시스템 설계 경험이 있나요?",
    "progress": "2/20",
    "personalized": false
  },
  "message": "AI 질문이 생성되었습니다. 2-3초 후 답변이 생성됩니다."
}
```

#### 요청 (2단계: 답변 생성)
```json
{
  "comparison_session_id": "comp_user_session_123",
  "step": "answer"
}
```

#### 응답 (2단계: 답변 생성 완료)
```json
{
  "success": true,
  "step": "answer_generated",
  "status": "continue",
  "ai_question": {
    "question_type": "기술",
    "question_content": "대용량 트래픽을 처리하는 시스템 설계 경험이 있나요?",
    "progress": "2/20"
  },
  "ai_answer": {
    "content": "네, 이전 회사에서 일일 100만 사용자를 처리하는 시스템을 설계했습니다...",
    "persona_name": "춘식이",
    "confidence": 0.89
  },
  "next_user_question": {
    "question_type": "지원동기",
    "question_content": "이 회사에 지원하게 된 이유는 무엇인가요?",
    "progress": "3/20"
  },
  "next_phase": "user_turn",
  "question_index": 3,
  "user_name": "홍길동"
}
```

---

## 📊 평가 시스템 API

### 🎯 면접 평가

**엔드포인트**: `POST /evaluate`

완료된 면접에 대한 종합 평가를 생성합니다.

#### 요청
```json
{
  "session_id": "personalized_naver_backend_1705398600"
}
```

#### 응답
```json
{
  "success": true,
  "evaluation": {
    "overall_score": 78,
    "grade": "B+",
    "strengths": [
      "기술적 깊이 있는 답변",
      "구체적인 경험 사례 제시",
      "논리적인 사고 과정"
    ],
    "improvements": [
      "답변의 간결성 개선 필요",
      "비즈니스 관점 추가 고려",
      "팀워크 경험 더 구체적으로 설명"
    ],
    "recommendation": "전반적으로 우수한 기술적 역량을 보여주었으나, 커뮤니케이션 스킬과 비즈니스 이해도를 더 발전시키면 좋겠습니다.",
    "next_steps": "실제 면접에서는 답변 시간을 2-3분으로 제한하여 연습해보세요.",
    "category_scores": {
      "기술_역량": 85,
      "문제_해결": 80,
      "커뮤니케이션": 70,
      "팀워크": 75,
      "성장_잠재력": 82
    },
    "personalization_effectiveness": 0.73,
    "interview_duration": "45분",
    "total_questions": 20,
    "personalized_questions": 12
  },
  "individual_feedbacks": [
    {
      "question": "간단하게 자기소개를 해주세요.",
      "question_type": "자기소개",
      "question_intent": "지원자의 기본 배경과 커뮤니케이션 능력 파악",
      "answer": "안녕하세요. 3년차 백엔드 개발자...",
      "score": 80,
      "feedback": "경력과 기술 스택을 명확하게 제시했으나, 네이버와의 연관성을 더 강조했으면 좋겠습니다.",
      "personalized": false
    }
    // ... 추가 질문들
  ]
}
```

### 🆚 비교 면접 평가

**엔드포인트**: `POST /evaluate_comparison_interview`

AI 경쟁 면접의 사용자 vs AI 비교 평가를 생성합니다.

#### 요청
```json
{
  "comparison_session_id": "comp_user_session_123"
}
```

#### 응답
```json
{
  "success": true,
  "evaluation": {
    "user_evaluation": {
      "overall_score": 78,
      "strengths": ["구체적인 경험", "기술적 깊이"],
      "improvements": ["답변 간결성", "비즈니스 관점"],
      "recommendation": "전반적으로 우수한 답변..."
    },
    "ai_evaluation": {
      "overall_score": 82,
      "strengths": ["논리적 구조", "포괄적 답변"],
      "model_performance": {
        "consistency": 0.89,
        "relevance": 0.85,
        "creativity": 0.78
      }
    },
    "comparison_analysis": {
      "winner": "AI",
      "score_difference": 4,
      "user_advantages": [
        "실제 경험 기반 답변",
        "감정적 어필 우수"
      ],
      "ai_advantages": [
        "일관된 품질",
        "포괄적 지식"
      ],
      "improvement_suggestions": [
        "답변 구조화 연습",
        "핵심 포인트 먼저 제시",
        "구체적 수치 활용"
      ]
    },
    "turn_by_turn_analysis": [
      {
        "turn": 1,
        "user_score": 80,
        "ai_score": 78,
        "comparison": "사용자의 실제 경험이 더 인상적"
      }
      // ... 추가 턴들
    ]
  }
}
```

---

## 🛠️ 기타 API

### 🏥 서버 상태 확인

**엔드포인트**: `GET /test`

서버의 정상 작동 여부를 확인합니다.

#### 응답
```json
{
  "status": "ok",
  "message": "Flask 앱이 정상적으로 작동 중입니다",
  "port": 8888,
  "debug": true,
  "timestamp": "2025-01-16T10:30:00Z"
}
```

### 🔧 디버그 정보

**엔드포인트**: `GET /debug`

개발 환경에서 디버그 정보를 확인합니다.

#### 응답
```json
{
  "status": "success",
  "message": "Flask 서버가 정상 작동합니다!",
  "environment": "development",
  "python_version": "3.9.7",
  "flask_version": "3.0.3"
}
```

---

## 📱 사용 예시

### JavaScript 클라이언트 예시
```javascript
// 파일 업로드
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('document_type', '자기소개서');

const uploadResponse = await fetch('/upload', {
    method: 'POST',
    body: formData
});

// 문서 분석
const analyzeResponse = await fetch('/analyze', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        documents: {
            '자기소개서': '업로드된 텍스트...'
        }
    })
});

// 개인화 면접 시작
const startResponse = await fetch('/start_personalized', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        company: 'naver',
        position: '백엔드 개발자',
        user_profile: analyzeResponse.profile
    })
});
```

### Python 클라이언트 예시
```python
import requests
import json

# 서버 URL
BASE_URL = "http://localhost:8888"

# 문서 분석
analyze_data = {
    "documents": {
        "자기소개서": "업로드된 텍스트..."
    }
}

response = requests.post(
    f"{BASE_URL}/analyze",
    json=analyze_data,
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    profile = response.json()["profile"]
    
    # 개인화 면접 시작
    start_data = {
        "company": "naver",
        "position": "백엔드 개발자",
        "user_profile": profile
    }
    
    interview_response = requests.post(
        f"{BASE_URL}/start_personalized",
        json=start_data
    )
    
    print(interview_response.json())
```

---

## 📝 참고사항

### Rate Limiting
- API 호출은 분당 60회로 제한됩니다
- 초과 시 429 에러 반환

### 파일 업로드 제한
- 최대 파일 크기: 16MB
- 지원 형식: PDF, DOCX, DOC, TXT
- 동시 업로드: 최대 3개 파일

### 세션 관리
- 세션은 1시간 후 자동 만료
- 만료된 세션으로 요청 시 404 에러

### 에러 처리
- 모든 API 호출에는 try-catch 구문 사용 권장
- 네트워크 오류, 타임아웃에 대한 재시도 로직 구현 권장