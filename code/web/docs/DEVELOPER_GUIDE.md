# 👨‍💻 개발자 가이드

AI 면접 시스템의 코드 구조, 확장 방법, 개발 환경 설정에 대한 종합 가이드입니다.

## 📋 목차
- [아키텍처 개요](#아키텍처-개요)
- [코드 구조](#코드-구조)
- [핵심 컴포넌트](#핵심-컴포넌트)
- [개발 환경 설정](#개발-환경-설정)
- [확장 가이드](#확장-가이드)
- [디버깅 및 테스트](#디버깅-및-테스트)
- [배포 가이드](#배포-가이드)

## 🏗️ 아키텍처 개요

### 시스템 구조
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   External      │
│   (React + TS)  │◄──►│   (FastAPI)     │◄──►│   (OpenAI API)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Database      │
                       │   (Supabase)    │
                       └─────────────────┘
```

### 주요 컴포넌트 간 상호작용
```
Document Upload → Document Processor → User Profile → Question Generation → Interview Session → Evaluation
```

### 기술 스택
- **Backend**: Python 3.10+, FastAPI 0.104+, Uvicorn
- **AI Engine**: OpenAI GPT-4o-mini, AutoML (AutoGluon)
- **Database**: Supabase (PostgreSQL), Real-time subscriptions
- **Frontend**: React 19.1.0, TypeScript, Tailwind CSS
- **Document Processing**: PyPDF2, python-docx, sentence-transformers
- **Infrastructure**: CORS middleware, JWT authentication

## 📁 코드 구조

### 디렉토리 구조 상세
```
yoseop_1/
├── backend/                   # FastAPI 서버 (v3.0 계층화)
│   ├── main.py                # FastAPI 앱 엔트리포인트
│   ├── routers/               # API 라우터 (RESTful)
│   │   ├── interview.py       # 면접 API
│   │   ├── auth.py            # 인증 API
│   │   ├── company.py         # 회사 관리 API
│   │   └── user.py            # 사용자 관리 API
│   ├── services/              # 비즈니스 로직 레이어
│   │   ├── interview_service.py # 면접 서비스
│   │   └── supabase_client.py # DB 클라이언트
│   └── schemas/               # Pydantic 모델
├── frontend/                  # React + TypeScript (SPA)
│   ├── src/                   
│   │   ├── components/        # React 컴포넌트
│   │   ├── pages/             # 페이지 컴포넌트
│   │   ├── hooks/             # Custom hooks
│   │   └── services/          # API 서비스
│   └── package.json           # Node.js 의존성
├── llm/                       # 🆕 모듈형 AI/LLM 구조 (v3.0)
│   ├── session/               # 세션 관리 모듈
│   ├── interviewer/           # 면접관 모듈 (질문 생성)
│   ├── candidate/             # AI 지원자 모듈 (답변 생성)
│   ├── feedback/              # 평가 모듈 (ML + LLM)
│   └── shared/                # 공용 모듈
├── scripts/                   # 실행 및 도구 스크립트
│   └── start_backend.py       # 백엔드 실행 스크립트
├── logs/                      # 로그 파일
└── requirements.txt           # Python 의존성
```

### 모듈 의존성 다이어그램 (v3.0)
```
FastAPI App (backend/main.py)
    ↓
API Routers (backend/routers/)
    ↓
Service Layer (backend/services/)
    ↓
LLM Session Manager (llm/session/manager.py)
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│   Interviewer   │   AI Candidate  │   Feedback      │
│   (질문 생성)    │   (답변 생성)    │   (평가)        │
│   llm/interviewer│   llm/candidate │   llm/feedback  │
└─────────────────┴─────────────────┴─────────────────┘
    ↓
Shared Components (llm/shared/)
    ↓
External Services (OpenAI API, Supabase, AutoML)
```

## 🔧 핵심 컴포넌트

### 1. Document Processor (`core/document_processor.py`)

**책임**: 문서 업로드, 텍스트 추출, 사용자 프로필 생성

```python
class DocumentProcessor:
    def __init__(self):
        self.supported_formats = ALLOWED_FILE_EXTENSIONS
        
    def extract_text_from_file(self, file_content: bytes, file_type: str) -> str:
        """파일에서 텍스트 추출"""
        
    def create_user_profile(self, documents: Dict[str, str]) -> UserProfile:
        """문서 분석하여 사용자 프로필 생성"""
        
    def analyze_document_content(self, text: str) -> Dict[str, Any]:
        """문서 내용 분석"""
```

**주요 기능**:
- PDF, DOCX, DOC, TXT 파일 처리
- 텍스트 추출 및 정제
- AI 기반 프로필 생성
- 기술 스킬, 프로젝트, 경험 분류

### 2. Session Manager (`llm/session/manager.py`)

**책임**: 모든 면접 세션(일반 및 비교) 관리, 질문 생성 및 답변 처리 위임

```python
class SessionManager:
    def __init__(self):
        self.base_session_manager = BaseInterviewSession()
        self.comparison_session_manager = ComparisonSessionManager()
        
    def start_interview(self, company_id: str, position: str, candidate_name: str) -> str:
        """일반 면접 시작"""
        
    def get_next_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        """다음 질문 가져오기"""
        
    def submit_answer(self, session_id: str, answer_content: str) -> Dict[str, Any]:
        """답변 제출"""
        
    def start_comparison_interview(self, company_id: str, position: str, user_name: str, ai_name: str = "춘식이") -> str:
        """AI 비교 면접 시작"""
```

**주요 기능**: 
- 일반 면접 세션 및 AI 비교 면접 세션 통합 관리
- 각 세션 유형에 맞는 질문 생성 및 답변 처리 로직 위임
- 세션 상태 추적 및 결과 제공

### 3. AI Candidate Model (`llm/candidate/model.py`)

**책임**: AI 지원자 모델링, 답변 생성, 경쟁 면접 관리

```python
class AICandidateModel:
    def __init__(self):
        self.personas = self.load_personas()
        
    def generate_answer(self, answer_request: AnswerRequest) -> AnswerResponse:
        """AI 답변 생성"""
        
    def get_ai_name(self, llm_provider: LLMProvider) -> str:
        """AI 이름 반환 (춘식이 고정)"""
        
    def start_ai_interview(self, company: str, position: str) -> str:
        """AI 면접 세션 시작"""
```

**AI 답변 특징**:
- 페르소나 기반 일관된 답변
- 기업별 맞춤형 내용
- 신뢰도 점수 제공

### 4. LLM Manager (`core/llm_manager.py`)

**책임**: OpenAI API 관리, 에러 처리, 재시도 로직

```python
class LLMManager:
    def __init__(self):
        self.rate_limiter = RateLimiter()
        
    def generate_response(self, prompt: str, **kwargs) -> str:
        """LLM 응답 생성 (재시도 로직 포함)"""
        
    def handle_api_error(self, error: Exception) -> str:
        """API 에러 처리"""
```

**기능**:
- Rate limiting (분당 60회)
- 지수 백오프 재시도
- 토큰 사용량 모니터링
- 다중 모델 지원

### 5. Conversation Context (`llm/interviewer/conversation_context.py`)

**책임**: 대화 컨텍스트 관리, 중복 질문 방지

```python
class ConversationContext:
    def __init__(self):
        self.similarity_threshold = 0.5
        
    def is_duplicate_question(self, new_question: str, existing_questions: List[str]) -> bool:
        """중복 질문 검사"""
        
    def calculate_semantic_similarity(self, q1: str, q2: str) -> float:
        """의미적 유사도 계산"""
```

**중복 방지 알고리즘**:
- 의도 유사도 (60%) + 키워드 유사도 (30%) + 구조 유사도 (10%)
- 임계값 50% 이상 시 중복 판정

## 🚀 개발 환경 설정

### 1. 로컬 개발 환경

```bash
# 1. 저장소 클론
git clone <repository-url>
cd final_project/yoseop_1

# 2. 가상환경 설정
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Python 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
# .env 파일에서 OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY 설정

# 5. 백엔드 개발 서버 실행
python scripts/start_backend.py
# 또는 직접: python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# 6. 프론트엔드 개발 서버 실행 (별도 터미널)
cd frontend
npm install
npm start
```

### 2. 개발 도구 설정

#### VS Code 확장 프로그램
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.flake8",
    "ms-python.black-formatter",
    "ms-python.pylint",
    "ms-toolsai.jupyter"
  ]
}
```

#### Pre-commit 훅 설정
```bash
# pre-commit 설치
pip install pre-commit

# 훅 설정
pre-commit install

# .pre-commit-config.yaml 생성
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
EOF
```

### 3. 디버깅 설정

#### FastAPI 디버그 모드
```python
# backend/main.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # 개발 시에만 True (자동 재시작)
        log_level="info"
    )
```

#### 로깅 설정
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

## 🔧 확장 가이드

### 1. 새로운 기업 추가

#### 단계 1: 기업 데이터 추가
```json
// data/companies_data.json
{
  "companies": [
    {
      "id": "new_company",
      "name": "새로운 기업",
      "talent_profile": "인재상 설명",
      "core_competencies": ["역량1", "역량2"],
      "tech_focus": ["기술1", "기술2"],
      "interview_keywords": ["키워드1", "키워드2"],
      "company_culture": {
        "work_style": "업무 스타일",
        "decision_making": "의사결정 방식",
        "growth_support": "성장 지원",
        "core_values": ["가치1", "가치2"]
      },
      "interviewer_personas": {
        "tech_lead": {
          "name": "기술 리드 이름",
          "role": "역할",
          "experience": "경험",
          "personality": "성격",
          "speaking_style": "말하는 스타일"
        }
      }
    }
  ]
}
```

#### 단계 2: 상수 업데이트
```python
# core/constants.py
SUPPORTED_COMPANIES = [
    'naver', 'kakao', 'line', 'coupang', 
    'baemin', 'danggeun', 'toss', 'new_company'  # 추가
]
```

#### 단계 3: 프론트엔드 업데이트
```html
<!-- web/app.py HTML 템플릿 -->
<select id="company">
    <option value="">회사 선택...</option>
    <option value="new_company">새로운 기업</option>
</select>
```

### 2. 새로운 질문 타입 추가

#### 단계 1: 질문 타입 정의
```python
# core/interview_system.py
class QuestionType(Enum):
    INTRO = "자기소개"
    MOTIVATION = "지원동기"
    HR = "인사"
    TECH = "기술"
    COLLABORATION = "협업"
    FOLLOWUP = "심화"
    CREATIVITY = "창의성"  # 새로운 타입 추가
```

#### 단계 2: 질문 계획 업데이트
```python
# core/interview_system.py
class InterviewSession:
    def __init__(self, company_id: str, position: str, candidate_name: str):
        self.question_plan = [
            # 기존 질문들...
            {"type": QuestionType.CREATIVITY, "fixed": False}  # 추가
        ]
```

#### 단계 3: 프롬프트 템플릿 추가
```python
# core/prompt_templates.py
class PromptTemplates:
    @staticmethod
    def get_creativity_question_prompt(company_data: dict, **kwargs) -> str:
        return f"""
        {company_data['name']}의 창의성 평가를 위한 질문을 생성하세요.
        
        평가 포인트:
        - 창의적 사고 능력
        - 혁신적 아이디어 제안
        - 문제 해결의 독창성
        """
```

### 3. 새로운 평가 지표 추가

#### 단계 1: 평가 모델 확장
```python
# core/personalized_system.py
def evaluate_answer_with_new_metrics(self, qa_pair: QuestionAnswer) -> Dict:
    evaluation = {
        "score": 0,
        "feedback": "",
        "creativity_score": 0,      # 새로운 지표
        "innovation_level": 0,      # 새로운 지표
        "originality": 0           # 새로운 지표
    }
    return evaluation
```

#### 단계 2: 프롬프트 업데이트
```python
def get_evaluation_prompt_with_creativity(self, qa_pair: QuestionAnswer) -> str:
    return f"""
    다음 기준으로 평가하세요:
    1. 기술적 정확성 (30%)
    2. 논리적 구조 (25%)
    3. 창의성 (25%)           # 새로운 기준
    4. 실용성 (20%)
    """
```

### 4. 새로운 AI 모델 통합

#### 단계 1: LLM Provider 추가
```python
# core/llm_manager.py
class LLMProvider(Enum):
    OPENAI_GPT35 = "openai-gpt-3.5-turbo"
    OPENAI_GPT4 = "openai-gpt-4"
    CLAUDE = "claude-3-sonnet"           # 새로운 모델
    GEMINI = "gemini-pro"               # 새로운 모델
```

#### 단계 2: 클라이언트 구현
```python
class LLMManager:
    def __init__(self):
        self.clients = {
            LLMProvider.OPENAI_GPT35: OpenAIClient(),
            LLMProvider.CLAUDE: ClaudeClient(),      # 새로운 클라이언트
            LLMProvider.GEMINI: GeminiClient()       # 새로운 클라이언트
        }
    
    def generate_response(self, prompt: str, provider: LLMProvider) -> str:
        client = self.clients[provider]
        return client.generate(prompt)
```

## 🧪 디버깅 및 테스트

### 1. 단위 테스트

#### 테스트 구조
```
tests/
├── __init__.py
├── test_document_processor.py
├── test_interview_system.py
├── test_ai_candidate_model.py
├── test_llm_manager.py
└── fixtures/
    ├── sample_resume.pdf
    ├── sample_cover_letter.docx
    └── mock_responses.json
```

#### 예시 테스트
```python
# tests/test_document_processor.py
import unittest
from core.document_processor import DocumentProcessor

class TestDocumentProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = DocumentProcessor()
    
    def test_extract_text_from_pdf(self):
        with open('tests/fixtures/sample_resume.pdf', 'rb') as f:
            content = f.read()
        
        text = self.processor.extract_text_from_file(content, 'pdf')
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
    
    def test_create_user_profile(self):
        documents = {
            '자기소개서': 'Python 개발자 홍길동입니다...',
            '이력서': '경력 3년, 백엔드 개발...'
        }
        
        profile = self.processor.create_user_profile(documents)
        self.assertIsNotNone(profile.name)
        self.assertGreater(len(profile.technical_skills), 0)
```

### 2. 통합 테스트

```python
# tests/test_integration.py
import unittest
import json
from web.app import app

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_full_interview_flow(self):
        # 1. 문서 업로드
        with open('tests/fixtures/sample_resume.pdf', 'rb') as f:
            response = self.app.post('/upload', data={
                'file': f,
                'document_type': '이력서'
            })
        self.assertEqual(response.status_code, 200)
        
        # 2. 문서 분석
        response = self.app.post('/analyze', json={
            'documents': {'이력서': '테스트 내용'}
        })
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # 3. 면접 시작
        response = self.app.post('/start_personalized', json={
            'company': 'naver',
            'position': '백엔드 개발자',
            'user_profile': data['profile']
        })
        self.assertEqual(response.status_code, 200)
```

### 3. 성능 테스트

```python
# tests/test_performance.py
import time
import unittest
from core.llm_manager import LLMManager

class TestPerformance(unittest.TestCase):
    def test_response_time(self):
        manager = LLMManager()
        
        start_time = time.time()
        response = manager.generate_response("테스트 질문")
        end_time = time.time()
        
        # 응답 시간이 10초 이내여야 함
        self.assertLess(end_time - start_time, 10)
    
    def test_concurrent_requests(self):
        import threading
        
        def make_request():
            manager = LLMManager()
            manager.generate_response("테스트 질문")
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
```

### 4. 디버깅 유틸리티

```python
# core/debug_utils.py
import logging
import json
from functools import wraps

def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logging.info(f"{func.__name__} returned: {result}")
        return result
    return wrapper

def debug_interview_session(session_id: str):
    """면접 세션 디버그 정보 출력"""
    from web.app import app_state
    
    if session_id in app_state.current_sessions:
        session = app_state.current_sessions[session_id]
        print(f"세션 ID: {session_id}")
        print(f"질문 수: {len(session.conversation_history)}")
        print(f"현재 진행률: {session.current_question_count}/{len(session.question_plan)}")
        
        for i, qa in enumerate(session.conversation_history):
            print(f"Q{i+1}: {qa.question_content}")
            print(f"A{i+1}: {qa.answer_content[:100]}...")
```

## 🚀 배포 가이드

### 1. Docker 배포

#### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8888

CMD ["python", "run.py"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  ai-interview:
    build: .
    ports:
      - "8888:8888"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FLASK_ENV=production
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - ai-interview
```

### 2. 클라우드 배포

#### AWS EC2 배포
```bash
# 1. EC2 인스턴스 생성 (Ubuntu 20.04)
# 2. 보안 그룹 설정 (포트 80, 443, 8888 오픈)

# 3. 서버 설정
sudo apt update
sudo apt install python3-pip nginx certbot python3-certbot-nginx

# 4. 애플리케이션 배포
git clone <repository>
cd final_Q_test
pip3 install -r requirements.txt

# 5. 환경변수 설정
echo "OPENAI_API_KEY=your-key" > .env

# 6. 시스템 서비스 등록
sudo tee /etc/systemd/system/ai-interview.service > /dev/null <<EOF
[Unit]
Description=AI Interview System
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/final_Q_test
ExecStart=/usr/bin/python3 run.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable ai-interview
sudo systemctl start ai-interview
```

#### Nginx 설정
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /uploads {
        alias /home/ubuntu/final_Q_test/uploads;
    }
    
    client_max_body_size 16M;
}
```

### 3. 모니터링 설정

#### 로그 모니터링
```python
# core/monitoring.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    
    # 로그 파일 로테이션
    handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
```

#### 성능 모니터링
```python
# core/metrics.py
import time
import psutil
from typing import Dict

class MetricsCollector:
    def __init__(self):
        self.metrics = {
            'requests_count': 0,
            'average_response_time': 0,
            'memory_usage': 0,
            'cpu_usage': 0
        }
    
    def record_request(self, response_time: float):
        self.metrics['requests_count'] += 1
        self.metrics['average_response_time'] = (
            self.metrics['average_response_time'] * (self.metrics['requests_count'] - 1) + 
            response_time
        ) / self.metrics['requests_count']
    
    def get_system_metrics(self) -> Dict:
        return {
            'memory_usage': psutil.virtual_memory().percent,
            'cpu_usage': psutil.cpu_percent(),
            'disk_usage': psutil.disk_usage('/').percent
        }
```

### 4. 보안 강화

#### HTTPS 설정
```bash
# Let's Encrypt SSL 인증서 설치
sudo certbot --nginx -d your-domain.com
```

#### 환경변수 보안
```python
# core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # 프로덕션 환경에서는 더 강력한 보안 설정
    if os.environ.get('FLASK_ENV') == 'production':
        SESSION_COOKIE_SECURE = True
        SESSION_COOKIE_HTTPONLY = True
        SESSION_COOKIE_SAMESITE = 'Lax'
```

## 📚 추가 리소스

### 참고 문서
- [Flask 공식 문서](https://flask.palletsprojects.com/)
- [OpenAI API 문서](https://platform.openai.com/docs)
- [Python 타입 힌트 가이드](https://docs.python.org/3/library/typing.html)

### 유용한 도구
- **코드 품질**: `black`, `flake8`, `pylint`
- **테스트**: `pytest`, `coverage`
- **API 테스트**: `postman`, `insomnia`
- **모니터링**: `prometheus`, `grafana`

### 커뮤니티
- **GitHub Issues**: 버그 리포트 및 기능 요청
- **Stack Overflow**: 기술적 질문
- **Discord/Slack**: 실시간 개발자 채팅

---

**🔧 개발 팁**: 새로운 기능 개발 시 항상 테스트 코드를 먼저 작성하고(TDD), 작은 단위로 커밋하며, 코드 리뷰를 통해 품질을 유지하세요!