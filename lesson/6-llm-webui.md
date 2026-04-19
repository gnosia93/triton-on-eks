
### 아키텍처 ###
```
사용자
  ↓ HTTP
Open WebUI (프론트엔드)
  ↓ OpenAI-compatible API (/v1/chat/completions)
FastAPI (OpenAI API 호환 레이어)
  ↓ invoke()
LangGraph Agent (워크플로우)
  ├─ Tool: RAGSearch (Milvus)
  ├─ Tool: web_fetch
  ├─ Tool: ...
  └─ Bedrock (LLM)
```
Open WebUI는 백엔드가 OpenAI API 호환 스펙만 지키면 무엇이든 통합할 수 있다.
* FastAPI가 POST /v1/chat/completions 엔드포인트를 가지고
* 요청 받아 LangGraph 에이전트 실행
* 결과를 OpenAI 응답 포맷으로 감싸서 반환

