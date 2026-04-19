from pymilvus import connections, Collection
from sentence_transformers import SentenceTransformer

# 연결
connections.connect(host="localhost", port="19530")
collection = Collection("papers")
collection.load()

# 임베딩 모델 (저장 때와 동일)
model = SentenceTransformer("BAAI/bge-m3")


def search(query: str, top_k: int = 3):
    vec = model.encode([query], normalize_embeddings=True).tolist()

    results = collection.search(
        data=vec,
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 16}},
        limit=top_k,
        output_fields=["text", "doc_name", "page"],
    )

    print(f"\n질의: {query}")
    print("=" * 70)
    for i, hit in enumerate(results[0], 1):
        print(f"\n{i}. [{hit.entity.get('doc_name')} p.{hit.entity.get('page')}] "
              f"score={hit.score:.3f}")
        print(f"   {hit.entity.get('text')[:200]}...")


# 여러 질의로 테스트
queries = [
    "What is LoRA?",
    "How does attention mechanism work?",
    "Retrieval-Augmented Generation",
    "low-rank adaptation의 핵심 아이디어는?",
    "FlashAttention의 성능 향상 비결",
]

for q in queries:
    search(q)
