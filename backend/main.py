from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import json

# OpenAI 서비스 모듈 임포트
from openai_service import get_answer_from_openai

app = FastAPI()

# --- Pydantic Models for Request Bodies ---

class QuestionRequest(BaseModel):
    question: str

class LogRequest(BaseModel):
    who: str
    question: str
    answer: str

# --- API Endpoints ---

@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    """
    사용자 질문을 받아 OpenAI API를 통해 답변을 반환하는 엔드포인트
    """
    answer = get_answer_from_openai(request.question)
    return {"answer": answer}

@app.post("/api/save_log")
async def save_log(log_data: LogRequest):
    """
    질문과 답변 로그를 JSON 파일에 저장하는 엔드포인트
    """
    log_file_path = os.path.join(os.path.dirname(__file__), "interview_log.json")
    
    # 기존 로그 파일이 있으면 읽어오고, 없으면 빈 리스트로 시작
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []

    # 새로운 로그 추가
    logs.append({"who": log_data.who, "question": log_data.question, "answer": log_data.answer})

    # 파일에 다시 저장
    try:
        with open(log_file_path, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        return {"status": "success", "message": "Log saved successfully."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/api/clear_log")
async def clear_log():
    """
    면접 로그 파일을 삭제하는 엔드포인트
    """
    log_file_path = os.path.join(os.path.dirname(__file__), "interview_log.json")
    try:
        if os.path.exists(log_file_path):
            os.remove(log_file_path)
            return {"status": "success", "message": "Log file cleared successfully."}
        else:
            return {"status": "success", "message": "Log file does not exist, no action needed."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# --- React Frontend Serving ---

# 정적 파일 제공 설정
static_files_path = os.path.join(os.path.dirname(__file__), "..", "dist")

# '/assets' 경로로 요청이 오면 dist/assets 폴더에서 파일을 찾도록 설정
app.mount("/assets", StaticFiles(directory=os.path.join(static_files_path, "assets")), name="assets")

# 루트 경로 또는 다른 경로로 접속했을 때 React의 index.html을 보여줌
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    index_path = os.path.join(static_files_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html not found"}