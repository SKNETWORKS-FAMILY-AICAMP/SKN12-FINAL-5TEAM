#!/usr/bin/env python3
"""
서버 구동 및 API 테스트 스크립트
"""
import requests
import time
import subprocess
import sys
import os
from pathlib import Path

def test_backend_health():
    """백엔드 서버 헬스체크"""
    try:
        response = requests.get("http://127.0.0.1:8000/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ 백엔드 서버 정상 동작")
            return True
        else:
            print(f"❌ 백엔드 서버 응답 오류: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 백엔드 서버 연결 실패: {e}")
        return False

def test_interview_api():
    """면접 API 기본 테스트"""
    try:
        # 면접 시작 API 테스트
        start_data = {
            "company": "네이버",
            "position": "백엔드 개발자", 
            "mode": "normal",
            "difficulty": "medium",
            "candidate_name": "테스트사용자"
        }
        
        response = requests.post("http://127.0.0.1:8000/api/interview/start", 
                               json=start_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get("session_id")
            print(f"✅ 면접 시작 API 성공 - 세션 ID: {session_id}")
            return session_id
        else:
            print(f"❌ 면접 시작 API 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 면접 API 테스트 오류: {e}")
        return None

if __name__ == "__main__":
    print("🔍 서버 구동 테스트 시작")
    
    # 헬스체크
    if test_backend_health():
        # API 테스트
        session_id = test_interview_api()
        if session_id:
            print("🎉 모든 서버 테스트 통과!")
        else:
            print("⚠️ API 테스트 실패")
    else:
        print("⚠️ 서버가 구동되지 않았습니다. 먼저 서버를 시작해주세요.")
        print("실행 방법: cd backend && python -m uvicorn main:app --reload")