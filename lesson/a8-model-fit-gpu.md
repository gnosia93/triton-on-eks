
![](https://github.com/gnosia93/eks-agentic-ai/blob/main/lesson/images/gpu-sel-process.png)


### 모델 메모리 계산 공식 ###
```
모델 메모리 ≈ 파라미터 수 × 바이트/파라미터

FP16: 파라미터 수 × 2 bytes
FP8:  파라미터 수 × 1 byte
INT4: 파라미터 수 × 0.5 bytes
```

### KV 캐시 메모리 계산 ###
```
KV Cache ≈ 2 × num_layers × hidden_dim × seq_len × batch_size × bytes
```
* 실제로는 동시 요청 수와 시퀀스 길이에 따라 수 GB ~ 수십 GB 추가됨.
* 2x 배수를 곱하는 이유는 하나의 Key 다른 하나는 Value 캐시임.
* hidden_dim(임베딩 백터 사이즈)를 곱하는 이유는 각 토큰의 K, V가 hidden_dim 크기의 벡터이기 때문.


### 빠른 판단 공식 ###

```
필요한 GPU 수 (최소) = 모델 메모리 / (GPU VRAM × 0.8)

예: Llama 70B FP16
= 140GB / (80GB × 0.8)
= 140 / 64
= 2.19 → H100 3장 (KV cache 여유 포함)

예: Llama 70B FP8
= 70GB / (80GB × 0.8)
= 70 / 64
= 1.09 → H100 1장으로 가능 (KV cache 여유 적음)
```
