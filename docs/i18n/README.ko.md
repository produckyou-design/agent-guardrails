# agent-guardrails

AI한테 "여기 간격만 좀 고쳐줘"라고 했는데 끝나고 보니 파일 12개가 바뀌어 있던 적 있습니까?

함수 이름이 바뀌고, 중복 코드가 정리되고, 몇 달째 멀쩡하던 재시도 로직까지 "개선"돼 있습니다. diff는 그럴듯하고 테스트도 통과할 수 있습니다.

그리고 며칠 뒤 엉뚱한 곳이 깨집니다.

`agent-guardrails`는 바로 그 문제를 막는 작은 Git 게이트입니다. **AI 코딩 에이전트가 이미 완성됐고 이번 작업과 상관없는 코드를 건드리는 것**을 커밋 단계에서 막습니다.

프롬프트에 "기존 코드 건드리지 마"를 한 줄 더 쓰는 대신, 그 규칙을 실행되는 코드로 만듭니다. 보호된 경로가 바뀌면 커밋 자체가 거부됩니다.

의존성도 없고 모델 API도 호출하지 않습니다. Python과 Git만 씁니다.

[English](../../README.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## 30초 테스트

에이전트에게 작은 작업 하나를 시켜보세요.

```text
설정 페이지 버튼 간격만 조금 고쳐줘.
```

끝난 뒤:

```sh
git diff --stat
```

원래 예상한 파일은 2개인데 9개가 바뀌었다면 나머지 7개를 열어보세요.

대개 이런 게 섞여 있습니다.

```text
"이름이 애매해서 정리했습니다."
"중복 로직을 공통 함수로 뺐습니다."
"사용하지 않는 것 같아 제거했습니다."
"일관성을 위해 주변 코드도 수정했습니다."
```

전부 그럴듯합니다. 전부 시킨 적 없는 작업입니다.

정말 시킨 것만 diff에 들어온다면 아직 이 도구가 필요 없을 수도 있습니다. 그렇지 않다면 아래부터 보면 됩니다.

## 이 도구가 푸는 문제

예를 들어 이 파일이 3개월째 문제없이 운영 중이라고 합시다.

```text
src/billing/charge.py
```

오늘 시킨 일은 이것뿐입니다.

```text
청구서 화면 여백 수정
```

AI는 `charge.py`가 왜 조금 이상하게 생겼는지 모릅니다. 반년 전 실제 장애 때문에 생긴 분기인지, 상류 API가 불안정해서 남겨둔 재시도인지 알 수 없습니다. AI가 보는 건 현재 코드이지 그 코드가 살아남은 역사까지는 아닙니다.

그래서 보통 이렇게 적습니다.

```text
이 파일은 건드리지 마세요.
```

AGENTS.md에도 적고, CLAUDE.md에도 적고, 프롬프트에도 적습니다.

문제는 문서는 규칙을 설명할 뿐 규칙을 집행하지 않는다는 겁니다.

`agent-guardrails`는

```text
건드리지 마세요
```

를

```text
commit rejected
```

로 바꿉니다.

## 어떻게 동작하나

완성된 경로를 `frozen.json`에 적습니다.

```json
{
  "frozen": [
    {
      "label": "결제",
      "paths": ["src/billing/charge.py"],
      "reason": "완성돼서 운영 중이고 로드맵에 없습니다.",
      "what_breaks": "계산이 틀려도 화면은 정상입니다. 금액만 달라집니다.",
      "before_you_touch": [
        "부분 환불은 refund.py가 담당합니다.",
        "실패하면 트랜잭션 전체를 되돌립니다.",
        "통화 반올림은 경계에서 한 번만 결정합니다."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

이제 에이전트가 해당 파일을 고치고 커밋하면 바로 멈춥니다.

```text
$ git commit -m "invoice: tidy up rounding"

frozen: FAIL - a frozen path was changed
  src/billing/charge.py
      [Billing] Finished and in production.
      breaks -> Wrong math still renders a normal screen.
                 Only the amount changes.
        - Partial refunds live in refund.py, not here.
        - Failure rolls the whole transaction back.
      verify -> pytest tests/test_billing.py -q
```

게이트는 로컬 Python 코드입니다. LLM을 호출하지 않습니다.

정상 작업은 그냥 통과하고, 경계를 넘었을 때만 필요한 설명이 나타납니다.

## 정말 그 파일을 고쳐야 한다면

동결은 영구 봉인이 아닙니다.

정말 수정할 이유가 있으면 커밋 메시지에 세 줄을 남깁니다.

```text
UNFREEZE: src/billing/charge.py - 새 결제 수단 때문에 분기가 필요합니다
UNFREEZE-IMPACT: 잘못되면 결제 금액 계산이 달라질 수 있습니다
UNFREEZE-ROLLBACK: git revert <sha> 후 pytest tests/test_billing.py 재실행
```

하나라도 빠지면 커밋이 거부됩니다.

왜 세 줄이냐면 "왜 지금 고치는가"만 알아서는 부족하기 때문입니다. **틀렸을 때 무엇이 깨지는지**, **어떻게 되돌릴지**까지 설명할 수 있어야 합니다.

그 둘을 못 쓰겠다면, 아직 그 코드를 고칠 준비가 안 됐다는 걸 프로덕션이 아니라 커밋 전에 알아낸 겁니다.

## 실제로 뭐가 달라지나

### 작은 작업이 대형 diff로 번지는 걸 막습니다

```text
요청:
버튼 간격 수정

딸려온 변경:
컴포넌트 이름 변경
API helper 리팩터링
재시도 로직 정리
타입 정의 통합
```

작업 범위가 커진 사실이 배포 전에 드러납니다.

### 이상해 보이지만 이유가 있는 코드가 살아남습니다

오래된 코드베이스에는 꼭 있습니다.

```text
왜 여기서 두 번 호출하지?
왜 이 조건만 따로 있지?
왜 굳이 이렇게 우회하지?
```

보기엔 정리 대상인데 실제로는 과거 장애를 막고 있을 수 있습니다. `before_you_touch`가 그 이유를 에이전트가 건드리는 바로 그 순간 보여줍니다.

### 리뷰 순서가 생깁니다

밤사이 에이전트가 34개 커밋을 만들었는데 두 개에만 `UNFREEZE`가 있다면 그 둘부터 보면 됩니다.

에이전트를 더 신중하게 만드는 게 아니라, 예외적인 변경이 스스로 표시되게 만드는 겁니다.

### 모델이 바뀌어도 규칙은 남습니다

오늘 Claude, 내일 Codex, 다음 주 Gemini를 써도 상관없습니다. 규칙은 모델 기억이 아니라 Git에서 집행됩니다.

## 토큰도 아끼나?

게이트 자체는 **LLM 토큰을 0개 씁니다.** 로컬 Python 스크립트입니다.

```sh
python scripts/check_frozen.py
python scripts/check_git_policy.py
python scripts/check_scope.py
```

줄일 수 있는 건 잘못된 변경 뒤에 따라오는 비용입니다.

- 불필요한 파일 탐색
- 범위 밖 리팩터링
- 그 리팩터링용 코드 생성
- 추가 테스트
- 회귀 원인 조사
- 롤백
- 다시 수정하고 다시 테스트

"토큰 37% 절약" 같은 숫자는 일부러 적지 않았습니다. 프로젝트마다 에이전트가 범위를 벗어나는 빈도가 다르기 때문입니다.

이건 토큰 최적화기가 아니라 **애초에 필요 없던 작업이 생기는 걸 막는 도구**입니다.

## 작업 범위까지 잠글 수 있습니다

`check_scope.py`를 사용하면 현재 작업에서 허용된 경로를 정할 수 있습니다.

```text
작업: 설정 화면 간격 수정

허용:
frontend/settings/**
frontend/styles/settings.css

금지:
backend/**
database/**
billing/**
```

scope는 선택 기능입니다. 설정하지 않으면 비활성 상태입니다.

## Git에 남은 진짜 미완료 작업도 찾습니다

AI 에이전트는 브랜치와 worktree를 만들고 다음 작업으로 넘어가는 일이 많습니다.

`check_git_policy.py`는 브랜치 개수만 세지 않습니다. `git cherry`의 패치 동등성으로 이미 squash나 rebase를 통해 main에 반영된 것과 실제로 main에 없는 작업을 구분합니다.

이 도구가 나온 프로젝트에서는 "미병합 브랜치 11개"가 "실제로 확인할 것 1개"로 줄었습니다.

## 어디서 나왔나

이론부터 만든 도구가 아닙니다.

AI 에이전트들이 실제 프로덕션 코드를 몇 달 동안 만들었고, 그 과정에서 라이브가 60번 깨졌습니다. 매번 아래 형식으로 기록했습니다.

```text
Symptom   어떻게 보였나
Cause     왜 그렇게 됐나
Fix       무엇을 고쳤나
Rule      다음부터 어떻게 하나
```

그중 사람이 기억할 필요 없이 코드로 강제할 수 있는 규칙이 이 게이트가 됐습니다.

그 배경이 된 실패 기록 28건도 `FAILURE_MODES.md`에 들어 있습니다.

## 설치

Linux / macOS:

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /path/to/your-repo
```

Windows:

```powershell
git clone https://github.com/produckyou-design/agent-guardrails
.\agent-guardrails\install.ps1 C:\path\to\your-repo
```

설치 확인:

```sh
python scripts/doctor.py
python scripts/doctor.py --json
```

로컬 훅은 `--no-verify`로 건너뛸 수 있지만 CI는 건너뛸 수 없습니다. 둘 다 두는 것을 권합니다.

## 처음부터 전부 잠그지 마세요

처음에는 비워둬도 됩니다.

```json
{
  "frozen": []
}
```

에이전트가 어느 날 이미 끝난 코드를 쓸데없이 건드렸다면 그때 하나 추가하면 됩니다.

저장소 전체를 잠그면 경고가 소음이 됩니다. 실제로 완성됐고 건드렸을 때 비용이 큰 경로만 보호하는 편이 낫습니다.

## `git add -A`도 피합니다

에이전트는 working tree의 모든 변경이 자기 것이라고 가정하면 안 됩니다.

```sh
git add -A
git add .
git add -u
```

대신 자신이 수정한 파일을 명시합니다.

```sh
git add src/thing.py tests/test_thing.py
```

## 검증은 실제 실행한 것만

`skill/SKILL.md`에는 diff만으로 강제하기 어려운 운영 규칙이 들어 있습니다.

코드를 읽고 "될 것 같다"고 말하는 건 검증이 아닙니다. 실행하지 못했다면 `NOT_RUN`, 실패했다면 실패했다고 남깁니다. 화면이 바뀌었다면 실제 렌더링도 확인합니다.

## 테스트

```sh
python tests/test_gates.py
```

16개 테스트가 있습니다. mock으로 Git을 흉내내지 않고 임시 디렉터리에 실제 Git 저장소를 만들고 실제 커밋과 별도 프로세스로 게이트를 실행합니다.

게이트 자체에서 발견된 버그도 회귀 테스트로 남겨둡니다.

규칙은 실행되는 코드여야 한다고 주장하는 프로젝트라면 자기 규칙부터 실행 가능한 형태로 검증할 수 있어야 합니다.

## 같이 들어 있는 것

- `FAILURE_MODES.md` - 이 규칙들이 나온 실제 실패 기록 28건
- `skill/SKILL.md` - 에이전트용 운영 규칙
- `check_frozen.py` - 완성된 경로 보호
- `check_scope.py` - 선택형 작업 범위 제한
- `check_git_policy.py` - 실제로 남은 Git 작업 판별
- `check_guardrail_integrity.py` - 가드레일 자체 보호
- `doctor.py` - 설치 상태 진단

## 하지 않는 것

시크릿 검사는 gitleaks 같은 도구가 더 잘합니다.

일반적인 위험 코드 패턴은 semgrep 같은 도구가 더 잘합니다.

코드 리뷰를 대체하지 않습니다.

AI가 더 좋은 코드를 쓰게 만들지도 않습니다.

딱 하나를 다룹니다.

> 이미 맞게 돌아가던 코드에 들어가는 그럴듯한 범위 밖 수정이 평범한 커밋처럼 조용히 들어가는 것을 막습니다.

## 한 줄로 말하면

프롬프트에

```text
기존 코드 불필요하게 건드리지 마세요.
```

라고 한 줄 더 쓰는 도구가 아닙니다.

그 말을 무시했을 때

```text
commit rejected
```

가 뜨게 만드는 도구입니다.

## 라이선스

MIT. 필요한 것만 가져다 써도 됩니다.