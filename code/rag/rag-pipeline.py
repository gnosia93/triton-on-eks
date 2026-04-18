import json
import boto3
from pymilvus import connections, Collection
from sentence_transformers import SentenceTransformer


# ─────────────────────────────────────────────
# 1. 설정
# ─────────────────────────────────────────────
REGION = "ap-northeast-2"
MILVUS_HOST = "localhost"        # port-forward 중이면 localhost
MILVUS_PORT = "19530"
COLLECTION_NAME = "docs"

EMBEDDING_MODEL = "BAAI/bge-m3"
RERANK_MODEL_ID = "cohere.rerank-v3-5:0"
LLM_MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"  # 예시

TOP_K_RETRIEVE = 20   # Milvus에서 뽑을 개수
TOP_K_RERANK = 5      # 리랭킹 후 LLM에 넘길 개수


# ─────────────────────────────────────────────
# 2. 클라이언트 초기화
# ─────────────────────────────────────────────
connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
collection = Collection(COLLECTION_NAME)
collection.load()

embedder = SentenceTransformer(EMBEDDING_MODEL)

bedrock = boto3.client("bedrock-runtime", region_name=REGION)
bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=REGION)


# ─────────────────────────────────────────────
# 3. Milvus 검색
# ─────────────────────────────────────────────
def retrieve(query: str, top_k: int = TOP_K_RETRIEVE):
    query_vec = embedder.encode([query], normalize_embeddings=True)[0].tolist()

    results = collection.search(
        data=[query_vec],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"ef": 64}},
        limit=top_k,
        output_fields=["text", "source", "page"],
    )

    hits = []
    for hit in results[0]:
        hits.append({
            "text": hit.entity.get("text"),
            "source": hit.entity.get("source"),
            "page": hit.entity.get("page"),
            "score": hit.score,
        })
    return hits


# ─────────────────────────────────────────────
# 4. Cohere Rerank (Bedrock 경유)
# ─────────────────────────────────────────────
def rerank(query: str, docs: list, top_n: int = TOP_K_RERANK):
    body = {
        "query": query,
        "documents": [d["text"] for d in docs],
        "top_n": top_n,
        "api_version": 2,
    }

    response = bedrock.invoke_model(
        modelId=RERANK_MODEL_ID,
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())

    # 결과는 인덱스와 relevance_score로 돌아옴
    reranked = []
    for item in result["results"]:
        doc = docs[item["index"]]
        doc["rerank_score"] = item["relevance_score"]
        reranked.append(doc)
    return reranked


# ─────────────────────────────────────────────
# 5. 프롬프트 조립 + LLM 호출
# ─────────────────────────────────────────────
def build_prompt(query: str, docs: list) -> str:
    context_blocks = []
    for i, d in enumerate(docs, 1):
        context_blocks.append(
            f"[문서 {i}] (출처: {d['source']}, p.{d['page']})\n{d['text']}"
        )
    context = "\n\n".join(context_blocks)

    return f"""다음 문서를 참고해서 질문에 답하세요.
문서에 없는 내용은 추측하지 말고 "문서에 없음"이라고 답하세요.
답변 시 근거가 된 문서 번호를 [문서 N] 형식으로 표시하세요.

### 참고 문서
{context}

### 질문
{query}

### 답변
"""


def generate(query: str, docs: list) -> str:
    prompt = build_prompt(query, docs)

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = bedrock.invoke_model(
        modelId=LLM_MODEL_ID,
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


# ─────────────────────────────────────────────
# 6. 전체 파이프라인
# ─────────────────────────────────────────────
def rag(query: str) -> dict:
    # 1) 벡터 검색
    retrieved = retrieve(query, top_k=TOP_K_RETRIEVE)

    # 2) 리랭킹
    reranked = rerank(query, retrieved, top_n=TOP_K_RERANK)

    # 3) LLM 생성
    answer = generate(query, reranked)

    return {
        "query": query,
        "answer": answer,
        "sources": [
            {"source": d["source"], "page": d["page"], "score": d["rerank_score"]}
            for d in reranked
        ],
    }


# ─────────────────────────────────────────────
# 실행 예시
# ─────────────────────────────────────────────
if __name__ == "__main__":
    result = rag("EKS에서 Milvus를 배포할 때 주의할 점은?")

    print("=" * 60)
    print("답변:")
    print(result["answer"])
    print("\n" + "=" * 60)
    print("근거 문서:")
    for s in result["sources"]:
        print(f"  - {s['source']} p.{s['page']} (score: {s['score']:.3f})")
