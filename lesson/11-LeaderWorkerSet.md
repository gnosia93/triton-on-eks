
## [LeaderWorkerSet](https://lws.sigs.k8s.io/docs/overview/) ##

LLM 서빙이 본격적으로 프로덕션에 들어오면서, 기존 Kubernetes 워크로드 리소스만으로는 다루기 어려운 영역이 생겼다. 대표적인 사례가 모델을 여러 노드에 쪼개서 서빙해야 하는 경우다. Llama 3.1 405B, DeepSeek V3 같은 초대형 모델은 단일 노드의 GPU 메모리로는 감당이 안 된다. H100 80GB 8장짜리 노드(640 GiB) 두 대를 묶어 텐서 병렬(TP)과 파이프라인 병렬(PP)을 조합해야 겨우 돌아간다.

메모리 계산
```
1 B  = 10⁹  = 1,000,000,000         (10억)
405B = 405 × 10⁹ = 405,000,000,000  (4,050억 파라미터)
```
FP16 가중치 메모리:
* 2 bytes × 405 × 10⁹ = 810 × 10⁹ bytes = 810 GB ≈ 754 GiB

여기에 KV 캐시와 활성화 메모리까지 더하면 실서빙에는 800 GiB 이상이 필요하다. H100 노드 한 대(640 GiB)로는 가중치조차 올릴 수 없고, 두 대를 묶어야 비로소 여유가 생긴다.

### Deployment와 StatefulSet의 한계점 ###
Deployment와 StatefulSet은 파드에 문제가 생기면 해당 파드만 재시작한다. 단일 파드로 배포되는 워크로드에는 자연스러운 동작이지만, 멀티노드 GPU 서빙에는 적합하지 않다.
TP+PP 구조에서는 여러 파드가 NCCL로 서로 통신하며 하나의 모델을 함께 서빙한다. 파드 하나가 죽으면 NCCL 통신 그룹 전체가 깨지기 때문에, 그룹 내 모든 파드를 함께 재시작해야 한다. Deployment와 StatefulSet은 이와 같은 "그룹 단위 생명주기"라는 개념을 지원하지 않는다.  
그래서 이 공백을 메우기 위해 Kubernetes SIG가 새롭게 도입한 리소스가 바로 LeaderWorkerSet(LWS) 이다.

### LWS 그룹 ###
LWS의 가장 중요한 개념은 그룹이다. 한 그룹은 리더 1개와 워커 N개로 구성되며, LWS의 리프릴카는 파드수가 아니라 그룹수를 의미한다.
```
LeaderWorkerSet (replicas: 2)
├── Group 0
│   ├── Leader Pod  (rank 0)
│   ├── Worker Pod  (rank 1)
│   ├── Worker Pod  (rank 2)
│   └── Worker Pod  (rank 3)
└── Group 1
    ├── Leader Pod  (rank 0)
    ├── Worker Pod  (rank 1)
    ├── Worker Pod  (rank 2)
    └── Worker Pod  (rank 3)
```
그룹 하나가 독립된 추론 단위로, 외부에서 보면 하나의 그룹이 Deployment의 파드처럼 동작한다. 트래픽은 리더 파드로만 들어가고, 그룹을 구성하는 워커들과 협력해 응답을 만들어 낸다.
* Leader: 외부 요청을 받고, 텐서/파이프라인 병렬 연산을 조정한다. (rank 0)
* Worker: 모델 가중치의 일부만 들고 있으며, Leader의 지시를 받아 연산한다.

LWS 컨트롤러는 각 Pod에 필요한 환경변수를 자동으로 주입해 준다. 애플리케이션은 이 값을 읽어서 torchrun의 --master_addr, --rank 같은 파라미터로 넘겨주게 된다.
* LWS_LEADER_ADDRESS: 같은 Group의 Leader Pod DNS 이름
* LWS_WORKER_INDEX: Group 내 rank (0 = leader)
* LWS_GROUP_SIZE: Group 내 Pod 총 수

그룹마다 헤드리스 서비스가 자동으로 만들어지고, 파드들은 안정적인 DNS 이름으로 서로를 찾게 되고 별도의 Service YAML을 필요치 않는다.
startupPolicy를 LeaderCreated로 설정하면 Leader가 먼저 Ready된 뒤에 Worker가 동작하고, master가 먼저 대기 상태로 진입한 후 worker가 Join 한다. 

### 설치하기 ###
아래 manifest YAML 를 사용하여 CRD 와 컨트롤러를 설치한다.
```
kubectl apply --server-side -f \
  https://github.com/kubernetes-sigs/lws/releases/latest/download/manifests.yaml
```
설치된 오브젝트를 확인한다.
```
kubectl get all -n lws-system
```
[결과]
```
NAME                                          READY   STATUS    RESTARTS   AGE
pod/lws-controller-manager-567cc75d78-4t9js   1/1     Running   0          65s
pod/lws-controller-manager-567cc75d78-cwgxv   1/1     Running   0          65s

NAME                                             TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)    AGE
service/lws-controller-manager-metrics-service   ClusterIP   172.20.106.195   <none>        8443/TCP   66s
service/lws-webhook-service                      ClusterIP   172.20.78.73     <none>        443/TCP    66s

NAME                                     READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/lws-controller-manager   2/2     2            2           65s

NAME                                                DESIRED   CURRENT   READY   AGE
replicaset.apps/lws-controller-manager-567cc75d78   2         2         2       65s
```

## Llama 3.1 405B 배포하기 ##
다음은 vLLM으로 Llama 3.1 405B를 2노드에 걸쳐 서빙하는 예제이다.

#### 배포 전 확인사항 ####
* hf-token Secret 생성됨 (kubectl create secret generic hf-token --from-literal=token=hf_xxx)
* llama-405b-cache PVC 준비됨 (최소 1TB, FSx Lustre 강력 추천)
* p5.48xlarge 노드 2대 확보 (Capacity Block 또는 Reserved)
* 두 노드 같은 placement group 소속
* EFA device plugin 설치됨
*  NVIDIA device plugin 설치됨

llm-serving 네임스페이스를 먼저 생성한다.
```
kubectl create ns llm-serving
```
LeaderWorkerSet 을 생성한다.
```
cat <<'EOF' | kubectl apply -f - 
apiVersion: leaderworkerset.x-k8s.io/v1
kind: LeaderWorkerSet
metadata:
  name: vllm-llama-405b
  namespace: llm-serving
  annotations:
    leaderworkerset.sigs.k8s.io/exclusive-topology: topology.kubernetes.io/zone
spec:
  replicas: 1
  rolloutStrategy:
    type: RollingUpdate
    rollingUpdateConfiguration:
      maxUnavailable: 0
      maxSurge: 1                                # 업데이트 중에 replicas를 초과해서 임시로 추가 생성할 수 있는 그룹의 최대 개수
  leaderWorkerTemplate:
    size: 2                                      # Leader 1, Worker 1 
    restartPolicy: RecreateGroupOnPodRestart     # 그룹 안의 파드 하나가 죽으면, 그룹 전체를 재생성하라 는 정책
    leaderTemplate:
      metadata:
        labels:
          role: leader
      spec:
        terminationGracePeriodSeconds: 120       # 파드를 종료할 때 얼마나 기다려줄지를 초 단위로 지정합니다. 여기선 120초 (2분).
        nodeSelector:
          node.kubernetes.io/instance-type: p5.48xlarge
        containers:
          - name: vllm-leader
            image: vllm/vllm-openai:v0.6.3
            command: ["/bin/bash", "-c"]
            args:
              - |
                bash /vllm-workspace/ray_init.sh leader \
                  --ray_cluster_size=$LWS_GROUP_SIZE;
                python -m vllm.entrypoints.openai.api_server \
                  --model=meta-llama/Llama-3.1-405B-Instruct \
                  --tensor-parallel-size=8 \
                  --pipeline-parallel-size=2 \
                  --distributed-executor-backend=ray
            env:
              - name: HUGGING_FACE_HUB_TOKEN
                valueFrom:
                  secretKeyRef:
                    name: hf-token
                    key: token
              - name: HF_HOME
                value: /models
            resources:
              limits:
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 32
                memory: 1000Gi
                cpu: "48"
            ports:
              - containerPort: 8000
            livenessProbe:
              httpGet:
                path: /health
                port: 8000
              initialDelaySeconds: 900
              periodSeconds: 30
            readinessProbe:
              httpGet:
                path: /health
                port: 8000
              initialDelaySeconds: 900
              periodSeconds: 10
            volumeMounts:
              - name: dshm
                mountPath: /dev/shm
              - name: model-cache
                mountPath: /models
        volumes:
          - name: dshm
            emptyDir:
              medium: Memory
              sizeLimit: 32Gi
          - name: model-cache
            persistentVolumeClaim:
              claimName: llama-405b-cache
    workerTemplate:
      spec:
        terminationGracePeriodSeconds: 120
        nodeSelector:
          node.kubernetes.io/instance-type: g7e.48xlarge
        containers:
          - name: vllm-worker
            image: vllm/vllm-openai:v0.6.3
            command: ["/bin/bash", "-c"]
            args:
              - |
                bash /vllm-workspace/ray_init.sh worker \
                  --ray_address=$LWS_LEADER_ADDRESS
            env:
              - name: HUGGING_FACE_HUB_TOKEN
                valueFrom:
                  secretKeyRef:
                    name: hf-token
                    key: token
              - name: HF_HOME
                value: /models
            resources:
              limits:
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 32
                memory: 1000Gi
                cpu: "48"
            volumeMounts:
              - name: dshm
                mountPath: /dev/shm
              - name: model-cache
                mountPath: /models
        volumes:
          - name: dshm
            emptyDir:
              medium: Memory
              sizeLimit: 32Gi
          - name: model-cache
            persistentVolumeClaim:
              claimName: llama-405b-cache
EOF
```
눈여겨 볼점은 리더와 워커의 `명령어셋이 다르다는 점`으로, 리더는 Ray 클러스터를 시작하고 vLLM 서버를 띄우고, 워커는 리더가 띄운 Ray에 조인만 한다.

### 조회하기 ###
```



```

### 테스트 하기 ###
```



```



## 마치며 ##
LWS는 "대형 LLM 분산 추론을 선언적으로 관리하고 싶다"라는 요구에서 출발해, 기존 StatefulSet + Service + Init Container 조합의 구성을 간결하게 바꿀 수 있다. 특히 vLLM 커뮤니티가 LWS를 표준 배포 방식으로 채택하고 있어서, 생태계 호환성 측면에서도 이점이 있다.


## 파드 종료 흐름 ##

> [!TIP]
> 파드 종료 흐름 / kubelet이 파드를 죽이려 할 때 일어나는 일:
>
> 1. preStop 훅 실행 (있으면)
> 2. SIGTERM 전송 → "정리하고 종료해"
> 3. terminationGracePeriodSeconds 동안 대기
> 4. 아직 살아있으면 SIGKILL → "강제 종료"
> 기본값은 30초이나, 대부분의 실전 워크로드는 명시적으로 그 값을 늘려준다.
> 


### 함께 쓰면 좋은 preStop 훅 ###
graceful shutdown 제대로 하려면 preStop 훅을 추가:
```
lifecycle:
  preStop:
    exec:
      command:
        - /bin/sh
        - -c
        - |
          # 1. Readiness false로 만들어 LB에서 빠지게 함
          # 2. 진행 중 요청 완료 대기
          sleep 30
          # 3. 그 다음에야 SIGTERM이 앱에 감
```
```
흐름:

t=0   : preStop 실행 시작 (sleep 30)
t=0~30: LB가 이 파드를 endpoint에서 제거
        새 요청 안 들어옴, 기존 요청만 처리 중
t=30  : preStop 끝, SIGTERM 앱에 전달
t=30~120: 앱이 graceful shutdown (진행 요청 완료, cleanup)
t=120 : 아직 살아있으면 SIGKILL
grace period 안에 preStop 시간도 포함됩니다. 즉 preStop이 30초면, 실제 앱이 쓸 수 있는 시간은 120 - 30 = 90초.
```

## 레퍼런스 ##
* [vllm lws](https://docs.vllm.ai/en/latest/deployment/frameworks/lws/)
