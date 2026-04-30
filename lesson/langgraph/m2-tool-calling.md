## 2. 도구 + 조건부 라우팅 + HITL ##

### 1. 왜 이 패턴을 배우는가 ###
챕터 1에서 만든 그래프는 정해진 순서대로 흐르는 파이프라인이었다. 하지만 실제 에이전트는 상황에 따라 다르게 움직여야 한다.

* 사용자의 질문을 보고 어떤 도구를 쓸지 LLM이 결정해야 한다
* 필요하면 도구를 여러 번 반복 호출해야 한다 (ReAct 루프)
* 돈이 드는 작업이나 되돌릴 수 없는 작업은 사람의 승인을 받아야 한다
이 세 가지를 조합한 구조가 업무용 에이전트의 표준 뼈대다.

### 2. 핵심 개념 ###
#### 2-1. 도구 — @tool 데코레이터 ####
함수에 @tool만 붙이면 LangChain 표준 도구가 된다. LLM 은 독스트링을 보고 "언제 이 도구를 쓸지" 판단한다. 독스트링이 부실하면 LLM이 엉뚱한 도구를 고른다. ```
from langchain_core.tools import tool

@tool
def get_pricing(instance_type: str) -> str:
    """EC2 인스턴스 타입의 시간당 가격(USD)을 조회한다.
    예: 'c7i.large', 'c7g.large'
    """
    ...
```

#### 2-2. ToolNode — 도구 실행을 담당하는 노드 ####
LangGraph가 제공하는 기성 노드. LLM이 tool_calls를 만들면, ToolNode가 그걸 파싱해서 실제 함수를 호출하고 결과를 ToolMessage로 상태에 넣는다. 직접 구현할 수 있지만 99%는 이걸 쓰면 된다.
```
from langgraph.prebuilt import ToolNode
tool_node = ToolNode([get_pricing, list_ec2_instances, ...])
```

#### 2-3. 조건부 엣지 — tools_condition ####
"LLM이 도구를 호출했는가?"를 보고 분기한다.

* LLM이 tool_calls를 만들었다 → tools 노드로
* 그냥 최종 답변만 했다 → END로
```
from langgraph.prebuilt import tools_condition

builder.add_conditional_edges("agent", tools_condition)
#                                       ↑ 라우팅 함수가 다음 노드 이름을 반환
builder.add_edge("tools", "agent")      # 도구 실행 후 다시 LLM에게
```
이 구조가 ReAct 루프다. 도구 호출이 없어질 때까지 agent ↔ tools를 오간다.

#### 2-4. Human-in-the-loop — interrupt ####
특정 지점에서 그래프 실행을 멈추고, 외부(사람)로부터 값을 받아 재개한다.
```
from langgraph.types import interrupt, Command

def human_approval(state):
    decision = interrupt({
        "question": "정말로 이 인스턴스를 종료할까요?",
        "tool_call": state["messages"][-1].tool_calls[0],
    })
    # ↑ 여기서 그래프가 멈춤. 외부에서 Command(resume=...)로 재개해야 함
    
    if decision == "approve":
        return {"approved": True}
    return {"approved": False}
```
재개는 이렇게 한다.
```
graph.invoke(Command(resume="approve"), config=...)
```
interrupt는 체크포인터가 있어야 동작한다. 실습에서는 MemorySaver를 붙인다.

### 3. 그래프 구조 ###
```
       ┌─────────┐
START ▶│  agent  │◀──────────┐
       └────┬────┘           │
            │                │
   tools_condition           │
            │                │
     ┌──────┴──────┐         │
     ▼             ▼         │
 ┌───────┐        END        │
 │ tools │──────────────────┘
 └───┬───┘
     │ (민감 도구면)
     ▼
 ┌─────────┐       ┌─────────┐
 │approval │──────▶│ execute │
 └─────────┘       └─────────┘
```
