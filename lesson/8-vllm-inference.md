## vLLM 배포하기 ##

Qwen2.5-27B 모델을 g6e.12xlarge (L40S 48GB * 4EA, TP=4) 설정으로 2개의 파드로 구성한다.
g6e.12xlarge 인스턴스는 2대가 필요하다.



```bash
kubectl -f https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/yaml/vllm-deployment.yaml
```
* vLLM 파라미터 
  * --gpu-memory-utilization=0.90  GPU 메모리 사용 비율 (0.95까지 안정적)
  * --max-model-len=8192           시퀀스 길이 제한 → KV Cache 상한 결정
  * --max-num-seqs=256             동시 처리 요청 수 → KV Cache 사용량 결정

### 메모리 계산 
* L40S 48GB per GPU:
  * 모델 가중치:  13.5 GB (TP=4)      <--- 27B * 2byte = 54 GB
  * KV Cache:    ~28 GB
  * 여유분:       ~4.8 GB (activation, CUDA, NCCL)        <--- vllm 파라미터 --gpu-memory-utilization=0.90 
  * 미사용:       ~1.7 GB (10% 밖)
