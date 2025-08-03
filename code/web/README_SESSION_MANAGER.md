# Claude 세션 상태 관리 시스템

터미널이나 세션이 바뀌어도 Claude의 플랜모드와 TODO 상태를 기억하고 복원할 수 있는 시스템입니다.

## 🎯 주요 기능

### 1. 자동 상태 저장
- **플랜 상태**: 플랜모드에서 생성한 계획과 승인 상태
- **TODO 상태**: 할일 목록과 각 항목의 진행 상황  
- **세션 정보**: 현재 작업 내용과 메모

### 2. 세션 간 복원
- 새 터미널이나 세션에서 이전 상태 자동 감지
- 사용자 선택에 따른 복원/새시작/삭제 옵션
- 진행률과 상태 요약 정보 제공

### 3. 안전한 저장
- `.claude_state/` 디렉토리에 JSON 형태로 저장
- `.gitignore`에 자동 추가되어 개인 상태 보호
- 오류 발생 시에도 상태 보존

## 🚀 사용 방법

### 1. 세션 상태 확인
```bash
# 이전 세션이 있는지 확인하고 복원 여부 선택
python check_session.py
```

### 2. 수동 상태 저장 (필요시)
```python
from core.utils import save_session_state

# 플랜 상태 저장
save_session_state(
    plan_content="구현할 계획 내용",
    todos=[{"id": "1", "content": "작업1", "status": "pending"}],
    session_info={"action": "현재 진행 중인 작업"}
)
```

### 3. 상태 로드
```python
from core.utils import load_session_state

# 이전 세션 상태 확인
state = load_session_state()
if state.get("has_active_plan"):
    print("이전 플랜이 있습니다!")
```

## 📁 저장 구조

```
.claude_state/
├── current_plan.json     # 현재 플랜 상태
├── todo_state.json      # TODO 목록과 진행률
└── session_info.json    # 세션 정보
```

### current_plan.json 구조
```json
{
  "is_active": true,
  "plan_content": "구현할 계획 내용",
  "status": "approved",
  "created_at": "2025-07-14T11:00:00",
  "last_updated": "2025-07-14T11:00:00"
}
```

### todo_state.json 구조
```json
{
  "todos": [
    {
      "id": "1",
      "content": "작업 내용",
      "status": "in_progress",
      "priority": "high"
    }
  ],
  "total_count": 6,
  "completed_count": 0,
  "in_progress_count": 1,
  "last_updated": "2025-07-14T11:00:00"
}
```

## 🔧 고급 기능

### 1. 상태 관리 API
```python
from core.claude_state.session_manager import create_session_manager

manager = create_session_manager()

# 플랜 상태 업데이트
manager.update_plan_status("completed")

# 상태 요약 확인
print(manager.get_state_summary())

# 모든 상태 초기화
manager.clear_all_state()
```

### 2. 세션 복원 자동화
프로젝트 시작 시 자동으로 세션 복원을 체크하려면:

```python
from core.utils import check_and_restore_session

# 프로젝트 시작 시 호출
if check_and_restore_session():
    print("이전 세션 복원됨")
else:
    print("새 세션 시작")
```

## 🛡️ 보안 및 프라이버시

- **개인 정보 보호**: `.claude_state/` 디렉토리는 자동으로 `.gitignore`에 추가
- **로컬 저장**: 모든 상태는 로컬 파일시스템에만 저장
- **안전한 삭제**: 상태 삭제 시 확인 절차 포함

## 📋 실제 사용 예시

### 시나리오 1: 작업 중단 후 재개
```bash
# 1. 작업 중 터미널 종료
# 2. 새 터미널에서 프로젝트 재시작
python check_session.py

# 출력:
# 🔄 이전 세션 발견!
# 📋 활성 플랜: approved (2025-07-14 11:00)
# ✅ TODO: 2/6 완료, 1개 진행중
# 
# 1. 이전 작업 계속하기 ← 선택
# 2. 새로 시작하기
# 3. 상태 삭제하기
```

### 시나리오 2: 팀원과 작업 인수인계
```bash
# 상태 요약 확인
python -c "
from core.claude_state.session_manager import create_session_manager
manager = create_session_manager()
print(manager.get_state_summary())
"

# 출력:
# 📊 현재 세션 상태:
# 📋 활성 플랜: approved (2025-07-14 11:00)
# ✅ TODO: 2/6 완료, 1개 진행중
# 🕒 마지막 세션: 2025-07-14 11:00
```

## 🚨 주의사항

1. **동시 실행**: 여러 세션에서 동시에 상태를 수정하면 충돌 가능
2. **디스크 공간**: 상태 파일은 작지만 정기적으로 정리 권장
3. **버전 호환성**: 다른 버전의 Claude Code와 호환되지 않을 수 있음

## 🔧 문제 해결

### 상태 파일 손상 시
```bash
# 모든 상태 초기화
python -c "
from core.claude_state.session_manager import create_session_manager
create_session_manager().clear_all_state()
"
```

### 권한 문제 시
```bash
# 상태 디렉토리 권한 확인
ls -la .claude_state/
chmod 755 .claude_state/
```

---

이제 **터미널이 바뀌어도 Claude가 이전 작업을 기억합니다!** 🎉