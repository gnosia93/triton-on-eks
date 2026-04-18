## PDF 문서 저장하기 (레이아웃 파싱/청킹/임베딩) ##

이 단계에서는 PDF 문서를 읽어 들여 의미 단위로 잘게 나누고(청킹), 각 조각을 벡터로 변환해(임베딩) Milvus에 저장한다. 이렇게 저장된 벡터는 이후 RAG 파이프라인에서 질의와 가장 유사한 문서 조각을 찾는 데 사용된다.

전체 과정은 다음과 같다.
```
PDF 파일 → 레이아웃 파싱 → 청킹 → 임베딩(벡터화) → Milvus 저장
```
아래 PDFVectorStore 클래스는 이 네 단계를 하나로 묶어 둔 래퍼이다. 다른 PDF 문서도 같은 방식으로 추가할 수 있도록 재사용 가능한 형태로 작성돼 있다.

### 1. 프로젝트 구조 ### 
```
rag/
├── PDFVectorStore.py       ← curl로 받은 파일
└── main.py                 ← 여기서 from PDFVectorStore import ...
└── pdfs/
    └── LoRA_Low-Rank_Adaptation.pdf
```

### 2. 환경 준비 ###
작업 디렉토리를 만들고 필요한 패키지를 설치한다.

```
mkdir rag && cd rag
pip install pymilvus langchain langchain-community pymupdf sentence-transformers
```
각 패키지의 역할: 
* pymilvus : Milvus 벡터 DB 파이썬 클라이언트
* langchain, langchain-community : 문서 로더와 텍스트 스플리터 제공
* pymupdf : PDF 레이아웃 파싱(텍스트/페이지 정보 추출)
* sentence-transformers : 로컬에서 실행되는 오픈소스 임베딩 모델 (무료)

### 3. PDFVectorStore 클래스 내려받기 ###
미리 작성해 둔 클래스 파일을 가져온다.
```
curl -o PDFVectorStore.py
https://raw.githubusercontent.com/gnosia93/eks-agentic-ai/refs/heads/main/code/rag/PDFVectorStore.py
```
이 파일 안에는 다음 기능이 구현돼 있다.  
* PyMuPDFLoader로 PDF를 페이지 단위로 로드
* RecursiveCharacterTextSplitter로 문맥을 최대한 보존하며 청킹 (기본 1,000자, 150자 오버랩)  
* BAAI/bge-m3 모델로 임베딩 (1,024차원, 다국어 지원)   
* Milvus 컬렉션 스키마 자동 생성 및 IVF_FLAT + COSINE 인덱스 구성

### 4. 실행 스크립트 작성 (main.py) ###
```
from PDFVectorStore import PDFVectorStore

store = PDFVectorStore(
    host="<리모트_IP_또는_호스트>",
    port="19530",
    collection_name="papers",
    reset=True,   # 기존 컬렉션을 초기화. 처음 한 번만 True로 두고 이후에는 False.
)

store.add_pdf("LoRA_Low-Rank_Adaptation.pdf")
# 문서를 추가로 저장하려면 같은 방식으로 호출
# store.add_pdf("Attention_Is_All_You_Need.pdf")
```
주요 파라미터 설명:
* host, port : 리모트에 떠 있는 Milvus 서버의 주소와 포트
* collection_name : 문서들을 저장할 컬렉션 이름.
* reset=True : 같은 이름의 컬렉션이 있으면 삭제하고 새로 만든다. 이미 저장된 데이터를 유지하면서 추가만 하고 싶다면 False로 설정한다.

### 5. 실행 ###
```
python main.py
```
실행이 끝나면 다음과 같은 메시지가 출력된다.

