## LangGraph로 Agentic AI 만들기 ##

```
사용자: "요즘 LLM 추론 최적화 트렌드가 뭐야?"
     ↓
에이전트:
  1. 질문 분석 → 검색 전략 수립
  2. [tool] paper_search(RAG MCP)로 관련 논문 찾기
  3. [tool] web_search로 최신 블로그/뉴스 보강
  4. 결과 비교/종합
  5. 필요하면 후속 검색 (인용 논문 추적)
  6. 요약 + 출처 정리해서 답변
```
### [1. 주피터 설정] ###

### [2. @tool 콜링](https://github.com/gnosia93/langgraph-agentic-ai/blob/main/lesson/6-tool-calling.md) ###

### 3. OAuth ###


### 4. 상태와 메모리 ###
  - LangGraph State: 그래프 전체에서 공유되는 상태
  - 단기 메모리: 대화 컨텍스트 (MessagesState)
  - 장기 메모리: 사용자 프로필, 선호도 (외부 저장소)
  - 실습: 이전 대화 기억하는 에이전트

### 5. 세션과 영속성 ###
  - Checkpointer: 대화 상태 저장/복구
  - 세션 ID 관리, 타임아웃
  - 실습: Redis/Postgres 체크포인터 붙이기

### [6. 관측성 (Langfuse)](https://github.com/gnosia93/langgraph-agentic-ai/blob/main/lesson/6-langfuse.md) ###

### [7. Open WebUI 연동](https://github.com/gnosia93/langgraph-agentic-ai/blob/main/lesson/6-llm-webui.md) ###
 
### 2. RAG를 에이전트 도구로 (L5와 연결) ###
  - L5에서 만든 RAG를 @tool로 감싸기
  - 에이전트가 "검색이 필요한지" 스스로 판단
  - 실습: 질문에 따라 RAG 쓸지 말지 결정하는 에이전트
