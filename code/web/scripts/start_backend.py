#!/usr/bin/env python3
"""
새로운 구조의 백엔드 서버 시작 스크립트
"""
import os
import subprocess
from pathlib import Path

# 프로젝트 루트 디렉토리
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"

def start_backend():
    """백엔드 서버 시작"""
    print("🚀 새로운 구조의 백엔드 서버를 시작합니다...")
    print(f"📍 백엔드 디렉토리: {backend_dir}")
    
    # 백엔드 디렉토리로 이동 후 서버 시작
    try:
        os.chdir(backend_dir)
        print("📂 백엔드 디렉토리로 이동 완료")
        
        # uvicorn으로 서버 시작
        cmd = ["python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
        print(f"🔧 실행 명령어: {' '.join(cmd)}")
        
        subprocess.run(cmd)
        
    except Exception as e:
        print(f"❌ 서버 시작 오류: {e}")

if __name__ == "__main__":
    start_backend()
    