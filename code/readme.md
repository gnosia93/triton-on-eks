핵심은 모델이 학습할 때와 추론할 때 동일한 포맷을 보게 하기 위해서입니다.

Alpaca 포맷의 원본 데이터는 이렇게 생겼죠:
```
{
  "instruction": "Kubernetes Pod가 CrashLoopBackOff일 때 디버깅 방법은?",
  "output": "kubectl describe pod, kubectl logs 순서로 확인하고..."
}
```
이걸 그대로 학습시키면 모델은 그냥 "텍스트 덩어리"로 학습합니다. 누가 질문이고 누가 답변인지 구분이 없어요.

apply_chat_template을 거치면 모델별 특수 토큰이 붙은 Chat 형식으로 변환됩니다. 예를 들어 Qwen의 경우:
```
<|im_start|>system
You are a helpful DevOps and ML engineering assistant.<|im_end|>
<|im_start|>user
Kubernetes Pod가 CrashLoopBackOff일 때 디버깅 방법은?<|im_end|>
<|im_start|>assistant
kubectl describe pod, kubectl logs 순서로 확인하고...<|im_end|>
```
이렇게 하는 이유는 두 가지입니다:

역할 구분: <|im_start|>user, <|im_start|>assistant 같은 특수 토큰으로 모델이 "여기까지가 질문, 여기서부터 내가 답변할 차례"를 정확히 인식합니다. 이게 없으면 모델이 질문과 답변의 경계를 모릅니다.

추론 시 일관성: vLLM이나 Ollama로 서빙할 때 OpenAI 호환 API를 쓰면 messages 형태로 요청이 들어오고, 내부적으로 동일한 apply_chat_template이 적용됩니다. 학습 때와 추론 때 같은 포맷을 보니까 성능이 그대로 나오는 거죠.

만약 Alpaca 포맷 그대로 학습시키고 Chat 형식으로 추론하면, 학습 때 본 적 없는 특수 토큰이 들어오니까 성능이 떨어집니다. 반대로 Chat 형식으로 학습하고 plain text로 추론해도 마찬가지고요.

한마디로, apply_chat_template은 "학습 데이터를 서빙 환경과 동일한 포맷으로 맞춰주는 전처리"입니다.
