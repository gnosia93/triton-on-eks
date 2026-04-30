### 1. 왜 LangGraph인가 ###

#### 체인의 한계 ####
LangChain의 체인은 선형 파이프라인이다. 프롬프트 → LLM → 파서 같은 단방향 흐름엔 훌륭하지만, 아래 상황에선 금세 한계에 부딪힌다.

* LLM의 응답에 따라 다음 단계가 바뀌어야 할 때 (조건 분기)
* 같은 단계를 여러 번 돌아야 할 때 (루프, ReAct)
* 중간에 사람의 승인을 받고 재개해야 할 때 (HITL)
* 여러 노드가 공유 상태를 읽고 써야 할 때
* 체인은 이런 흐름을 if/else로 우겨넣거나 별도 오케스트레이터를 붙여야 해서 복잡해진다.

#### 그래프로 넘어가는 이유 ####
LangGraph는 상태 기반 그래프다. 노드는 상태를 입력받아 상태의 변경분을 돌려주고, 엣지는 어느 노드로 갈지를 결정한다. 이 모델이 주는 이점:

* 분기·루프·사람 개입 같은 비선형 흐름을 일급으로 표현
* 각 노드 실행 후 상태를 체크포인트로 저장해 중단·재개 가능
* 그래프 구조를 시각화할 수 있어 디버깅이 쉬움
* 한 줄 요약: 에이전트가 "LLM이 뭘 할지 결정하는 루프"가 되려면 그래프가 자연스럽다.


### 2. 핵심 3요소 ###
#### State — 그래프가 공유하는 기억 ####
TypedDict나 Pydantic 모델로 정의한다. 모든 노드가 이 상태를 읽고, 부분 업데이트를 반환한다.
```
from typing import TypedDict

class State(TypedDict):
    input_text: str
    output_text: str
```
#### Node — 상태를 바꾸는 함수 ####
시그니처는 (state) -> dict. 반환한 dict가 상태에 병합된다. 반환하지 않은 키는 그대로 유지된다.
```
def upper_node(state: State) -> dict:
    return {"output_text": state["input_text"].upper()}
```

#### Edge — 노드 사이의 흐름 ####
START → node → END로 연결한다. 조건부 엣지(M2에서 다룸)로 분기도 만들 수 있다.

#### 리듀서 — 같은 키를 여러 번 업데이트할 때 ####
기본 동작은 덮어쓰기다. 그런데 메시지 리스트처럼 누적하고 싶은 키는 리듀서가 필요하다.
```
from typing import Annotated
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]  # 새 메시지를 기존 리스트에 "추가"
```
* add_messages가 없으면 매 노드마다 메시지 리스트가 통째로 교체돼 대화가 날아간다.

### 3. 전체흐름 ###
```
from langgraph.graph import StateGraph, START, END

builder = StateGraph(State)
builder.add_node("upper", upper_node)
builder.add_edge(START, "upper")
builder.add_edge("upper", END)
graph = builder.compile()

graph.invoke({"input_text": "hello"})
# {'input_text': 'hello', 'output_text': 'HELLO'}
```


### 4. 실습 시나리오 ###
영어 원문을 받아서 → translate 노드가 한국어로 번역 → summarize 노드가 한 줄 요약 → 최종 상태 반환.
```
"""
실습 1-2: 번역 → 요약 2-노드 파이프라인
"""
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class State(TypedDict):
    original: str        # 영어 원문
    translated: str      # 한국어 번역
    summary: str         # 한 줄 요약


def translate(state: State) -> dict:
    resp = llm.invoke(
        f"다음 영어 문장을 자연스러운 한국어로 번역하세요.\n\n{state['original']}"
    )
    return {"translated": resp.content}

def summarize(state: State) -> dict:
    resp = llm.invoke(
        f"다음 글을 한 문장으로 요약하세요.\n\n{state['translated']}"
    )
    return {"summary": resp.content}

def build_graph():
    builder = StateGraph(State)
    builder.add_node("translate", translate)
    builder.add_node("summarize", summarize)
    builder.add_edge(START, "translate")
    builder.add_edge("translate", "summarize")
    builder.add_edge("summarize", END)
    return builder.compile()

if __name__ == "__main__":
    graph = build_graph()
    text = (
        "LangGraph is a low-level framework for building stateful, "
        "multi-actor applications with LLMs. It extends LangChain "
        "with the ability to coordinate multiple chains across "
        "multiple steps of computation in a cyclic manner."
    )
    result = graph.invoke({"original": text})
    for k, v in result.items():
        print(f"[{k}]\n{v}\n")
```
