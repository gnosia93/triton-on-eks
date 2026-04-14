핵심은 "에이전트가 뭘 했는지(trajectory)"와 "결과가 좋은지(llm-rubric)"를 분리해서 테스트하는 것이다. 도구를 제대로 골랐는데 답변이 구리면 프롬프트 문제이고, 도구를 잘못 골랐으면 라우팅 로직 문제인 것이다.

### 1. 단위 테스트: 개별 도구/노드 테스트 ###
에이전트의 각 구성 요소를 독립적으로 테스트 하는것으로 일반 소프트웨어 단위 테스트와 동일하다.

[단위 테스트 샘플]
```
# pytest로 LangGraph 노드 개별 테스트
import pytest

def test_search_tool():
    result = search_tool.invoke({"query": "EKS 버전"})
    assert result is not None
    assert len(result) > 0

def test_retriever_node():
    state = {"question": "쿠버네티스란?"}
    result = retriever_node(state)
    assert "documents" in result
    assert len(result["documents"]) > 0
```
* 각 도구가 정상 동작하는가
* 각 노드가 올바른 출력을 내는가


### 2. 통합 테스트: 에이전트 전체 흐름 테스트 ###
에이전트가 올바른 도구를 올바른 순서로 호출하는지 검증하는 것으로 promptfoo의 trajectory assert 를 활용한다.
```
# promptfooconfig.yaml
providers:
  - id: http://localhost:8000/agent  # 에이전트 API 엔드포인트

tests:
  - vars:
      input: "서울 날씨 알려줘"
    assert:
      # 올바른 도구를 호출했는가
      - type: trajectory:tool-used
        value: weather_search

      # 도구 호출 순서가 맞는가
      - type: trajectory:tool-sequence
        value:
          - weather_search
          - format_response

      # 도구에 올바른 인자를 넘겼는가
      - type: trajectory:tool-args-match
        value:
          tool: weather_search
          args:
            location: "서울"

      # 최종 응답 품질
      - type: llm-rubric
        value: "서울의 현재 날씨 정보가 포함되어 있는가?"

  - vars:
      input: "이 PDF 요약해줘"
    assert:
      - type: trajectory:tool-used
        value: document_reader
      - type: trajectory:goal-success
        value: "사용자가 요청한 문서를 요약했는가?"
```
* 에이전트가 올바른 도구를 호출하는가 (trajectory:tool-used)
* 호출 순서가 맞는가 (trajectory:tool-sequence)
* 최종 응답 품질이 기준을 충족하는가 (llm-rubric)
* 보안 취약점은 없는가 (red-team)

### 3. CI/CD 파이프라인에 통합 ###

[github action 샘플]
```
# .github/workflows/agent-test.yml
name: Agent Test

on:
  pull_request:
    paths:
      - 'agent/**'
      - 'prompts/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # 단위 테스트
      - name: Unit Tests
        run: pytest tests/unit/

      # 에이전트 서버 띄우기
      - name: Start Agent
        run: docker compose up -d agent

      # promptfoo로 에이전트 통합 테스트
      - name: Agent Eval
        run: npx promptfoo@latest eval --ci
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      # 결과 확인 (실패 시 PR 블록)
      - name: Check Results
        run: npx promptfoo@latest eval --ci --fail-on-error
```


