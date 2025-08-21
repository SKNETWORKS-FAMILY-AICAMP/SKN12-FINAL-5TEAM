import aiohttp
from fastapi import HTTPException
import os
from dotenv import load_dotenv

load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
BASE_URL = "https://api.elevenlabs.io/v1"

async def elevenlabs_tts_stream(text: str, voice_id: str) -> bytes:
    """ElevenLabs API를 호출해서 텍스트 → MP3 음성 변환"""
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ElevenLabs API 키가 설정되지 않았습니다.")

    url = f"{BASE_URL}/text-to-speech/{voice_id}/stream"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }

    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5, 'speed' : 1.0},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as r:
            if r.status != 200:
                error_text = await r.text()   # ✅ 여기서 상세 메시지 읽기
                print(f"🔥 ElevenLabs API 응답 에러: {error_text}")  # 콘솔 출력
                raise HTTPException(
                    status_code=r.status,
                    detail=f"TTS API 오류: {error_text}"   # 그대로 FastAPI 에러에 포함
                )
            return await r.read()

