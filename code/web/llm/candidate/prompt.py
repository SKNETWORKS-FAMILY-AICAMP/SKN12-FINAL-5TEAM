#!/usr/bin/env python3
"""
AI 지원자 프롬프트 빌더
순수 프롬프트 문자열 생성만 담당 - 외부 의존성 제거
"""

from typing import Dict, Any, List, TYPE_CHECKING
from ..shared.models import LLMProvider, QuestionType, AnswerRequest

# TYPE_CHECKING을 사용하여 순환 import 방지
if TYPE_CHECKING:
    from .model import CandidatePersona

class CandidatePromptBuilder:
    """AI 지원자 프롬프트 생성을 담당하는 클래스"""
    
    def __init__(self):
        # 2단계: 직무별 정체성 DNA 시스템 초기화
        self.position_dna_system = self._initialize_position_dna_system()
        # 3단계: 5단계 서사 연결 시스템 초기화
        self.narrative_connection_system = self._initialize_narrative_system()
    
    def build_prompt(self, request, persona, company_data, interview_context: Dict = None) -> str:
        """질문 유형에 따라 적절한 프롬프트 빌더를 호출하는 통합 메서드 - 외부 의존성 제거"""
        print(f"🔍 [DEBUG] 질문 타입: {request.question_type}")
        print(f"🔍 [DEBUG] 질문 타입 값: {request.question_type.value}")
        print(f"🔍 [DEBUG] 질문 타입 값 (upper): {request.question_type.value.upper()}")
        print(f"🔍 [DEBUG] 질문 내용: {request.question_content}")
        print(f"🔍 [DEBUG] INTRO 비교: {request.question_type.value.upper() == 'INTRO'}")
        # 3단계: 면접 컨텍스트 기반 서사 연결 적용
        if interview_context is None:
            interview_context = {"previous_answers": [], "current_stage": 1, "total_questions": 20}
            
        if request.question_type.value == "자기소개":
            return self.build_intro_prompt(request, persona, company_data, interview_context)
        elif request.question_type.value == "지원동기":
            return self.build_motivation_prompt(request, persona, company_data, interview_context)
        elif request.question_type.value == "인사":
            return self.build_hr_prompt(request, persona, company_data, interview_context)
        elif request.question_type.value == "기술":
            return self.build_tech_prompt(request, persona, company_data, interview_context)
        elif request.question_type.value == "협업":
            return self.build_collaboration_prompt(request, persona, company_data, interview_context)
        else:
            return self.build_default_prompt(request, persona, company_data, interview_context)

    def _parse_tech_skills(self, tech_string: str) -> List[str]:
        """기술 스택 문자열을 배열로 파싱"""
        if not tech_string:
            return []
        
        # 쉼표, 세미콜론, 슬래시 등으로 분리
        import re
        skills = re.split(r'[,;/\n]', tech_string)
        
        # 공백 제거 및 빈 문자열 필터링
        parsed_skills = []
        for skill in skills:
            cleaned = skill.strip()
            if cleaned and len(cleaned) > 1:  # 너무 짧은 것은 제외
                parsed_skills.append(cleaned)
        
        return parsed_skills[:10]  # 최대 10개까지만
    
    def _extract_projects_from_career(self, career_text: str, activities_text: str = "") -> List[Dict[str, Any]]:
        """경력과 활동 텍스트에서 프로젝트 구조 추출"""
        projects = []
        
        if not career_text and not activities_text:
            return projects
        
        # 경력에서 프로젝트 추출
        if career_text:
            # 문장 단위로 분리하여 프로젝트 식별
            sentences = career_text.replace('–', '-').split('-')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:  # 의미있는 길이
                    project = {
                        "name": self._extract_project_name(sentence),
                        "description": sentence[:150],  # 설명은 150자로 제한
                        "role": self._infer_role_from_text(sentence),
                        "tech_stack": self._extract_tech_from_text(sentence),
                        "achievements": self._extract_achievements(sentence),
                        "challenges": self._infer_challenges(sentence)
                    }
                    projects.append(project)
        
        # 활동에서도 프로젝트 추출
        if activities_text:
            activity_projects = self._extract_projects_from_activities(activities_text)
            projects.extend(activity_projects)
        
        return projects[:3]  # 최대 3개 프로젝트만
    
    def _extract_project_name(self, text: str) -> str:
        """텍스트에서 프로젝트명 추출"""
        # 주요 키워드로 프로젝트명 추론
        keywords = ['앱', '시스템', '서비스', '플랫폼', '프로젝트', '개발', '솔루션']
        
        words = text.split()
        for i, word in enumerate(words):
            if any(keyword in word for keyword in keywords):
                # 해당 키워드 앞의 2-3개 단어를 프로젝트명으로
                start_idx = max(0, i-2)
                end_idx = min(len(words), i+2)
                project_name = ' '.join(words[start_idx:end_idx])
                return project_name[:30]  # 30자 제한
        
        # 키워드가 없으면 앞의 일부를 사용
        return text.split('.')[0][:25] if text else "주요 프로젝트"
    
    def _infer_role_from_text(self, text: str) -> str:
        """텍스트에서 역할 추론"""
        role_keywords = {
            '인턴': '인턴',
            '리더': '프로젝트 리더', 
            '개발': '개발자',
            '기획': '기획자',
            '운영': '운영 담당자',
            '설계': '설계 담당자'
        }
        
        for keyword, role in role_keywords.items():
            if keyword in text:
                return role
        
        return "팀원"
    
    def _extract_tech_from_text(self, text: str) -> List[str]:
        """텍스트에서 기술 스택 추출"""
        # 일반적인 기술 키워드들
        tech_keywords = [
            'Python', 'Java', 'JavaScript', 'React', 'Vue', 'Angular', 'Node.js',
            'Spring', 'Django', 'Flask', 'MySQL', 'PostgreSQL', 'MongoDB',
            'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure', 'Git', 'Jenkins',
            'Flutter', 'Android', 'iOS', 'Swift', 'Kotlin', 'Linux', 'Windows'
        ]
        
        found_techs = []
        text_upper = text.upper()
        
        for tech in tech_keywords:
            if tech.upper() in text_upper:
                found_techs.append(tech)
        
        return found_techs[:5]  # 최대 5개
    
    def _extract_achievements(self, text: str) -> List[str]:
        """텍스트에서 성과 추출"""
        achievement_patterns = [
            r'(\d+%\s*(?:증가|향상|개선))', 
            r'(\d+명?\s*(?:사용자|고객))',
            r'(수상|선정|달성|완료|성공)'
        ]
        
        achievements = []
        import re
        
        for pattern in achievement_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            achievements.extend(matches)
        
        # 기본 성과 템플릿
        if not achievements:
            if '운영' in text:
                achievements.append("시스템 안정적 운영")
            if '개발' in text:
                achievements.append("기능 개발 완료")
            if '협업' in text or '팀' in text:
                achievements.append("팀 협업을 통한 프로젝트 성공")
        
        return achievements[:3]
    
    def _infer_challenges(self, text: str) -> List[str]:
        """텍스트에서 도전과제 추론"""
        challenges = []
        
        if '복잡' in text or '어려움' in text:
            challenges.append("복잡한 요구사항 해결")
        if '협업' in text or '소통' in text:
            challenges.append("다양한 이해관계자간 협업")
        if '성능' in text or '최적화' in text:
            challenges.append("성능 최적화 및 안정성 확보")
        if '사용자' in text:
            challenges.append("사용자 요구사항 변화에 대응")
        
        # 기본 도전과제
        if not challenges:
            challenges = ["기술적 복잡도 해결", "프로젝트 일정 관리"]
        
        return challenges[:3]
    
    def _extract_projects_from_activities(self, activities_text: str) -> List[Dict[str, Any]]:
        """활동 텍스트에서 프로젝트 추출"""
        projects = []
        
        # 활동을 문장 단위로 분리
        sentences = activities_text.replace('–', '-').split('-')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 15:
                project = {
                    "name": self._extract_activity_project_name(sentence),
                    "description": sentence[:120],
                    "role": "참여자",
                    "tech_stack": self._extract_tech_from_text(sentence),
                    "achievements": ["활동 완료", "실전 경험 습득"],
                    "challenges": ["새로운 기술 학습", "팀 협업"]
                }
                projects.append(project)
        
        return projects
    
    def _extract_activity_project_name(self, text: str) -> str:
        """활동 텍스트에서 프로젝트명 추출"""
        activity_keywords = ['동아리', '프로젝트', '서비스', '시스템', '앱', '웹사이트']
        
        for keyword in activity_keywords:
            if keyword in text:
                # 키워드 주변 단어들로 이름 생성
                words = text.split()
                for i, word in enumerate(words):
                    if keyword in word:
                        start = max(0, i-1)
                        end = min(len(words), i+2)
                        return ' '.join(words[start:end])[:25]
        
        return text[:20] if text else "활동 프로젝트"
    
    def _extract_experiences_from_activities(self, activities_text: str, awards_text: str = "") -> List[Dict[str, Any]]:
        """활동과 수상에서 경험 구조 추출"""
        experiences = []
        
        if activities_text:
            # 활동을 여러 경험으로 분리
            activity_parts = activities_text.split(',')
            for part in activity_parts:
                part = part.strip()
                if len(part) > 10:
                    exp = {
                        "category": self._categorize_experience(part),
                        "experience": part[:100],
                        "lesson": self._infer_lesson_from_activity(part)
                    }
                    experiences.append(exp)
        
        if awards_text:
            # 수상 경험 추가
            award_parts = awards_text.split(',')
            for award in award_parts:
                award = award.strip()
                if len(award) > 5:
                    exp = {
                        "category": "수상 및 성과",
                        "experience": award[:80],
                        "lesson": "지속적인 노력과 도전의 중요성을 깨달음"
                    }
                    experiences.append(exp)
        
        return experiences[:4]  # 최대 4개
    
    def _categorize_experience(self, text: str) -> str:
        """경험 텍스트를 카테고리로 분류"""
        categories = {
            '동아리': '학술 동아리 활동',
            '인턴': '실무 경험',
            '프로젝트': '프로젝트 수행',
            '교육': '교육 및 학습',
            '대회': '경진대회 참가',
            '봉사': '봉사 활동',
            '리더': '리더십 경험'
        }
        
        for keyword, category in categories.items():
            if keyword in text:
                return category
        
        return "기타 경험"
    
    def _infer_lesson_from_activity(self, activity_text: str) -> str:
        """활동에서 배운 점 추론"""
        lesson_templates = {
            '동아리': "팀워크와 지속적인 학습의 중요성을 배움",
            '인턴': "실무 환경에서의 책임감과 전문성 향상",
            '프로젝트': "문제 해결 능력과 창의적 사고 개발",
            '교육': "새로운 지식 습득과 자기계발의 즐거움",
            '대회': "도전 정신과 경쟁력 강화",
            '협업': "소통과 협력의 가치를 체험"
        }
        
        for keyword, lesson in lesson_templates.items():
            if keyword in activity_text:
                return lesson
        
        return "새로운 경험을 통한 시야 확장과 성장"

    def _format_projects_for_prompt(self, projects: List[Dict[str, Any]]) -> str:
        """프로젝트 리스트를 프롬프트용 텍스트로 포맷팅"""
        if not projects:
            return "구체적인 프로젝트 경험 정보 없음"
        
        formatted = []
        for i, project in enumerate(projects, 1):
            tech_stack_str = ', '.join(project.get('tech_stack', []))
            achievements_str = ' / '.join(project.get('achievements', []))
            challenges_str = ' / '.join(project.get('challenges', []))
            
            project_text = f"""
{i}. **{project.get('name', '프로젝트')}**
   - 설명: {project.get('description', '')[:100]}...
   - 역할: {project.get('role', '팀원')}
   - 기술: {tech_stack_str}
   - 성과: {achievements_str}
   - 도전: {challenges_str}"""
            
            formatted.append(project_text)
        
        return '\n'.join(formatted)
    
    def _format_experiences_for_prompt(self, experiences: List[Dict[str, Any]]) -> str:
        """경험 리스트를 프롬프트용 텍스트로 포맷팅"""
        if not experiences:
            return "구체적인 활동/경험 정보 없음"
        
        formatted = []
        for i, exp in enumerate(experiences, 1):
            exp_text = f"""
{i}. **[{exp.get('category', '기타')}]** {exp.get('experience', '')[:80]}...
   → 배운 점: {exp.get('lesson', '')}"""
            
            formatted.append(exp_text)
        
        return '\n'.join(formatted)

    def build_persona_generation_prompt(self, resume_data: Dict[str, Any], company_name: str, position_name: str, company_info: Dict[str, Any], model_name: str = "gpt-4o-mini") -> str:
        """데이터베이스 이력서를 기반으로 LLM 페르소나 생성 프롬프트 구성"""
        
        # 이력서 원본 데이터 정리
        career = resume_data.get('career', '')
        academic = resume_data.get('academic_record', '')
        tech_skills_raw = resume_data.get('tech', '')
        activities = resume_data.get('activities', '')
        certificates = resume_data.get('certificate', '')
        awards = resume_data.get('awards', '')
        resume_id = resume_data.get('ai_resume_id', 0)
        
        # 🔥 NEW: 데이터 전처리를 통한 구조화
        parsed_tech_skills = self._parse_tech_skills(tech_skills_raw)
        structured_projects = self._extract_projects_from_career(career, activities)
        meaningful_experiences = self._extract_experiences_from_activities(activities, awards)
        
        # 회사 정보 정리
        company_profile = company_info.get('talent_profile', '')
        core_competencies = ', '.join(company_info.get('core_competencies', []))
        tech_focus = ', '.join(company_info.get('tech_focus', []))
        
        # 🔥 NEW: 구조화된 데이터를 프롬프트용으로 포맷팅
        formatted_projects = self._format_projects_for_prompt(structured_projects)
        formatted_experiences = self._format_experiences_for_prompt(meaningful_experiences)
        formatted_tech_skills = ', '.join(parsed_tech_skills) if parsed_tech_skills else tech_skills_raw
        
        prompt = f"""
다음 이력서 데이터를 분석하여 {company_name} {position_name} 직군에 지원하는 **인간미 넘치고 현실적인** AI 지원자 페르소나를 생성하세요.

=== 📊 실제 이력서 분석 결과 ===
**원본 데이터:**
- 경력: {career}
- 학력: {academic}
- 기술 스택: {tech_skills_raw}
- 활동: {activities}
- 자격증: {certificates}  
- 수상: {awards}

**🔍 구조화된 분석:**
**기술 역량 ({len(parsed_tech_skills)}개):** {formatted_tech_skills}

**프로젝트 경험 ({len(structured_projects)}개):**
{formatted_projects}

**의미있는 경험들 ({len(meaningful_experiences)}개):**
{formatted_experiences}

=== 🏢 {company_name} 회사 정보 ===
- 인재상: {company_profile}
- 핵심 역량: {core_competencies}
- 기술 중점: {tech_focus}

=== 🎯 페르소나 생성 지침 ===
**중요:** 위의 **실제 구조화된 데이터**를 기반으로 생생하고 현실적인 페르소나를 만드세요.
- 예시 텍스트 대신 실제 경력/프로젝트 내용 활용
- 구체적인 기술 스택과 경험 반영
- 인간적이고 매력적인 스토리 구성

아래 JSON 형태로 **정확히** 응답하되, **위의 구조화된 실제 데이터**를 활용하여 생생하고 현실적으로 채워넣으세요:

{{
  "name": "춘식이",
  "summary": "위 분석 결과를 바탕으로 {position_name}의 핵심 역량과 특징을 한 줄로 표현",
  "background": {{
    "career_years": "경력 텍스트에서 추정한 실제 경력 년수",
    "current_position": "{position_name}",
    "education": "{academic}",
    "major": "학력에서 추정한 전공 분야"
  }},
  "strengths": [
    "구조화된 기술 역량과 프로젝트에서 도출한 실제 강점 3개"
  ],
  "technical_skills": {parsed_tech_skills},
  "projects": [
    위의 구조화된 프로젝트 경험들을 JSON 배열로 변환
  ],
  "experiences": [
    위의 의미있는 경험들을 JSON 배열로 변환  
  ],
  "weaknesses": [
    "실제 경험에서 유추 가능한 개선점이나 도전 과제 2개"
  ],
  "motivation": "회사 정보와 개인 경험을 연결한 구체적인 지원 동기",
  "inferred_personal_experiences": [
    {{
      "category": "성장 경험",
      "experience": "위 경험들에서 더 개인적이고 감정적인 측면을 추론한 구체적 내용",
      "lesson": "그 경험을 통해 얻은 교훈이나 깨달음"
    }}
  ],
  "career_goal": "현재 경험과 회사 비전을 연결한 구체적 목표",
  "personality_traits": ["실제 경험과 활동에서 유추 가능한 성격 특성"],
  "interview_style": "위 모든 정보를 종합한 면접 스타일",
  "generated_by": "{model_name}"
}}

**중요**: 
1. 이름은 반드시 "춘식이"로 설정하세요.
2. 오직 JSON 형식으로만 응답하고, 다른 설명이나 주석은 절대 추가하지 마세요.
"""
        return prompt.strip()
    
    def build_system_prompt_for_persona_generation(self) -> str:
        """페르소나 생성용 시스템 프롬프트"""
        return """당신은 이력서 데이터를 분석하여 현실적이고 매력적인 AI 지원자 페르소나를 생성하는 전문가입니다.

핵심 원칙:
1. 주어진 이력서 데이터를 최대한 활용하되, 현실적이고 일관성 있게 보완
2. 회사의 인재상과 핵심 역량에 맞는 강점과 경험 강조
3. 완벽하지 않은 인간적인 면모(약점, 성장 과정) 포함
4. 구체적이고 측정 가능한 성과와 경험 중심으로 구성
5. 반드시 정확한 JSON 형식으로만 응답

절대 지켜야 할 사항:
- 이름은 반드시 "춘식이"
- JSON 외의 어떤 설명도 추가하지 않음
- 모든 필드를 빠짐없이 포함
- 예시 형태가 아닌 실제 내용으로 작성"""

    def build_system_prompt(self, persona: 'CandidatePersona', company_name: str, company_data: Dict, question_type: QuestionType, llm_provider: LLMProvider = LLMProvider.OPENAI_GPT4O) -> str:
        """질문 타입별 시스템 프롬프트 구성"""
        
        # AI 이름 결정 (모델에 따라 동적으로 설정)
        ai_name = self._get_ai_name(llm_provider)
        
        base_info = f"""당신은 {company_data.get('name', '회사')} 면접에 참여한 우수한 지원자입니다.

=== 중요: 당신의 이름은 "{ai_name}"입니다 ===
- **자기소개 질문(INTRO)에서만** "{ai_name}"라고 이름을 언급하세요
- **다른 모든 질문에서는 절대 이름을 언급하지 마세요**
- "안녕하세요" 같은 인사말도 자기소개가 아닌 경우 사용하지 마세요

예시:
- 자기소개: "안녕하세요, 저는 {ai_name}라고 합니다...."
- 지원동기: "제가 {company_name}에 지원하게 된 이유는..." (이름/인사 없이 바로 시작)
- 기술질문: "그 부분에 대해서는 제 경험을 말씀드리면..." (이름/인사 없이)
- 기타질문: "제 생각에는..." 또는 "저의 경험으로는..." (이름/인사 없이)

=== 당신의 배경 ===
- 경력: {persona.background.get('career_years', '0')}년
- 현재 직책: {persona.background.get('current_position', '지원자')}
- 성격 특성: {', '.join(persona.personality_traits)}
- 면접 스타일: {persona.interview_style}

=== 당신의 강점 ===
{', '.join(persona.strengths)}

=== 당신의 목표 ===
{persona.career_goal}

=== 면접 답변 가이드라인 ===
1. 자연스럽고 진정성 있는 톤 유지
2. 구체적인 경험과 사례 중심으로 답변
3. 회사의 가치와 본인의 경험을 연결
4. 적절한 길이 (30-60초 분량)
5. 겸손하지만 자신감 있는 태도

**절대 하지 말 것:**
- 지나치게 완벽한 답변 (인간적인 면모 유지)
- 회사 정보의 단순 나열
- 너무 짧거나 너무 긴 답변
- 질문과 관련 없는 내용"""

        return base_info

    def build_intro_prompt(self, request: AnswerRequest, persona: 'CandidatePersona', company_data: Dict, interview_context: Dict = None) -> str:
        """자기소개 질문 전용 프롬프트 빌더 - 1단계 인간적 스토리 전환"""
        print(f"🎭 [DEBUG] build_intro_prompt 호출됨! H.U.M.A.N 프레임워크 적용 중...")
        
        # 페르소나의 핵심 정보 추출
        summary = persona.summary
        name = persona.name
        background = persona.background
        main_strengths = persona.strengths[:2]  # 주요 강점 1-2개
        career_goal = persona.career_goal
        motivation = persona.motivation
        
        # 구체적 경험과 연결할 프로젝트/경험 선별
        key_project = persona.projects[0] if persona.projects else {}
        key_experience = persona.experiences[0] if persona.experiences else {}
        personal_experience = persona.inferred_personal_experiences[0] if persona.inferred_personal_experiences else {}
        
        # 2단계: 직무별 정체성 DNA 추출 및 적용  
        position_key = self._extract_position_key(request.position)
        position_dna = self.position_dna_system.get(position_key, self.position_dna_system["백엔드"])

        prompt = f"""
=== 면접 상황 ===
회사: {company_data.get('name', request.company_id)}
직군: {request.position}
질문 유형: {request.question_type.value} (자기소개)
질문: {request.question_content}
질문 의도: {request.question_intent}

=== 🧬 당신의 직무별 정체성 DNA [{position_key}] ===
**핵심 정체성**: {position_dna['core_identity']}
**고유 성격**: {', '.join(position_dna['personality_traits'])}
**말하기 스타일**: {position_dna['speech_patterns']['tone']}
**동기 DNA**: {position_dna['motivation_dna']}
**성장 서사**: {position_dna['growth_narrative']}
**고유 강점**: {', '.join(position_dna['unique_strengths'])}

=== 당신의 기본 정보 ===
- 이름: {name}
- 한 줄 요약: {summary}
- 경력: {background.get('career_years', '0')}년
- 현재 직책: {background.get('current_position', '지원자')}
- 개발 동기: {motivation}

🚨 절대 기계적 답변 금지! 진짜 {name}처럼 자연스럽게 🚨

=== H.U.M.A.N 프레임워크 ===
**💝 Honesty**: 기술나열 말고 진짜 개인적 동기 → {motivation}
**🌟 Uniqueness**: 나만의 특별한 경험 → {personal_experience.get('experience', '특별한 경험') if personal_experience else '특별한 경험'}
**⚡ Moment**: 구체적이고 생생한 감정과 깨달음 → {personal_experience.get('lesson', '중요한 교훈') if personal_experience else '중요한 교훈'}
**❤️ Affection**: 진짜 열정과 따뜻함 → {career_goal}에 대한 진심
**📖 Narrative**: 과거 → 현재 → 미래로 자연스럽게 연결

=== 답변 가이드 ===
❌ 금지: 딱딱하고 형식적인 기계적 말투
✅ 필수: 진짜 사람이 말하듯 편안하고 자연스럽게

**답변 흐름**: 따뜻한 인사 → 개인적 동기 → 생생한 경험 → 진솔한 미래 비전

**답변 길이**: 50-65초 분량
**핵심**: 진정성 있고 따뜻한 사람의 목소리로

=== 직무 DNA 활용 ===
- 정체성: {position_dna['core_identity']}
- 동기: {position_dna['motivation_dna']}  
- 강점: {', '.join(position_dna['unique_strengths'])}
- 성격: {', '.join(position_dna['personality_traits'])}

활용 정보: 동기({motivation}), 경험({personal_experience.get('experience', '개인적 경험') if personal_experience else '개인적 경험'}), 목표({career_goal}), 강점({', '.join(main_strengths)})
"""
        return prompt.strip()

    def build_motivation_prompt(self, request: AnswerRequest, persona: 'CandidatePersona', company_data: Dict, interview_context: Dict = None) -> str:
        """지원동기 질문 전용 프롬프트 빌더 - 인간적 스토리 전환"""
        
        company_name = company_data.get('name', request.company_id)
        
        # 회사 관련 정보 추출
        company_values = company_data.get('values', [])
        talent_profile = company_data.get('talent_profile', '')
        core_competencies = company_data.get('core_competencies', [])
        business_focus = company_data.get('business_focus', [])
        
        # 페르소나의 관련 정보
        career_goal = persona.career_goal
        strengths = persona.strengths
        motivation = persona.motivation
        key_projects = persona.projects[:2]  # 상위 2개 프로젝트
        personal_experiences = persona.inferred_personal_experiences[:2]
        
        # 직무별 정체성 DNA 추출 및 적용  
        position_key = self._extract_position_key(request.position)
        position_dna = self.position_dna_system.get(position_key, self.position_dna_system["백엔드"])

        prompt = f"""
=== 면접 상황 ===
회사: {company_name}
직군: {request.position}
질문 유형: {request.question_type.value} (지원동기)
질문: {request.question_content}
질문 의도: {request.question_intent}

=== 🧬 당신의 직무별 정체성 DNA [{position_key}] ===
**핵심 정체성**: {position_dna['core_identity']}
**고유 성격**: {', '.join(position_dna['personality_traits'])}
**말하기 스타일**: {position_dna['speech_patterns']['tone']}
**동기 DNA**: {position_dna['motivation_dna']}
**성장 서사**: {position_dna['growth_narrative']}
**고유 강점**: {', '.join(position_dna['unique_strengths'])}

=== {company_name} 회사 정보 ===
**회사 가치관:**
{', '.join(company_values) if company_values else '혁신과 성장을 추구하는 기업'}

**인재상:**
{talent_profile}

**핵심 역량:**
{', '.join(core_competencies)}

**사업 분야:**
{', '.join(business_focus)}

=== 당신의 개인적 동기와 경험 ===
**개발 동기:**
{motivation}

**개인 목표:**
{career_goal}

**의미있는 개인 경험:**"""

        for i, exp in enumerate(personal_experiences, 1):
            prompt += f"""
{i}. [{exp.get('category', '경험')}] {exp.get('experience', '개인적 경험')}
   배운 점: {exp.get('lesson', '깨달음')}"""

        prompt += f"""

**관련 프로젝트 스토리:**"""

        for i, project in enumerate(key_projects, 1):
            prompt += f"""
{i}. **{project.get('name', '프로젝트')}**
   - 도전했던 부분: {', '.join(project.get('challenges', ['어려웠던 경험']))}
   - 달성한 성과: {', '.join(project.get('achievements', ['의미있는 결과']))}
   - 느낀 점: 이 경험을 통해 성장했던 부분"""

        prompt += f"""

=== 🎭 H.U.M.A.N 프레임워크 적용 지원동기 ===

**💝 Honesty (진정성)**: 회사 홈페이지 복사가 아닌 진솔한 개인적 끌림
- 진짜 관심사: {company_name}의 어떤 부분이 내 경험/가치관과 연결되는가?
- 솔직한 감정: 단순히 "좋아서"가 아닌 "왜" 매력적으로 느꼈는지
- 개인적 연결점: 내 개발 동기({motivation})와 회사의 접점

**🌟 Uniqueness (독특함)**: 남들과 다른 나만의 지원 이유
- 특별한 관점: {', '.join(personal_experiences[0].get('experience', '독특한 개인 경험').split()[:5])}... 같은 경험에서 우러나온 관점
- 차별화된 기여: 남들과 다른 나만의 강점({', '.join(strengths[:2])})으로 할 수 있는 기여

**⚡ Moment (순간)**: 회사에 관심을 갖게 된 구체적 순간
- 결정적 순간: 언제, 어떤 계기로 이 회사에 지원하기로 결심했는가?
- 생생한 기억: {key_projects[0].get('name', '프로젝트 경험') if key_projects else '개발 경험'} 중 회사 업무와 연결되는 순간

**❤️ Affection (애정)**: 회사와 업무에 대한 진심어린 애정
- 업무 열정: {company_name}에서 하고 싶은 일에 대한 진짜 설렘
- 회사 애정: 단순한 취업이 아닌 함께 성장하고 싶은 마음

**📖 Narrative (서사)**: 과거 경험 → 현재 지원 → 미래 비전의 일관된 스토리
- 과거: {personal_experiences[0].get('experience', '시작점이 된 경험') if personal_experiences else '개발을 시작한 계기'}
- 현재: 그 경험이 어떻게 {company_name} 지원으로 이어졌는가
- 미래: 회사에서 실현하고 싶은 구체적 비전

=== 직무별 맞춤 {position_key} DNA 적용 ===

**직무 정체성 반영 방법:**
1. **{position_key} 관점**: {position_dna['core_identity']}의 시각으로 회사와 업무 이해
2. **고유 표현 사용**: {', '.join(position_dna['speech_patterns']['key_phrases'][:3])} 등을 자연스럽게 활용
3. **특화된 스토리텔링**: {position_dna['speech_patterns']['storytelling_style']}
4. **동기 연결**: {position_dna['motivation_dna']}와 회사 비전의 자연스러운 연결
5. **성장 패턴**: {position_dna['growth_narrative']} 구조로 지원 이유 서술

**{position_key} 개발자만의 차별화 포인트:**
- 핵심 강점: {', '.join(position_dna['unique_strengths'])}을 회사 업무와 연결
- 고유 성격: {', '.join(position_dna['personality_traits'])}이 회사 문화와 맞는 부분 강조
- {position_key} 전문성을 통해 회사에 기여할 수 있는 구체적 방안
"""
        return prompt.strip()

    def build_hr_prompt(self, request: AnswerRequest, persona: 'CandidatePersona', company_data: Dict, interview_context: Dict = None) -> str:
        """인성 질문 전용 프롬프트 빌더 - H.U.M.A.N 프레임워크 적용"""
        
        # 페르소나의 인성 관련 정보 추출
        personality_traits = persona.personality_traits
        strengths = persona.strengths  
        weaknesses = persona.weaknesses
        experiences = persona.experiences
        motivation = persona.motivation
        personal_experiences = persona.inferred_personal_experiences
        
        # 직무별 DNA 적용
        position_key = self._extract_position_key(request.position)
        position_dna = self.position_dna_system.get(position_key, self.position_dna_system["백엔드"])
        
        # 질문과 관련성 높은 경험 찾기
        question_lower = request.question_content.lower()
        relevant_experiences = []
        
        # 키워드 기반으로 관련 경험 필터링
        for exp in experiences:
            if any(keyword in question_lower for keyword in ['강점', '약점', '어려움', '갈등', '실패', '성장', '도전']):
                relevant_experiences.append(exp)
        
        # 관련 경험이 없으면 모든 경험 포함
        if not relevant_experiences:
            relevant_experiences = experiences[:3]  # 최대 3개
        
        prompt = f"""
=== 면접 상황 ===
회사: {company_data.get('name', request.company_id)}
직군: {request.position}
질문 유형: {request.question_type.value} (인성 질문)
질문: {request.question_content}
질문 의도: {request.question_intent}

=== 당신의 인성 정보 ===
**성격 특성:**
{', '.join(personality_traits)}

**개선하고 싶은 부분 (약점):**
{', '.join(weaknesses)}

=== 활용할 개인적 경험 ==="""

        for i, exp in enumerate(relevant_experiences, 1):
            prompt += f"""
{i}. **[{exp.get('category', '경험')}]** {exp.get('experience', '')}
   - 배운 점: {exp.get('lesson', '')}"""

        prompt += f"""

=== 🧬 직무별 정체성 DNA [{position_key}] ===
**핵심 정체성**: {position_dna['core_identity']}
**고유 성격**: {', '.join(position_dna['personality_traits'])}
**말하기 스타일**: {position_dna['speech_patterns']['tone']}

=== 🎭 H.U.M.A.N 프레임워크 적용 인성 답변 ===

**💝 Honesty (진정성)**: 완벽한 사람 연기가 아닌 진솔한 자기 인식
- 약점 인정: {', '.join(weaknesses)[:1]}와 같은 부분을 솔직하게 인정
- 성장 의지: 이를 개선하기 위한 구체적 노력과 경험
- 개인 동기: {motivation}에서 우러나오는 진짜 가치관

**🌟 Uniqueness (독특함)**: 남들과 다른 나만의 관점과 경험
- 특별한 시각: {position_key} 개발자로서의 독특한 관점
- 개인적 경험: {personal_experiences[0].get('experience', '독특한 개인 경험') if personal_experiences else '차별화된 학습 경험'}
- 고유한 해결법: {', '.join(position_dna['unique_strengths'][:1])}를 활용한 문제 해결

**⚡ Moment (순간)**: 구체적이고 생생한 경험의 순간들
- 전환점 순간: {personal_experiences[0].get('lesson', '인생을 바꾼 깨달음의 순간') if personal_experiences else '성장의 결정적 순간'}
- 감정적 순간: 그때 느꼈던 구체적 감정과 생각
- 행동 변화: 그 순간 이후 달라진 구체적 행동

**❤️ Affection (애정)**: 일과 성장에 대한 진심어린 애정
- 일에 대한 애정: {position_dna['motivation_dna']}
- 성장 열망: 지속적으로 발전하고 싶은 진심
- 팀에 대한 마음: 함께 일하는 사람들에 대한 진심

**📖 Narrative (서사)**: 과거-현재-미래로 이어지는 성장 스토리
- 과거: 어려움이나 실패를 겪었던 시점
- 현재: 그 경험을 통해 배우고 성장한 현재 모습  
- 미래: 앞으로 더 발전하고 싶은 방향

=== {position_key} DNA 기반 인성 답변 스타일 ===

당신의 성격 특성({', '.join(personality_traits)})과 {position_key} DNA를 바탕으로 
가장 자연스러운 방식으로 답변하세요:

**감정 중심 스타일**: 내면의 감정과 성찰에 집중
- 핵심: 경험 속에서 느꼈던 감정과 그로 인한 깊은 성찰 강조
- 적합한 성격: 감성적, 내성적, 성찰적인 특성을 가진 경우

**논리 중심 스타일**: 체계적이고 분석적인 접근
- 핵심: 상황 → 원인 분석 → 해결책 → 결과의 논리적 구조
- 강조점: 구체적 데이터나 방법론, 체계적인 개선 계획
- 적합한 성격: 논리적, 계획적, 분석적인 특성을 가진 경우

**경험 중심 스타일**: 생생한 스토리텔링 활용
- 핵심: 개인적 경험을 중심으로 한 생동감 있는 이야기 전개
- 강조점: 구체적 상황 묘사와 그 속에서의 깨달음
- 적합한 성격: 사교적, 표현력이 풍부한, 스토리텔링을 좋아하는 특성

=== 필수 포함 요소 ===

**모든 스타일 공통:**
1. **솔직한 자기 인식**: 약점이라면 {', '.join(weaknesses)} 중 관련된 내용을 솔직하게 인정
2. **구체적 경험 연결**: 위의 개인적 경험 중 관련성 높은 사례 활용
3. **성장 과정**: 그 경험을 통한 배움과 현재의 개선 노력
4. **미래 지향**: 지속적인 발전 의지 표현
"""
        return prompt.strip()

    def build_tech_prompt(self, request: AnswerRequest, persona: 'CandidatePersona', company_data: Dict, interview_context: Dict = None) -> str:
        """기술 질문 전용 프롬프트 빌더 - H.U.M.A.N 프레임워크 적용"""
        
        # 페르소나의 기술 관련 정보 추출 + H.U.M.A.N 요소
        technical_skills = persona.technical_skills
        projects = persona.projects
        experiences = persona.experiences
        strengths = persona.strengths
        
        # 직무별 정체성 적용
        position_key = self._extract_position_key(request.position)
        position_dna = self.position_dna_system.get(position_key, self.position_dna_system["백엔드"])
        
        # 기술 질문과 관련된 프로젝트 찾기
        question_lower = request.question_content.lower()
        relevant_projects = []
        
        for project in projects:
            # 프로젝트의 기술 스택이나 설명에서 질문과 관련된 키워드 찾기
            project_tech = ' '.join(project.get('tech_stack', [])).lower()
            project_desc = project.get('description', '').lower()
            
            if any(tech in project_tech or tech in project_desc 
                   for tech in ['python', 'java', 'react', 'node', 'database', 'api']):
                relevant_projects.append(project)
        
        # 관련 프로젝트가 없으면 모든 프로젝트 포함
        if not relevant_projects:
            relevant_projects = projects[:2]
        
        prompt = f"""
=== 면접 상황 ===
회사: {company_data.get('name', request.company_id)}
직군: {request.position}
질문 유형: {request.question_type.value} (기술 질문)
질문: {request.question_content}
질문 의도: {request.question_intent}

=== 당신의 기술적 배경 ===
**보유 기술:**
{', '.join(technical_skills)}

**관련 프로젝트 경험:**"""

        for i, project in enumerate(relevant_projects, 1):
            prompt += f"""
{i}. **{project.get('name', '프로젝트')}**
   - 사용 기술: {', '.join(project.get('tech_stack', []))}
   - 역할: {project.get('role', '개발자')}
   - 주요 성과: {', '.join(project.get('achievements', []))[:100]}...
   - 기술적 도전: {', '.join(project.get('challenges', []))[:100]}..."""

        prompt += f"""

=== 🧬 {position_key} 개발자 정체성 DNA ===
**핵심 정체성**: {position_dna['core_identity']}
**기술적 접근법**: {position_dna['technical_approach'] if 'technical_approach' in position_dna else '체계적이고 안정적인 기술 구현'}
**고유 강점**: {', '.join(position_dna['unique_strengths'])}

=== 🎭 H.U.M.A.N 프레임워크 적용 기술 답변 ===

**💝 Honesty (진정성)**: 과장 없는 솔직한 기술 경험
- 실제 경험: 직접 해본 것과 배우고 있는 것을 명확히 구분
- 한계 인정: 모르는 부분이나 어려웠던 점을 솔직하게 인정
- 학습 과정: 기술을 배워가는 과정에서의 진짜 어려움과 극복

**🌟 Uniqueness (독특함)**: 남들과 다른 나만의 기술적 접근
- 특별한 관점: {position_key}로서 문제를 바라보는 독특한 시각
- 차별화된 해결법: {', '.join(position_dna['unique_strengths'][:1])}를 활용한 기술적 해결책
- 창의적 구현: 기존과 다른 나만의 방식으로 문제 해결한 경험

**⚡ Moment (순간)**: 기술적 깨달음이나 돌파구를 찾은 구체적 순간
- 문제 해결 순간: 막혔던 기술적 문제를 해결한 그 순간의 경험
- 학습의 순간: 새로운 기술을 이해하게 된 결정적 순간
- 성장의 순간: 기술적으로 한 단계 성장했다고 느꼈던 경험

**❤️ Affection (애정)**: 기술과 개발에 대한 진심어린 열정
- 기술 사랑: 특정 기술이나 개발 자체에 대한 진짜 애정
- 품질 추구: 좋은 코드, 좋은 아키텍처에 대한 진심
- 지속적 학습: 새로운 기술을 배우고 싶은 진심어린 욕구

**📖 Narrative (서사)**: 기술 학습과 성장의 일관된 스토리
- 과거: 처음 이 기술을 접했을 때의 상황과 동기
- 현재: 그 기술을 어떻게 발전시켜왔는지의 과정
- 미래: 이 기술을 어떻게 더 발전시키고 활용하고 싶은지

=== {position_key} 개발자로서의 기술적 정체성 ===

**{position_key} 관점에서의 기술 답변:**
1. **전문성 강조**: {position_dna['core_identity']}로서의 깊이 있는 기술 이해
2. **실무 중심**: 이론보다는 실제 프로젝트에서의 적용 경험 중심
3. **문제 해결**: {', '.join(position_dna['unique_strengths'])}를 통한 기술적 문제 해결
4. **지속적 학습**: {position_key} 개발자로서의 기술 학습 여정

**기술 설명 시 포함할 요소:**
- 해당 기술을 선택한 이유와 배경
- 실제 구현 과정에서의 고민과 해결책
- 다른 기술 대안과의 비교 및 선택 근거
- 프로젝트나 팀에 미친 구체적 영향
- 그 경험을 통해 배운 점과 개선 방향

{position_key} 개발자로서의 정체성과 H.U.M.A.N 프레임워크를 바탕으로 
기술적 전문성을 갖추면서도 인간적인 매력이 느껴지는 답변을 만들어주세요.
"""
        return prompt.strip()

    def build_collaboration_prompt(self, request: AnswerRequest, persona: 'CandidatePersona', company_data: Dict, interview_context: Dict = None) -> str:
        """협업 질문 전용 프롬프트 빌더 - H.U.M.A.N 프레임워크 적용"""
        
        # 페르소나의 협업 관련 정보
        experiences = persona.experiences
        strengths = persona.strengths
        personality_traits = persona.personality_traits
        projects = persona.projects
        
        # 직무별 DNA 적용
        position_key = self._extract_position_key(request.position)
        position_dna = self.position_dna_system.get(position_key, self.position_dna_system["백엔드"])
        
        # 협업 관련 경험 필터링
        collaboration_experiences = []
        for exp in experiences:
            exp_text = exp.get('experience', '').lower()
            if any(keyword in exp_text for keyword in ['팀', '협업', '소통', '갈등', '리더', '프로젝트']):
                collaboration_experiences.append(exp)
        
        if not collaboration_experiences:
            collaboration_experiences = experiences[:2]
        
        # 팀 프로젝트 경험
        team_projects = [p for p in projects if p.get('team_size', 1) > 1][:2]
        
        prompt = f"""
=== 면접 상황 ===
회사: {company_data.get('name', request.company_id)}
직군: {request.position}
질문 유형: {request.question_type.value} (협업 질문)
질문: {request.question_content}
질문 의도: {request.question_intent}

=== 당신의 협업 관련 배경 ===
**성격 특성 (협업 관련):**
{', '.join([trait for trait in personality_traits if any(keyword in trait.lower() for keyword in ['소통', '협력', '리더', '팀', '배려'])])}

**협업 경험:**"""

        for i, exp in enumerate(collaboration_experiences, 1):
            prompt += f"""
{i}. **[{exp.get('category', '경험')}]** {exp.get('experience', '')}
   - 배운 점: {exp.get('lesson', '')}"""

        prompt += f"""

**팀 프로젝트 경험:**"""

        for i, project in enumerate(team_projects, 1):
            prompt += f"""
{i}. **{project.get('name', '팀 프로젝트')}**
   - 팀 규모: {project.get('team_size', '팀')}명
   - 역할: {project.get('role', '팀원')}
   - 협업 도구: {', '.join(project.get('collaboration_tools', ['일반적인 협업 도구']))}
   - 성과: {', '.join(project.get('achievements', []))[:100]}..."""

        prompt += f"""

=== 🧬 {position_key} 개발자의 협업 DNA ===
**핵심 정체성**: {position_dna['core_identity']}
**협업 스타일**: {position_dna.get('collaboration_style', '체계적이고 책임감 있는 협업')}
**커뮤니케이션**: {position_dna['speech_patterns']['tone']}

=== 🎭 H.U.M.A.N 프레임워크 적용 협업 답변 ===

**💝 Honesty (진정성)**: 완벽한 팀플레이어 연기가 아닌 솔직한 협업 경험
- 어려웠던 점: 협업 과정에서 실제로 겪었던 어려움이나 갈등
- 개인적 성향: 협업에서의 나의 장단점을 솔직하게 인정
- 성장 과정: 협업 능력이 어떻게 발전해왔는지의 진실한 여정

**🌟 Uniqueness (독특함)**: 남들과 다른 나만의 협업 방식
- 특별한 접근: {position_key} 개발자로서의 독특한 협업 관점
- 고유한 기여: {', '.join(position_dna['unique_strengths'][:1])}를 활용한 팀 기여 방식
- 차별화된 소통: 나만의 특별한 커뮤니케이션 스타일

**⚡ Moment (순간)**: 협업에서의 결정적이고 구체적인 순간들
- 갈등 해결 순간: 팀 내 갈등이나 문제를 해결한 구체적 순간
- 성과 창출 순간: 팀워크로 큰 성과를 이뤄낸 그 순간
- 깨달음의 순간: 협업의 중요성을 실감한 결정적 경험

**❤️ Affection (애정)**: 팀과 협업에 대한 진심어린 애정
- 팀에 대한 마음: 함께 일하는 동료들에 대한 진심어린 마음
- 협업의 가치: 혼자가 아닌 함께 할 때의 시너지에 대한 믿음
- 성장 욕구: 팀과 함께 더 나아지고 싶은 진심

**📖 Narrative (서사)**: 협업 능력의 성장 스토리
- 과거: 처음 팀 작업을 했을 때의 어색함이나 어려움
- 현재: 그 경험들을 통해 발전한 현재의 협업 능력
- 미래: 앞으로 팀에서 어떤 역할을 하고 싶은지의 비전

=== {position_key} 협업 스타일 가이드 ===

**{position_key} 개발자로서의 협업 정체성:**
1. **전문성 기반 기여**: {position_dna['core_identity']}로서 팀에 제공하는 가치
2. **체계적 소통**: {position_key}다운 논리적이고 명확한 커뮤니케이션
3. **책임감**: 맡은 부분에 대한 확실한 책임감과 완수 의지
4. **학습 자세**: 다른 분야 동료들로부터 배우려는 열린 마음

**협업 경험 설명 시 포함할 요소:**
- 구체적인 상황과 배경 설명
- 그때 내가 취한 구체적 행동과 이유
- 다른 팀원들과의 상호작용 과정
- 그 경험을 통해 배운 점과 개선한 점
- 팀과 프로젝트에 미친 실제 영향

{position_key} 개발자로서의 전문성을 바탕으로 하되, 
인간적인 따뜻함과 협업 정신이 느껴지는 답변을 만들어주세요.
"""
        return prompt.strip()

    def build_default_prompt(self, request: AnswerRequest, persona: 'CandidatePersona', company_data: Dict, interview_context: Dict = None) -> str:
        """기본/기타 질문 전용 프롬프트 빌더 - 4단계 H.U.M.A.N 프레임워크 전면 적용"""
        
        prompt = f"""
=== 면접 상황 ===
회사: {company_data.get('name', request.company_id)}
직군: {request.position}
질문 유형: {request.question_type.value}
질문: {request.question_content}
질문 의도: {request.question_intent}

=== 당신의 페르소나 정보 ===
**기본 배경:**
- 경력: {persona.background.get('career_years', '0')}년
- 현재 직책: {persona.background.get('current_position', '지원자')}
- 성격 특성: {', '.join(persona.personality_traits)}

**주요 강점:**
{', '.join(persona.strengths)}

**기술 스킬:**
{', '.join(persona.technical_skills)}

**주요 프로젝트:**"""

        for i, project in enumerate(persona.projects[:2], 1):
            prompt += f"""
{i}. {project.get('name', '프로젝트')}: {project.get('description', '')}
   - 역할: {project.get('role', '개발자')}
   - 성과: {', '.join(project.get('achievements', []))}"""

        prompt += f"""

**개인적 경험:**"""

        for i, exp in enumerate(persona.experiences[:2], 1):
            prompt += f"""
{i}. [{exp.get('category', '경험')}] {exp.get('experience', '')}
   - 배운 점: {exp.get('lesson', '')}"""

        prompt += f"""

=== 답변 가이드라인 ===

**질문 분석 우선:**
1. 질문의 핵심 의도 파악: {request.question_intent}
2. 요구되는 답변의 성격 (경험, 의견, 계획 등) 판단
3. 활용할 페르소나 정보 선별

**답변 구성:**
- **도입**: 질문에 대한 직접적인 응답 시작
- **본론**: 관련된 개인 경험이나 견해를 구체적 사례와 함께 설명
- **결론**: 향후 계획이나 학습 의지, 회사와의 연결점 표현

**답변 스타일:**
- 질문의 성격에 맞는 톤 조절 (진지한 주제는 신중하게, 일반적 주제는 자연스럽게)
- 개인적 경험과 견해를 바탕으로 한 진솔한 답변
- 회사와 직무에 대한 이해를 바탕으로 한 연결고리 포함

**답변 길이**: 30-50초 분량 (180-280자)
**답변 톤**: 질문의 성격과 상황에 맞는 적절한 전문성과 친근함

=== 주의사항 ===
- 질문 유형이 명확하지 않은 경우, 가장 관련성 높은 경험이나 강점을 활용
- 지나치게 복잡하거나 완벽한 답변보다는 솔직하고 자연스러운 답변
- 질문의 숨은 의도를 파악하여 면접관이 원하는 정보 제공
- 모르는 부분이 있다면 솔직히 인정하되, 학습 의지나 해결 방안 제시
"""
        return prompt.strip()

    def _get_ai_name(self, llm_provider: LLMProvider) -> str:
        """LLM 프로바이더에 따른 AI 이름 결정"""
        name_mapping = {
            LLMProvider.OPENAI_GPT35: "춘식이",
            LLMProvider.OPENAI_GPT4: "춘식이", 
            LLMProvider.OPENAI_GPT4O: "춘식이",
            LLMProvider.OPENAI_GPT4O_MINI: "춘식이",
            LLMProvider.GOOGLE_GEMINI_PRO: "제미니",
            LLMProvider.GOOGLE_GEMINI_FLASH: "제미니",
            LLMProvider.KT_BELIEF: "믿음이"
        }
        return name_mapping.get(llm_provider, "춘식이")
    
    def _initialize_position_dna_system(self) -> Dict[str, Dict[str, Any]]:
        """직무별 고유 정체성 DNA 시스템 구축"""
        return {
            "프론트엔드": {
                "core_identity": "사용자 경험을 최우선으로 생각하는 UI/UX 크리에이터",
                "personality_traits": ["섬세함", "사용자 중심적 사고", "미적 감각", "완벽주의 성향"],
                "speech_patterns": {
                    "key_phrases": ["사용자 입장에서", "직관적인 인터페이스", "사용성 개선", "반응형 디자인"],
                    "tone": "친근하고 섬세하며, 사용자 경험에 대한 열정적 어조",
                    "storytelling_style": "시각적이고 구체적인 사용자 시나리오 중심"
                },
                "motivation_dna": "복잡한 기술을 사용자가 쉽고 즐겁게 사용할 수 있도록 만드는 것",
                "growth_narrative": "개발 → UI/UX 관심 → 사용자 피드백 수집 → 더 나은 경험 설계",
                "unique_strengths": ["사용자 관점에서의 문제 발견", "디자인-개발 간 원활한 소통", "접근성 고려"]
            },
            "백엔드": {
                "core_identity": "안정적이고 확장 가능한 시스템의 설계자",
                "personality_traits": ["논리적 사고", "시스템적 접근", "안정성 추구", "문제 해결 집착"],
                "speech_patterns": {
                    "key_phrases": ["시스템 안정성", "확장 가능한 아키텍처", "성능 최적화", "데이터 일관성"],
                    "tone": "차분하고 논리적이며, 기술적 깊이를 보여주는 어조",
                    "storytelling_style": "문제-분석-해결-결과의 체계적 서술"
                },
                "motivation_dna": "보이지 않는 곳에서 서비스를 안정적으로 지탱하는 든든한 기반 구축",
                "growth_narrative": "개발 → 성능 이슈 경험 → 아키텍처 학습 → 안정적 시스템 구축",
                "unique_strengths": ["복잡한 시스템 설계 능력", "병목 지점 발견과 최적화", "장애 대응 경험"]
            },
            "기획": {
                "core_identity": "사용자와 비즈니스를 연결하는 전략적 사고자",
                "personality_traits": ["전략적 사고", "소통 능력", "데이터 기반 판단", "사용자 공감 능력"],
                "speech_patterns": {
                    "key_phrases": ["사용자 니즈", "비즈니스 임팩트", "데이터 기반 의사결정", "사용자 여정"],
                    "tone": "논리적이면서도 공감적이며, 전략적 통찰력을 보여주는 어조",
                    "storytelling_style": "사용자 관점과 비즈니스 관점을 균형있게 연결"
                },
                "motivation_dna": "사용자의 진짜 문제를 발견하고 비즈니스 가치로 연결시키는 것",
                "growth_narrative": "사용자 관찰 → 문제 발견 → 솔루션 기획 → 임팩트 검증",
                "unique_strengths": ["사용자 니즈 파악", "이해관계자 간 조율", "데이터 분석과 인사이트 도출"]
            },
            "AI": {
                "core_identity": "데이터와 알고리즘으로 새로운 가능성을 탐구하는 연구자",
                "personality_traits": ["호기심 많음", "실험 정신", "논리적 추론", "지속적 학습 의지"],
                "speech_patterns": {
                    "key_phrases": ["모델 성능 개선", "데이터 품질", "실험과 검증", "AI 윤리"],
                    "tone": "탐구적이고 열정적이며, 기술적 깊이와 가능성에 대한 흥미",
                    "storytelling_style": "실험-결과-개선의 반복적 학습 과정 중심"
                },
                "motivation_dna": "AI 기술로 사람들의 일상과 업무를 더 스마트하게 만드는 것",
                "growth_narrative": "AI 접촉 → 모델 실험 → 성능 개선 → 실제 문제 해결",
                "unique_strengths": ["복잡한 데이터 패턴 발견", "모델 최적화 경험", "AI 기술의 실용적 적용"]
            },
            "데이터사이언스": {
                "core_identity": "데이터 속에서 비즈니스 인사이트를 발굴하는 탐정",
                "personality_traits": ["분석적 사고", "패턴 인식 능력", "비즈니스 감각", "시각화 센스"],
                "speech_patterns": {
                    "key_phrases": ["데이터 기반 인사이트", "비즈니스 임팩트", "가설 검증", "의사결정 지원"],
                    "tone": "분석적이면서도 비즈니스 친화적이며, 데이터로 스토리를 만드는 어조",
                    "storytelling_style": "데이터 발견-분석-인사이트-액션의 탐정 같은 서술"
                },
                "motivation_dna": "복잡한 데이터 속에서 비즈니스 성장의 열쇠를 찾아내는 것",
                "growth_narrative": "데이터 호기심 → 분석 도구 학습 → 인사이트 발견 → 비즈니스 기여",
                "unique_strengths": ["복잡한 데이터 해석", "비즈니스 문제 해결", "인사이트 커뮤니케이션"]
            }
        }
    
    def _extract_position_key(self, position_title: str) -> str:
        """직책명에서 직무별 DNA 키 추출"""
        position_lower = position_title.lower().replace(" ", "")
        
        # 프론트엔드 키워드
        if any(keyword in position_lower for keyword in ["프론트", "frontend", "fe", "ui", "웹개발"]):
            return "프론트엔드"
        
        # 백엔드 키워드  
        elif any(keyword in position_lower for keyword in ["백엔드", "backend", "be", "서버", "api"]):
            return "백엔드"
        
        # 기획 키워드
        elif any(keyword in position_lower for keyword in ["기획", "pm", "product", "서비스기획", "전략기획"]):
            return "기획"
        
        # AI 키워드
        elif any(keyword in position_lower for keyword in ["ai", "인공지능", "머신러닝", "ml", "딥러닝"]):
            return "AI"
        
        # 데이터사이언스 키워드
        elif any(keyword in position_lower for keyword in ["데이터", "data", "분석", "ds", "사이언티스트"]):
            return "데이터사이언스"
        
        # 기본값은 백엔드
        else:
            return "백엔드"
    
    def _initialize_narrative_system(self) -> Dict[str, Dict[str, Any]]:
        """3단계: 5단계 면접 서사 연결 시스템 구축"""
        return {
            "narrative_stages": {
                "1_intro": {
                    "stage_name": "도입 (자기소개)",
                    "narrative_role": "주인공 등장 - 나는 누구인가?",
                    "key_elements": ["개발 시작 계기", "핵심 정체성 확립", "현재까지의 여정"],
                    "connection_seeds": ["동기_연결점", "역량_힌트", "성장_방향성"],
                    "storytelling_focus": "개인적 동기와 정체성 중심의 진솔한 시작"
                },
                "2_motivation": {
                    "stage_name": "동기 (지원동기)", 
                    "narrative_role": "여정의 목적지 - 왜 이 회사인가?",
                    "key_elements": ["개인 경험과 회사 연결", "미래 비전 제시", "기여 의지"],
                    "connection_seeds": ["도입_연결", "역량_근거", "협업_가치관"],
                    "storytelling_focus": "과거 경험이 현재 지원으로 자연스럽게 이어지는 필연성"
                },
                "3_competency": {
                    "stage_name": "역량 (기술/인성)",
                    "narrative_role": "능력 증명 - 무엇을 할 수 있는가?", 
                    "key_elements": ["구체적 경험과 성과", "문제해결 과정", "학습과 성장"],
                    "connection_seeds": ["동기_구현", "협업_경험", "비전_실현"],
                    "storytelling_focus": "도입과 동기에서 언급한 역량을 구체적 사례로 입증"
                },
                "4_collaboration": {
                    "stage_name": "협업 (팀워크)",
                    "narrative_role": "관계 구축 - 어떻게 함께 일하는가?",
                    "key_elements": ["팀 내 역할과 기여", "갈등 해결 경험", "상호 성장"], 
                    "connection_seeds": ["역량_활용", "가치관_실현", "비전_공유"],
                    "storytelling_focus": "개인 역량이 팀 성과로 이어지는 협업 철학과 경험"
                },
                "5_vision": {
                    "stage_name": "비전 (미래 계획)",
                    "narrative_role": "여정의 연속 - 앞으로 어디로 갈 것인가?",
                    "key_elements": ["장기 목표와 계획", "회사에서의 성장", "기여 방안"],
                    "connection_seeds": ["전체_스토리_완성", "일관성_유지", "미래_다짐"],
                    "storytelling_focus": "지금까지의 모든 이야기가 미래 비전으로 수렴되는 완결성"
                }
            },
            "connection_strategies": {
                "thread_weaving": {
                    "description": "면접 전체를 관통하는 핵심 테마 설정",
                    "techniques": [
                        "개인 동기 키워드 반복 활용",
                        "핵심 가치관의 일관된 표현", 
                        "성장 스토리의 단계적 전개"
                    ]
                },
                "callback_system": {
                    "description": "이전 답변 내용을 자연스럽게 언급하여 연결성 강화",
                    "techniques": [
                        "앞서 말씀드린 ~처럼",
                        "제가 ~에서 경험했듯이",
                        "이는 처음에 언급한 ~와 연결됩니다"
                    ]
                },
                "foreshadowing": {
                    "description": "다음 질문에서 다룰 내용을 미리 암시",
                    "techniques": [
                        "이런 경험을 통해 팀워크의 중요성도 깨달았는데",
                        "기술적 성장뿐만 아니라 협업 능력도",
                        "앞으로는 이런 방향으로 발전하고 싶어서"
                    ]
                }
            },
            "consistency_framework": {
                "character_consistency": {
                    "personality": "면접 전반에 걸쳐 일관된 성격과 가치관 유지",
                    "speech_pattern": "말하는 스타일과 어조의 일관성",
                    "core_values": "핵심 가치관과 동기의 일관된 표현"
                },
                "story_consistency": {
                    "timeline": "시간순 일관성과 논리적 연결",
                    "experience_reference": "동일한 경험을 다룰 때 일관된 서술",
                    "growth_arc": "성장 과정의 자연스러운 발전 단계"
                }
            }
        }