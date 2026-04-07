## vLLM 배포하기 ##

Qwen2.5-27B 모델을 g6e.12xlarge (L40S 48GB * 4EA, TP=4) 설정으로 2개의 파드로 구성한다.
g6e.12xlarge 인스턴스는 2대가 필요하다.



```bash
kubectl -f https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/yaml/vllm-deployment.yaml
```
* vLLM 파라미터 
  * --model                     사용모델
  * --tensor-parallel-size      GPU 갯수
  * --max-model-len             최대 시퀀스 길이
  * --gpu-memory-utilization    GPU 메모리 상용률(90% 권장)
     - CUDA 커널 실행 오버헤드, Activation 임시 버퍼, Tensor 연산 중간 결과물, NCCL 통신 버퍼 (TP 사용시)


