
## TensorRT-LLM 배포하기 ##

모델을 컴파일 하여 S3 에 저장한다.
```bash
# S3 버킷 생성
export ENGINE_BUCKET=tensorrt-llm-$(date +%Y%m%d%H%M)

aws s3 mb s3://${ENGINE_BUCKET} --region ap-northeast-2
eksctl create iamserviceaccount \
  --name s3-access-sa \
  --namespace default \
  --cluster <cluster-name> \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --approve

curl -o trtllm-engine-build.yaml \
  https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/yaml/trtllm-engine-build.yaml
envsubst < trtllm-engine-build.yaml | kubectl apply -f -

kubectl wait --for=condition=complete job/trtllm-engine-build --timeout=60m
kubectl logs job/trtllm-engine-build
```

TensorRT-LLM 서버를 배포한다.
```
curl -o trtllm-qwen.yaml https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/yaml/trtllm-qwen.yaml
kubectl apply -f trtllm-qwen.yaml
```


## 레퍼런스 ##
* https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/index.html


