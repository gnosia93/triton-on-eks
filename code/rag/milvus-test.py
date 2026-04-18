from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# 연결
connections.connect(host="localhost", port="19530")

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
]
schema = CollectionSchema(fields)
collection = Collection("test_collection", schema)

# 입력 
import random
vectors = [[random.random() for _ in range(128)] for _ in range(10)]
collection.insert([vectors])

# 검색
collection.create_index("embedding", {"index_type": "HNSW", "metric_type": "L2", "params": {"M": 8, "efConstruction": 64}})
collection.load()

results = collection.search(
    data=[vectors[0]],
    anns_field="embedding",
    param={"metric_type": "L2", "params": {"ef": 10}},
    limit=5
)
print(results)
