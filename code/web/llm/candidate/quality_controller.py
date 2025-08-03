#!/usr/bin/env python3
"""
답변 품질 제어 시스템
사용자 설정에 따라 AI 지원자의 답변 품질을 조절
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json

class QualityLevel(Enum):
    """답변 품질 레벨"""
    EXCELLENT = 10    # 탁월한 수준 (95-100점)
    VERY_GOOD = 9     # 매우 좋은 수준 (85-94점)
    GOOD = 8          # 좋은 수준 (75-84점)
    ABOVE_AVERAGE = 7 # 평균 이상 (65-74점)
    AVERAGE = 6       # 평균 수준 (55-64점)
    BELOW_AVERAGE = 5 # 평균 이하 (45-54점)
    POOR = 4          # 부족한 수준 (35-44점)
    VERY_POOR = 3     # 매우 부족 (25-34점)
    MINIMAL = 2       # 최소 수준 (15-24점)
    INADEQUATE = 1    # 부적절한 수준 (5-14점)

@dataclass
class QualityConfig:
    """품질 레벨별 설정"""
    level: QualityLevel
    description: str
    answer_length_min: int
    answer_length_max: int
    detail_level: str  # 'high', 'medium', 'low'
    specificity: str   # 'very_specific', 'specific', 'general', 'vague'
    professional_tone: bool
    include_examples: bool
    include_metrics: bool
    include_challenges: bool
    temperature: float
    additional_instructions: List[str]
    model_name: str

class AnswerQualityController:
    """답변 품질 제어 컨트롤러"""
    
    def __init__(self):
        self.quality_configs = self._initialize_quality_configs()
        
    def _initialize_quality_configs(self) -> Dict[QualityLevel, QualityConfig]:
        """품질 레벨별 설정 초기화"""
        return {
            QualityLevel.EXCELLENT: QualityConfig(
                level=QualityLevel.EXCELLENT,
                description="탁월한 수준 - 매우 구체적이고 인상적인 답변",
                answer_length_min=200,
                answer_length_max=400,
                detail_level="high",
                specificity="very_specific",
                professional_tone=True,
                include_examples=True,
                include_metrics=True,
                include_challenges=True,
                temperature=0.6,
                additional_instructions=[
                    "구체적인 수치와 성과를 포함하세요",
                    "실제 경험에서 나온 깊이 있는 인사이트를 제시하세요",
                    "문제 해결 과정과 결과를 상세히 설명하세요",
                    "전문적인 용어를 적절히 사용하되 이해하기 쉽게 설명하세요",
                    "회사의 가치와 연결지어 답변하세요"
                ],
                model_name="gpt-4o"
            ),
            
            QualityLevel.VERY_GOOD: QualityConfig(
                level=QualityLevel.VERY_GOOD,
                description="매우 좋은 수준 - 구체적이고 전문적인 답변",
                answer_length_min=150,
                answer_length_max=300,
                detail_level="high",
                specificity="specific",
                professional_tone=True,
                include_examples=True,
                include_metrics=True,
                include_challenges=False,
                temperature=0.7,
                additional_instructions=[
                    "구체적인 예시와 경험을 포함하세요",
                    "성과나 결과를 수치로 표현하세요",
                    "전문적이면서도 자연스러운 톤을 유지하세요",
                    "논리적인 구조로 답변을 구성하세요"
                ],
                model_name="gpt-4o"
            ),
            
            QualityLevel.GOOD: QualityConfig(
                level=QualityLevel.GOOD,
                description="좋은 수준 - 적절하고 잘 구성된 답변",
                answer_length_min=120,
                answer_length_max=250,
                detail_level="medium",
                specificity="specific",
                professional_tone=True,
                include_examples=True,
                include_metrics=False,
                include_challenges=False,
                temperature=0.7,
                additional_instructions=[
                    "관련 경험을 예시로 들어 설명하세요",
                    "명확하고 체계적으로 답변하세요",
                    "적절한 전문성을 보여주세요"
                ],
                model_name="gpt-4o"
            ),
            
            QualityLevel.ABOVE_AVERAGE: QualityConfig(
                level=QualityLevel.ABOVE_AVERAGE,
                description="평균 이상 - 무난하고 적절한 답변",
                answer_length_min=100,
                answer_length_max=200,
                detail_level="medium",
                specificity="general",
                professional_tone=True,
                include_examples=True,
                include_metrics=False,
                include_challenges=False,
                temperature=0.8,
                additional_instructions=[
                    "기본적인 내용을 충실히 포함하세요",
                    "간단한 예시를 들어 설명하세요",
                    "성실한 태도를 보여주세요"
                ],
                model_name="gpt-4o-mini"
            ),
            
            QualityLevel.AVERAGE: QualityConfig(
                level=QualityLevel.AVERAGE,
                description="평균 수준 - 기본적이지만 완전한 답변",
                answer_length_min=80,
                answer_length_max=150,
                detail_level="medium",
                specificity="general",
                professional_tone=False,
                include_examples=False,
                include_metrics=False,
                include_challenges=False,
                temperature=0.8,
                additional_instructions=[
                    "질문에 직접적으로 답변하세요",
                    "기본적인 내용을 포함하세요",
                    "자연스럽고 솔직한 톤을 유지하세요"
                ],
                model_name="gpt-4o-mini"
            ),
            
            QualityLevel.BELOW_AVERAGE: QualityConfig(
                level=QualityLevel.BELOW_AVERAGE,
                description="평균 이하 - 부족하지만 노력하는 답변",
                answer_length_min=60,
                answer_length_max=120,
                detail_level="low",
                specificity="general",
                professional_tone=False,
                include_examples=False,
                include_metrics=False,
                include_challenges=False,
                temperature=0.9,
                additional_instructions=[
                    "간단하고 솔직하게 답변하세요",
                    "부족한 부분이 있어도 성실히 답변하세요",
                    "긴장감이나 어색함을 자연스럽게 표현하세요"
                ],
                model_name="gpt-4o-mini"
            ),
            
            QualityLevel.POOR: QualityConfig(
                level=QualityLevel.POOR,
                description="부족한 수준 - 기본적이고 아쉬운 답변",
                answer_length_min=40,
                answer_length_max=80,
                detail_level="low",
                specificity="vague",
                professional_tone=False,
                include_examples=False,
                include_metrics=False,
                include_challenges=False,
                temperature=1.0,
                additional_instructions=[
                    "짧고 간단하게 답변하세요",
                    "구체적인 내용보다는 일반적인 내용으로 답변하세요",
                    "약간의 준비 부족이 느껴지도록 하세요"
                ],
                model_name="gpt-4o-mini"
            )
        }
    
    def get_quality_config(self, level: QualityLevel) -> QualityConfig:
        """품질 레벨에 따른 설정 반환"""
        return self.quality_configs.get(level, self.quality_configs[QualityLevel.AVERAGE])
    
    def generate_quality_prompt(self, base_prompt: str, level: QualityLevel, question_type: str = "") -> str:
        """품질 레벨에 맞는 프롬프트 생성"""
        config = self.get_quality_config(level)
        
        quality_instructions = f"""
=== 답변 품질 가이드라인 ===
품질 수준: {config.description}
답변 길이: {config.answer_length_min}-{config.answer_length_max}자 정도
세부 정도: {config.detail_level}
구체성: {config.specificity}
전문적 톤: {'사용' if config.professional_tone else '자연스럽게'}
예시 포함: {'필수' if config.include_examples else '선택'}
수치/성과: {'포함' if config.include_metrics else '불필요'}
도전/어려움: {'포함' if config.include_challenges else '불필요'}

=== 추가 지침 ===
"""
        
        for instruction in config.additional_instructions:
            quality_instructions += f"- {instruction}\n"
        
        # 질문 유형별 추가 가이드
        if question_type:
            quality_instructions += f"\n=== {question_type} 질문 특화 가이드 ===\n"
            quality_instructions += self._get_question_type_guide(question_type, level)
        
        return f"{base_prompt}\n\n{quality_instructions}"
    
    def _get_question_type_guide(self, question_type: str, level: QualityLevel) -> str:
        """질문 유형별 품질 가이드"""
        guides = {
            "자기소개": {
                QualityLevel.EXCELLENT: "개인적 배경, 핵심 역량, 성과, 성장 과정을 균형있게 포함하고 회사와의 연결점을 제시하세요.",
                QualityLevel.GOOD: "기본 배경, 주요 경험, 강점을 포함하여 체계적으로 소개하세요.",
                QualityLevel.AVERAGE: "이름, 학력/경력, 지원 동기를 간단히 소개하세요.",
                QualityLevel.POOR: "기본적인 정보만 간단히 언급하세요."
            },
            "지원동기": {
                QualityLevel.EXCELLENT: "회사 분석, 개인 목표와의 연결점, 구체적인 기여 방안, 장기 비전을 포함하세요.",
                QualityLevel.GOOD: "회사에 대한 관심, 본인의 목표, 기여하고 싶은 점을 명확히 설명하세요.",
                QualityLevel.AVERAGE: "회사에 관심을 갖게 된 이유와 지원 이유를 설명하세요.",
                QualityLevel.POOR: "간단한 지원 이유만 언급하세요."
            },
            "기술": {
                QualityLevel.EXCELLENT: "구체적인 기술 스택, 실제 프로젝트 경험, 문제 해결 사례, 기술적 성장 계획을 포함하세요.",
                QualityLevel.GOOD: "주요 기술 경험, 프로젝트 사례, 학습 과정을 설명하세요.",
                QualityLevel.AVERAGE: "사용 가능한 기술과 간단한 경험을 언급하세요.",
                QualityLevel.POOR: "기본적인 기술 지식만 간단히 언급하세요."
            },
            "협업": {
                QualityLevel.EXCELLENT: "구체적인 협업 사례, 갈등 해결 경험, 팀 성과 기여도, 리더십 경험을 포함하세요.",
                QualityLevel.GOOD: "팀 프로젝트 경험, 역할, 소통 방식을 구체적으로 설명하세요.",
                QualityLevel.AVERAGE: "팀워크 경험과 협업 스타일을 간단히 설명하세요.",
                QualityLevel.POOR: "기본적인 협업 경험만 간단히 언급하세요."
            }
        }
        
        question_guides = guides.get(question_type, {})
        return question_guides.get(level, "질문에 성실히 답변하세요.")
    
    def get_quality_feedback(self, level: QualityLevel) -> str:
        """품질 레벨에 대한 피드백 메시지"""
        feedback_messages = {
            QualityLevel.EXCELLENT: "🌟 탁월한 답변입니다! 구체적이고 인상적인 내용으로 면접관에게 강한 인상을 줄 수 있습니다.",
            QualityLevel.VERY_GOOD: "⭐ 매우 좋은 답변입니다! 전문성과 구체성이 잘 드러납니다.",
            QualityLevel.GOOD: "👍 좋은 답변입니다! 체계적이고 적절한 내용입니다.",
            QualityLevel.ABOVE_AVERAGE: "👌 무난한 답변입니다. 조금 더 구체적인 예시가 있으면 더 좋겠습니다.",
            QualityLevel.AVERAGE: "📝 평균적인 답변입니다. 더 구체적인 경험이나 예시를 추가해보세요.",
            QualityLevel.BELOW_AVERAGE: "🤔 개선이 필요한 답변입니다. 더 자세한 설명과 구체적인 사례가 필요합니다.",
            QualityLevel.POOR: "💭 부족한 답변입니다. 질문의 의도를 파악하고 더 충실한 답변을 준비하세요."
        }
        
        return feedback_messages.get(level, "답변을 검토해보세요.")
    
    def suggest_improvements(self, level: QualityLevel, question_type: str = "") -> List[str]:
        """품질 개선 제안"""
        if level.value >= 8:
            return ["이미 훌륭한 답변입니다. 현재 수준을 유지하세요!"]
        
        general_improvements = {
            QualityLevel.AVERAGE: [
                "구체적인 경험이나 사례를 추가해보세요",
                "답변의 구조를 더 체계적으로 정리해보세요",
                "전문적인 용어를 적절히 사용해보세요"
            ],
            QualityLevel.BELOW_AVERAGE: [
                "답변 길이를 늘려 더 자세히 설명해보세요",
                "실제 경험을 바탕으로 구체적인 예시를 들어보세요",
                "질문의 의도를 정확히 파악하고 답변해보세요"
            ],
            QualityLevel.POOR: [
                "질문을 다시 읽고 핵심 포인트를 파악해보세요",
                "개인적인 경험을 포함하여 답변해보세요",
                "답변의 기본 구조(상황-행동-결과)를 활용해보세요"
            ]
        }
        
        return general_improvements.get(level, ["더 구체적이고 자세한 답변을 준비해보세요."])
    
    def process_complete_answer(self, raw_answer: str, quality_level: QualityLevel, question_type: str = "") -> str:
        """답변에 대한 완전한 품질 처리 (model.py에서 이동한 로직)"""
        if not raw_answer or not raw_answer.strip():
            return "죄송합니다, 답변을 생성할 수 없었습니다."
        
        # 기본 정리
        processed = raw_answer.strip()
        
        # 품질 레벨에 따른 설정 가져오기
        config = self.get_quality_config(quality_level)
        
        # 길이 조정
        if len(processed) > config.answer_length_max:
            # 문장 단위로 자르기
            sentences = processed.split('. ')
            total_length = 0
            result_sentences = []
            
            for sentence in sentences:
                if total_length + len(sentence) <= config.answer_length_max:
                    result_sentences.append(sentence)
                    total_length += len(sentence) + 2  # '. ' 포함
                else:
                    break
            
            processed = '. '.join(result_sentences)
            if not processed.endswith('.'):
                processed += '.'
        
        # 최소 길이 확보
        elif len(processed) < config.answer_length_min:
            # 품질 레벨에 따른 추가 내용 생성 가이드
            if config.include_examples:
                processed += " 구체적인 예시를 통해 더 자세히 설명드리겠습니다."
            elif config.include_challenges:
                processed += " 이 과정에서 겪었던 도전과 그 해결 방법도 중요한 경험이었습니다."
        
        # 전문적 톤 조정
        if config.professional_tone:
            # 존댓말과 전문적 표현 강화
            processed = self._enhance_professional_tone(processed)
        
        # 품질 레벨별 마무리 조정
        processed = self._apply_quality_finishing(processed, quality_level)
        
        return processed
    
    def _enhance_professional_tone(self, text: str) -> str:
        """전문적 톤으로 조정"""
        # 기본적인 톤 조정 (간단한 규칙 기반)
        replacements = {
            '그냥': '단순히',
            '되게': '매우',
            '진짜': '정말로',
            '좀': '조금',
            '엄청': '매우'
        }
        
        result = text
        for informal, formal in replacements.items():
            result = result.replace(informal, formal)
        
        return result
    
    def _apply_quality_finishing(self, text: str, quality_level: QualityLevel) -> str:
        """품질 레벨별 마무리 조정"""
        if quality_level.value >= 8:  # GOOD 이상
            # 높은 품질: 명확하고 자신감 있는 마무리
            if not text.endswith(('.', '습니다', '입니다')):
                text += '.'
        elif quality_level.value <= 4:  # POOR 이하
            # 낮은 품질: 약간의 불확실성 표현
            uncertain_endings = ['요.', '것 같습니다.', '생각합니다.']
            if not any(text.endswith(ending) for ending in uncertain_endings):
                if not text.endswith('.'):
                    text += '.'
        
        return text
    
    def compare_quality_levels(self, base_level: QualityLevel, target_level: QualityLevel) -> str:
        """품질 레벨 간 비교 설명"""
        if base_level.value == target_level.value:
            return "동일한 품질 수준입니다."
        
        if base_level.value < target_level.value:
            diff = target_level.value - base_level.value
            return f"{target_level.value}점 수준은 현재보다 {diff}점 높은 수준으로, 더 구체적이고 전문적인 답변이 필요합니다."
        else:
            diff = base_level.value - target_level.value
            return f"{target_level.value}점 수준은 현재보다 {diff}점 낮은 수준으로, 더 간단하고 기본적인 답변입니다."

if __name__ == "__main__":
    # 답변 품질 제어 시스템 테스트
    print("🎯 답변 품질 제어 시스템 테스트")
    
    controller = AnswerQualityController()
    
    # 품질 레벨별 설정 확인
    print("\n📊 품질 레벨별 설정:")
    for level in [QualityLevel.EXCELLENT, QualityLevel.GOOD, QualityLevel.AVERAGE, QualityLevel.POOR]:
        config = controller.get_quality_config(level)
        print(f"\n{level.value}점 ({level.name}):")
        print(f"  설명: {config.description}")
        print(f"  답변 길이: {config.answer_length_min}-{config.answer_length_max}자")
        print(f"  온도: {config.temperature}")
        print(f"  피드백: {controller.get_quality_feedback(level)}")
    
    # 프롬프트 생성 테스트
    base_prompt = "네이버 백엔드 개발자 지원 면접에서 '간단한 자기소개를 해주세요'라는 질문에 답변하세요."
    
    print(f"\n📝 품질별 프롬프트 예시 (자기소개 질문):")
    for level in [QualityLevel.EXCELLENT, QualityLevel.AVERAGE]:
        quality_prompt = controller.generate_quality_prompt(base_prompt, level, "자기소개")
        print(f"\n{level.value}점 수준 프롬프트:")
        print("=" * 50)
        print(quality_prompt[:200] + "..." if len(quality_prompt) > 200 else quality_prompt)