Speculative Decoding 은 추론 latency를 줄이는 핵심 기법 중 하나로 작은 모델(draft)이 먼저 여러 토큰을 추측 생성하고, 큰 모델(target)이 한 번에 검증하는 방식으로 추론 속도를 높이는 방식이다.

### vLLM 설정 ###
```
args:
  - "--model=Qwen/Qwen2.5-Coder-27B-Instruct"
  - "--tensor-parallel-size=4"
  - "--max-model-len=4096"
  - "--gpu-memory-utilization=0.90"
  - "--speculative-model=Qwen/Qwen2.5-Coder-3B-Instruct"
  - "--num-speculative-tokens=5"
```
* --speculative-model	추측 생성에 사용할 draft 모델
* --num-speculative-tokens	draft 모델이 한 번에 추측할 토큰 수 (5가 일반적)
* draft 모델(3B)은 target 모델(27B)과 같은 GPU 메모리에 함께 로드된다. 3B 모델은 약 6GB 정도 차지하므로 L40S 48GB × 4 구성에서 메모리 여유가 충분하다.


### TensorRT-LLM 설정 ###


## 레퍼런스 ##
* https://www.baseten.co/blog/how-we-built-production-ready-speculative-decoding-with-tensorrt-llm/#speculative-decoding-in-tensorrt-llm
* https://developer.nvidia.com/ko-kr/blog/an-introduction-to-speculative-decoding-for-reducing-latency-in-ai-inference/
