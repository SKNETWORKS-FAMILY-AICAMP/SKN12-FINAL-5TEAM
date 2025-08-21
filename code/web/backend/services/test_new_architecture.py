#!/usr/bin/env python3
"""
새로운 아키텍처 테스트
Orchestrator가 세션을 관리하고 JSON 메시지로 통신하는지 확인
"""

import asyncio
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from interview_service import InterviewService

async def test_new_architecture():
    """새로운 아키텍처 테스트"""
    print("🧪 새로운 아키텍처 테스트 시작")
    
    # 면접 서비스 초기화
    service = InterviewService()
    
    # 면접 설정
    settings = {
        'company': '네이버',
        'position': '백엔드 개발자',
        'candidate_name': '테스트 지원자'
    }
    
    try:
        # 1. 면접 시작
        print("1️⃣ 면접 시작...")
        result = await service.start_ai_competition(settings)
        print(f"결과: {result}")
        
        if 'error' in result:
            print(f"❌ 면접 시작 실패: {result['error']}")
            return
            
        session_id = result.get('session_id') or list(service.active_orchestrators.keys())[0]
        print(f"✅ 세션 생성됨: {session_id}")
        
        # 2. 첫 번째 턴 진행 (사용자 답변 없이)
        print("\n2️⃣ 첫 번째 턴 진행...")
        result = await service.advance_interview_turn(session_id)
        print(f"결과: {result}")
        
        # 3. 사용자 답변 제출
        print("\n3️⃣ 사용자 답변 제출...")
        user_answer = "안녕하세요. 저는 3년차 백엔드 개발자입니다."
        result = await service.advance_interview_turn(session_id, user_answer)
        print(f"결과: {result}")
        
        # 4. Orchestrator 상태 확인
        print("\n4️⃣ Orchestrator 상태 확인...")
        orchestrator = service.active_orchestrators.get(session_id)
        if orchestrator:
            print(f"Orchestrator 상태: {orchestrator.state}")
        else:
            print("❌ Orchestrator를 찾을 수 없습니다.")
            
        print("\n✅ 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_new_architecture())
