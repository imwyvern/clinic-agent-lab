# clinic-agent-lab

버전 **0.1.0** · Apache-2.0 · [GitHub: imwyvern](https://github.com/imwyvern)

> **명확한 사용 범위:** SYNTHETIC 합성 데이터만 사용합니다. **not a medical device — 의료기기가 아닙니다.**
> 진단, 임상 모델 학습, 처방·지시의 자동 실행을 수행하지 않으며, 운영 환경용 시스템이 아닙니다.
> 실제 환자 데이터를 입력하지 마세요. 데모 의사가 워크플로 결정을 확인한 뒤에도
> 모든 제안은 MedicationRequest `draft` 상태로 유지됩니다.

[English](../../README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md)

## 하는 일

작은 Python 워크플로 실험실입니다. 결정론적 에이전트가 가상 환자의 요약, 검사 결과,
알레르기, 복용 약물 정보를 수집하고, 픽스처에 정해진 제안의 초안을 작성한 다음 안전 카드를
생성합니다. 인증되지 않은 **데모 의사 역할**로 결정을 확인하거나 거절할 수 있습니다.
도구 조율, 영속성, 멱등성, 안전 게이트, 재현 가능한 평가를 위한 엔지니어링 방법을 보여 줍니다.
진단이나 치료법을 선택하지 않습니다.

P0에는 **합성 픽스처 10개**와 **직접 작성한 규칙 4개**로 구성된 **Demo Rule Pack**이 포함됩니다.
짧은 규칙과 임의의 용량 범위는 데모 로직이며 임상 지침이 아닙니다.
리소스는 간소화된 FHIR 스타일 JSON으로, 완전한 FHIR이나 상호운용 가능한 EHR이 아닙니다.

## 빠른 시작

Python **3.11+**가 필요합니다. 이 체크아웃의 루트에서 실행하세요. 키, 외부 모델, 유료 서비스는 필요 없습니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m clinic_agent_lab.demo --serve
```

<http://127.0.0.1:8000>을 여세요. 데모는 아래 시나리오를 실행한 뒤 로컬 서버를 계속 실행합니다.
성공 요약이 출력된 뒤 Ctrl-C를 누르면 종료 코드 0으로 끝납니다. 기본 데이터베이스는
`.demo/demo.db`입니다. 다시 실행할 때마다 고유한 가상 업무 키를 사용하며 이전 기록은 유지합니다.
8000 포트를 사용 중이면 `--port 8001` 또는 `--port 0`을 사용하고 출력된 주소를 확인하세요.

실제 HTTP로 관리 페이지를 검사한 후 자동 종료하는 데모:

```bash
python -m clinic_agent_lab.demo
```

관리 페이지 주소와 저장된 사례를 다시 여는 명령을 출력한 후 검사 서버를 종료합니다.
데이터가 없는 별도의 로컬 API 및 관리 서버도 시작할 수 있습니다.

```bash
python -m uvicorn clinic_agent_lab.api:app --host 127.0.0.1 --port 8000
```

이 서버는 `.demo/clinic.db`를 사용합니다. 데모 기록을 다시 열려면 동일한 서버 명령을 실행하기 전에
`CLINIC_DB_PATH=.demo/demo.db`를 설정하세요. `.env.example`에 설정 예시가 있습니다.
앱은 환경 변수를 읽으며 `.env`를 자동으로 불러오지 않습니다.
기본값은 `CLINIC_CASE_TTL_SECONDS=300`입니다. 백그라운드 작업 없이 접근할 때 만료를 확인합니다.

## 데모 단계와 API

1. 정상 제안이 `awaiting_physician`으로 들어갑니다. 데모 의사가 확인하면 타임라인은 `confirmed`로 끝납니다.
2. 페니실린 계열 알레르기는 `block`을 생성합니다. 확인 요청은 HTTP 409를 반환하며 거절은 가능합니다.
3. 필수 검사 누락은 `warn`을 생성합니다. 확인과 거절 경로를 모두 시연합니다.
4. 같은 `clientCaseId`를 다시 요청하면 기존 사례와 초안 1개를 반환합니다.
5. 짧은 TTL을 가진 사례는 `expired`가 됩니다. 늦은 확인 요청은 HTTP 409를 반환합니다.
6. 목록·상세 페이지, 안전 카드, 저장된 도구·상태·결정 이벤트 타임라인을 확인합니다.

별도 서버가 실행 중일 때 최소 [API 예제](../../examples/api_demo.py)를 실행하세요.

```bash
python examples/api_demo.py
```

API: `GET /api/fixtures`, `POST /api/cases`, `GET /api/cases`,
`GET /api/cases/{id}`, `POST /api/cases/{id}/decision`.
생성 요청은 `clientCaseId`와 번들에 포함된 `fixture_id`만 받으며 환자 기록 업로드는 받지 않습니다.
결정 요청은 `action` (`confirm`/`reject`), `role`, `actor`, 선택적 `reason`을 받습니다. 가상 내용만 입력하세요.
두 작업 모두 `physician` 역할이 필요하며 `observer`는 HTTP 403으로 거부됩니다.
**인증 기능이나 의료인 신원 확인은 없습니다.** 루프백 주소에만 바인딩하세요.

## 상태 머신과 안전 의미

```text
accepted → gathering → drafted → awaiting_physician → confirmed | rejected | expired | failed
```

모든 비종료 상태는 `expired` 또는 `failed`가 될 수 있습니다. 종료된 상태는 다시 열 수 없습니다.
도구 순서는 `get_patient_summary`, `get_labs`, `get_allergies`, `get_medications`,
`draft_order`로 고정됩니다. 상태 전이와 도구 출력은 SQLite의 `cases`, `events`, `drafts`에 저장됩니다.
업무 키 `clientCaseId`는 고유하며, 다른 픽스처로 재사용하면 409를 반환합니다.

카드 수준은 `clear`, `caution`, `warn`, `block`이며 `block`이 `warn`보다 우선합니다.
`caution`은 예약된 수준으로 P0 규칙에서는 생성하지 않습니다. `clear`는 데모 규칙의 적중이 없다는 뜻이며
임상적으로 안전하다는 증거가 아닙니다. 각 카드에는 규칙 ID, 누락 데이터, 충돌, 설명, 초안이 있습니다.
차단된 제안의 확인은 `awaiting_physician`을 바꾸지 않고 거부됩니다. 이후 거절하거나 만료될 수 있습니다.
다른 수준에서는 데모 의사의 결정이 가능합니다. **어떤 수준도 처방·지시를 실행하지 않습니다.**

## 평가

```bash
ruff check .
pytest
python -m clinic_agent_lab.evaluate --output .demo/evaluation.json
python scripts/check_docs.py
```

테스트는 라벨이 있는 알레르기·용량 초과 차단 픽스처, 차단된 확인 거부, 경고 전용 동작과 두 결정,
재요청·동시 요청에서의 멱등성, 만료, 비실행, 결정론적 동작, 문서 일관성을 고정합니다.
평가에서는 실제 픽스처별 규칙 적중과 워크플로 검사만 보고합니다. 진단 정확도, 의사와의 일치도,
지연 시간에 대한 주장은 하지 않습니다. 실제 HKT 실행 시각이 기록된 [결과와 방법](../evaluation.md)을 확인하세요.

## 로컬 컨테이너

```bash
docker build -t clinic-agent-lab:local .
docker run --rm -p 127.0.0.1:8000:8000 clinic-agent-lab:local
```

시나리오 데모 대신 로컬 API와 페이지를 실행합니다. 로컬 디렉터리를 `/app/data`에 마운트하지 않으면
컨테이너 데이터는 일시적입니다. 편의를 위한 이미지이며 운영 환경 배포가 아닙니다.

## Shipped — 제공된 기능

P0: Python/FastAPI/Pydantic v2, SQLite 상태 머신, 결정론적 도구, 합성 픽스처 10개,
데모 규칙 4개, 안전 카드, 의사 게이트, HTML 관리 화면, 실제 HTTP 데모, 픽스처 평가,
테스트, 린트, CI 워크플로 파일, 로컬 Dockerfile, 6개 언어 문서.
이 구현은 로컬에서 검증했습니다. CI 워크플로 파일만으로는 호스팅된 CI 상태나 공개 릴리스의 존재를 확인할 수 없습니다.

## Planned — 계획된 기능

P1/T8은 이번 릴리스의 범위 밖입니다. 규칙 결정을 바꿀 수 없는 선택적 LLM 문구 재작성,
라이선스를 확인한 Synthea 가져오기, 작은 합성 특성 분류기 베이스라인을 계획했습니다.
모두 구현되지 않았습니다. 임상 모델 학습, 병원 연동, 실행 어댑터는 없습니다.

## 경험 범위와 면책 사항

작성자는 주로 TypeScript/Node로 백엔드 작업을 합니다. Python 경험에는 Django,
FastAPI, py-agents, 개인 프로젝트가 포함되지만 Python은 일상의 주력 스택이 아닙니다.
임상 데이터 학습 경험, 병원 시스템 통합 경험, 의료인 면허 배경, 의사와 임상 시스템을 공동 개발한
경험은 없습니다. 이 실험실은 워크플로 에이전트, 안전 게이트, 재현 가능한 평가를 보여 줍니다.
임상 전문성이나 임상 사용 준비가 되었음을 증명하지 않습니다.

번들에 포함된 가상 픽스처만 사용하세요. 실제 진료, 처방, 진단, 운영 결정에 출력을 사용하지 마세요.
확인은 로컬 데모 결정만 기록합니다.

## 문서, 기여, 라이선스

[아키텍처](../architecture.md) · [규칙과 카드](../rules-and-safety.md) ·
[데이터와 라이선스](../data-and-license.md) · [보안](../../SECURITY.md) ·
[기여](../../CONTRIBUTING.md) · [변경 기록](../../CHANGELOG.md)

코드, 직접 만든 픽스처, 문서: [Apache-2.0](../../LICENSE), [NOTICE](../../NOTICE) 포함.
연락처: wpkreg@gmail.com · GitHub: [imwyvern](https://github.com/imwyvern).
