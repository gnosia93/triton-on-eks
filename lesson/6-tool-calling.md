```
cat << 'EOF' > requirements.txt
langgraph==1.1.6
langchain-aws==1.4.1
langchain-core==1.2.26
boto3==1.42.52
EOF

pip install -r requirements.txt
```

[simple_tool.py]
```
cat << 'EOF' > simple_tool.py
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_aws import ChatBedrockConverse
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# 1. 툴 정의
@tool
def get_weather(city: str) -> str:
    """특정 도시의 현재 날씨를 조회합니다."""
    fake_db = {
        "서울": "맑음, 18°C",
        "부산": "흐림, 20°C",
        "제주": "비, 16°C",
    }
    return fake_db.get(city, f"{city}의 날씨 정보가 없습니다.")

@tool
def calculator(expression: str) -> str:
    """수식을 계산합니다. 예: '2 + 3 * 4'"""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"계산 오류: {e}"

tools = [get_weather, calculator]

# 2. 상태 정의
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# 3. Bedrock LLM에 툴 바인딩
llm = ChatBedrockConverse(
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name="us-west-2",
    temperature=0,
)
llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# 4. 그래프 구성
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools))

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()

# 5. 실행
if __name__ == "__main__":
    question = "서울 날씨 알려주고, 15 * 23도 계산해줘"
    result = graph.invoke({"messages": [HumanMessage(content=question)]})
    
    for msg in result["messages"]:
        msg.pretty_print()
EOF
```
