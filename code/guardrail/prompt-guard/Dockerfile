FROM python:3.11-slim

WORKDIR /app
COPY app.py .

RUN pip install --no-cache-dir \
    fastapi uvicorn transformers torch --index-url https://download.pytorch.org/whl/cpu

# 모델을 빌드 시 미리 다운로드
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    AutoTokenizer.from_pretrained('meta-llama/Prompt-Guard-86M'); \
    AutoModelForSequenceClassification.from_pretrained('meta-llama/Prompt-Guard-86M')"

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
