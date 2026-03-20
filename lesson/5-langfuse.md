```
pip install langfuse
```

```
# .env 파일
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

```
# 코드
from dotenv import load_dotenv
load_dotenv()

langfuse_handler = CallbackHandler()  # 자동으로 환경변수 읽음
```
