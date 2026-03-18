## Foundation 모델 ##
* https://huggingface.co/Qwen/Qwen3.5-27B
```
Qwen3.5 (2026년 2월):
  - Agentic AI 시대를 위해 설계 ← 딱 맞음
  - 네이티브 멀티모달 (텍스트 + 이미지 + 비디오)
  - 하이브리드 아키텍처 (Gated DeltaNet + MoE)
  - 256K 컨텍스트
  - 201개 언어
```

## 1. General Benchmark (범용 밴치마크) ##
* https://github.com/EleutherAI/lm-evaluation-harness
```
pip install lm-eval

import sys
!{sys.executable} -m lm_eval --model hf \
  --model_args pretrained=Qwen/Qwen3.5-27B,dtype=bfloat16 \
  --tasks mmlu,arc_challenge,gsm8k,hellaswag,lambada_openai,winogrande,truthfulqa_mc2,openbookqa,toxigen,bbq \
  --batch_size 4 \
  --limit 100 \
  --output_path ./eval_results/
```

### 5가지 평가영역 ###

| 영역 | 벤치마크 1 | 설명 | 벤치마크 2 | 설명 |
|------|-----------|------|-----------|------|
| Knowledge/Understanding | mmlu | 57개 학문 분야 지식 평가 (수학, 역사, 법률 등) | arc_challenge | 초등~중등 수준 과학 추론 (어려운 버전) |
| Reasoning | gsm8k | 초등 수학 문장제 풀이 (다단계 추론) | hellaswag | 문장 완성 기반 상식 추론 |
| Conversation | lambada_openai | 긴 문맥에서 마지막 단어 예측 (문맥 이해력) | winogrande | 대명사 참조 해석 (문맥 파악 능력) |
| Human Preference | truthfulqa_mc2 | 거짓/오해 유발 답변 생성 여부 (환각 측정) | openbookqa | 기본 과학 상식 + 추론 결합 |
| Safety | toxigen | 유해/혐오 발언 생성 여부 측정 | bbq | 사회적 편향 (성별, 인종, 나이 등) 측정 |

### 평가 샘플 ###
![](https://github.com/gnosia93/agentic-ai-eks/blob/main/lesson/images/lm-eval.png)


## 2. Domain Benchmark (도메인 벤치마크) ##
PPL(Perplexity)은 모델이 주어진 텍스트를 얼마나 "당연하게" 예측하는지를 측정하는 지표로, 수학적으로는 모델이 다음 토큰을 예측할 때의 평균 불확실성이다.
```
PPL = exp(-1/N × Σ log P(token_i | token_1, ..., token_i-1))
```
* PPL = 1: 모델이 다음 단어를 100% 확신 (완벽한 예측)
* PPL = 10: 매 토큰마다 평균 10개 후보 중 고민
* PPL = 100: 매 토큰마다 100개 후보 중 고민 (잘 모르는 도메인)
PPL 값이 낮을수록 좋다.

#### #### 
파인튜닝 전후로 모델에 대한 PPL 값을 측정하여 비교하면 해당 모델에 대한 도메인 이해도를 비교 측저할 수 있다. 예를 들어
```
파인튜닝 전 도메인 PPL: 15.3
파인튜닝 후 도메인 PPL: 4.2 
```
인 경우 도메인에 대한 이해도가 향상된 것이다.   

#### #### 
동시에 일반 텍스트에 대한 PPL도 같이 측정해서, 일반 PPL이 크게 올라가면 catastrophic forgetting이 발생한 거라고 판단할 수 있다.
```
              도메인 PPL    일반 PPL
파인튜닝 전     15.3         8.1
파인튜닝 후      4.2         8.5   ← 일반 능력 유지, 도메인 향상 (좋음)
파인튜닝 후      4.2        25.0   ← catastrophic forgetting (나쁨)
```
한마디로 PPL은 "모델이 이 도메인 텍스트를 얼마나 자연스럽게 느끼는가"의 수치화이고, 파인튜닝 효과를 정량적으로 검증하는 가장 기본적인 방법이다.

### 2-1. PPL 측정 ###
![](https://github.com/gnosia93/agentic-ai-eks/blob/main/lesson/images/qwen-ppl.png)
* https://github.com/gnosia93/agentic-ai-eks/blob/main/code/qwen_ppl.py 

### 2-2. 도메인 밴치마크 툴 사용 ###
* 코딩: HumanEval, MBPP, DS-1000, SWE-bench
* 의료: MedQA, PubMedQA, MedMCQA, BioASQ
* 법률: LegalBench, LEXTREME, CaseHOLD
* 금융: FinBen, FLUE, ConvFinQA
* 수학/과학: MATH, GPQA, SciQ, TheoremQA
* 다국어: KMMLU, C-Eval, JMMLU
* 에이전트: BFCL, ToolBench, AgentBench

## 3. LLM-as-a-Judge ##
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

## 4. 추론 성능 (Inference Performance) ##
- Throughput: 초당 처리 토큰 수 (tokens/sec)
- Latency: 첫 토큰까지 시간 (TTFT), 토큰 간 시간 (TBT)
- 동시 처리: 동시 요청 수 대비 처리량

## 레퍼런스 ##
* https://artificialanalysis.ai/leaderboards/models

