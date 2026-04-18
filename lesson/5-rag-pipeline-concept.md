
### 1. 파이프라인 ###
파이프라인 설계는 데이터가 흘러가는 순서와 각 단계의 기술에 대한 선택으로 어떤 청킹 전략을 쓸지, 임베딩 모델은 뭘 쓸지, 리랭커를 넣을지 말지와 같은 기술적 결정이다.

![](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/images/rag-pipeline.png)
* 문서 수집 → (레이아웃) 파싱 → 청킹 → 임베딩 → 벡터DB 저장 → 검색 → 리랭킹 → LLM 생성

### 2. 청킹 전략 ###

```
1. Fixed Size Chunking       — 정해진 크기로 기계적 분할
2. Recursive Chunking        — 구분자 우선순위로 재귀 분할
3. Document-Aware Chunking   — 문서 구조(제목/섹션) 기반 분할
4. Semantic Chunking         — 의미 유사도 기반 분할
5. Sliding Window            — 중첩(overlap) 두고 분할
6. Parent-Child Chunking     — 작게 검색, 크게 답변
7. Agentic Chunking          — LLM이 직접 나눔
```

### 3. 임베딩 모델 선정 ###

#### 1. 성능 (벤치마크) ####
* MTEB (Massive Text Embedding Benchmark) — 영어 표준
* https://huggingface.co/spaces/mteb/leaderboard
* MTEB Korean / KoMTEB — 한국어 평가
* BEIR — 검색 특화 벤치마크

[벤치마크 해석]
```
* Retrieval 점수가 RAG에선 제일 중요 (분류/클러스터링 점수 아님)
* 전체 평균만 보지 말고 내 도메인과 비슷한 태스크 점수 확인
* 주의: 벤치마크 성능 1~2% 차이는 실제 체감 거의 없음. 상위권 모델 중에 다른 요소(비용, 차원)로 고르는 게 현실적.
```

#### 2. 차원 수 (중요!) ####
벡터 차원이 크면 정확도↑, 저장/검색 비용↑.

#### 3. 최대 토큰 (context length) ####
* 한 번에 임베딩할 수 있는 최대 길이(청크 사이즈) 
* 긴 문서 다루면 8K 지원 모델 유리. 짧은 청크(300~500)만 쓸 거면 512로도 충분.

#### 4. 비용 모델 ####
API 기반:
```
OpenAI text-embedding-3-small: $0.02 / 1M tokens
OpenAI text-embedding-3-large: $0.13 / 1M tokens
Cohere embed-v3:              $0.10 / 1M tokens
Voyage AI:                    $0.12 / 1M tokens
```
자체 호스팅 (오픈소스):
```
서버 비용 (GPU 인스턴스)
BGE-M3, E5 등은 무료
```

#### 5. 도메인 적합성 ####
일반 모델은 범용적이지만, 특수 도메인이면 전용 모델이 나음
```
코드: voyage-code-2, jina-embeddings-v2-code, CodeBERT
의료: BioBERT, PubMedBERT 기반
법률: LegalBERT
금융: FinBERT
```
다만 대부분은 범용 + 리랭커 조합이 실용적. 도메인 모델은 학습 데이터가 제한적이라 일반 질문엔 약할 수 있음.




