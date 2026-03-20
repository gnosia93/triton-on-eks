reranker 를 호출하는 RAG 파이프라인으로 vscode 에서 아래 코드를 실행한다.

* [셀 1] 설치
```python
!pip install langgraph langchain langchain-openai langchain-community \
faiss-cpu sentence-transformers
```

* [셀 2] LangGraph 구성
```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from sentence_transformers import CrossEncoder

docs = [
    Document(page_content="LangGraph는 LangChain 팀이 만든 에이전트 프레임워크입니다."),
    Document(page_content="LangGraph는 상태 기반 그래프로 복잡한 워크플로우를 구성합니다."),
    Document(page_content="FastAPI는 Python의 고성능 웹 프레임워크입니다."),
    Document(page_content="RAG는 Retrieval Augmented Generation의 약자입니다."),
    Document(page_content="RAG는 외부 문서를 검색해서 LLM의 답변 품질을 높이는 기법입니다."),
]
vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings())
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
llm = ChatOpenAI(model="gpt-4o")

prompt = ChatPromptTemplate.from_messages([
    ("system", """컨텍스트를 참고하여 답변하세요.

컨텍스트:
{context}"""),
    ("human", "{question}")
])

class RAGState(TypedDict):
    question: str
    retrieved_docs: list[Document]
    reranked_docs: list[Document]
    answer: str

def retrieve(state: RAGState):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
    docs = retriever.invoke(state["question"])
    return {"retrieved_docs": docs}

def rerank(state: RAGState):
    question = state["question"]
    docs = state["retrieved_docs"]
    pairs = [(question, doc.page_content) for doc in docs]
    scores = cross_encoder.predict(pairs)
    scored_docs = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    top_docs = [doc for score, doc in scored_docs[:3]]
    return {"reranked_docs": top_docs}

def generate(state: RAGState):
    context = "\n".join([doc.page_content for doc in state["reranked_docs"]])
    response = llm.invoke(
        prompt.invoke({"context": context, "question": state["question"]})
    )
    return {"answer": response.content}

graph_builder = StateGraph(RAGState)
graph_builder.add_node("retrieve", retrieve)
graph_builder.add_node("rerank", rerank)
graph_builder.add_node("generate", generate)

graph_builder.add_edge(START, "retrieve")
graph_builder.add_edge("retrieve", "rerank")
graph_builder.add_edge("rerank", "generate")
graph_builder.add_edge("generate", END)

agent = graph_builder.compile()
```

* [셀 3] 직접 실행
```
# FastAPI 없이 그래프 직접 호출
result = await agent.ainvoke({"question": "RAG가 뭐야?"})

print("답변:", result["answer"])
print("\n출처:")
for doc in result["reranked_docs"]:
    print(f"  - {doc.page_content}")
```

> [!NOTE]
> FAISS는 Meta(Facebook)에서 만든 오픈소스 벡터 유사도 검색 라이브러리로, 대량의 고차원 벡터에서 유사한 벡터를 빠르게 찾아주는 것이 핵심 기능입니다. C++로 작성되어 속도가 빠르고, Python 바인딩을 제공하며, CPU와 GPU 모두 지원한다.
> FAISS의 검색 엔진에는 ANN이라는 기법이 사용되는데, ANN(Approximate Nearest Neighbor)이란 모든 벡터를 하나씩 비교하는 대신 약간의 정확도(15%)를 포기하고 검색 범위를 대폭 줄여서 수백수천 배 빠르게 유사 벡터를 찾는 근사 검색 기법이다.
>
> ANN을 구현하는 대표적인 알고리즘이 HNSW(Hierarchical Navigable Small World)인데, 이는 벡터들을 여러 계층의 그래프로 연결해놓고 상위 계층(넓은 범위)에서 하위 계층(좁은 범위)으로 내려가며 탐색하는 방식입니다. > 별도의 사전 학습 없이 바로 사용할 수 있고, 정확도와 속도 모두 우수해서 Pinecone, Qdrant 등 대부분의 벡터 DB가 내부적으로 HNSW를 채택하고 있다.

