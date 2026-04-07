
Prometheus → KEDA (직접 연결) → HPA 자동 생성
```
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: vllm-qwen-scaler
spec:
  scaleTargetRef:
    name: vllm-qwen
  minReplicaCount: 2
  maxReplicaCount: 8
  cooldownPeriod: 300
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus-server.monitoring:9090
        query: sum(vllm:num_requests_waiting{namespace="default"})
        threshold: "10"
```
