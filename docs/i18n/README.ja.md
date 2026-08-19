# agent-guardrails

AIコーディングエージェントに「ここの余白だけ直して」と頼んだのに、終わってみたら12ファイル変わっていたことはありませんか？

関数名が変わり、重複コードが「整理」され、何か月も安定していたリトライ処理まで簡略化されている。diffを見るともっともらしい。テストも通るかもしれません。

そして数日後、関係ない場所が壊れます。

`agent-guardrails` はその問題を止めるための小さなGitゲートです。**AIエージェントが、すでに完成していて今回のタスク範囲外のコードを変更すること**をコミット時に止めます。

プロンプトに「既存コードを触らないで」ともう一文足して信じるのではなく、ルール自体を実行可能にします。保護されたパスが変更されれば、コミットは拒否されます。

依存関係なし。モデルAPIなし。PythonとGitだけです。

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## 30秒テスト

エージェントに小さなタスクを一つ頼みます。

```text
設定ページの余白だけ直して。
```

終わったら:

```sh
git diff --stat
```

2ファイルだけのつもりが9ファイル変わっていたら、残り7ファイルを開いてみてください。

よくあるのはこんな変更です。

```text
「分かりやすくするため名前を変更しました」
「重複ロジックを共通化しました」
「未使用に見えたコードを削除しました」
「一貫性のため周辺コードも修正しました」
```

全部もっともらしい。でも全部頼んでいません。

diffに本当に頼んだ変更しか入らないなら、まだこのツールは不要かもしれません。

## 何を解決するのか

例えば次のファイルが3か月間、本番で問題なく動いているとします。

```text
src/billing/charge.py
```

今日のタスクはこれだけです。

```text
請求書ページの余白を調整
```

エージェントは `charge.py` がなぜ少し不自然な形なのか知りません。半年前の障害を防ぐために残った分岐なのかもしれません。エージェントが見るのは現在のコードであって、その形になった履歴ではありません。

だから普通はこう書きます。

```text
このファイルは触らないでください。
```

`AGENTS.md`、`CLAUDE.md`、プロンプト、コメントなどに。

問題は、ドキュメントはルールを説明できても強制はできないことです。

`agent-guardrails` は

```text
触らないでください
```

を

```text
commit rejected
```

に変えます。

## 仕組み

完成済みのパスを `frozen.json` に登録します。

```json
{
  "frozen": [
    {
      "label": "Billing",
      "paths": ["src/billing/charge.py"],
      "reason": "完成済みで本番稼働中。ロードマップ対象外。",
      "what_breaks": "計算が間違っても画面は正常に見え、金額だけが変わります。",
      "before_you_touch": [
        "部分返金は refund.py が担当します。",
        "失敗時はトランザクション全体をロールバックします。",
        "通貨の丸めは境界で一度だけ決定します。"
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

このパスを変更してコミットしようとすると、必要な文脈が最も重要な瞬間に止まります。

```text
$ git commit -m "invoice: tidy up rounding"

frozen: FAIL - a frozen path was changed
  src/billing/charge.py
      [Billing] Finished and in production.
      breaks -> Wrong math still renders a normal screen.
      verify -> pytest tests/test_billing.py -q
```

ゲートはローカルPythonです。LLMを呼びません。

通常の作業はそのまま通過し、境界を越えたときだけ追加情報が出ます。

## 本当に変更が必要なら

Frozenは永久凍結ではありません。

正当な変更ならコミットメッセージに3行書きます。

```text
UNFREEZE: src/billing/charge.py - 新しい決済方式の分岐が必要
UNFREEZE-IMPACT: 誤ると請求額が変わる可能性がある
UNFREEZE-ROLLBACK: git revert <sha> 後に pytest tests/test_billing.py を再実行
```

1行でも欠ければコミットは拒否されます。

「なぜ今変えるのか」だけでは足りません。実績のあるコードを変えるなら、**間違えたら何が壊れるか**、**どう戻すか**まで説明できる必要があります。

## 実際に何が変わるか

### 小さな依頼が巨大diffになりにくい

```text
依頼:
余白修正

勝手に付いてきた変更:
コンポーネント名変更
API helperリファクタ
リトライ処理簡略化
型定義統合
```

スコープの逸脱がmainに入る前に見えるようになります。

### 不自然に見えて理由のあるコードが残る

成熟したコードベースには「整理したくなるが、実は何かを支えている」コードがあります。`before_you_touch` はエージェントが触ろうとした瞬間に理由を見せます。

### レビューに優先順位がつく

夜間エージェントが34コミット作り、そのうち2つにだけ `UNFREEZE` があるなら、その2つから見ればいい。

### モデルが変わってもルールは残る

今日Claude、明日Codex、来週Geminiでも関係ありません。強制するのはモデルの記憶ではなくGitです。

## トークンは節約できる？

ゲート自体が使う **LLMトークンは0です。** ローカルスクリプトだからです。

```sh
python scripts/check_frozen.py
python scripts/check_git_policy.py
python scripts/check_scope.py
```

減らせる可能性があるのは、悪い変更の後に発生する高コストな作業です。

- 不要なファイル探索
- 範囲外リファクタリング
- そのためのコード生成
- 追加テスト
- 回帰原因の調査
- ロールバック
- やり直し

「37%節約」のような数字はあえて出していません。どれだけエージェントが範囲外に出るかはプロジェクトごとに違うからです。

これはトークン最適化ツールではありません。**そもそも発生する必要のなかった作業を止めるツール**です。

## タスク範囲も制限できる

`check_scope.py` で許可パスを指定できます。

```text
タスク: 設定画面の余白修正

許可:
frontend/settings/**
frontend/styles/settings.css

禁止:
backend/**
database/**
billing/**
```

scopeは任意です。scopeファイルがなければチェックはinactiveです。

## 放置されたGit作業も探す

`check_git_policy.py` はブランチ数を数えるだけではありません。patch equivalence (`git cherry`) を使い、本当に `main` に入っていない作業と、squash/rebaseですでに反映済みの作業を区別します。

元のプロジェクトでは「未マージ11ブランチ」が「本当に確認すべき1ブランチ」になりました。

## どこから生まれたか

きれいな理論から作ったツールではありません。

AIエージェントが実際の本番コードを数か月開発し、その間に本番が60回壊れました。各事故を次の形式で記録しました。

```text
Symptom   どう見えたか
Cause     なぜ起きたか
Fix       何を直したか
Rule      次回どうするか
```

その中で機械的に強制できるルールがこのゲートになりました。

背景になった実際の失敗28件は `FAILURE_MODES.md` に入っています。

## インストール

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

診断:

```sh
python scripts/doctor.py
python scripts/doctor.py --json
```

ローカルhookは `--no-verify` で回避できますが、CIは回避できません。両方使うのを推奨します。

## 最初は空でいい

リポジトリ全体を凍結しないでください。

```json
{
  "frozen": []
}
```

エージェントが完成済みコードを「親切に」触った最初のタイミングで、そのパスを追加すれば十分です。

常に鳴るゲートはノイズになります。本当に完成済みで、壊したときのコストが高い場所だけ守ります。

## stagingの原則

避けるもの:

```sh
git add -A
git add .
git add -u
```

変更したファイルを明示します。

```sh
git add src/thing.py tests/test_thing.py
```

共有working treeの全変更が自分のものだとエージェントは仮定できません。

## 検証とは実行したこと

`skill/SKILL.md` はdiffだけでは強制しにくい運用ルールを扱います。

コードを読んで「動くはず」は検証ではありません。実行していないなら `NOT_RUN`、失敗したなら失敗と報告します。見た目が変わるなら完了扱いする前に実際のレンダリングを確認します。

## テスト

```sh
python tests/test_gates.py
```

16テストあります。Gitをmockせず、実際の一時Gitリポジトリ、実際のコミット、別プロセスのゲートで検証します。

ゲート自身で見つかったバグも回帰テストとして残します。

## 含まれるもの

- `FAILURE_MODES.md` - ルールの元になった実際の失敗28件
- `skill/SKILL.md` - エージェント運用ルール
- `check_frozen.py` - 完成済みパス保護
- `check_scope.py` - 任意のタスク範囲制限
- `check_git_policy.py` - 本当に残っているGit作業を判定
- `check_guardrail_integrity.py` - guardrail自体を保護
- `doctor.py` - インストール診断

## やらないこと

secret検出はgitleaksのようなツールの方が得意です。

一般的な危険パターン検出はsemgrepの方が得意です。

コードレビューは置き換えません。

AIにより良いコードを書かせるツールでもありません。

もっと狭い一つだけを扱います。

> すでに正しく動いているコードへの、もっともらしい範囲外変更が普通のコミットとして静かに入るのを止めます。

## 一言で言うと

これはもう一つのプロンプトではありません。

```text
既存コードを不要に変更しないでください。
```

その一文をエージェントが無視した後に、こうなるためのツールです。

```text
commit rejected
```

## License

MIT。必要なものだけ使ってください。