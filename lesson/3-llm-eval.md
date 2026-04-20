### 수정할 내용 ###
```
 3.1 후보 모델 선정
      - 오픈소스 LLM 현황 (Llama 3.1, Qwen 2.5, Mistral, Gemma, Phi 등)
      - 크기별 트레이드오프 (7B / 13B / 32B / 70B+)
      - 라이선스 체크 (상업 이용 가능 여부)

  3.2 평가 축 4가지
      - 일반 능력: lm-eval-harness (MMLU, ARC, HellaSwag)
      - 언어 모델링: Perplexity
      - 도메인 적합성: 커스텀 벤치마크
      - 응답 품질: LLM-as-a-Judge

  3.3 인프라 제약 평가
      - GPU 메모리 요구량 (A10G/L4/A100/H100)
      - 추론 속도 / 처리량 (tokens/sec)
      - 배포 비용 (시간당 $$)

  3.4 비교 매트릭스와 최종 선택
      - 점수표 작성
      - "우리 서비스에 Qwen2.5-32B를 선택한 이유"
```













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

## 1. General Benchmark (범용 벤치마크) ##
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

### 2-1. PPL ###
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




## 레퍼런스 ##
* https://artificialanalysis.ai/leaderboards/models

