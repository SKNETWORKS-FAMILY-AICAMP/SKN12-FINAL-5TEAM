# 🎯 AI 면접 시스템 (AI Interview System)

한국 주요 IT 기업 맞춤형 AI 면접 시스템으로, **사용자 vs AI 후보자 "춘식이"와의 실시간 경쟁 면접**을 제공합니다.

> **🎉 최신 업데이트 (v3.0)**: 전체 프로젝트 구조 리팩터링 완료! 모듈형 아키텍처와 서비스 계층 도입으로 확장성과 유지보수성이 크게 향상되었습니다.

## 🚀 주요 기능

### 🏆 **AI 경쟁 면접 (메인 기능)**
- **실시간 경쟁**: 사용자와 AI 후보자 "춘식이"가 턴제로 면접 진행
- **영상통화 스타일 UI**: 3명의 면접관(인사/협업/기술)과 함께하는 몰입감 있는 인터페이스
- **동적 면접관 하이라이트**: 질문 유형에 따라 해당 면접관이 강조
- **세션 완전 분리**: 사용자와 AI가 각각 독립적인 세션에서 면접 진행
- **실시간 타임라인**: 모든 질문과 답변이 시간순으로 표시

### 🏢 지원 기업 (7개)
| 기업 | 특화 분야 | 핵심 기술 |
|------|-----------|-----------|
| 네이버 | 검색, AI, 클라우드 | 하이퍼클로바X, NCP |
| 카카오 | 플랫폼, 메시징 | MSA, 대용량 처리 |
| 라인 | 글로벌 메시징 | 실시간 통신, 품질 |
| 쿠팡 | 이커머스, 물류 | 스케일링, 자동화 |
| 배달의민족 | 플랫폼, 매칭 | 실시간 시스템 |
| 당근마켓 | 로컬 커뮤니티 | 위치 기반 서비스 |
| 토스 | 핀테크, 결제 | 보안, 사용자 경험 |

### 🎯 지원 직군 (7개)
- 백엔드 개발자
- 프론트엔드 개발자
- 풀스택 개발자
- 데이터 엔지니어
- AI/ML 엔지니어
- DevOps 엔지니어
- 모바일 개발자

### ✨ 새로 추가된 기능 (v3.0)
- **🏗️ 모듈형 아키텍처**: 면접관/지원자/피드백/공용 모듈로 역할별 분리
- **🔧 서비스 계층**: 비즈니스 로직과 API 계층 완전 분리
- **📦 계층화된 구조**: Frontend → API → Service → LLM 모듈
- **🏢 회사 데이터 통합**: 7개 회사의 상세 정보 완전 활용 (인재상, 면접관 페르소나, 기술 스택)
- **🎯 개인화 강화**: 회사별 맞춤 질문 생성 시스템
- **📊 CompanyDataLoader**: 회사 정보 효율적 관리 클래스
- **🔄 자동 디버깅**: Import 오류 자동 감지 및 수정 시스템
- **⚡ 성능 최적화**: 새로운 구조로 메모리 사용량 및 응답 속도 개선

## 🛠️ 기술 스택

### **모듈형 프로덕션 아키텍처 (v3.0)**

#### Frontend
- **React 19.1.0 + TypeScript** - 최신 React with 타입 안정성
- **Tailwind CSS 3.4.17** - 유틸리티 우선 CSS
- **React Router 7.7.0** - 라우팅
- **Axios 1.10.0** - API 통신

#### Backend (새로운 계층화 구조)
- **FastAPI** - 고성능 비동기 웹 프레임워크 (API 계층)
- **Service Layer** - 비즈니스 로직 중앙 관리
- **Python 3.8+** - 메인 언어
- **Uvicorn** - ASGI 서버
- **Supabase Python Client 2.17.0** - 데이터베이스 연결

#### Database
- **Supabase (PostgreSQL)** - 클라우드 데이터베이스
- **Row Level Security (RLS)** - 보안 관리
- **Real-time subscriptions** - 실시간 데이터 동기화

#### LLM/AI (새로운 모듈형 구조)
- **OpenAI GPT-4o-mini** - 메인 AI 모델
- **GPT-4 & GPT-3.5** - 추가 모델 옵션
- **Modular LLM Architecture** - 역할별 분리된 AI 모듈
  - **Interviewer Module** - 질문 생성 전담
  - **Candidate Module** - AI 답변 생성 전담
  - **Feedback Module** - 답변 평가 전담
  - **Shared Module** - 공통 모델 및 유틸리티

## 🏗️ 새로운 프로젝트 구조 (v3.0)

```
yoseop_1/
├── 📱 frontend/              # React TypeScript 앱
│   ├── src/
│   │   ├── components/       # 재사용 가능 컴포넌트
│   │   ├── pages/           # 페이지 컴포넌트 (면접 진행, 설정 등)
│   │   ├── contexts/        # React Context (면접 상태 관리)
│   │   └── services/        # API 호출 서비스
│   └── package.json
│
├── 🖥️ backend/               # FastAPI 서버 (계층화)
│   ├── main.py             # FastAPI 메인 애플리케이션 (API 계층)
│   ├── services/           # 🆕 서비스 계층
│   │   └── interview_service.py  # 비즈니스 로직 중앙 관리
│   └── extensions/         # 확장 기능들
│       ├── database_integration.py    # 데이터베이스 API
│       └── migration_api.py          # 마이그레이션 API
│
├── 🗄️ database/             # 데이터베이스 레이어
│   ├── supabase_client.py   # Supabase 클라이언트
│   ├── models.py           # 데이터 모델 (Pydantic)
│   └── services/           # 데이터 서비스
│       ├── existing_tables_service.py  # 기존 테이블 관리
│       └── data_migration_service.py   # 마이그레이션 서비스
│
├── 🧠 llm/                  # 🆕 모듈형 AI/LLM 구조
│   ├── session/           # 🆕 세션 관리 모듈 (핵심!)
│   │   ├── manager.py     # 통합 세션 관리자 (일반/비교 면접)
│   │   ├── base_session.py # 기본 면접 세션 로직
│   │   ├── comparison_session.py # 비교 면접 세션 로직
│   │   └── models.py      # 세션 관련 데이터 모델
│   ├── interviewer/        # 🆕 면접관 모듈 (질문 생성)
│   │   ├── service.py      # 개인화된 면접 시스템
│   │   ├── document_processor.py  # 문서 처리
│   │   ├── prompt_templates.py    # 회사별 프롬프트 템플릿
│   │   └── data/          # 면접관 전용 데이터
│   ├── candidate/         # 🆕 지원자 모듈 (AI 답변)
│   │   ├── model.py       # AI 지원자 "춘식이" 모델
│   │   ├── quality_controller.py  # 답변 품질 제어
│   │   └── data/          # 지원자 전용 데이터
│   ├── feedback/          # 🆕 피드백 모듈 (답변 평가)
│   │   └── service.py     # 답변 평가 및 피드백 생성
│   ├── shared/            # 🆕 공용 모듈
│   │   ├── models.py      # 공통 데이터 모델
│   │   ├── constants.py   # 공통 상수
│   │   ├── utils.py       # 공통 유틸리티
│   │   ├── config.py      # 공통 설정
│   │   ├── company_data_loader.py  # 🆕 회사 데이터 로더
│   │   └── data/          # 🆕 공용 데이터
│   │       └── companies_data.json  # 🆕 7개 회사 통합 정보
│   └── core/              # LLM 관리 및 기타 공통 기능
│       └── llm_manager.py # LLM 관리자
│
├── 🔄 scripts/              # 실행 및 도구 스크립트
│   ├── start_backend.py    # 백엔드 서버 시작
│   ├── database/           # 🆕 DB 관련 스크립트
│   │   ├── migrate_data.py
│   │   └── check_table_schema.py
│   └── tests/             # 🆕 테스트 관련 스크립트
│       └── test_server.py
│
├── 🤖 agents/               # 미래 MCP/Agent2Agent 확장
├── 📁 media/                # 미래 이력서/화상면접 파일 저장
├── 📚 docs/                 # 프로젝트 문서
├── .env                    # 🆕 환경변수 설정
└── requirements.txt        # Python 의존성
```

## 📦 설치 및 실행

### 1. 환경 설정
```bash
# 저장소 클론
git clone <repository-url>
cd final_Q_test

# Python 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Python 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정
```bash
# .env 파일 생성 및 설정
cp .env.example .env  # 예제 파일이 있다면
# 또는 직접 생성:
touch .env

# .env 파일에 다음 설정 추가:
# OPENAI_API_KEY=your_openai_api_key_here
# SUPABASE_URL=your_supabase_url_here  
# SUPABASE_ANON_KEY=your_supabase_key_here

# 🚨 주의: API 키는 절대 Git에 커밋하지 마세요!
```

**필수 환경변수:**
- `OPENAI_API_KEY`: OpenAI API 키 (GPT 모델 사용)
- `SUPABASE_URL`: Supabase 프로젝트 URL
- `SUPABASE_ANON_KEY`: Supabase 익명 키

### 3. 데이터베이스 상태 확인
```bash
# 현재 데이터베이스 상태 확인
python scripts/migrate_data.py --task validate

# 결과: 
# - 회사 데이터: 7개 (마이그레이션 완료)
# - 포지션 데이터: 7개 (마이그레이션 완료)  
# - 고정 질문: 26개 (마이그레이션 완료)
# - AI 후보자: 진행 중 (서버 안정화 대기)
```

### 4. 백엔드 서버 실행
```bash
# 🎯 권장 방법: 스크립트 사용
python scripts/start_backend.py

# 🔧 대안 방법 1: 직접 실행
cd backend && python main.py

# 🔧 대안 방법 2: uvicorn 사용
cd backend && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# ✅ 성공적인 출력 예시:
# INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO: Started server process
# INFO: Application startup complete.
# ✅ 데이터베이스 확장 로드 성공
# ✅ 서비스 계층 초기화 완료
```

### 5. 프론트엔드 실행
```bash
# 의존성 설치
cd frontend
npm install

# 개발 서버 시작
npm start
```

### 6. 회사 데이터 통합 확인
```bash
# 7개 회사 데이터 로드 확인
python -c "
from llm.shared.company_data_loader import get_company_loader
loader = get_company_loader()
print('지원 회사:', [c['name'] for c in loader.get_company_list()])
print('네이버 인재상:', loader.get_company_data('naver')['talent_profile'][:50] + '...')
"

# 예상 출력:
# ✅ 회사 데이터 로드 완료: 7개 회사
# 지원 회사: ['네이버', '카카오', '라인', '쿠팡', '배달의민족', '당근마켓', '토스']
# 네이버 인재상: 기술로 모든 것을 연결하는 플랫폼 빌더 - Connect Everything을 실현하는 혁...
```

### 7. 브라우저 접속
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://127.0.0.1:8000
- **API 문서**: http://127.0.0.1:8000/docs
- **데이터베이스 관리**: http://127.0.0.1:8000/api/database/...

## 🎮 사용 가이드

### 🏆 AI 경쟁 면접 (메인 기능)

1. **면접 설정**
   - 회사 선택 (네이버, 카카오, 토스 등) - DB에서 실시간 로드
   - 직군 선택 (백엔드, 프론트엔드, 풀스택 등) - DB에서 실시간 로드
   - 이름 입력

2. **면접 진행**
   - 영상통화 스타일 UI에서 진행
   - 상단: 3명의 면접관 (인사/협업/기술)
   - 하단: 사용자와 춘식이 영역
   - 질문 유형에 따라 해당 면접관 자동 하이라이트

3. **턴제 시스템**
   - 사용자 턴 → 춘식이 턴 순서로 진행
   - 각각 독립적인 세션에서 질문 받고 답변
   - 모든 데이터 실시간 Supabase 저장
   - 실시간 타임라인에서 전체 진행 상황 확인

4. **최종 결과**
   - 사용자 vs 춘식이 성과 비교
   - 카테고리별 상세 분석
   - 개선 포인트 제안

### 🏢 회사별 개인화 면접 시스템 (v3.0 핵심 기능)

#### 📊 7개 회사 상세 정보 활용
각 회사의 실제 채용 정보를 바탕으로 완전히 개인화된 면접 경험을 제공합니다:

```python
# 네이버 면접 예시
네이버 채용 컨텍스트:
• 인재상: 기술로 모든 것을 연결하는 플랫폼 빌더 - Connect Everything을 실현하는 혁신가
• 핵심 역량: 기술적 깊이와 안정성, 대용량 서비스 설계, 사용자 중심 혁신
• 기술 포커스: 검색엔진 최적화, 하이퍼클로바X AI, 네이버클라우드플랫폼, 대용량 분산시스템
• 면접 키워드: 검색랭킹최적화, AI서비스구현, 클라우드아키텍처, 대규모트래픽처리

회사 문화 및 가치관:
• 업무 스타일: 기술적 완성도와 안정성을 중시하는 엔지니어링 문화
• 의사결정 방식: 데이터 기반 의사결정, 사용자 피드백 중심
• 핵심 가치: Connect Everything, 사용자 최우선, 기술 혁신, 사회적 책임

기술적 도전과제:
1. 일 100억+ 검색 쿼리 처리
2. 실시간 개인화 추천 서빙
3. 멀티 클라우드 환경 관리

면접관 페르소나 정보:
• 박검색 테크리드: 네이버 검색플랫폼 테크리드
  특징: 논리적이고 체계적, 기술적 완성도 추구, 성능과 안정성 중시
• 김클로바 리서처: 네이버 AI Lab 시니어 리서처
  특징: 호기심 많고 분석적, 최신 기술 트렌드 민감, 실용적 AI 구현 중시
```

#### 🎯 회사별 질문 생성 차별화
- **네이버**: 대용량 시스템 설계, AI 서비스 구현 경험 중심
- **카카오**: 플랫폼 확장성, 사회적 가치, 크루 문화 적합성 중심
- **토스**: 금융 도메인 이해, UX 간소화, 사용자 임팩트 중심
- **쿠팡**: 고객 중심 사고, 오너십 마인드, 대규모 스케일링 중심
- **배민**: 코드 품질 철학, 팀워크, 우아한 설계 능력 중심
- **당근마켓**: 지역사회 가치, 사용자 신뢰, 따뜻한 기술 철학 중심
- **라인**: 글로벌 서비스 경험, 품질 기준, 국제적 협업 중심

## 🔧 개발자 가이드

### 🧪 테스트 실행
```bash
# 데이터베이스 연결 테스트
python scripts/test_simple_migration.py

# 스키마 검사
python scripts/inspect_schemas.py

# 서버 테스트  
python scripts/test_server.py

# 🆕 회사 데이터 통합 테스트
python -c "
from llm.shared.company_data_loader import get_company_loader
loader = get_company_loader()
print('✅ 지원 회사 수:', len(loader.get_company_list()))
print('✅ 네이버 데이터:', bool(loader.get_company_data('naver')))
print('✅ 토스 면접관 수:', len(loader.get_interviewer_personas('toss')))
"
```

### 📊 CompanyDataLoader API 사용법 (v3.0 신규)
```python
from llm.shared.company_data_loader import get_company_loader

# 싱글톤 인스턴스 가져오기
loader = get_company_loader()

# 모든 회사 목록 조회
companies = loader.get_company_list()
# 결과: [{'id': 'naver', 'name': '네이버'}, ...]

# 특정 회사 상세 정보
naver_data = loader.get_company_data('naver')
print(naver_data['talent_profile'])  # 인재상
print(naver_data['tech_focus'])      # 기술 포커스 영역

# 회사별 특화 정보 조회
culture = loader.get_company_culture('kakao')
personas = loader.get_interviewer_personas('toss')
keywords = loader.get_interview_keywords('coupang')
challenges = loader.get_technical_challenges('baemin')

# 유효성 검사
if loader.is_valid_company('daangn'):
    print("당근마켓은 지원되는 회사입니다")
```

### 🗄️ 데이터베이스 관리

#### 마이그레이션 도구
```bash
# 전체 데이터 마이그레이션
python scripts/migrate_data.py --task all

# 특정 데이터만 마이그레이션
python scripts/migrate_data.py --task companies
python scripts/migrate_data.py --task questions  
python scripts/migrate_data.py --task candidates

# 드라이 런 (실제 실행하지 않고 미리보기)
python scripts/migrate_data.py --task all --dry-run
```

#### API를 통한 데이터 관리
```bash
# 마이그레이션 상태 확인
curl http://127.0.0.1:8000/api/migration/status

# 데이터 검증
curl http://127.0.0.1:8000/api/migration/validate

# 마이그레이션 실행 (웹 인터페이스)
curl -X POST http://127.0.0.1:8000/api/migration/run \
  -H "Content-Type: application/json" \
  -d '{"task": "all", "dry_run": false}'
```

### 📊 API 엔드포인트 (v2.1)

#### 핵심 면접 API
| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/health` | GET | 서버 상태 확인 |
| `/api/interview/start` | POST | 면접 시작 |
| `/api/interview/question` | GET | 다음 질문 가져오기 |
| `/api/interview/answer` | POST | 답변 제출 |
| `/api/interview/ai/start` | POST | AI 경쟁 면접 시작 |
| `/api/interview/comparison/user-turn` | POST | 사용자 턴 제출 |
| `/api/interview/comparison/ai-turn` | POST | AI 턴 처리 |

#### 새로운 데이터베이스 API (v2.1)
| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/database/companies` | GET | 회사 목록 조회 |
| `/api/database/positions` | GET | 직군 목록 조회 |
| `/api/database/questions` | GET | 질문 목록 조회 |
| `/api/migration/status` | GET | 마이그레이션 상태 |
| `/api/migration/run` | POST | 마이그레이션 실행 |
| `/api/migration/validate` | GET | 데이터 검증 |

## 🗄️ 데이터베이스 현황 (v2.1)

### ✅ 마이그레이션 완료
- **Company 테이블**: 7개 회사 데이터 (네이버, 카카오, 라인, 쿠팡, 배달의민족, 당근마켓, 토스)
- **Position 테이블**: 7개 직군 (백엔드, 프론트엔드, 풀스택, 데이터, AI/ML, DevOps, 모바일)
- **Fix_Question 테이블**: 26개 기술 분야별 고정 질문

### 🔄 진행 중
- **AI_Resume 테이블**: AI 후보자 페르소나 (서버 안정화 대기)

### 📊 테이블 구조
```sql
-- Company 테이블
company_id (int, PK)
name (string, NOT NULL)  
talent_profile, core_competencies, tech_focus,
interview_keywords, question_direction,
company_culture, technical_challenges

-- Position 테이블  
position_id (int, PK)
position_name (string, NOT NULL)

-- Fix_Question 테이블
question_id (int, PK)
question_index (int)
question_content (string, NOT NULL)
question_intent, question_level

-- Interview 테이블 (기존)
interview_id, user_id, ai_resume_id, 
user_resume_id, posting_id, company_id,
position_id, total_feedback, date
```

## 🔮 미래 확장 계획

### 📋 이력서 기반 기능
- **춘식이 페르소나 선택**: 신입/3년차/시니어 등 고정 페르소나
- **사용자 맞춤 질문**: 이력서 업로드 기반 개인화된 질문 생성
- **구현 위치**: `media/resumes/`, `backend/extensions/resume/`

### 📹 화상면접 기능
- **WebRTC 실시간 통신**: 실제 화상면접 환경
- **음성 인식**: 답변 자동 텍스트 변환
- **표정 분석**: 추가적인 면접 피드백
- **구현 위치**: `frontend/src/components/video/`, `backend/extensions/video/`

### 🤝 MCP/Agent2Agent
- **면접관 협업**: 3명 면접관 AI들의 실시간 상호작용
- **그룹 면접**: 여러 AI 후보자들과의 동시 면접
- **구현 위치**: `agents/protocols/`, `agents/coordination/`

## 🚨 주의사항

### 🔐 보안
- OpenAI API 키를 `.env` 파일에서 관리 (Git에 커밋하지 않음)
- Supabase 인증 키 보안 관리
- Row Level Security (RLS) 적용

### 💰 비용 관리
- GPT-4o-mini 사용으로 비용 최적화
- Supabase 무료 티어 한도 모니터링
- 토큰 사용량 모니터링 권장

### 🎯 성능
- FastAPI의 비동기 처리로 동시 사용자 지원 향상
- Supabase 실시간 구독으로 데이터 동기화 최적화
- React의 가상 DOM으로 UI 성능 최적화

## 📚 추가 문서

- [데이터베이스 마이그레이션 가이드](docs/DATABASE_MIGRATION.md) - Supabase 통합 상세 내용
- [API 문서](docs/API_REFERENCE.md) - 상세한 API 스펙  
- [개발자 가이드](docs/DEVELOPER_GUIDE.md) - 개발 환경 설정 및 기여 방법

---

---

## 🆕 v3.0 리팩터링 하이라이트

### 🏗️ 아키텍처 개선사항
- **모듈 분리**: LLM 모듈을 면접관/지원자/피드백/공용으로 명확히 분리
- **서비스 계층**: 비즈니스 로직을 API에서 분리하여 테스트 및 유지보수성 향상
- **계층화**: Frontend → API → Service → LLM 구조로 의존성 명확화
- **Import 최적화**: 모든 모듈 간 import 경로 일관성 확보
- **🆕 회사 데이터 통합**: 7개 회사의 상세 정보를 완전히 활용하는 통합 시스템
- **🆕 CompanyDataLoader**: 싱글톤 패턴 기반 효율적 회사 데이터 관리
- **🆕 개인화 강화**: 회사별 맞춤형 프롬프트 및 질문 생성 시스템

### ⚡ 성능 및 확장성
- **메모리 최적화**: 중복 코드 제거 및 효율적인 모듈 로딩
- **응답 속도**: 서비스 계층 도입으로 비즈니스 로직 실행 속도 향상
- **확장성**: 새로운 기능 추가 시 적절한 모듈에 배치 가능한 구조

### 🔧 개발자 경험
- **디버깅 개선**: 자동 Import 오류 감지 및 수정
- **코드 가독성**: 각 모듈의 역할과 책임이 명확히 정의
- **유지보수성**: 기능별 모듈화로 버그 수정 및 기능 개선 용이

---

**개발팀**: AI Interview System Team  
**버전**: 3.0.0 (모듈형 아키텍처 리팩터링 완료)  
**최종 업데이트**: 2025-01-23  
**아키텍처**: 모듈형 계층화 구조  
**데이터베이스**: Supabase (PostgreSQL)