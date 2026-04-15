# prompt-guard.py
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

app = FastAPI(title="Prompt Guard")

model_name = "meta-llama/Prompt-Guard-86M"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
model.eval()

LABELS = ["benign", "injection", "jailbreak"]

class Request(BaseModel):
    text: str

class Response(BaseModel):
    label: str
    scores: dict
    is_safe: bool

@app.post("/classify", response_model=Response)
def classify(req: Request):
    inputs = tokenizer(req.text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0]
    scores = {LABELS[i]: round(probs[i].item(), 4) for i in range(len(LABELS))}
    label = LABELS[probs.argmax().item()]
    return Response(label=label, scores=scores, is_safe=(label == "benign"))

@app.get("/health")
def health():
    return {"status": "ok"}
