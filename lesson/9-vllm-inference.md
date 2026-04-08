## vLLM 배포하기 ##

Qwen2.5-27B 모델을 g6e.12xlarge (L40S 48GB * 4EA, TP=4) 설정으로 2개의 파드로 구성한다.
[g6e.12xlarge](https://aws.amazon.com/ko/ec2/instance-types/g6e/) 인스턴스는 2대가 필요하다.

* https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/yaml/vllm-qwen.yaml
```bash
curl -o vllm-qwen.yaml https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/yaml/vllm-qwen.yaml
kubectl -f vllm-qwen.yaml
```

vLLM은 시작 시 먼저 모델 가중치를 GPU 메모리에 로드하고, gpu-memory-utilization 설정값에 따라 사용 가능한 전체 메모리 범위를 결정한다. 그런 다음 모델 가중치와 내부 버퍼를 제외한 나머지 메모리를 KV Cache로 자동 할당하며, 이 KV Cache 크기와 max-model-len을 기반으로 동시에 처리할 수 있는 최대 요청 수를 자동으로 결정한다.
모델 가중치 로드 → 남은 메모리 계산 (gpu-memory-utilization 기준) → 남은 메모리를 KV Cache로 자동 할당 → KV Cache 크기 + max-model-len 기반으로 동시 처리 가능 수 자동 결정

* vLLM 파라미터 
  * --model                     사용모델
  * --tensor-parallel-size      GPU 갯수
  * --max-model-len             최대 시퀀스 길이
  * --gpu-memory-utilization    GPU 메모리 상용률(90% 권장)
     - CUDA 커널 실행 오버헤드, Activation 임시 버퍼, Tensor 연산 중간 결과물, NCCL 통신 버퍼 (TP 사용시)


### 테스트 하기 ###
```bash
# 클러스터 내부에서 테스트 (임시 파드)
kubectl run test --rm -it --image=curlimages/curl -- \
  curl http://vllm-qwen-svc/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'
```
또는
```bash
# 터미널 1: 포트 포워딩
kubectl port-forward svc/vllm-qwen-svc 8080:80

# 터미널 2: 테스트
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'
```

### 성능 밴치마크 ###
```bash
kubectl get pods

# vLLM 벤치마크 (파드 안에서 실행)
kubectl exec -it <vllm-pod-name> -- python -m vllm.entrypoints.openai.api_server &

python -m vllm.entrypoints.openai.bench_serving \
  --backend openai \
  --base-url http://localhost:8000 \
  --model qwen \
  --num-prompts 100 \
  --request-rate 10
```

### Speculative Decoding 적용 ###
Speculative Decoding은 작은 모델(draft)이 먼저 여러 토큰을 추측 생성하고, 큰 모델(target)이 한 번에 검증하는 방식으로 추론 속도를 높이는 방식이다.

* Target 모델: Qwen2.5-27B (기존 배포 모델)
* Draft 모델: Qwen2.5-3B (같은 계열의 작은 모델, 추측 적중률이 높음)
기존 vllm-qwen.yaml 에서 args 부분만 수정한다.
```
args:
  - "--model"
  - "Qwen/Qwen2.5-Coder-27B-Instruct"
  - "--tensor-parallel-size 4"
  - "--max-model-len 4096"
  - "--gpu-memory-utilization 0.90"
  - "--speculative-model Qwen/Qwen2.5-Coder-3B-Instruct"
  - "--num-speculative-tokens 5"
```

* 파라미터	설명
 * --speculative-model	추측 생성에 사용할 draft 모델
 * --num-speculative-tokens	draft 모델이 한 번에 추측할 토큰 수 (5가 일반적)
draft 모델(3B)은 target 모델(27B)과 같은 GPU 메모리에 함께 로드된다. 3B 모델은 약 6GB 정도 차지하므로 L40S 48GB × 4 구성에서 메모리 여유가 충분하다.

#### 성능 비교 벤치마크 ####
Speculative Decoding 적용 후 동일한 벤치마크를 실행하여 베이스라인과 비교한다.

```
kubectl exec -it <vllm-pod-name> -- \
  python -m vllm.entrypoints.openai.bench_serving \
    --backend openai \
    --base-url http://localhost:8000 \
    --model qwen \
    --num-prompts 100 \
    --request-rate 10
```
TTFT (Time to First Token), TPOT (Time per Output Token), Throughput (tokens/sec), Request Latency (p50/p99) 을 baseline 과 비교한다.

TPOT와 Throughput에서 가장 큰 차이가 나타난다. 일반적으로 1.5~2.5배 속도 향상을 기대할 수 있으며, 코드 생성처럼 정형화된 출력에서 효과가 더 크다.

num-speculative-tokens는 너무 높이면 draft 모델의 추측이 틀릴 확률이 올라가서 오히려 느려질수 있다. 5가 무난한 시작점이고, 벤치마크 결과 보면서 3~7 사이에서 조절한다.
