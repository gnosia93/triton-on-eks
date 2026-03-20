```
pip install langfuse
```

```
import os

# 환경변수 설정
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-..."
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-..."
os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com"

from langfuse.callback import CallbackHandler

# 자동으로 환경변수에서 읽음
langfuse_handler = CallbackHandler()
```
