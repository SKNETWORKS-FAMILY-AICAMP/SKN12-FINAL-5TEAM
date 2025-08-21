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

## 단기 계획 (3개월 이내) - shortly_plan
다음 4개 영역에서 각각 3개씩 면접 평가 결과를 바탕으로 3개월 내 개선 가능한 사항을 제시해주세요:
1. 답변 스킬 개선 (3개) - 평가에서 지적된 논리성, 구체성, 일관성 등 답변 방식 개선
2. 의사소통 능력 향상 (3개) - 언어 사용, 표현력, 설명 능력 등 평가에서 드러난 소통 약점 보완
3. 기술 지식 보강 (3개) - 면접에서 부족했던 기술적 깊이, 전문성을 높이기 위한 학습 계획
4. 면접 태도 개선 (3개) - 자신감, 적극성, 예의 등 면접 매너와 태도 관련 개선사항

## 장기 계획 (6개월) - long_plan  
다음 4개 영역에서 각각 3개씩 면접 평가를 통해 파악된 약점을 바탕으로 6개월 내 성장 계획을 제시해주세요:
1. 전문성 강화 (3개) - 평가에서 부족했던 기술 역량과 도메인 지식을 심화하기 위한 계획
2. 실무 역량 개발 (3개) - 답변에서 드러난 경험 부족을 보완하기 위한 실무 능력 향상 방안
3. 문제해결 능력 향상 (3개) - 기술 질문 대응력과 논리적 사고력을 기르기 위한 훈련 계획
4. 자기표현 능력 개발 (3개) - 자신의 장점과 경험을 효과적으로 어필하는 능력 향상 방안

# 응답 형식
반드시 다음 JSON 형식으로만 응답해주세요:

```json
{
  "shortly_plan": {
    "답변_스킬_개선": ["답변개선1", "답변개선2", "답변개선3"],
    "의사소통_능력_향상": ["소통향상1", "소통향상2", "소통향상3"],
    "기술_지식_보강": ["기술보강1", "기술보강2", "기술보강3"],
    "면접_태도_개선": ["태도개선1", "태도개선2", "태도개선3"]
  },
  "long_plan": {
    "전문성_강화": ["전문성1", "전문성2", "전문성3"],
    "실무_역량_개발": ["실무역량1", "실무역량2", "실무역량3"],
    "문제해결_능력_향상": ["문제해결1", "문제해결2", "문제해결3"],
    "자기표현_능력_개발": ["자기표현1", "자기표현2", "자기표현3"]
  }
}
```

각 항목은 구체적이고 실행 가능한 내용으로 작성해주세요.
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

# 테스트용 실행 블록
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