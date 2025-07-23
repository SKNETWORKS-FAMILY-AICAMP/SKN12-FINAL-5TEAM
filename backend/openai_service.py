import os
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
# API 키는 환경 변수 'OPENAI_API_KEY'에서 자동으로 읽어옵니다.
client = OpenAI()

def get_answer_from_openai(question: str) -> str:
    """
    OpenAI의 ChatCompletion API를 사용하여 주어진 질문에 대한 답변을 생성합니다.

    Args:
        question: 사용자의 질문 문자열

    Returns:
        AI가 생성한 답변 문자열
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # 또는 "gpt-4"
            messages=[
                {"role": "system", "content": "너 이름은 춘식이고, 너는 면접을 보러 온 지원자야. 지금은 2줄 이내로 말해"},
                {"role": "user", "content": question}
            ]
        )
        # 답변은 response 객체의 choices 리스트 첫 번째 항목의 message.content에 있습니다.
        answer = response.choices[0].message.content
        return answer
    except Exception as e:
        # API 호출 중 오류 발생 시
        print(f"An error occurred: {e}")
        return "Sorry, I couldn't process your request at the moment."
