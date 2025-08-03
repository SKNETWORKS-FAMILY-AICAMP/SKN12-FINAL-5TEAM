# AI 지원자 모델 시스템

AI 기반 면접 지원자 답변 생성 시스템입니다. 각 회사별 합격자 수준의 페르소나를 기반으로 자연스럽고 질 높은 면접 답변을 생성합니다.

## 🎯 주요 기능

### 1. 멀티 LLM 지원
- **OpenAI GPT 모델들**: GPT-4, GPT-4o-mini, GPT-3.5-turbo
- **Google Gemini**: Gemini Pro, Gemini Flash (향후 구현)
- **KT 믿음 모델**: 한국형 LLM (향후 구현)
- 모델별 특성에 맞는 프롬프트 최적화

### 2. 답변 품질 제어
- **10단계 품질 조절**: 1점(부적절) ~ 10점(탁월) 
- **품질별 특성**:
  - 답변 길이, 구체성, 전문성 수준 조절
  - 예시 포함 여부, 수치/성과 데이터 포함 여부
  - 전문적 톤 vs 자연스러운 톤
- **질문 유형별 최적화**: 자기소개, 지원동기, 기술, 협업 등

### 3. 회사별 페르소나 시스템
현재 구현된 페르소나:
- **네이버**: 검색/AI 전문가, 대용량 시스템 경험
- **카카오**: 플랫폼 개발자, 사회적 가치 추구
- **토스**: 핀테크 전문가, 사용자 경험 중시

각 페르소나별 특성:
- 실제 경력과 프로젝트 경험
- 회사별 기술 스택과 문화 반영
- 구체적인 성과와 수치 데이터
- 개인 성향과 면접 스타일

### 4. 통합 설정 관리
- JSON 기반 설정 파일
- 모델별 API 키 및 파라미터 관리
- 품질 기준 및 답변 옵션 설정
- 로깅 및 캐시 설정

## 🚀 빠른 시작

### 1. 의존성 설치
```bash
pip install openai
```

### 2. 데모 실행
```bash
python demo_ai_candidate.py
```

### 3. 기본 사용법
```python
from core.ai_candidate_model import AICandidateModel, AnswerRequest
from core.llm_manager import LLMProvider
from core.answer_quality_controller import QualityLevel
from core.interview_system import QuestionType

# 모델 초기화
ai_candidate = AICandidateModel(api_key="your-openai-api-key")

# 답변 요청 생성
request = AnswerRequest(
    question_content="간단한 자기소개를 해주세요.",
    question_type=QuestionType.INTRO,
    question_intent="지원자의 기본 배경과 역량 파악",
    company_id="naver",
    position="백엔드 개발자",
    quality_level=QualityLevel.GOOD,
    llm_provider=LLMProvider.OPENAI_GPT4O_MINI
)

# 답변 생성
response = ai_candidate.generate_answer(request)
print(f"답변: {response.answer_content}")
print(f"신뢰도: {response.confidence_score}")
```

## 📁 프로젝트 구조

```
core/
├── ai_candidate_model.py      # 메인 AI 지원자 모델
├── llm_manager.py            # LLM 모델 통합 관리
├── answer_quality_controller.py  # 답변 품질 제어
├── ai_candidate_config.py    # 설정 관리
└── ...

data/
├── candidate_personas.json   # 회사별 페르소나 데이터
└── companies_data.json      # 회사 정보

config/                      # 설정 파일 저장소
logs/                       # 로그 파일 저장소
demo_ai_candidate.py        # 통합 데모 스크립트
```

## 🎭 데모 기능

데모 스크립트(`demo_ai_candidate.py`)에서 제공하는 기능:

1. **기본 답변 생성**: 단일 질문에 대한 답변 생성
2. **품질 레벨 비교**: 동일 질문을 다양한 품질로 생성
3. **모델 성능 비교**: 여러 LLM 모델 결과 비교
4. **페르소나 비교**: 회사별 답변 스타일 차이 확인
5. **전체 면접 시뮬레이션**: 완전한 면접 과정 시뮬레이션
6. **설정 관리**: 실시간 설정 변경 및 관리
7. **페르소나 정보**: 각 회사별 페르소나 상세 정보

## ⚙️ 설정 옵션

### 모델 설정
```json
{
  "model_settings": {
    "openai_gpt4o_mini": {
      "enabled": true,
      "max_tokens": 600,
      "temperature": 0.7,
      "timeout": 30.0
    }
  }
}
```

### 품질 설정
```json
{
  "quality_settings": {
    "default_level": 8,
    "min_answer_length": 50,
    "max_answer_length": 500,
    "enable_post_processing": true
  }
}
```

## 📊 품질 레벨 가이드

| 레벨 | 설명 | 특징 |
|------|------|------|
| 10점 | 탁월한 수준 | 매우 구체적, 수치 포함, 전문적 |
| 8-9점 | 우수한 수준 | 구체적 예시, 체계적 구성 |
| 6-7점 | 양호한 수준 | 적절한 내용, 무난한 답변 |
| 4-5점 | 보통 수준 | 기본적 내용, 간단한 구성 |
| 1-3점 | 부족한 수준 | 짧고 표면적, 준비 부족 |

## 🏢 페르소나 추가 가이드

새로운 회사 페르소나 추가 시 `data/candidate_personas.json` 파일에 다음 구조로 추가:

```json
{
  "personas": {
    "company_id": {
      "name": "페르소나 이름",
      "background": {
        "career_years": "경력 년수",
        "current_position": "현재 직책",
        "education": ["학력 정보"]
      },
      "technical_skills": ["기술 스택"],
      "projects": [
        {
          "name": "프로젝트명",
          "description": "설명",
          "achievements": ["성과"]
        }
      ],
      "strengths": ["강점"],
      "career_goal": "커리어 목표",
      "interview_style": "면접 스타일"
    }
  }
}
```

## 🔧 확장 계획

### 단기 계획
- Google Gemini API 연동
- KT 믿음 모델 API 연동  
- 웹 인터페이스 구축 (React + FastAPI)
- Supabase 데이터베이스 연동

### 장기 계획
- 실시간 피드백 시스템
- 면접 영상 분석 연동
- 다국어 지원
- 커스텀 페르소나 생성 도구

## 🤝 기여 방법

1. 새로운 페르소나 데이터 제공
2. 품질 평가 알고리즘 개선
3. 추가 LLM 모델 연동
4. 테스트 케이스 작성

## 📄 라이선스

이 프로젝트는 면접 준비 및 교육 목적으로 개발되었습니다.

---

**주의사항**: 실제 면접에서는 본인의 진정한 경험과 생각을 바탕으로 답변하시기 바랍니다. 이 시스템은 면접 준비와 연습을 위한 참고 자료로만 사용해주세요.