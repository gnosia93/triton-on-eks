### s3 버킷생성 ###
milvus 용 데이터 저장 버킷을 생성한다.
```
export CLUSTER_NAME=eks-agentic-ai
export VECTORDB_BUCKET_NAME=${CLUSTER_NAME}-vectordb-milvus

aws s3 mb s3://${VECTORDB_BUCKET_NAME} --region ap-northeast-2
```

### milvus 설치 ###
eks 클러스터에 milvus 를 설치한다.
```
helm repo add milvus https://zilliz.github.io/milvus-helm/
helm repo update

helm install milvus milvus/milvus \
  --set cluster.enabled=false \
  --set externalS3.enabled=true \
  --set externalS3.host=s3.amazonaws.com \
  --set externalS3.bucketName=${VECTORDB_BUCKET_NAME} \
  --set externalS3.useIAM=true \
  --set minio.enabled=false \
  --set pulsar.enabled=false \
  --set milvus.standalone.messageQueue=rocksmq \
  -n milvus --create-namespace
```

### IRSA ##
```
EKS에서 useIAM=true 쓰려면
IRSA 설정이 되어 있어야 합니다:

OIDC Provider가 EKS 클러스터에 연결되어 있어야 하고
S3 접근 권한이 있는 IAM Role을 만들고
해당 Role을 Milvus ServiceAccount에 annotate

kubectl annotate serviceaccount milvus \
  -n milvus \
  eks.amazonaws.com/role-arn=arn:aws:iam::<ACCOUNT_ID>:role/<ROLE_NAME>
```

## 테스트 ##
Milvus는 gRPC(19530)와 HTTP(9091) 두 가지 포트를 노출한다.

###  클러스터 내부에서 접근 ###
같은 EKS 안의 다른 Pod에서 접근할 때:
```
milvus.milvus.svc.cluster.local:19530
```

#### Python SDK 예시: ####
```
from pymilvus import connections

connections.connect(
    alias="default",
    host="milvus.milvus.svc.cluster.local",
    port="19530"
)
```

### 로컬에서 테스트할 때 ###
port-forward로 빠르게 확인:
```
kubectl port-forward svc/milvus -n milvus 19530:19530
```

파이썬 IDE 에서 아래 코드를 실행한다.
```
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

connections.connect(host="localhost", port="19530")

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
]
schema = CollectionSchema(fields)
collection = Collection("test_collection", schema)
```

#### 더미 백터(128차원) 생성 및 DB 입력 ####
```
import random
vectors = [[random.random() for _ in range(128)] for _ in range(10)]
collection.insert([vectors])
```

#### 인덱스 생성 & 로드 ####
Milvus는 검색 성능을 위해 메모리에 올라와 있는 인덱스만 검색한다. 아래 load() 함수는 해당 collection을 메모리로 올리는 함수이다.

```
collection.create_index("embedding", {"index_type": "HNSW", "metric_type": "L2", "params": {"M": 8, "efConstruction": 64}})
collection.load()
```

#### 검색 ####
```
results = collection.search(
    data=[vectors[0]],
    anns_field="embedding",
    param={"metric_type": "L2", "params": {"ef": 10}},
    limit=5
)
print(results)
```



