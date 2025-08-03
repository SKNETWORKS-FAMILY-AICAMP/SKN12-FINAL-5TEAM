from openai import OpenAI
import os
import json
from dotenv import load_dotenv
import time

load_dotenv()

# 계획 수립용 LLM 클라이언트 설정
client = OpenAI()  # 자동으로 .env의 OPENAI_API_KEY 사용됨

# 계획 수립용 모델 설정
PLAN_MODEL = "gpt-4o"

def build_plan_prompt(final_feedback):
    """면접 준비 계획 수립을 위한 프롬프트 생성"""
    prompt = f"""
당신은 전문 면접 코치입니다. 면접자의 전체 평가 결과를 바탕으로 체계적인 면접 준비 계획을 수립해주세요.

# 면접 전체 평가 결과
**종합 점수**: {final_feedback.get('overall_score', 'N/A')}/100점

**전체 피드백**: 
{final_feedback.get('overall_feedback', '')}

**요약**: 
{final_feedback.get('summary', '')}

**개별 질문 평가**:
"""
    
    # 개별 질문 평가 추가
    if final_feedback.get('per_question'):
        for i, q_eval in enumerate(final_feedback['per_question'], 1):
            prompt += f"""
질문 {i}: {q_eval.get('question', '')}
- 점수: {q_eval.get('final_score', 'N/A')}/100
- 평가: {q_eval.get('evaluation', '')}
- 개선점: {q_eval.get('improvement', '')}
"""
    
    prompt += """

# 요구사항
위 평가 결과를 종합하여 다음과 같은 구체적인 면접 준비 계획을 수립해주세요:

## 1-2주차 단기 개선 계획 (shortly_plan)
다음 3개 영역에서 각각 3개씩 간단한 개선사항을 제시해주세요:
1. 즉시개선 가능한 부분 (3개)
2. 다음 면접 준비사항 (3개) 
3. 구체적 개선 사항 (3개)

## 3-4주차 장기 발전 계획 (long_plan)
다음 3개 영역에서 각각 3개씩 간단한 발전계획을 제시해주세요:
1. 기술개발 (3개)
2. 경험 영역 (3개)
3. 경력 경로 (3개)

# 응답 형식
반드시 다음 JSON 형식으로만 응답해주세요:

```json
{
  "shortly_plan": {
    "즉시개선_가능한_부분": ["개선사항1", "개선사항2", "개선사항3"],
    "다음_면접_준비": ["준비사항1", "준비사항2", "준비사항3"],
    "구체적_개선사항": ["개선사항1", "개선사항2", "개선사항3"]
  },
  "long_plan": {
    "기술개발": ["기술계획1", "기술계획2", "기술계획3"],
    "경험_영역": ["경험계획1", "경험계획2", "경험계획3"], 
    "경력_경로": ["경로계획1", "경로계획2", "경로계획3"]
  }
}
```

각 항목은 간단하고 실행 가능한 내용으로 작성해주세요.
"""
    
    return prompt

def generate_interview_plan(final_feedback):
    """
    면접 전체 평가 결과를 바탕으로 준비 계획 생성
    
    Args:
        final_feedback (dict): 최종 평가 결과
        
    Returns:
        dict: 단기/장기 면접 준비 계획
    """
    try:
        print("TARGET: 면접 준비 계획을 수립 중...")
        
        # 프롬프트 생성
        prompt = build_plan_prompt(final_feedback)
        
        # GPT-4o 호출
        response = client.chat.completions.create(
            model=PLAN_MODEL,
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 전문 면접 코치입니다. 면접자의 평가 결과를 바탕으로 체계적이고 실행 가능한 면접 준비 계획을 수립합니다."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # 응답 파싱
        content = response.choices[0].message.content
        print(f"NOTE: 계획 수립 완료!")
        
        # JSON 추출 (```json ... ``` 형태에서)
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            json_content = content[json_start:json_end].strip()
        else:
            json_content = content
        
        # JSON 파싱
        plan_data = json.loads(json_content)
        
        return {
            "success": True,
            "shortly_plan": plan_data.get("shortly_plan", []),
            "long_plan": plan_data.get("long_plan", []),
            "raw_response": content
        }
        
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON 파싱 오류: {str(e)}")
        return {
            "success": False,
            "error": f"JSON 파싱 실패: {str(e)}",
            "raw_response": content if 'content' in locals() else None
        }
    except Exception as e:
        print(f"ERROR: 계획 수립 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # 테스트용 샘플 데이터
    sample_feedback = {
        "overall_score": 75,
        "overall_feedback": "전반적으로 좋은 답변이지만 기술적 깊이와 구체적 경험 사례가 부족합니다.",
        "summary": "의사소통 능력은 우수하나 기술 역량 어필이 아쉬움",
        "per_question": [
            {
                "question": "자기소개를 해주세요",
                "final_score": 80,
                "evaluation": "명확한 소개이지만 차별화 요소 부족",
                "improvement": "구체적인 성과와 차별화 포인트 추가 필요"
            }
        ]
    }
    
    result = generate_interview_plan(sample_feedback)
    print(json.dumps(result, ensure_ascii=False, indent=2))