import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen3.5-27B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")

# DevOps/ML 도메인 평가 텍스트
eval_texts = [
    "Kubernetes Pod가 CrashLoopBackOff 상태일 때 kubectl describe pod로 Events를 확인하고 kubectl logs로 컨테이너 로그를 분석한다.",
    "FSDP는 모델 파라미터를 GPU 간에 샤딩하여 메모리 사용량을 줄이면서 데이터 병렬 학습을 수행한다.",
    "Prometheus는 pull 방식으로 메트릭을 수집하며 PromQL을 사용하여 시계열 데이터를 쿼리한다.",
]

model.eval()
total_loss = 0
total_tokens = 0

with torch.no_grad():
    for text in eval_texts:
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        outputs = model(**inputs, labels=inputs["input_ids"])
        total_loss += outputs.loss.item() * inputs["input_ids"].size(1)
        total_tokens += inputs["input_ids"].size(1)

ppl = torch.exp(torch.tensor(total_loss / total_tokens))
print(f"파인튜닝 전 도메인 PPL: {ppl:.2f}")
