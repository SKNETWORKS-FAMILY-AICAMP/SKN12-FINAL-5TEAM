#!/usr/bin/env python3
"""
InterviewerService 기반 비교면접 테스트 예시
프론트엔드에서 새로운 방식을 테스트할 때 참고용
"""

# 1. 새로운 InterviewerService 방식으로 면접 시작
start_settings = {
    "company": "네이버",
    "position": "백엔드 개발자",
    "candidate_name": "김개발",
    "use_interviewer_service": True,  # 🎯 핵심: 이 플래그 추가 (테스트용으로 활성화됨)
    "career_years": "3",
    "technical_skills": ["Python", "Django", "PostgreSQL"],
    "projects": [{"name": "이커머스 API", "description": "대용량 트래픽 처리"}]
}

# API 호출: POST /api/interview/ai/start
# 응답 예시:
start_response_example = {
    "session_id": "interviewer_comp_abc12345",
    "comparison_session_id": "interviewer_comp_abc12345",
    "question": {
        "id": "q_1",
        "question": "간단한 자기소개를 부탁드립니다.",
        "category": "HR",
        "time_limit": 120,
        "keywords": []
    },
    "current_phase": "user_turn",
    "total_questions": 15,  # SessionManager 방식은 20개, InterviewerService는 15개
    "interviewer_type": "HR",
    "message": "InterviewerService 기반 면접이 시작되었습니다. 김개발님부터 시작합니다"
}

# 2. 사용자 답변 제출
user_answer_data = {
    "comparison_session_id": "interviewer_comp_abc12345",
    "answer": "안녕하세요. 3년차 백엔드 개발자 김개발입니다. 주로 Django와 PostgreSQL을 활용한 API 개발 경험이 있습니다."
}

# API 호출: POST /api/interview/comparison/user-turn
# 응답 예시:
user_response_example = {
    "status": "success",
    "message": "사용자 답변이 제출되었습니다 (InterviewerService)",
    "next_phase": "ai_turn",
    "progress": {
        "current": 1,
        "total": 15,
        "percentage": 6.67
    }
}

# 3. AI 답변 생성 및 다음 질문
ai_turn_data = {
    "comparison_session_id": "interviewer_comp_abc12345",
    "step": "answer"
}

# API 호출: POST /api/interview/comparison/ai-turn
# 응답 예시:
ai_response_example = {
    "status": "success",
    "step": "answer_generated",
    "interview_status": "continue",
    "ai_answer": {
        "content": "안녕하세요. 저는 춘식이입니다. 3년차 백엔드 개발자로 Python과 Django를 활용한 웹 서비스 개발에 특화되어 있습니다. 특히 대용량 데이터 처리와 API 최적화에 관심이 많습니다.",
        "persona_name": "춘식이",
        "confidence": 0.85
    },
    "next_question": {
        "id": "q_2",
        "question": "네이버에 지원하게 된 동기는 무엇인가요?",
        "category": "HR",
        "time_limit": 120,
        "keywords": ["지원동기", "회사"]
    },
    "next_phase": "user_turn",
    "interviewer_type": "HR",
    "progress": {
        "current": 1,
        "total": 15,
        "percentage": 6.67
    },
    "message": "InterviewerService AI 답변 완료. HR 면접관이 다음 질문을 준비했습니다."
}

# 🎯 주요 차이점:
# 1. 시작 시 "use_interviewer_service": True 플래그 추가
# 2. total_questions가 20개 → 15개로 변경
# 3. interviewer_type 필드 추가 (HR, TECH, COLLABORATION)
# 4. 메시지에 "InterviewerService" 표시
# 5. 꼬리질문과 면접관 턴 전환 로직 포함

print("✅ InterviewerService 기반 비교면접 API 사용 예시")
print("🎯 프론트엔드에서 use_interviewer_service: True 플래그로 테스트 가능")