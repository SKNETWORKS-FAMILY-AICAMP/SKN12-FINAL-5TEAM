# React + Vite + FastAPI 프로젝트

이 프로젝트는 React 프론트엔드와 FastAPI 백엔드를 함께 사용합니다.

## 🚀 시작하기

### 1. 환경 설정

#### Python (FastAPI 백엔드)

1.  **Conda 환경 활성화:** `mcp` Conda 환경을 활성화합니다.
    ```bash
    conda activate mcp
    ```
    (만약 `mcp` 환경이 없다면 `conda create -n mcp python=3.12` 로 생성 후 활성화)
2.  **의존성 설치:** `backend` 폴더로 이동하여 필요한 라이브러리를 설치합니다.
    ```bash
    cd backend
    pip install -r requirements.txt
    cd .. # 프로젝트 루트로 돌아오기
    ```
3.  **OpenAI API 키 설정:**
    *   `backend/` 폴더 안에 `.env` 파일을 만듭니다.
    *   파일 안에 다음 내용을 추가하고 `your_openai_api_key_here` 부분을 실제 키로 바꿔주세요.
        ```
        OPENAI_API_KEY="your_openai_api_key_here"
        ```
    *   **주의:** `.env` 파일은 Git에 올라가지 않도록 `.gitignore`에 추가해야 합니다.

#### Node.js (React 프론트엔드)

1.  **의존성 설치:** 프로젝트 루트에서 필요한 Node.js 패키지를 설치합니다.
    ```bash
    npm install
    ```

### 2. 애플리케이션 실행

FastAPI 백엔드가 React 프론트엔드를 함께 제공합니다.

1.  **React 프론트엔드 빌드:** 프로젝트 루트에서 React 앱을 빌드합니다. `dist/` 폴더가 생성됩니다.
    ```bash
    npm run build
    ```

2.  **FastAPI 백엔드 실행:** `backend` 폴더로 이동하여 FastAPI 서버를 시작합니다. `mcp` Conda 환경이 활성화되어 있어야 합니다.
    ```bash
    cd backend
    uvicorn main:app --reload
    ```

3.  **접속:** 웹 브라우저에서 `http://127.0.0.1:8000` 으로 접속합니다.

## 💡 개발 시 참고

*   **프론트엔드 코드 변경 시:** `src/` 폴더의 React 코드를 수정했다면, 변경 사항을 적용하기 위해 `npm run build`를 다시 실행해야 합니다.
*   **백엔드 코드 변경 시:** `backend/` 폴더의 FastAPI 코드를 수정하면, `uvicorn`이 `--reload` 옵션으로 실행 중일 경우 자동으로 서버가 재시작됩니다.
