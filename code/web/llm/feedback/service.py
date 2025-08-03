#!/usr/bin/env python3
"""
피드백 서비스
답변 평가 및 피드백 생성을 담당
"""

import openai
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

from ..shared.models import QuestionAnswer, QuestionType
from ..candidate.model import CandidatePersona
from backend.models.session import InterviewSession  # 호환성을 위한 별도 모듈
from ..shared.utils import safe_json_load

class FeedbackService:
    """면접 답변 평가 및 피드백 생성 서비스"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        # LLMManager 제거 - 직접 OpenAI 클라이언트 사용
        self.companies_data = self._load_companies_data()
    
    def evaluate_answer(self, question_answer: QuestionAnswer, 
                       company_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """단일 답변 평가"""
        try:
            evaluation_prompt = self._create_evaluation_prompt(question_answer, company_context)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 전문 면접관입니다. 답변을 객관적으로 평가해주세요."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            return self._parse_evaluation_result(result)
            
        except Exception as e:
            return {
                "score": 70,
                "feedback": "평가 중 오류가 발생했습니다.",
                "strengths": [],
                "improvements": [],
                "detailed_feedback": str(e)
            }
    
    def evaluate_session(self, session: InterviewSession, 
                        company_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """전체 세션 종합 평가"""
        if not session.question_answers:
            return {
                "total_score": 0,
                "category_scores": {},
                "overall_feedback": "답변이 없습니다.",
                "recommendations": []
            }
        
        # 카테고리별 점수 계산
        category_scores = self._calculate_category_scores(session.question_answers)
        
        # 종합 점수 계산
        total_score = sum(category_scores.values()) // len(category_scores)
        
        # 종합 피드백 생성
        overall_feedback = self._generate_overall_feedback(session, category_scores, company_context)
        
        # 개선 추천사항 생성
        recommendations = self._generate_recommendations(category_scores, session.question_answers)
        
        return {
            "total_score": total_score,
            "category_scores": category_scores,
            "overall_feedback": overall_feedback,
            "recommendations": recommendations,
            "detailed_evaluations": [self.evaluate_answer(qa, company_context) for qa in session.question_answers]
        }
    
    def _create_evaluation_prompt(self, question_answer: QuestionAnswer, 
                                company_context: Dict[str, Any] = None) -> str:
        """평가 프롬프트 생성"""
        context_info = ""
        if company_context:
            context_info = f"""
=== 기업 정보 ===
회사: {company_context.get('name', '알 수 없음')}
인재상: {company_context.get('talent_profile', '우수한 인재')}
핵심 역량: {', '.join(company_context.get('core_competencies', ['전문성', '협업']))}
"""
        
        return f"""
{context_info}

=== 면접 질문 및 답변 ===
질문 유형: {question_answer.question_type.value}
질문: {question_answer.question_content}
답변: {question_answer.answer_content}

위 답변을 다음 기준으로 평가해주세요:

1. 질문 이해도 (질문의 의도를 정확히 파악했는가?)
2. 답변 완성도 (구체적이고 상세한 답변인가?)
3. 전문성 (해당 분야의 전문 지식을 보여주는가?)
4. 논리성 (답변의 구조와 논리가 명확한가?)
5. 진정성 (진솔하고 설득력 있는 답변인가?)

평가 결과를 다음 형식으로 제공해주세요:

점수: [0-100점]
강점: [구체적인 강점 2-3개, 쉼표로 구분]
개선점: [구체적인 개선사항 2-3개, 쉼표로 구분]
피드백: [종합적인 피드백 2-3문장]
"""
    
    def _parse_evaluation_result(self, result: str) -> Dict[str, Any]:
        """평가 결과 파싱"""
        try:
            lines = result.strip().split('\n')
            evaluation = {
                "score": 70,
                "strengths": [],
                "improvements": [],
                "feedback": "평가 완료"
            }
            
            for line in lines:
                line = line.strip()
                if line.startswith('점수:'):
                    try:
                        score_str = line.replace('점수:', '').strip().replace('점', '')
                        evaluation["score"] = min(100, max(0, int(score_str)))
                    except:
                        evaluation["score"] = 70
                        
                elif line.startswith('강점:'):
                    strengths_str = line.replace('강점:', '').strip()
                    evaluation["strengths"] = [s.strip() for s in strengths_str.split(',') if s.strip()]
                    
                elif line.startswith('개선점:'):
                    improvements_str = line.replace('개선점:', '').strip()
                    evaluation["improvements"] = [i.strip() for i in improvements_str.split(',') if i.strip()]
                    
                elif line.startswith('피드백:'):
                    evaluation["feedback"] = line.replace('피드백:', '').strip()
            
            return evaluation
            
        except Exception as e:
            return {
                "score": 70,
                "strengths": ["답변 제출 완료"],
                "improvements": ["더 구체적인 설명 필요"],
                "feedback": "평가 파싱 중 오류가 발생했습니다."
            }
    
    def _calculate_category_scores(self, question_answers: List[QuestionAnswer]) -> Dict[str, int]:
        """카테고리별 점수 계산"""
        category_scores = {}
        category_counts = {}
        
        for qa in question_answers:
            category = qa.question_type.value
            score = qa.individual_score or 70  # 기본값
            
            if category not in category_scores:
                category_scores[category] = 0
                category_counts[category] = 0
            
            category_scores[category] += score
            category_counts[category] += 1
        
        # 평균 계산
        for category in category_scores:
            if category_counts[category] > 0:
                category_scores[category] = category_scores[category] // category_counts[category]
        
        # 기본 카테고리들이 없으면 기본값 설정
        default_categories = ["자기소개", "지원동기", "인사", "기술", "협업"]
        for category in default_categories:
            if category not in category_scores:
                category_scores[category] = 75
        
        return category_scores
    
    def _generate_overall_feedback(self, session: InterviewSession,
                                 category_scores: Dict[str, int],
                                 company_context: Dict[str, Any] = None) -> str:
        """종합 피드백 생성"""
        avg_score = sum(category_scores.values()) // len(category_scores)
        
        if avg_score >= 90:
            feedback = f"{session.candidate_name}님은 전 영역에서 우수한 면접 역량을 보여주셨습니다."
        elif avg_score >= 80:
            feedback = f"{session.candidate_name}님은 대체로 좋은 면접 역량을 보여주셨습니다."
        elif avg_score >= 70:
            feedback = f"{session.candidate_name}님은 기본적인 면접 역량을 보여주셨습니다."
        else:
            feedback = f"{session.candidate_name}님은 추가 준비가 필요해 보입니다."
        
        # 가장 강한 영역과 약한 영역 식별
        best_category = max(category_scores, key=category_scores.get)
        worst_category = min(category_scores, key=category_scores.get)
        
        feedback += f" 특히 {best_category} 영역에서 강점을 보이셨고, {worst_category} 영역에서 더 보완하시면 좋겠습니다."
        
        return feedback
    
    def _generate_recommendations(self, category_scores: Dict[str, int],
                                question_answers: List[QuestionAnswer]) -> List[str]:
        """개선 추천사항 생성"""
        recommendations = []
        
        # 점수가 낮은 카테고리에 대한 추천
        for category, score in category_scores.items():
            if score < 75:
                if category == "기술":
                    recommendations.append("기술적 깊이를 더 보완하시고 구체적인 프로젝트 경험을 준비하세요")
                elif category == "협업":
                    recommendations.append("팀워크 경험과 소통 능력을 더 구체적으로 어필하세요")
                elif category == "인사":
                    recommendations.append("개인적 성장 스토리와 가치관을 더 명확히 표현하세요")
        
        # 답변 дл度 기반 추천
        avg_answer_length = sum(len(qa.answer_content) for qa in question_answers) / len(question_answers)
        if avg_answer_length < 100:
            recommendations.append("답변을 더 구체적이고 상세하게 준비하세요")
        elif avg_answer_length > 500:
            recommendations.append("답변을 더 간결하고 핵심적으로 정리하세요")
        
        # 기본 추천사항
        if not recommendations:
            recommendations = [
                "구체적인 사례와 숫자로 성과를 어필하세요",
                "회사에 대한 이해도를 높이고 지원 동기를 명확히 하세요",
                "면접 연습을 통해 자신감을 기르세요"
            ]
        
        return recommendations[:3]  # 최대 3개
    
    def _load_companies_data(self) -> Dict[str, Any]:
        """회사 데이터 로드"""
        # llm/shared/data/companies_data.json 경로를 사용합니다.
        return safe_json_load("llm/shared/data/companies_data.json", {"companies": []})
    
    def _get_company_data(self, company_id: str) -> Dict[str, Any]:
        """회사 데이터 조회"""
        for company in self.companies_data.get("companies", []):
            if company["id"] == company_id:
                return company
        return {}
    
    def evaluate_ai_interview(self, ai_session: InterviewSession) -> Dict[str, Any]:
        """AI 지원자 면접 평가 (면접자와 동일한 구조)"""
        if not ai_session:
            return {"error": "AI 세션을 찾을 수 없습니다"}
        
        company_data = self._get_company_data(ai_session.company_id)
        
        # 1. 각 답변을 개별적으로 평가
        individual_feedbacks = []
        total_score = 0
        category_scores = {}
        
        for qa in ai_session.question_answers:
            # 개별 답변 평가 (면접자와 동일한 로직)
            individual_evaluation = self._evaluate_ai_single_answer(qa, company_data)
            
            # 평가 결과를 qa_pair에 저장
            qa.individual_score = individual_evaluation["score"]
            qa.individual_feedback = individual_evaluation["feedback"]
            
            individual_feedbacks.append({
                "question_number": len(individual_feedbacks) + 1,
                "question_type": qa.question_type.value,
                "question": qa.question_content,
                "question_intent": qa.question_intent,
                "answer": qa.answer_content,
                "score": qa.individual_score,
                "feedback": qa.individual_feedback,
                "personalized": False  # AI는 표준 질문 사용
            })
            
            total_score += qa.individual_score
            
            # 카테고리별 점수 계산
            category = qa.question_type.value
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(qa.individual_score)
        
        # 전체 평균 계산
        overall_score = int(total_score / len(ai_session.question_answers))
        
        # 카테고리별 평균
        for category in category_scores:
            category_scores[category] = int(sum(category_scores[category]) / len(category_scores[category]))
        
        # 2. 종합 평가 생성
        overall_evaluation = self._generate_ai_overall_evaluation(ai_session, company_data, overall_score)
        
        # AICandidateSession 속성 안전 접근
        session_id = getattr(ai_session, 'session_id', f"{ai_session.company_id}_{ai_session.position}_ai")
        candidate_name = getattr(ai_session, 'persona', None)
        candidate_name = candidate_name.name if candidate_name else ai_session.candidate_name
        
        return {
            "session_id": session_id,
            "company": company_data.get("name", ""),
            "position": ai_session.position,
            "candidate": candidate_name,
            "candidate_type": "AI",
            "individual_feedbacks": individual_feedbacks,
            "evaluation": {
                "overall_score": overall_score,
                "category_scores": category_scores,
                **overall_evaluation
            },
            "completed_at": datetime.now().isoformat()
        }
    
    def _evaluate_ai_single_answer(self, qa: QuestionAnswer, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI 답변 개별 평가 (면접자와 동일한 엄격한 기준)"""
        
        answer = qa.answer_content.strip()
        
        # 기본 검증
        if len(answer) < 10:
            return {
                "score": 20,
                "feedback": f"📝 질문 의도: {qa.question_intent}\n\n💬 평가: AI 답변이 너무 짧습니다.\n\n🔧 개선 방법: 더 구체적이고 상세한 답변이 필요합니다."
            }
        
        prompt = f"""
다음 AI 지원자의 면접 답변을 평가해주세요.

=== 질문 정보 ===
질문 유형: {qa.question_type.value}
질문: {qa.question_content}
질문 의도: {qa.question_intent}

=== AI 지원자 답변 ===
{answer}

=== 평가 기준 ===
- 65-75점: AI 답변의 기본 품질 범위
- 75-85점: 구체적이고 인상적인 답변
- 85-95점: 매우 우수한 답변
- 95-100점: 완벽에 가까운 답변

평가 요소:
1. 질문 의도 이해도
2. 답변의 구체성과 사실성
3. 논리적 구성
4. 전문성과 깊이
5. 일관성

JSON 형식으로 응답:
{{
  "score": 점수,
  "feedback": "📝 질문 의도: {qa.question_intent}\\n\\n💬 평가: 구체적인 평가 내용\\n\\n🔧 개선 방법: 실질적인 개선 제안"
}}
"""
        
        try:
            # LLMManager 대신 직접 OpenAI 클라이언트 사용
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 AI 지원자 답변을 평가하는 면접 평가 전문가입니다."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            result = response.choices[0].message.content.strip()
            
            # JSON 파싱
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                evaluation = json.loads(json_str)
                
                # AI 답변은 일반적으로 높은 품질이므로 기본 점수 조정
                score = max(evaluation["score"], 65)  # 최소 65점
                evaluation["score"] = score
                
                return evaluation
            else:
                raise ValueError("JSON 형식을 찾을 수 없습니다")
                
        except Exception as e:
            print(f"AI 답변 평가 중 오류: {str(e)}")
            # 기본 점수 (AI는 일반적으로 좋은 답변을 생성)
            return {
                "score": 75,
                "feedback": f"📝 질문 의도: {qa.question_intent}\n\n💬 평가: AI 답변이 적절합니다.\n\n🔧 개선 방법: 더 구체적인 경험과 사례를 포함할 수 있습니다."
            }
    
    def _generate_ai_overall_evaluation(self, ai_session: InterviewSession, company_data: Dict[str, Any], overall_score: int) -> Dict[str, Any]:
        """AI 지원자 종합 평가 생성"""
        
        conversation_summary = ""
        for qa in ai_session.question_answers:
            conversation_summary += f"[{qa.question_type.value}] {qa.question_content}\n답변: {qa.answer_content}\n개별 점수: {qa.individual_score}점\n\n"
        
        # AICandidateSession 속성 안전 접근
        candidate_name = getattr(ai_session, 'persona', None)
        candidate_name = candidate_name.name if candidate_name else ai_session.candidate_name
        
        prompt = f"""
{company_data.get('name', '')} {ai_session.position} AI 지원자 종합 평가를 수행해주세요.

=== AI 지원자 정보 ===
- 이름: {candidate_name}
- 지원 직군: {ai_session.position}
- 전체 평균 점수: {overall_score}점
- 페르소나 유형: AI 지원자

=== 면접 내용 ===
{conversation_summary}

=== 기업 요구사항 ===
- 인재상: {company_data.get('talent_profile', '')}
- 핵심 역량: {', '.join(company_data.get('core_competencies', []))}

AI 지원자의 답변 품질과 일관성을 평가하여 JSON 형식으로 응답:
{{
  "strengths": ["구체적인 강점1", "구체적인 강점2", "구체적인 강점3"],
  "improvements": ["구체적인 개선점1", "구체적인 개선점2", "구체적인 개선점3"],
  "recommendation": "AI 지원자 성능 평가",
  "next_steps": "실제 면접 준비 단계 제안",
  "overall_assessment": "AI 지원자의 전체적인 성능 평가"
}}
"""
        
        try:
            # LLMManager 대신 직접 OpenAI 클라이언트 사용
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"{company_data.get('name', '')} AI 지원자 면접 평가 전문가입니다."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            result = response.choices[0].message.content.strip()
            
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                return json.loads(json_str)
            
        except Exception as e:
            print(f"AI 종합 평가 중 오류: {str(e)}")
        
        # 기본 평가 (AI는 일반적으로 좋은 성능)
        return {
            "strengths": ["일관된 답변", "논리적 구성", "전문적 표현"],
            "improvements": ["개인 경험 구체화", "감정적 표현", "창의성 향상"],
            "recommendation": f"AI 지원자 성능: {overall_score}점 수준",
            "next_steps": "실제 면접 준비 시 참고 자료로 활용",
            "overall_assessment": f"AI 지원자가 {overall_score}점 수준의 답변을 제공했습니다."
        }

