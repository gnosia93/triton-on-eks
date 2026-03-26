## TensorRT-LLM ##
TensorRT-LLM은 NVIDIA의 범용 딥러닝 추론 엔진인 TensorRT를 LLM에 특화시킨 인퍼런스 프레임워크로, 기존 TensorRT의 커널 퓨전, 메모리 레이아웃 최적화, 패딩 최적화에 더해, LLM 서빙에 필수적인 KV Cache 관리(Paged Attention), Inflight Batching(동적 배칭), Tensor/Pipeline Parallel(멀티 GPU/노드 분산), FP8/INT4 양자화, Speculative Decoding 등을 추가한 것이다. PyTorch 모델을 TensorRT 엔진으로 컴파일해서 GPU 아키텍처별 최적 CUDA 커널을 생성하기 때문에, vLLM 대비 10~30% 높은 성능을 낼 수 있지만 빌드 과정이 복잡하고 NVIDIA GPU에서만 동작한다.

### 연산 최적화 기술 ###
TensorRT은 커널 퓨전, 메모리 레이아웃 최적화, 패딩 최적화를 통해서 L2 캐시에 비해 느린 HBM 메모리 접근 횟수를 줄여 GPU 의 연산을 최적화 한다. 참고로 GPU 는 128 bytes 단위로 메모리 어드레싱 작업을 수행한다. 

![](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/images/tensorrt-optimization.png)


### prerequisite ###

기본 설치된 CUDA 12.8용 PyTorch 대신, CUDA 13.0 환경에서 빌드된 PyTorch 2.9.1 버전을 설치한다. PyTorch와 CUDA 런타임 버전을 일치시켜야 드라이버 충돌이나 성능 저하 없이 GPU 연산을 수행할 수 있다.
```bash 
pip3 install torch==2.9.1 torchvision --index-url https://download.pytorch.org/whl/cu130
```
고성능 병렬 계산을 위한 OpenMPI 개발 라이브러리를 설치한다.TensorRT-LLM은 대규모 모델을 여러 개의 GPU에 나누어 처리(모델 병렬화)할 때 GPU 간 통신이 필수적이다. 
```bash
sudo apt-get -y install libopenmpi-dev
```
메시지 큐 라이브러리인 ZeroMQ(ZMQ) 개발 패키지를 설치한다. disagg-serving' (Disaggregated Serving)을 위한 설정으로 
추론 과정 중 '입력값 처리(Prefill)'와 '토큰 생성(Decode)' 단계를 서로 다른 노드/GPU에서 분리해서 처리되는데, 이때 서로 다른 서버(노드) 간에 데이터를 빠르고 안정적으로 주고받기 위해 ZeroMQ라는 통신 엔진이 사용된다.
```bash
# Optional step: Only required for disagg-serving
sudo apt-get -y install libzmq3-dev
```

### TensorRT 엔진 설치 ###
```
pip3 install --ignore-installed pip setuptools wheel && pip3 install tensorrt_llm
```

아래 파이썬 프로그램으로 동작을 테스트한다. 
```python
from tensorrt_llm import LLM, SamplingParams


def main():

    # Model could accept HF model name, a path to local HF model,
    # or Model Optimizer's quantized checkpoints like nvidia/Llama-3.1-8B-Instruct-FP8 on HF.
    llm = LLM(model="TinyLlama/TinyLlama-1.1B-Chat-v1.0")

    # Sample prompts.
    prompts = [
        "Hello, my name is",
        "The capital of France is",
        "The future of AI is",
    ]

    # Create a sampling params.
    sampling_params = SamplingParams(temperature=0.8, top_p=0.95)

    for output in llm.generate(prompts, sampling_params):
        print(
            f"Prompt: {output.prompt!r}, Generated text: {output.outputs[0].text!r}"
        )

    # Got output like
    # Prompt: 'Hello, my name is', Generated text: '\n\nJane Smith. I am a student pursuing my degree in Computer Science at [university]. I enjoy learning new things, especially technology and programming'
    # Prompt: 'The president of the United States is', Generated text: 'likely to nominate a new Supreme Court justice to fill the seat vacated by the death of Antonin Scalia. The Senate should vote to confirm the'
    # Prompt: 'The capital of France is', Generated text: 'Paris.'
    # Prompt: 'The future of AI is', Generated text: 'an exciting time for us. We are constantly researching, developing, and improving our platform to create the most advanced and efficient model available. We are'


if __name__ == '__main__':
    main()
```

```mermaid
graph TB
    subgraph GPU["GPU 내부"]
        SM["SM (연산 코어)<br/>연산 속도: 매우 빠름"]
        CACHE["L2 Cache / 레지스터<br/>용량 작음, 속도 빠름"]
    end

    subgraph HBM["HBM (GPU 메모리)"]
        DATA["텐서 데이터<br/>용량 큼, 속도 느림 (병목)"]
    end

    DATA -->|"읽기 (병목)"| CACHE
    CACHE -->|"연산"| SM
    SM -->|"결과"| CACHE
    CACHE -->|"쓰기 (병목)"| DATA

    style GPU fill:#51cf66,color:#fff
    style HBM fill:#ff6b6b,color:#fff
```
```mermaid
graph TB
    subgraph OPT1["1. 메모리 레이아웃 최적화"]
        direction LR
        subgraph BEFORE1["Before: Column-major로 행 읽기"]
            B1_HBM["HBM: [1, 5, 9, 13, 2, 6, 10, 14, 3, ...]"]
            B1_R1["읽기1 → 1"]
            B1_R2["읽기2 → 2"]
            B1_R3["읽기3 → 3"]
            B1_R4["읽기4 → 4"]
            B1_RESULT["HBM 접근 4번 ❌"]
            B1_HBM --> B1_R1 --> B1_R2 --> B1_R3 --> B1_R4 --> B1_RESULT
        end
        subgraph AFTER1["After: Row-major로 행 읽기"]
            A1_HBM["HBM: [1, 2, 3, 4, 5, 6, 7, 8, ...]"]
            A1_R1["읽기1 → 1,2,3,4 한 번에"]
            A1_RESULT["HBM 접근 1번 ✅"]
            A1_HBM --> A1_R1 --> A1_RESULT
        end
    end

    subgraph OPT2["2. 패딩 최적화 (128B 경계 정렬)"]
        direction LR
        subgraph BEFORE2["Before: 경계 안 맞음"]
            B2_HBM["HBM: [텐서A 100B][텐서B...]"]
            B2_READ["텐서B 시작이 128B 경계 밖"]
            B2_RESULT["HBM 접근 2번 ❌"]
            B2_HBM --> B2_READ --> B2_RESULT
        end
        subgraph AFTER2["After: 패딩으로 정렬"]
            A2_HBM["HBM: [텐서A 100B + 패딩 28B][텐서B...]"]
            A2_READ["텐서B 시작이 128B 경계에 딱 맞음"]
            A2_RESULT["HBM 접근 1번 ✅"]
            A2_HBM --> A2_READ --> A2_RESULT
        end
    end

    subgraph OPT3["3. 커널 퓨전"]
        direction LR
        subgraph BEFORE3["Before: 커널 3개 따로"]
            B3_R1["HBM → 읽기"]
            B3_K1["MatMul"]
            B3_W1["HBM ← 쓰기"]
            B3_R2["HBM → 읽기"]
            B3_K2["LayerNorm"]
            B3_W2["HBM ← 쓰기"]
            B3_R3["HBM → 읽기"]
            B3_K3["Activation"]
            B3_W3["HBM ← 쓰기"]
            B3_RESULT["HBM 접근 6번 ❌"]
            B3_R1 --> B3_K1 --> B3_W1 --> B3_R2 --> B3_K2 --> B3_W2 --> B3_R3 --> B3_K3 --> B3_W3 --> B3_RESULT
        end
        subgraph AFTER3["After: 커널 1개로 퓨전"]
            A3_R1["HBM → 읽기"]
            A3_FUSED["MatMul + LayerNorm + Activation<br/>(중간 결과는 레지스터/캐시)"]
            A3_W1["HBM ← 쓰기"]
            A3_RESULT["HBM 접근 2번 ✅"]
            A3_R1 --> A3_FUSED --> A3_W1 --> A3_RESULT
        end
    end

    style OPT1 fill:#4a9eff,color:#fff
    style OPT2 fill:#cc5de8,color:#fff
    style OPT3 fill:#51cf66,color:#fff
    style BEFORE1 fill:#ff6b6b,color:#fff
    style BEFORE2 fill:#ff6b6b,color:#fff
    style BEFORE3 fill:#ff6b6b,color:#fff
    style AFTER1 fill:#51cf66,color:#fff
    style AFTER2 fill:#51cf66,color:#fff
    style AFTER3 fill:#51cf66,color:#fff
```

