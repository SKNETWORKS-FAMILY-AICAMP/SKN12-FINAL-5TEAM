# Agents Directory

이 폴더는 미래에 MCP(Model Context Protocol) 및 Agent2Agent 기능 확장을 위해 준비되었습니다.

## 계획된 구조

```
agents/
├── protocols/
│   ├── mcp_protocol.py     # MCP 구현
│   └── agent2agent.py      # Agent2Agent 통신
├── coordination/
│   ├── message_broker.py   # 메시지 브로커
│   └── decision_engine.py  # 의사결정 엔진
└── registry/
    └── agent_registry.py   # 에이전트 등록/관리
```

## 미래 기능

- **MCP**: 면접관 AI들 간 컨텍스트 공유 및 협업
- **Agent2Agent**: 에이전트들 간 실시간 상호작용
- **멀티 에이전트 면접**: 여러 AI 후보자들과의 그룹 면접