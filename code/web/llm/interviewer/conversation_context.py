#!/usr/bin/env python3
"""
대화 컨텍스트 관리 시스템
질문/답변 중복 방지 및 유기적 소통을 위한 핵심 모듈
"""

import json
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from collections import defaultdict

from ..shared.models import QuestionType, QuestionAnswer

class TopicCategory(Enum):
    """주제 카테고리"""
    PERSONAL_BACKGROUND = "개인 배경"
    TECHNICAL_SKILLS = "기술 역량"
    PROJECT_EXPERIENCE = "프로젝트 경험"
    TEAM_COLLABORATION = "팀 협업"
    PROBLEM_SOLVING = "문제 해결"
    CAREER_GOALS = "커리어 목표"
    COMPANY_CULTURE = "회사 문화"
    LEADERSHIP = "리더십"
    LEARNING_ABILITY = "학습 능력"
    COMMUNICATION = "소통 능력"

@dataclass
class TopicTracker:
    """주제 추적기"""
    category: TopicCategory
    keywords: Set[str]
    questions_asked: List[str]
    answers_given: List[str]
    coverage_score: float = 0.0  # 0.0 ~ 1.0
    
    def add_question(self, question: str):
        """질문 추가"""
        self.questions_asked.append(question)
        
    def add_answer(self, answer: str):
        """답변 추가"""
        self.answers_given.append(answer)
        self._update_coverage_score()
    
    def _update_coverage_score(self):
        """커버리지 점수 업데이트"""
        if not self.answers_given:
            self.coverage_score = 0.0
            return
        
        # 답변에서 키워드 매칭률 계산
        total_keywords = len(self.keywords)
        if total_keywords == 0:
            self.coverage_score = 0.0
            return
        
        matched_keywords = 0
        combined_answers = " ".join(self.answers_given).lower()
        
        for keyword in self.keywords:
            if keyword.lower() in combined_answers:
                matched_keywords += 1
        
        self.coverage_score = matched_keywords / total_keywords

@dataclass
class ConversationMemory:
    """대화 기억 저장소"""
    mentioned_projects: Set[str] = None
    mentioned_technologies: Set[str] = None
    mentioned_experiences: Set[str] = None
    personality_traits: Set[str] = None
    achievements: Set[str] = None
    
    def __post_init__(self):
        if self.mentioned_projects is None:
            self.mentioned_projects = set()
        if self.mentioned_technologies is None:
            self.mentioned_technologies = set()
        if self.mentioned_experiences is None:
            self.mentioned_experiences = set()
        if self.personality_traits is None:
            self.personality_traits = set()
        if self.achievements is None:
            self.achievements = set()

class QuestionDuplicateDetector:
    """질문 중복 감지기 (의미적 유사도 기반)"""
    
    def __init__(self):
        # HR과 협업 질문 타입 명확하게 구분
        self.question_patterns = {
            QuestionType.INTRO: [
                "자기소개", "본인", "소개", "배경", "프로필"
            ],
            QuestionType.MOTIVATION: [
                "지원동기", "동기", "이유", "관심", "선택"
            ],
            QuestionType.HR: [
                # 개인 인성, 가치관, 성격 중심
                "성격", "가치관", "인생관", "철학", "신념", "원칙", 
                "인생목표", "꿈", "비전", "동기부여", "영감", "롤모델",
                "성장과정", "변화", "깨달음", "반성", "후회", "자랑스러운",
                "개인적특성", "습관", "취미", "관심사"
            ],
            QuestionType.TECH: [
                "기술", "개발", "언어", "프레임워크", "아키텍처", "설계", "구현"
            ],
            QuestionType.COLLABORATION: [
                # 협업, 팀워크, 소통 능력 중심
                "협업", "팀워크", "소통", "커뮤니케이션", "대화", "설득",
                "갈등해결", "조율", "중재", "리더십", "팔로워십", "역할분담",
                "회의", "브레인스토밍", "의견조율", "합의", "협력", "동료",
                "상사", "부하", "고객응대", "이해관계자"
            ],
            QuestionType.FOLLOWUP: [
                "구체적", "자세히", "예시", "경험", "사례", "과정"
            ]
        }
        
        # 질문 의도별 분류 (의미적 유사도 검사용)
        self.question_intents = {
            "개인가치관": ["가치관", "인생관", "철학", "신념", "원칙", "중요하게"],
            "성격특성": ["성격", "특성", "스타일", "방식", "접근법"],
            "성장경험": ["성장", "변화", "발전", "깨달음", "배움", "학습"],
            "목표비전": ["목표", "꿈", "비전", "계획", "미래", "지향"],
            "팀워크": ["팀", "협업", "함께", "공동", "협력"],
            "소통능력": ["소통", "대화", "설명", "표현", "전달", "공유"],
            "갈등해결": ["갈등", "문제", "해결", "조율", "중재", "극복"],
            "리더십": ["리더", "이끌", "지도", "가이드", "멘토", "책임"]
        }
    
    def extract_keywords(self, question: str) -> Set[str]:
        """질문에서 키워드 추출"""
        keywords = set()
        question_lower = question.lower()
        
        # 기본 키워드 추출
        for question_type, patterns in self.question_patterns.items():
            for pattern in patterns:
                if pattern in question_lower:
                    keywords.add(pattern)
        
        # 추가 키워드 추출 (정규식 사용)
        # 기술 관련 키워드
        tech_keywords = re.findall(r'(파이썬|자바|스프링|리액트|도커|쿠버네티스|AWS|데이터베이스|API)', question_lower)
        keywords.update(tech_keywords)
        
        # 동작 관련 키워드  
        action_keywords = re.findall(r'(개발|구현|설계|운영|관리|해결|개선|최적화)', question_lower)
        keywords.update(action_keywords)
        
        return keywords
    
    def extract_question_intent(self, question: str) -> Set[str]:
        """질문의 의도 추출"""
        intents = set()
        question_lower = question.lower()
        
        for intent_type, keywords in self.question_intents.items():
            for keyword in keywords:
                if keyword in question_lower:
                    intents.add(intent_type)
                    break  # 하나라도 매칭되면 해당 의도로 분류
        
        return intents
    
    def calculate_semantic_similarity(self, question1: str, question2: str) -> float:
        """두 질문 간 의미적 유사도 계산"""
        # 1. 키워드 기반 유사도
        keywords1 = self.extract_keywords(question1)
        keywords2 = self.extract_keywords(question2)
        
        keyword_similarity = 0.0
        if keywords1 or keywords2:
            intersection = keywords1.intersection(keywords2)
            union = keywords1.union(keywords2)
            keyword_similarity = len(intersection) / len(union) if union else 0.0
        
        # 2. 의도 기반 유사도
        intents1 = self.extract_question_intent(question1)
        intents2 = self.extract_question_intent(question2)
        
        intent_similarity = 0.0
        if intents1 or intents2:
            intent_intersection = intents1.intersection(intents2)
            intent_union = intents1.union(intents2)
            intent_similarity = len(intent_intersection) / len(intent_union) if intent_union else 0.0
        
        # 3. 구조적 유사도 (질문 형태)
        structure_similarity = self._calculate_structure_similarity(question1, question2)
        
        # 가중 평균 (의도 60%, 키워드 30%, 구조 10%)
        total_similarity = (
            intent_similarity * 0.6 + 
            keyword_similarity * 0.3 + 
            structure_similarity * 0.1
        )
        
        return total_similarity
    
    def _calculate_structure_similarity(self, question1: str, question2: str) -> float:
        """질문 구조적 유사도 계산"""
        # 질문 유형 패턴 분석
        patterns = [
            r"어떤.*있나요", r"어떻게.*하나요", r"무엇.*인가요", 
            r"왜.*하나요", r"언제.*하나요", r"누구.*인가요",
            r"설명.*주세요", r"말씀.*주세요", r"얘기.*주세요",
            r"생각.*어떤가요", r"어떤.*생각", r"의견.*어떤가요"
        ]
        
        import re
        pattern1_matches = set()
        pattern2_matches = set()
        
        for pattern in patterns:
            if re.search(pattern, question1):
                pattern1_matches.add(pattern)
            if re.search(pattern, question2):
                pattern2_matches.add(pattern)
        
        if not pattern1_matches and not pattern2_matches:
            return 0.0
        
        intersection = pattern1_matches.intersection(pattern2_matches)
        union = pattern1_matches.union(pattern2_matches)
        
        return len(intersection) / len(union) if union else 0.0
    
    def calculate_similarity(self, question1: str, question2: str) -> float:
        """두 질문 간 유사도 계산 (향상된 버전)"""
        return self.calculate_semantic_similarity(question1, question2)
    
    def is_duplicate(self, new_question: str, previous_questions: List[str], threshold: float = 0.5) -> Tuple[bool, Optional[str]]:
        """새로운 질문이 중복인지 확인 (의미적 유사도 기반)"""
        if not previous_questions:
            return False, None
        
        max_similarity = 0.0
        most_similar_question = None
        
        for prev_question in previous_questions:
            similarity = self.calculate_similarity(new_question, prev_question)
            
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_question = prev_question
            
            # 높은 유사도면 즉시 중복 판정
            if similarity >= threshold:
                return True, prev_question
        
        # 의도가 완전히 같은 경우 추가 검사
        new_intents = self.extract_question_intent(new_question)
        if new_intents:
            for prev_question in previous_questions[-3:]:  # 최근 3개 질문만 검사
                prev_intents = self.extract_question_intent(prev_question)
                if new_intents == prev_intents and len(new_intents) > 0:
                    # 의도가 완전히 같으면 낮은 임계값 적용
                    similarity = self.calculate_similarity(new_question, prev_question)
                    if similarity >= 0.3:  # 낮은 임계값
                        return True, prev_question
        
        return False, None
    
    def get_duplicate_analysis(self, new_question: str, previous_questions: List[str]) -> Dict[str, Any]:
        """중복 분석 상세 정보 제공"""
        if not previous_questions:
            return {"is_duplicate": False, "analysis": "이전 질문 없음"}
        
        analysis = {
            "is_duplicate": False,
            "max_similarity": 0.0,
            "similar_question": None,
            "similarity_breakdown": {},
            "intent_overlap": [],
            "recommendations": []
        }
        
        new_intents = self.extract_question_intent(new_question)
        
        for prev_question in previous_questions:
            similarity = self.calculate_semantic_similarity(new_question, prev_question)
            
            if similarity > analysis["max_similarity"]:
                analysis["max_similarity"] = similarity
                analysis["similar_question"] = prev_question
                
                # 유사도 세부 분석
                keywords1 = self.extract_keywords(new_question)
                keywords2 = self.extract_keywords(prev_question)
                intents1 = new_intents
                intents2 = self.extract_question_intent(prev_question)
                
                analysis["similarity_breakdown"] = {
                    "keyword_overlap": list(keywords1.intersection(keywords2)),
                    "intent_overlap": list(intents1.intersection(intents2)),
                    "structural_similarity": self._calculate_structure_similarity(new_question, prev_question)
                }
        
        # 중복 여부 판정
        is_duplicate, similar_q = self.is_duplicate(new_question, previous_questions)
        analysis["is_duplicate"] = is_duplicate
        
        # 개선 권장사항
        if analysis["max_similarity"] > 0.3:
            if analysis["similarity_breakdown"]["intent_overlap"]:
                analysis["recommendations"].append("질문 의도를 다른 각도로 접근해보세요")
            if analysis["similarity_breakdown"]["keyword_overlap"]:
                analysis["recommendations"].append(f"다음 키워드를 피해보세요: {', '.join(analysis['similarity_breakdown']['keyword_overlap'])}")
        
        return analysis

class ConversationContext:
    """대화 컨텍스트 관리자"""
    
    def __init__(self, company_id: str, position: str, persona_name: str):
        self.company_id = company_id
        self.position = position
        self.persona_name = persona_name
        self.created_at = datetime.now()
        
        # 주제 추적기들
        self.topic_trackers = self._initialize_topic_trackers()
        
        # 질문 중복 감지기
        self.duplicate_detector = QuestionDuplicateDetector()
        
        # 대화 기억 저장소
        self.memory = ConversationMemory()
        
        # 질문/답변 히스토리
        self.question_history: List[str] = []
        self.answer_history: List[str] = []
        
        # 사용된 키워드 추적
        self.used_keywords: Set[str] = set()
        
        # 답변에서 추출된 정보
        self.extracted_info = {
            'projects': [],
            'technologies': [],
            'experiences': [],
            'achievements': []
        }
    
    def _initialize_topic_trackers(self) -> Dict[TopicCategory, TopicTracker]:
        """주제 추적기 초기화"""
        trackers = {}
        
        # 각 주제별 키워드 정의 (HR과 협업 명확히 구분)
        topic_keywords = {
            TopicCategory.PERSONAL_BACKGROUND: {
                "자기소개", "배경", "경력", "학력", "성장", "계기", "인생", "과정"
            },
            TopicCategory.TECHNICAL_SKILLS: {
                "기술", "언어", "프레임워크", "도구", "개발", "구현", "설계"
            },
            TopicCategory.PROJECT_EXPERIENCE: {
                "프로젝트", "개발", "구현", "결과", "성과", "경험", "담당"
            },
            TopicCategory.TEAM_COLLABORATION: {
                # 협업 전용: 팀워크, 소통, 갈등해결에 집중
                "팀워크", "협업", "협력", "소통", "커뮤니케이션", "대화", 
                "갈등해결", "조율", "중재", "역할분담", "회의", "브레인스토밍",
                "의견조율", "합의", "동료", "상사", "부하", "고객응대"
            },
            TopicCategory.PROBLEM_SOLVING: {
                "문제", "해결", "어려움", "도전", "개선", "최적화", "분석"
            },
            TopicCategory.CAREER_GOALS: {
                # HR 전용: 개인 목표와 비전
                "목표", "계획", "비전", "발전", "미래", "꿈", "지향점", "포부"
            },
            TopicCategory.COMPANY_CULTURE: {
                "회사", "문화", "가치", "철학", "비전", "미션", "환경"
            },
            TopicCategory.LEADERSHIP: {
                # 협업 전용: 리더십 스킬
                "리더십", "이끌다", "관리", "지도", "멘토", "가이드", 
                "팔로워십", "책임", "의사결정", "방향제시"
            },
            TopicCategory.LEARNING_ABILITY: {
                # HR 전용: 개인 학습과 성장
                "학습", "배우다", "익히다", "습득", "성장", "발전", "향상",
                "자기계발", "공부", "연구", "탐구"
            },
            TopicCategory.COMMUNICATION: {
                # 협업 전용: 소통 스킬
                "소통", "의사소통", "전달", "설명", "공유", "논의", "협의",
                "프레젠테이션", "설득", "경청", "피드백"
            }
        }
        
        for category, keywords in topic_keywords.items():
            trackers[category] = TopicTracker(
                category=category,
                keywords=keywords,
                questions_asked=[],
                answers_given=[]
            )
        
        return trackers
    
    def add_question_answer(self, question: str, answer: str, question_type: QuestionType):
        """질문과 답변 추가"""
        self.question_history.append(question)
        self.answer_history.append(answer)
        
        # 질문 키워드 추적
        question_keywords = self.duplicate_detector.extract_keywords(question)
        self.used_keywords.update(question_keywords)
        
        # 답변에서 정보 추출
        self._extract_info_from_answer(answer)
        
        # 주제별 추적 업데이트
        self._update_topic_trackers(question, answer, question_type)
    
    def _extract_info_from_answer(self, answer: str):
        """답변에서 정보 추출"""
        answer_lower = answer.lower()
        
        # 프로젝트 정보 추출
        project_patterns = [
            r'(.+?)\s*프로젝트',
            r'(.+?)\s*시스템',
            r'(.+?)\s*서비스',
            r'(.+?)\s*플랫폼'
        ]
        
        for pattern in project_patterns:
            matches = re.findall(pattern, answer_lower)
            for match in matches:
                if len(match.strip()) > 1:
                    self.extracted_info['projects'].append(match.strip())
                    self.memory.mentioned_projects.add(match.strip())
        
        # 기술 정보 추출
        tech_patterns = [
            r'(파이썬|자바|스프링|리액트|노드|도커|쿠버네티스|AWS|MySQL|Redis)',
            r'(Python|Java|Spring|React|Node|Docker|Kubernetes|MySQL|Redis)',
            r'(javascript|typescript|html|css|bootstrap)'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, answer, re.IGNORECASE)
            for match in matches:
                self.extracted_info['technologies'].append(match)
                self.memory.mentioned_technologies.add(match.lower())
        
        # 성과/성취 정보 추출
        achievement_patterns = [
            r'(\d+%\s*(?:향상|개선|증가|감소))',
            r'(\d+배\s*(?:향상|개선|증가))',
            r'(\d+초\s*(?:단축|개선))',
            r'(\d+\s*(?:명|개|건)\s*(?:달성|완료|성공))'
        ]
        
        for pattern in achievement_patterns:
            matches = re.findall(pattern, answer_lower)
            for match in matches:
                self.extracted_info['achievements'].append(match)
                self.memory.achievements.add(match)
    
    def _update_topic_trackers(self, question: str, answer: str, question_type: QuestionType):
        """주제별 추적기 업데이트"""
        # 질문 타입에 따른 주제 매핑 (HR과 협업 명확히 구분)
        type_to_topics = {
            QuestionType.INTRO: [TopicCategory.PERSONAL_BACKGROUND],
            QuestionType.MOTIVATION: [TopicCategory.CAREER_GOALS, TopicCategory.COMPANY_CULTURE],
            # HR: 개인 인성, 가치관, 성장에 집중 (협업 스킬 제외)
            QuestionType.HR: [
                TopicCategory.PERSONAL_BACKGROUND, 
                TopicCategory.LEARNING_ABILITY,
                TopicCategory.CAREER_GOALS
            ],
            QuestionType.TECH: [TopicCategory.TECHNICAL_SKILLS, TopicCategory.PROJECT_EXPERIENCE],
            # COLLABORATION: 팀워크, 소통, 리더십에 집중 (개인 특성 제외)
            QuestionType.COLLABORATION: [
                TopicCategory.TEAM_COLLABORATION, 
                TopicCategory.COMMUNICATION,
                TopicCategory.LEADERSHIP
            ],
            QuestionType.FOLLOWUP: [TopicCategory.PROBLEM_SOLVING]
        }
        
        relevant_topics = type_to_topics.get(question_type, [])
        
        for topic in relevant_topics:
            if topic in self.topic_trackers:
                tracker = self.topic_trackers[topic]
                tracker.add_question(question)
                tracker.add_answer(answer)
    
    def check_question_duplicate(self, new_question: str, threshold: float = 0.6) -> Tuple[bool, Optional[str], float]:
        """새로운 질문의 중복 여부 확인"""
        is_duplicate, similar_question = self.duplicate_detector.is_duplicate(
            new_question, self.question_history, threshold
        )
        
        if is_duplicate:
            similarity = self.duplicate_detector.calculate_similarity(new_question, similar_question)
            return True, similar_question, similarity
        
        return False, None, 0.0
    
    def get_underexplored_topics(self) -> List[TopicCategory]:
        """덜 탐색된 주제들 반환"""
        underexplored = []
        
        for topic, tracker in self.topic_trackers.items():
            if tracker.coverage_score < 0.3:  # 30% 미만 커버리지
                underexplored.append(topic)
        
        # 커버리지가 낮은 순으로 정렬
        underexplored.sort(key=lambda t: self.topic_trackers[t].coverage_score)
        
        return underexplored
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """대화 요약 정보 반환"""
        return {
            'total_questions': len(self.question_history),
            'total_answers': len(self.answer_history),
            'unique_keywords': len(self.used_keywords),
            'topic_coverage': {
                topic.value: tracker.coverage_score 
                for topic, tracker in self.topic_trackers.items()
            },
            'extracted_info': self.extracted_info,
            'memory_summary': {
                'projects': len(self.memory.mentioned_projects),
                'technologies': len(self.memory.mentioned_technologies),
                'experiences': len(self.memory.mentioned_experiences),
                'achievements': len(self.memory.achievements)
            }
        }
    
    def suggest_next_question_focus(self) -> Dict[str, Any]:
        """다음 질문 집중 영역 제안"""
        underexplored = self.get_underexplored_topics()
        
        # 반복 사용된 키워드 식별
        keyword_usage = defaultdict(int)
        for question in self.question_history:
            keywords = self.duplicate_detector.extract_keywords(question)
            for keyword in keywords:
                keyword_usage[keyword] += 1
        
        overused_keywords = [kw for kw, count in keyword_usage.items() if count >= 2]
        
        return {
            'underexplored_topics': [topic.value for topic in underexplored[:3]],
            'avoid_keywords': overused_keywords,
            'suggested_new_angles': self._suggest_new_angles(),
            'coverage_gaps': self._identify_coverage_gaps()
        }
    
    def _suggest_new_angles(self) -> List[str]:
        """새로운 접근 각도 제안"""
        suggestions = []
        
        # 기존 답변에서 언급된 내용을 바탕으로 심화 질문 제안
        if self.memory.mentioned_projects:
            suggestions.append("구체적인 프로젝트 도전 과제")
        
        if self.memory.mentioned_technologies:
            suggestions.append("기술 선택 이유와 트레이드오프")
        
        if self.memory.achievements:
            suggestions.append("성과 달성 과정의 어려움")
        
        return suggestions
    
    def _identify_coverage_gaps(self) -> List[str]:
        """커버리지 부족 영역 식별"""
        gaps = []
        
        for topic, tracker in self.topic_trackers.items():
            if tracker.coverage_score < 0.2:
                gaps.append(f"{topic.value} 영역 탐색 부족")
        
        return gaps