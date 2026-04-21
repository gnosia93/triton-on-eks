
## [LeaderWorkerSet](https://lws.sigs.k8s.io/docs/overview/) ##

LLM 서빙이 본격적으로 프로덕션에 들어오면서, 기존 Kubernetes 워크로드 리소스만으로는 다루기 어려운 영역이 생겼다. 대표적인 것이 여러 노드에 걸쳐 모델을 쪼개서 서빙해야 하는 경우다. Llama 3.1 405B, DeepSeek V3 같은 초대형 모델은 단일 노드의 GPU 메모리로는 감당이 안 된다. H100 8장짜리 노드 두 대를 묶어서, 텐서 병렬과 파이프라인 병렬을 조합해야 겨우 돌아간다.

이런 상황에서 Deployment와 StatefulSet은 애매하다. 그래서 Kubernetes SIG가 새로 내놓은 리소스가 LeaderWorkerSet(이하 LWS)이다. 이 글에서는 LWS가 해결하려는 문제, 내부 구조, 실제 사용 방법을 정리한다.

### 왜 기존 리소스로는 부족한가 ###
Deployment와 StatefulSet은 모두 "각 Pod가 동등한 복제본"이라는 전제 위에서 설계됐다. 하지만 분산 추론은 역할이 비대칭이다.

* Leader: 외부 요청을 받고, 텐서/파이프라인 병렬 연산을 조정한다. 보통 rank 0.
* Worker: 모델 가중치의 일부만 들고 있으며, Leader의 지시를 받아 연산한다.

이 구조를 Deployment로 표현하려고 하면 몇 가지 불편한 지점이 생긴다.

`1. 부분 실패 처리가 어렵다`

Worker 하나가 OOM으로 죽었다고 해보자. Deployment는 그 Pod 하나만 재시작하지만, 분산 추론에서는 Worker 하나가 빠진 상태의 그룹은 무용지물이다. 새로 뜬 Worker는 기존 그룹의 통신 채널에 합류하지 못하고, Leader도 재초기화가 필요하다. 사실상 그룹 전체를 같이 재시작해야 정상 복구된다.

`2. 스케일링 단위가 맞지 않는다`

replicas: 3을 원하는 상황에서 Deployment의 replicas는 "Pod 3개"를 의미한다. 하지만 분산 추론에서는 "Leader+Worker 묶음 3세트"가 필요하다. 이 단위 차이를 HPA나 Karpenter에 그대로 맞추기 어렵다.

`3. 피어 디스커버리를 직접 구현해야 한다`

Leader 주소를 Worker가 어떻게 알 것인가? 각자의 rank는 어떻게 배정할 것인가? StatefulSet의 안정적 네트워크 ID로 엇비슷하게 흉내낼 수는 있지만, init container와 사이드카, 별도 ConfigMap을 얹어가며 조립해야 한다. 결과물은 보통 fragile하다.

이런 요구사항을 "그룹을 1급 시민으로" 취급해서 풀어낸 것이 LWS다.

### LWS의 핵심 개념: Group ###
LWS의 가장 중요한 개념은 Group이다. 한 Group은 Leader 1개와 Worker N개로 구성되며, LWS의 replicas는 Pod 수가 아니라 Group 수를 의미한다.
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
Group 하나가 독립된 추론 단위다. 외부에서 보면 Group 하나가 Deployment의 Pod 하나처럼 동작한다. 트래픽은 Leader Pod로만 들어가고, 그 안에서 Worker들과 협력해 응답을 만든다.


### 해결된 문제들 ###
이 모델 덕분에 자연스럽게 해결되는 문제들이 있다.

`그룹 단위 생명주기`

RecreateGroupOnPodRestart 정책을 쓰면, Group 내 어떤 Pod가 죽어도 그 Group 전체가 재시작된다. 일부만 살아있는 애매한 상태가 남지 않는다.

`자동 환경변수 주입`

LWS 컨트롤러는 각 Pod에 필요한 환경변수를 자동으로 박아준다.

LWS_LEADER_ADDRESS: 같은 Group의 Leader Pod DNS 이름
LWS_WORKER_INDEX: Group 내 rank (0 = leader)
LWS_GROUP_SIZE: Group 내 Pod 총 수
애플리케이션은 이 값을 읽어서 torchrun의 --master_addr, --rank 같은 파라미터로 넘기면 된다.

`Headless Service 자동 생성`

Group마다 Headless Service가 자동으로 만들어지고, Pod들은 안정적인 DNS 이름으로 서로를 찾는다. 따로 Service YAML을 쓸 필요가 없다.

`순차 기동`

startupPolicy: LeaderCreated로 설정하면 Leader가 먼저 Ready된 뒤에 Worker가 뜬다. 분산 프레임워크 중 master가 먼저 대기 상태여야 worker가 연결 가능한 것들에 유용하다.


