### 온톨로지란 ? ###

온톨로지(Ontology)는 원래 "존재하는 것은 무엇인가"를 다루는 철학 용어지만, 컴퓨터 과학에서는 특정 도메인의 개념·속성·관계를 기계가 이해할 수 있게 정의한 지식 체계를 뜻한다.

예를 들어 단순한 JSON 데이터 {"name": "홍길동", "company": "Cohere"} 만 보면 컴퓨터는 홍길동이 사람인지 회사인지 알 수 없다. 반면 온톨로지는 "Person은 name을 가지며, Organization에 worksFor 관계로 연결된다"처럼 의미와 관계를 명시해, 기계가 데이터를 추론할 수 있게 만든다.

이 구조를 실체화한 것이 지식 그래프(Knowledge Graph) 이며, Neo4j 같은 그래프 DB로 구현한다. 최근에는 LLM과 결합한 GraphRAG로 확장되어, 벡터 기반 RAG의 한계(관계 추론 부족)를 보완하는 기술로 주목받고 있다.

### Neo4j 설치 ###
```
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update
```
neo4j-values.yaml 파일을 생성한다.
```
cat <<'EOF' > neo4j-values.yaml
# neo4j-values.yaml
neo4j:
  name: neo4j
  edition: community               # 무료 버전
  password: "neo4j-admin"          # 초기 비밀번호 (8자 이상 필수)

  resources:
    cpu: "1"
    memory: "4Gi"

volumes:
  data:
    mode: defaultStorageClass
    defaultStorageClass:
      requests:
        storage: 20Gi

services:
  neo4j:
    enabled: true
    type: ClusterIP               # 클러스터 내부 접근만 허용

# Graviton(ARM) 노드에 스케줄링
nodeSelector:
  kubernetes.io/arch: arm64
EOF
```
neo4j 를 설치한다.
```
helm install neo4j neo4j/neo4j -n neo4j \
  -f neo4j-values.yaml --create-namespace
```
#### 설치확인 ####
```
kubectl get all -n neo4j
```
[결과]
```
```

### 접속 테스트 ###
```
pip install neo4j

kubectl port-forward -n neo4j svc/neo4j 7474:7474 7687:7687 &
PF_PID=$!
sleep 3
```
[test.py]
```
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "WorkshopPass123!"),
)

with driver.session() as session:
    # 테스트 데이터 생성
    session.run("""
        CREATE (p:Paper {title: 'LoRA', year: 2021})
        CREATE (a:Author {name: 'Edward Hu'})
        CREATE (a)-[:AUTHORED]->(p)
    """)

    # 쿼리
    result = session.run("""
        MATCH (a:Author)-[:AUTHORED]->(p:Paper)
        RETURN a.name AS author, p.title AS title
    """)
    for r in result:
        print(f"{r['author']} → {r['title']}")

driver.close()
```

```
python test.py
kill $PF_PID
```
