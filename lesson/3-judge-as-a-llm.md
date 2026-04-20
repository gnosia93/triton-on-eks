## LLM-as-a-Judge ##

"LLM의 출력을 또 다른 LLM이 채점/비교하게 하는" 평가 방식으로, 사람이 일일이 라벨링하는 비용을 낮추면서도 BLEU/ROUGE 같은 표면적 지표보다 의미 기반 평가를 할 수 있다. 

### 1. 기본 세 가지 패턴 ###

#### Pointwise (단일 점수 매기기) ####
응답 하나를 주고 기준별로 점수를 매기게 함. 예: 정확성 15, 유용성 15.
* 장점: 절대 평가 가능, 여러 모델을 독립적으로 비교.
* 단점: 점수 분포가 판정 모델에 따라 편향됨. 보통 4~5에 몰리는 경향(positivity bias).

#### Pairwise (두 응답 비교) ####
같은 프롬프트에 대한 두 모델/버전의 답을 주고 "어느 쪽이 더 나은지" 고르게 함. A/B/Tie.
* 장점: 상대 평가라 점수 보정 필요 없고, 사람 평가와 가장 상관관계가 높다고 알려져 있음 (Chatbot Arena 방식).
* 단점: N개 모델 비교하려면 쌍 수가 많아짐. 위치 편향(앞에 놓인 답을 선호) 존재.

#### Reference-based (정답 비교) ####
정답(또는 이상적 답변)과 응답을 함께 주고 "의미적으로 일치하는지" 판단.
* RAG의 답변 정확성, QA 평가에 적합.

### 2. 평가 기준(Criteria) 정의 ###

* Correctness: 사실이 맞는가, 정답과 의미가 같은가
* Faithfulness / Groundedness: 제공된 context(RAG)만으로 답했는가, 환각 없는가
* Relevance: 질문에 실제로 답하고 있는가
* Completeness: 빠진 정보 없이 충분한가
* Coherence / Fluency: 논리적이고 읽기 좋은가
* Safety / Tone: 부적절한 내용이나 톤 문제 없는가

한 judge가 여러 기준을 동시에 채점하기보단, 기준별로 나눠 호출하거나 각 기준의 점수를 JSON으로 구조화하는 것이 좋다.


```
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")

def llm_judge(question, answer, criteria="정확성, 완전성, 실용성"):
    response = client.chat.completions.create(
        model="Qwen/Qwen3.5-27B",
        messages=[
            {"role": "system", "content": "당신은 AI 응답 품질 평가 전문가입니다."},
            {"role": "user", "content": f"""
다음 답변을 평가하세요.

[질문] {question}
[답변] {answer}
[평가 기준] {criteria}

각 기준별 1~5점과 이유를 JSON으로 출력:
{{"정확성": {{"score": N, "reason": "..."}}, "완전성": {{"score": N, "reason": "..."}}, "실용성": {{"score": N, "reason": "..."}}}}
"""}
        ],
        temperature=0
    )
    return response.choices[0].message.content

# 사용
result = llm_judge(
    question="EFA와 일반 네트워크의 차이점은?",
    answer="EFA는 OS bypass로 저지연 통신을 제공합니다."
)
print(result)
```
* 평가 LLM은 평가 대상 모델보다 같거나 더 강한 모델을 써야 한다. (보통 GPT-4, Claude 등)
* 자기 자신을 평가하면 자기 편향(self-bias)이 생김
* Pairwise에서 답변 순서를 바꿔서 2번 평가하면 위치 편향(position bias)을 줄일 수 있음
  
프로덕션에서는 사용자 요청과 LLM 응답을 로깅하고, 로그중 일부를 샘플링하여 비동기로 백그라운드에서 LLM Judge를 돌리고, 결과를 Prometheus 메트릭으로 수집하는 방식으로 운영.
* 도구: MT-Bench, AlpacaEval, G-Eval, 직접 구현
* 방식: Single Rating, Pairwise Comparison, Reference-based

