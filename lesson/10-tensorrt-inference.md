
## TensorRT-LLM 배포하기 ##

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

트리톤 서버를 이용하여 Qwen 모델을 컴파일 한다.
```bash
curl -o trtllm-engine-build.yaml \
  https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/yaml/trtllm-engine-build.yaml
envsubst < trtllm-engine-build.yaml | kubectl apply -f -

kubectl wait --for=condition=complete job/trtllm-engine-build --timeout=60m
kubectl logs job/trtllm-engine-build
```
[결과]
```



```

TensorRT-LLM 서버를 배포한다.
```
curl -o trtllm-qwen.yaml \
  https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/yaml/trtllm-qwen.yaml
kubectl apply -f trtllm-qwen.yaml
```

## 레퍼런스 ##
* https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/index.html


