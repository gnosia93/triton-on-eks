## 입력값 필터링 ##

실습 아키텍처에서는 "입력값 필터링 → Llama Guard 3로 안전성 분류 → LLM 호출" 의 파이프라인을 구성할 예정이다.
입력값 필터링의 제공하는 오픈소스 라이브러리에는 다음과 같은 것들이 있고, 그 특징은 아래표과 같다.

| 도구 | 프롬프트 인젝션 | PII 마스킹 | 독성/욕설 | 한국어 | 가벼움 |
|------|:---:|:---:|:---:|:---:|:---:|
| Guardrails AI | ○ | ○ | ○ | △ | △ |
| Presidio | × | ◎ | × | ○ | ○ |
| LLM Guard | ◎ | ○ | ○ | △ | ○ |
| NeMo Guardrails | ○ | △ | ○ | △ | × |

```○ = 지원, ◎ = 강점, △ = 제한적, × = 미지원```

이미 Llama Guard 3를 뒤에 배치할 예정이라, 입력 필터링 단계에서 프롬프트 인젝션 탐지를 중복으로 할 필요는 없다(Llama Guard 3의 경우 프롬프트 인젝션 기능이 좋다). 
그래서 입력 필터링 단계에서 실제로 필요한 건:

* PII 마스킹 (개인정보가 LLM에 들어가지 않게)
* 기본적인 입력 위생 처리 (길이 제한, 의미 없는 텍스트 차단 등)

이다.

PII 보호가 중요하다면 → Presidio가 가장 좋다. PII 탐지/마스킹에 특화되어 있고, 한국어도 Spacy 연동으로 지원되고(한국어 NER 모델 설정필요), 가볍기 때문이다. 또한 마이크로소프트가 관리하니 유지보수도 안정적이다.
보안 방어를 폭넓게 하고 싶다면 → LLM Guard가 낫다. 스캐너 30개 이상을 파이프라인으로 조합할 수 있어서, PII + 악성 코드 + 선정적 표현 등을 한 번에 처리 가능하다.

#### 추천 조합 ####
```
사용자 입력
  → Presidio (PII 마스킹)
  → Llama Guard 3 (안전성 분류 / 프롬프트 인젝션 탐지)
  → LLM 호출
```
Presidio는 역할이 명확하고(PII만 처리), Llama Guard 3과 기능이 겹치지 않아서 파이프라인이 깔끔해 진다. Guardrails AI나 NeMo는 이 구조에서는 오버스펙으로, 프레임워크 레벨의 오케스트레이션이 필요한 게 아니기 때문에 현재의 설계 구조에서는 불필요하다(입력 전처리만 필요).
만약 PII 외에 욕설/독성 필터링도 입력 단계에서 하고 싶다면, LLM Guard를 Presidio 대신 쓰거나 둘을 같이 쓰면 된다.  
기본적인 입력 위생 처리 (길이 제한, 의미 없는 텍스트 차단 등)는 별도 로직(직접 구현하거나 LLM Guard의 스캐너)으로 구현해야 한다.

Presidio에서 한국어 PII를 탐지하려면 다음 중 하나의 방법이 필요하다:

* Spacy의 한국어 모델(ko_core_news_lg 등)을 설치
* 한국어 NER(Named Entity Recognition)을 지원하는 커스텀 recognizer를 추가
* Hugging Face의 한국어 NER 모델(예: monologg/koelectra-base-v3-named-entity-recognition)을 연동

> [!NOTE]
> NER(Named Entity Recognition)은 텍스트에서 사람 이름, 전화번호, 주소 같은 "개체명"을 찾아내는 전통적인 NLP 모델로, 수십~수백 MB 수준의 가벼운 모델이다.


## Presidio (PII 마스킹) 샘플 코드 ##

#### 1. 설치 ####
```
pip install presidio-analyzer presidio-anonymizer
python -m spacy download en_core_web_lg
```

#### 2. 기본 사용법 #### 
```
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# 엔진 초기화
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# 분석할 텍스트
text = "My name is John Smith and my email is john.smith@example.com. Call me at 212-555-1234."

# PII 탐지
results = analyzer.analyze(
    text=text,
    language="en",
    entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"],
)

# 탐지 결과 출력
for result in results:
    print(f"Entity: {result.entity_type}, Score: {result.score:.2f}, "
          f"Start: {result.start}, End: {result.end}")

# 익명화 (기본: <ENTITY_TYPE>으로 대체)
anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
print(f"\n익명화 결과: {anonymized.text}")
# => My name is <PERSON> and my email is <EMAIL_ADDRESS>. Call me at <PHONE_NUMBER>.
```

#### 3. 커스텀 마스킹 전략 ####
```
# 해시, 마스킹, 대체 등 다양한 전략 적용
operators = {
    "PERSON": OperatorConfig("replace", {"new_value": "[이름]"}),
    "EMAIL_ADDRESS": OperatorConfig("mask", {
        "type": "mask",
        "masking_char": "*",
        "chars_to_mask": 12,
        "from_end": False,
    }),
    "PHONE_NUMBER": OperatorConfig("hash", {"hash_type": "sha256"}),
}

anonymized = anonymizer.anonymize(
    text=text,
    analyzer_results=results,
    operators=operators,
)
print(f"커스텀 마스킹: {anonymized.text}")
```

#### 4. 커스텀 패턴 인식기 추가 (예: 한국 전화번호) ####
```
from presidio_analyzer import PatternRecognizer, Pattern

# 한국 전화번호 패턴
kr_phone_pattern = Pattern(
    name="kr_phone",
    regex=r"0\d{1,2}-\d{3,4}-\d{4}",
    score=0.9,
)

kr_phone_recognizer = PatternRecognizer(
    supported_entity="KR_PHONE_NUMBER",
    patterns=[kr_phone_pattern],
    supported_language="en",  # 언어 설정
)

# 분석기에 등록
analyzer.registry.add_recognizer(kr_phone_recognizer)

kr_text = "연락처는 010-1234-5678이고 이메일은 test@example.com입니다."

results = analyzer.analyze(
    text=kr_text,
    language="en",
    entities=["KR_PHONE_NUMBER", "EMAIL_ADDRESS"],
)

anonymized = anonymizer.anonymize(text=kr_text, analyzer_results=results)
print(f"한국 전화번호 마스킹: {anonymized.text}")
```

#### 5. 역익명화 (Deanonymize) ####
```
from presidio_anonymizer.entities import OperatorConfig

# 암호화 기반 익명화 → 복원 가능
anonymized_enc = anonymizer.anonymize(
    text=text,
    analyzer_results=results,
    operators={
        "DEFAULT": OperatorConfig("encrypt", {"key": "WmZq4t7w!z%C&F)J"})
    },
)
print(f"암호화: {anonymized_enc.text}")

# 복원
deanonymized = anonymizer.deanonymize(
    text=anonymized_enc.text,
    entities=anonymized_enc.items,
    operators={
        "DEFAULT": OperatorConfig("decrypt", {"key": "WmZq4t7w!z%C&F)J"})
    },
)
print(f"복원: {deanonymized.text}")
```

주요 포인트:

* AnalyzerEngine이 PII를 탐지하고, AnonymizerEngine이 마스킹을 수행
* 기본 제공 엔티티: PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, IP_ADDRESS 등
* PatternRecognizer로 커스텀 패턴(한국 주민번호, 전화번호 등)을 쉽게 추가 가능
* encrypt/decrypt 연산자를 쓰면 역익명화도 가능

## 입력 위생 처리 로직 샘플 ##
```
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

sanitizer = InputSanitizer()
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

def process_input(user_input: str) -> str:
    # Step 1: 입력 위생 처리
    result = sanitizer.sanitize(user_input)
    if not result.is_valid:
        raise ValueError(f"입력 거부: {result.rejection_reason}")

    # Step 2: Presidio PII 마스킹
    pii_results = analyzer.analyze(text=result.sanitized_text, language="en")
    masked = anonymizer.anonymize(text=result.sanitized_text, analyzer_results=pii_results)

    # Step 3: Llama Guard 3 → LLM 호출 (이후 단계)
    return masked.text
```
