
import asyncio
import sys
import os
import json

# 프로젝트 루트 경로를 시스템 경로에 추가하여 모듈 임포트
current_dir = os.path.dirname(os.path.abspath(__file__))
yoseop_1_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, yoseop_1_root)

# backend.services가 아닌 services로 바로 접근하기 위해 경로 추가
backend_root = os.path.join(yoseop_1_root, 'backend')
sys.path.insert(0, backend_root)

from services.interview_service import InterviewService

async def run_mock_interview():
    """
    Orchestrator와 InterviewService를 사용하여 모의 면접을 실행하는 스크립트.
    """
    print("="*80)
    print("🚀 모의 면접 시뮬레이션을 시작합니다.")
    print("="*80)

    interview_service = InterviewService()

    # 1. 면접 시작 설정
    mock_settings = {
        "company": "카카오",
        "position": "백엔드 개발자",
        "candidate_name": "홍길동"
    }
    print(f"📋 면접 설정: {mock_settings}")

    # 2. 면접 시작
    # start_ai_competition은 첫 턴을 자동으로 진행합니다.
    print("\n--- 1️⃣ 면접 시작 및 첫 턴 진행 ---")
    result = await interview_service.start_ai_competition(mock_settings)
    print(f"\n[면접 시작 결과]:\n{json.dumps(result, indent=2, ensure_ascii=False)}")

    if "error" in result:
        print(f"\n❌ 면접 시작 중 오류 발생: {result['error']}")
        return

    session_id = result.get("session_id")
    if not session_id:
        print("\n❌ 세션 ID를 가져올 수 없습니다.")
        return

    print(f"\n✅ 면접 세션이 시작되었습니다. Session ID: {session_id}")

    # 3. 면접 턴 진행 (3턴 시뮬레이션)
    for i in range(2, 5): # 2, 3, 4턴
        print("\n" + "="*80)
        print(f"--- {i}번째 턴 진행 ---")
        print("="*80)

        # 현재 질문 확인
        current_question = result.get("question") or result.get("next_question")
        if not current_question:
             print("현재 질문이 없습니다. 면접을 종료합니다.")
             break
        print(f"❓ 면접관 질문: {current_question}")

        # 다음 액션 확인
        next_action = result.get("next_action")
        print(f"👉 다음 액션: {next_action}")

        if next_action == "user_should_answer":
            # 사용자 답변 제출
            user_answer = f"저는 {i}번째 턴의 사용자 답변입니다. 이 질문에 대해 깊이 생각해 보았습니다."
            print(f"\n👤 사용자 답변 제출: {user_answer}")
            result = await interview_service.submit_user_answer(session_id, user_answer, time_spent=15.5)
            print(f"\n[사용자 답변 제출 후 결과]:\n{json.dumps(result, indent=2, ensure_ascii=False)}")

        elif next_action == "waiting_for_user_answer":
            # AI가 먼저 답변한 경우
            ai_answer = result.get("ai_answer")
            print(f"\n🤖 AI 후보자 답변: {ai_answer}")
            user_answer = f"저는 {i}번째 턴의 사용자 답변입니다. AI의 답변을 듣고 제 생각을 정리했습니다."
            print(f"\n👤 사용자 답변 제출: {user_answer}")
            result = await interview_service.submit_user_answer(session_id, user_answer, time_spent=20.0)
            print(f"\n[사용자 답변 제출 후 결과]:\n{json.dumps(result, indent=2, ensure_ascii=False)}")

        elif next_action == "interview_completed":
            print("\n🏁 면접이 완료되었습니다.")
            break
        
        else:
            # 예상치 못한 상태일 경우, 그냥 다음 턴으로 진행
            print(f"\n⚠️ 예상치 못한 액션({next_action})입니다. 다음 턴으로 진행합니다.")
            result = await interview_service.continue_interview_flow(session_id)
            print(f"\n[다음 턴 진행 결과]:\n{json.dumps(result, indent=2, ensure_ascii=False)}")

        if "error" in result:
            print(f"\n❌ 면접 진행 중 오류 발생: {result['error']}")
            break

    print("\n" + "="*80)
    print("🎉 모의 면접 시뮬레이션이 종료되었습니다.")
    print("="*80)

    # 최종 면접 기록 확인
    orchestrator = interview_service.active_orchestrators.get(session_id)
    if orchestrator:
        print("\n--- 최종 QA 기록 ---")
        print(json.dumps(orchestrator.state['qa_history'], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Windows에서 aiohttp 관련 이벤트 루프 정책 설정
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(run_mock_interview())
    except ImportError as e:
        print(f"\n❌ ImportError: {e}")
        print("스크립트가 프로젝트의 루트 디렉토리를 올바르게 참조하고 있는지 확인하세요.")
        print("PYTHONPATH 환경 변수 설정이 필요할 수 있습니다.")
