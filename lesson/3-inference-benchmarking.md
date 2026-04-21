## 인퍼런스 벤치마킹 ##

### 종합 선택 기준 ###

실무에서 모델 고를 때 체크하는 것들:

* 품질: MMLU, 도메인 벤치, LLM-as-Judge 점수
* 속도: TTFT, TPOT(Time Per Output Token), ITL(Inter-Token Latency), Throughput
* 메모리: VRAM 요구량, 최대 컨텍스트 길이
* 라이선스: 상업 사용 가능 여부
* 언어: 한국어 지원 수준
운영 비용: 위 1+2+3 합산해서 "달러당 품질"

### llmperf(Anyscale) 를 활용한 측정 ###
```
git clone https://github.com/ray-project/llmperf.git
cd llmperf
pip install -e .
```
```
export OPENAI_API_BASE="http://localhost:8000/v1"
export OPENAI_API_KEY="dummy"

python token_benchmark_ray.py \
  --model "Qwen/Qwen2.5-7B-Instruct" \
  --mean-input-tokens 1024 \
  --stddev-input-tokens 200 \
  --mean-output-tokens 128 \
  --stddev-output-tokens 30 \
  --max-num-completed-requests 100 \
  --num-concurrent-requests 8 \
  --llm-api openai
```
