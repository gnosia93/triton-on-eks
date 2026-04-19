## FastAPI + LangGraph ##
```
import json
import time
import uuid
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.graph import StateGraph
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# (여기서는 간단히 구조만. 실제 LangGraph 에이전트는 별도 모듈로 분리 추천)
from my_agent import build_agent   # LangGraph 워크플로우 빌드 함수


app = FastAPI(title="Agentic AI Gateway")

# 에이전트는 프로세스 시작 시 한 번만 빌드
agent = build_agent()


# ---------- Pydantic 모델 (OpenAI 스펙) ----------

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = 0.2
    max_tokens: int | None = None


# ---------- /v1/models ----------

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "agentic-rag",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "workshop",
            }
        ],
    }


# ---------- /v1/chat/completions ----------

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    # OpenAI 메시지 → LangChain 메시지로 변환
    lc_messages = []
    for m in req.messages:
        if m.role == "system":
            lc_messages.append(SystemMessage(content=m.content))
        elif m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))

    if req.stream:
        return StreamingResponse(
            stream_agent(lc_messages, req.model),
            media_type="text/event-stream",
        )

    # Non-stream: 한 번에 결과 반환
    result = await agent.ainvoke({"messages": lc_messages})
    answer = result["messages"][-1].content

    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": answer},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


# ---------- 스트리밍 ----------

async def stream_agent(messages, model: str) -> AsyncIterator[str]:
    """LangGraph의 astream으로 토큰 단위 스트리밍."""
    chat_id = f"chatcmpl-{uuid.uuid4()}"
    created = int(time.time())

    # LangGraph가 노드 단위로 결과를 흘려보냄
    async for chunk in agent.astream(
        {"messages": messages},
        stream_mode="messages",   # 토큰 단위
    ):
        # chunk 구조는 LangGraph 설정에 따라 다름
        # 예시: (message_chunk, metadata) 튜플
        if isinstance(chunk, tuple):
            msg_chunk = chunk[0]
            content = getattr(msg_chunk, "content", "")
        else:
            content = str(chunk)

        if not content:
            continue

        payload = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None,
            }],
        }
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    # 마지막에 종료 시그널
    done_payload = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(done_payload)}\n\n"
    yield "data: [DONE]\n\n"


# ---------- 헬스체크 ----------

@app.get("/health")
async def health():
    return {"status": "ok"}
```

실행:
```
pip install fastapi uvicorn langgraph langchain-aws
uvicorn agent_gateway:app --host 0.0.0.0 --port 8000
```

----

고려할 포인트

1. 스트리밍이 중요
Open WebUI는 스트리밍을 기대해요. 한 번에 답 주면 사용자가 몇 초씩 기다려야 함. LangGraph의 astream(stream_mode="messages") 꼭 쓰세요.

2. Tool 호출 진행 표시
고급 사용자 경험을 위해, Tool 실행 중 상태를 사용자에게 보여주면 좋아요:

🔍 Milvus에서 검색 중...
📊 재순위화 중...
💭 답변 생성 중...
Open WebUI가 "thinking" 블록을 지원하는데 <thinking>...</thinking> 태그나 o1 스타일 reasoning_content 포맷 쓰면 접어서 보여줘요.

3. 세션/메모리 관리
Open WebUI는 대화 이력을 messages 배열로 매번 다시 보내요. LangGraph의 Checkpointer(Memory)와 겹치면 이중 저장 돼서 혼란스러울 수 있어요.

두 전략 중 선택:

A. Open WebUI에만 맡기기: LangGraph는 매 요청 stateless, messages 그대로 사용
B. LangGraph가 주도: conversation_id를 커스텀 헤더로 받아 Checkpointer 관리
워크샵용이면 A가 간단.

4. 에러 처리
LangGraph에서 예외 나면 Open WebUI는 응답이 오기를 계속 기다려요. 에러도 OpenAI 포맷으로 반환:

from fastapi import HTTPException

try:
    result = await agent.ainvoke({"messages": lc_messages})
except Exception as e:
    return {
        "error": {
            "message": str(e),
            "type": "internal_error",
            "code": 500,
        }
    }
5. 인증 (프로덕션)
"API Key: dummy"는 교육용. 프로덕션이면:

API Key 검증 미들웨어
ALB + Cognito
mTLS (사내 Zero Trust 환경)






## @tool 콜링 ##

* [셀 1] 임포트
```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import random
```

* [셀 2] @tool 선언
```python
# ──────────────────────────────────────
# 1. IT 운영 도구 정의
# ──────────────────────────────────────

@tool
def check_server_status(hostname: str) -> str:
    """서버의 현재 상태(CPU, 메모리, 디스크)를 조회합니다."""
    # 실제로는 Prometheus API, SSH 등으로 조회
    data = {
        "api-server-01": {"cpu": 72, "memory": 85, "disk": 45, "status": "running", "uptime": "32일"},
        "api-server-02": {"cpu": 23, "memory": 41, "disk": 38, "status": "running", "uptime": "32일"},
        "db-master":     {"cpu": 91, "memory": 93, "disk": 78, "status": "warning", "uptime": "120일"},
        "redis-01":      {"cpu": 15, "memory": 62, "disk": 20, "status": "running", "uptime": "45일"},
    }
    info = data.get(hostname)
    if not info:
        return f"호스트 '{hostname}'을 찾을 수 없습니다. 사용 가능: {list(data.keys())}"
    return (f"[{hostname}] 상태: {info['status']}, "
            f"CPU: {info['cpu']}%, MEM: {info['memory']}%, "
            f"DISK: {info['disk']}%, 업타임: {info['uptime']}")


@tool
def query_database(sql: str) -> str:
    """데이터베이스에 SQL 쿼리를 실행합니다. SELECT 쿼리만 허용됩니다."""
    # 실제로는 DB 커넥션으로 실행
    if not sql.strip().upper().startswith("SELECT"):
        return "오류: SELECT 쿼리만 허용됩니다."

    # 더미 결과
    if "error_log" in sql.lower():
        return ("최근 에러 로그:\n"
                "| timestamp           | level | service    | message                    |\n"
                "|---------------------|-------|------------|----------------------------|\n"
                "| 2026-03-21 04:32:11 | ERROR | auth-api   | Connection timeout to DB   |\n"
                "| 2026-03-21 04:33:45 | ERROR | auth-api   | Connection timeout to DB   |\n"
                "| 2026-03-21 04:35:02 | WARN  | payment-api| Slow query detected (3.2s) |\n"
                f"총 3건")
    elif "active_user" in sql.lower() or "session" in sql.lower():
        return "현재 활성 세션: 1,247개, 최근 1시간 신규 로그인: 342건"
    else:
        return "쿼리 실행 완료. 결과: 0건"


@tool
def check_pod_status(namespace: str) -> str:
    """Kubernetes 네임스페이스의 Pod 상태를 조회합니다."""
    pods = {
        "production": [
            {"name": "auth-api-7d8f9-xk2lm", "status": "Running", "restarts": 0, "age": "5d"},
            {"name": "auth-api-7d8f9-mn4qr", "status": "Running", "restarts": 0, "age": "5d"},
            {"name": "payment-api-3b2c1-ab8cd", "status": "Running", "restarts": 2, "age": "3d"},
            {"name": "gateway-5f4e3-zz9yy", "status": "CrashLoopBackOff", "restarts": 15, "age": "1d"},
        ],
        "staging": [
            {"name": "auth-api-staging-abc12", "status": "Running", "restarts": 0, "age": "2d"},
            {"name": "payment-api-staging-def34", "status": "Running", "restarts": 0, "age": "2d"},
        ]
    }
    pod_list = pods.get(namespace)
    if not pod_list:
        return f"네임스페이스 '{namespace}'를 찾을 수 없습니다."

    lines = [f"[{namespace}] Pod 목록:"]
    for p in pod_list:
        icon = "✅" if p["status"] == "Running" else "❌"
        lines.append(f"  {icon} {p['name']} | {p['status']} | 재시작: {p['restarts']}회 | {p['age']}")
    return "\n".join(lines)


@tool
def rollback_deployment(service: str, version: str) -> str:
    """서비스를 특정 버전으로 롤백합니다. 주의: 프로덕션에 영향을 줍니다."""
    valid_services = ["auth-api", "payment-api", "gateway", "user-api"]
    if service not in valid_services:
        return f"서비스 '{service}'를 찾을 수 없습니다. 사용 가능: {valid_services}"
    return f"✅ [{service}] v{version}으로 롤백 완료. 새 Pod 생성 중... (예상 소요: 30초)"


@tool
def get_deploy_history(service: str) -> str:
    """서비스의 최근 배포 이력을 조회합니다."""
    history = {
        "gateway": [
            "v2.3.1 (2026-03-21 03:00) ← 현재 ❌ CrashLoopBackOff",
            "v2.3.0 (2026-03-20 14:00) ← 정상 운영됨",
            "v2.2.9 (2026-03-18 10:00)",
        ],
        "auth-api": [
            "v1.8.2 (2026-03-16 09:00) ← 현재",
            "v1.8.1 (2026-03-10 11:00)",
        ]
    }
    h = history.get(service)
    if not h:
        return f"'{service}'의 배포 이력이 없습니다."
    return f"[{service}] 배포 이력:\n" + "\n".join(f"  {i+1}. {v}" for i, v in enumerate(h))

tools = [check_server_status, query_database, check_pod_status, rollback_deployment, get_deploy_history]
```

* [셀3] 에이전트 구성
```python
# ──────────────────────────────────────
# 2. 에이전트 구성
# ──────────────────────────────────────
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools(tools)

class State(TypedDict):
    messages: Annotated[list, add_messages]

def agent(state: State):
    system_msg = {
        "role": "system",
        "content": "당신은 IT 인프라 운영 전문가입니다. 서버 상태, DB, K8s를 모니터링하고 장애를 진단합니다."
    }
    response = llm_with_tools.invoke([system_msg] + state["messages"])
    return {"messages": [response]}

tool_node = ToolNode(tools)

def should_use_tool(state: State):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

graph_builder = StateGraph(State)
graph_builder.add_node("agent", agent)
graph_builder.add_node("tools", tool_node)
graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", should_use_tool)
graph_builder.add_edge("tools", "agent")

agent = graph_builder.compile()
```

* [셀4] 테스트 / 실행
```python
# ──────────────────────────────────────
# 3. 실행 예시
# ──────────────────────────────────────

# 예시 1: 장애 진단
result = agent.invoke({
    "messages": [{"role": "user", "content": "프로덕션에 문제 있는 것 같아. Pod 상태 확인해줘"}]
})
print(result["messages"][-1].content)

# 예시 2: 연쇄 조사 (도구 여러 번 호출)
result = agent.invoke({
    "messages": [{"role": "user", "content": "db-master 서버 상태 확인하고, 관련 에러 로그도 조회해줘"}]
})
print(result["messages"][-1].content)

# 예시 3: 롤백 판단
result = agent.invoke({
    "messages": [{"role": "user", "content": "gateway가 CrashLoop인데, 배포 이력 보고 이전 버전으로 롤백해줘"}]
})
print(result["messages"][-1].content)
```



