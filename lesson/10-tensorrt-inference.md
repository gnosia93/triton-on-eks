## TensorRT-LLM 인퍼런스 ##
TensorRT-LLM은 NVIDIA의 범용 딥러닝 추론 엔진인 TensorRT를 LLM에 특화시킨 인퍼런스 프레임워크로, 기존 TensorRT의 커널 퓨전, 메모리 레이아웃 최적화, 패딩 최적화에 더해, LLM 서빙에 필수적인 KV Cache 관리(Paged Attention), Inflight Batching(동적 배칭), Tensor/Pipeline Parallel(멀티 GPU/노드 분산), FP8/INT4 양자화, Speculative Decoding 등을 추가한 것이다. PyTorch 모델을 TensorRT 엔진으로 컴파일해서 GPU 아키텍처별 최적 CUDA 커널을 생성하기 때문에, vLLM 대비 10~30% 높은 성능을 낼 수 있지만 빌드 과정이 복잡하고 NVIDIA GPU에서만 동작한다.

### 연산 최적화 기술 ###
TensorRT은 커널 퓨전, 메모리 레이아웃 최적화, 패딩 최적화를 통해서 레지스터, L2 캐시에 비해 느린 ___HBM 메모리 접근 횟수를 줄여___ GPU 의 연산을 최적화 한다. 참고로 GPU 는 128 bytes 단위로 메모리 어드레싱 작업을 수행한다. 

![](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/images/tensorrt-optimization.png)


### Triton Server vs TensorRT-LLM ###
Triton Server는 서빙 인프라로 HTTP/gRPC 엔드포인트를 제공하고, 요청 큐잉과 배칭을 처리하며, 여러 모델을 하나의 서버에서 동시에 서빙할 수 있다. 모델 버전 관리(v1 → v2 전환), 헬스체크, Prometheus 메트릭 수집, 모델 로드/언로드 기능을 제공한다.

TensorRT-LLM은 추론 엔진으로 모델을 TensorRT 엔진으로 컴파일(빌드)하고, GPU에서 최적화된 커널로 추론을 실행한다. KV Cache 관리, Tensor Parallel 처리, 그리고 vLLM의 Continuous Batching과 유사한 In-flight Batching을 지원한다.

## TensorRT-LLM 에 모델 배포하기 ##

S3 버킷을 생성하고 테라폼에서 생성한 eks-agentic-ai-s3-access 을 쿠버네티스의 서비스 어카운트에 할당한다
```bash
export CLUSTER_NAME=eks-agentic-ai
export ENGINE_BUCKET=${CLUSTER_NAME}-tensorrt-llm-$(date +%Y%m%d%H%M)
export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

aws s3 mb s3://${ENGINE_BUCKET} --region ap-northeast-2

kubectl create serviceaccount s3-access-sa -n default
kubectl annotate serviceaccount s3-access-sa -n default \
  eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/eks-agentic-ai-s3-access
```

### 모델 컴파일 하기 ###

[trtllm-engine-build.yaml](https://github.com/gnosia93/eks-agentic-ai/blob/main/code/yaml/trtllm-engine-build.yaml) 으로 Qwen 모델을 컴파일 한다.
```bash
mkdir triton && cd triton
curl -o trtllm-engine-build.yaml \
  https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/yaml/trtllm-engine-build.yaml

envsubst < trtllm-engine-build.yaml | kubectl apply -f -

kubectl logs job/trtllm-engine-build -f
```
[결과]
```
Download complete. Moving file to /workspace/qwen-hf/model-00003-of-00037.safetensors
Fetching 47 files:  19%|█▉        | 9/47 [00:10<00:43,  1.14s/it]Downloading 'model-00013-of-00037.safetensors' to '/workspace/qwen-hf/.cache/huggingface/download/PWuBP-Hof8RRqr17zbm-lsSqkWg=.091e0a428c3786c0fe75fb9f3445ea7173f0f6af35133a898bf817890d16bec3.incomplete'
Downloading 'model-00014-of-00037.safetensors' to '/workspace/qwen-hf/.cache/huggingface/download/thvUQ1D_SSAk7X9laonYIrmn2cY=.cdb3585244781534f601d22fbba8e2583fe0fc08d46846df86788bb08a4f9b9b.incomplete'
Download complete. Moving file to /workspace/qwen-hf/model-00009-of-00037.safetensors
Downloading 'model-00015-of-00037.safetensors' to '/workspace/qwen-hf/.cache/huggingface/download/5165UonhYHQraDFi8a6AzeYNDDA=.8f6d40610c1470d4097c298a3ad6951ae06bf60458d743fb77be4b52753e0b9c.incomplete'
Download complete. Moving file to /workspace/qwen-hf/model-00005-of-00037.safetensors
Fetching 47 files:  23%|██▎       | 11/47 [00:20<01:33,  2.59s/it]Download complete. Moving file to /workspace/qwen-hf/model-00012-of-00037.safetensors
Download complete. Moving file to /workspace/qwen-hf/model-00014-of-00037.safetensors
Download complete. Moving file to /workspace/qwen-hf/model-00013-of-00037.safetensors
Downloading 'model-00016-of-00037.safetensors' to '/workspace/qwen-hf/.cache/huggingface/download/Pqpxba7EhM6HCzYC2Kg8oCdwqeA=.32b0cb30dcde0bd0a00c2191cd0ced6786aed1126b424e2827987d53cb412eb7.incomplete'
...
```

> [!TIP] 설치된 파이썬 패키지 조회하기  
> kubectl exec -it [pod name] -- bash  
> pip show transformers torch tensorrt_llm  

### 모델 배포하기 ###
[trtllm-qwen.yaml](https://github.com/gnosia93/eks-agentic-ai/blob/main/code/yaml/trtllm-qwen.yaml) 로 TensorRT-LLM 서버를 배포한다.
```
curl -o trtllm-qwen.yaml \
  https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/yaml/trtllm-qwen.yaml
kubectl apply -f trtllm-qwen.yaml
```

## 레퍼런스 ##
* NGC 이미지 태그 목록: https://catalog.ngc.nvidia.com/orgs/nvidia/containers/tritonserver/tags
* 버전별 호환성 매트릭스: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/introduction/compatibility.html
* TRT-LLM GitHub 릴리즈: https://github.com/NVIDIA/TensorRT-LLM/releases
* https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/index.html


