# EKS Agentic AI  

* [L1. EKS 설치하기](https://github.com/gnosia93/eks-agentic-ai/tree/main/iac/tf)

* [L2. PC 노트북 설정](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/2-pc-notebook.md)

* [L3. LLM 평가하기](https://github.com/gnosia93/agentic-ai-eks/blob/main/lesson/3-llm-eval.md)

* [L4. 파인튜닝하기](https://github.com/gnosia93/agentic-ai-eks/blob/main/lesson/4-finetune.md)

* [L5. RAG 파이프라인 설계](https://github.com/gnosia93/agentic-ai-eks/blob/main/lesson/5-rag.md)

* L6. Agentic AI
   - [LangGraph로 RAG 구현](https://github.com/gnosia93/agentic-ai-eks/blob/main/lesson/6-langgraph-rag.md)
   - [@tool 콜링](https://github.com/gnosia93/agentic-ai-eks/blob/main/lesson/6-tool-calling.md)
   - [LangFuse 사용하기](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/6-langfuse.md)
   - 멀티 에이전트
   - [프로적션 최적화]()
     
* [L7. 가드레일 구성하기](https://github.com/gnosia93/agentic-ai-eks/blob/main/lesson/7.guard-rail.md)

* [L8. RAG 평가 파이프라인 구성하기](https://github.com/gnosia93/agentic-ai-eks/blob/main/lesson/8.eval-framework.md)

* L9. EKS 배포하기
   - [vLLM 인퍼런스](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/9-vllm-inference.md)  
   - [TensorRT-LLM 인퍼런스](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/9-tensorrt-inference.md)
   - [KEDA 기반 오토 스케일링](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/9-keda-autoscaling.md)
  
* [L10. Post Training](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/10.post-training.md)


### _Appendix_ ###

* [TensorRT-LLM 연산최적화](https://github.com/gnosia93/infer-on-eks/blob/main/lesson/a1-tensorrt-llm.md)
* [Prometheus/Loki Stack](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/a2-prometheus-loki.md)   
* [LOKI에 K8S 이벤트 저장하기](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/a3-k8s-event.md)
* [K8S 컨트롤 플레인](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/a4-k8s-controlplan.md)
* [Harness Engineering](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/a5.harness-eng.md)
* 에이전트 오케스트레이션, 하네스 엔지니어링
* 장시간 실행되는 에이전트의 상태 관리, 복구, 모니터링
* 프롬프트 엔지니어링 심화: 시스템 프롬프트 설계, few-shot, chain-of-thought 같은 기법을 체계적으로 다루는 파트가 없어요.
* 메모리/상태 관리: 에이전트의 대화 히스토리, 장기 메모리, 세션 관리 같은 부분. LangGraph에서 살짝 다루겠지만 별도 주제로 깊이 있게 할 만해요.
* 에러 핸들링/폴백 전략: 에이전트가 실패했을 때 어떻게 복구하는지, 재시도 로직, 타임아웃 처리 같은 프로덕션 필수 요소.
* 스트리밍 응답: 실시간 토큰 스트리밍, SSE/WebSocket 기반 응답 처리.
* 사용자 피드백 루프: 응답에 대한 thumbs up/down 수집하고 개선에 반영하는 구조.
* 비용 최적화: 토큰 사용량 추적, 캐싱 전략, 모델 라우팅(간단한 질문은 작은 모델, 복잡한 건 큰 모델).
* CI/CD 파이프라인: 프롬프트 버전 관리, 에이전트 로직 테스트 자동화, 배포 파이프라인.
     
## 레퍼런스 ##
* https://github.com/NVIDIA/Model-Optimizer/tree/main 
* https://github.com/huggingface/accelerate









