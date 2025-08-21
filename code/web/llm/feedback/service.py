"""
FeedbackService - 호환성을 위한 래퍼 클래스

api_service.py의 InterviewEvaluationService를 FeedbackService로 래핑하여
기존 코드와의 호환성을 제공합니다.
"""

from .api_service import InterviewEvaluationService

class FeedbackService:
    """
    기존 코드 호환성을 위한 FeedbackService 클래스
    내부적으로 InterviewEvaluationService를 사용합니다.
    """
    
    def __init__(self):
        """FeedbackService 초기화"""
        self.evaluation_service = InterviewEvaluationService()
    
    def evaluate_interview(self, *args, **kwargs):
        """면접 평가 - InterviewEvaluationService로 위임"""
        return self.evaluation_service.evaluate_multiple_questions(*args, **kwargs)
    
    def generate_plans(self, interview_id):
        """면접 계획 생성 - InterviewEvaluationService로 위임"""
        return self.evaluation_service.generate_interview_plans(interview_id)
    
    # 추가적인 호환성 메서드들을 필요에 따라 추가할 수 있습니다.