# Full-stack Docker image (React + FastAPI)

# Stage 1: Build React frontend
FROM node:18-alpine as frontend-build

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --force

# Copy source code first
COPY frontend/ ./

# Copy frontend .env file to the React project root
COPY frontend/.env ./

# Build with environment variables (React reads .env from project root)
# Disable TypeScript checking during build
ENV GENERATE_SOURCEMAP=false
ENV TSC_COMPILE_ON_ERROR=true
RUN npm run build

# Stage 2: Python backend with React static files
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Force remove opencv-contrib-python and ensure only headless version
RUN pip uninstall opencv-contrib-python opencv-python -y || true
RUN pip install --no-cache-dir opencv-python-headless --force-reinstall

# Copy application code
COPY backend/ ./backend/
COPY llm/ ./llm/

# Copy React build from frontend stage - flatten structure
COPY --from=frontend-build /app/frontend/build/ ./backend/static/
RUN if [ -d "/app/backend/static/static" ]; then \
      cp -r /app/backend/static/static/* /app/backend/static/ && \
      rm -rf /app/backend/static/static; \
    fi

# Copy image files from frontend public directory
COPY --from=frontend-build /app/frontend/public/img/ ./backend/static/img/

# Set Python path
ENV PYTHONPATH=/app:/app/backend:/app/llm

# Expose the port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]