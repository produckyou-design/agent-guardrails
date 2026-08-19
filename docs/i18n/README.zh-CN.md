# agent-guardrails

让 AI 编码代理“只改一下间距”，结果回来一看改了 12 个文件？

函数被重命名，重复代码被“清理”，一个稳定运行了几个月的重试循环也被顺手简化。diff 看起来很合理，测试甚至可能全部通过。

几天后，另一个毫不相关的地方坏了。

`agent-guardrails` 就是为这个问题准备的小型 Git gate：**阻止 AI 代理修改已经完成、而且不属于当前任务范围的代码。**

它不是再往 prompt 里加一句“不要乱改”，而是把规则变成可执行代码。受保护路径一旦被修改，commit 直接被拒绝。

无依赖。无模型 API。只有 Python 和 Git。

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## 30 秒测试

给代理一个很小的任务：

```text
只调整设置页面的间距。
```

结束后运行：

```sh
git diff --stat
```

如果你预期只改 2 个文件，却出现了 9 个，就打开另外 7 个看看。

通常会看到：

```text
“为了更清晰而重命名。”
“抽取了重复逻辑。”
“删除了看起来未使用的代码。”
“为了保持一致顺手修改了附近代码。”
```

都很合理。也都不是你要求的。

如果你的 diff 一直只包含明确要求的改动，那你可能暂时不需要它。

## 它解决什么问题

假设这个文件已经在生产环境稳定运行三个月：

```text
src/billing/charge.py
```

今天的任务只是：

```text
调整发票页面间距。
```

代理不知道 `charge.py` 为什么长得有点奇怪。它不知道那段分支是不是六个月前真实事故留下的防线。它看到的是代码，不是代码形成的历史。

所以我们经常写：

```text
不要修改这个文件。
```

放进 `AGENTS.md`、`CLAUDE.md`、prompt 或注释。

问题是，文档只能解释规则，不能执行规则。

`agent-guardrails` 把：

```text
请不要改这里
```

变成：

```text
commit rejected
```

## 工作方式

把已经完成的路径写进 `frozen.json`：

```json
{
  "frozen": [
    {
      "label": "Billing",
      "paths": ["src/billing/charge.py"],
      "reason": "已经完成并在生产环境运行，不在当前路线图中。",
      "what_breaks": "计算错误时页面仍然正常显示，只有金额会错。",
      "before_you_touch": [
        "部分退款由 refund.py 处理。",
        "失败时会回滚整个事务。",
        "货币舍入只在边界处决定一次。"
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

代理修改该路径并尝试 commit 时，会在最需要上下文的时刻被拦住：

```text
$ git commit -m "invoice: tidy up rounding"

frozen: FAIL - a frozen path was changed
  src/billing/charge.py
      [Billing] Finished and in production.
      breaks -> Wrong math still renders a normal screen.
      verify -> pytest tests/test_billing.py -q
```

gate 是本地 Python，不调用 LLM。

正常工作直接通过。只有越界时才显示额外上下文。

## 如果真的必须改被冻结的文件

Frozen 不代表永远不能改。

合法修改需要在 commit message 里写三行：

```text
UNFREEZE: src/billing/charge.py - 新支付方式需要在这里增加分支
UNFREEZE-IMPACT: 逻辑错误可能改变实际扣款金额
UNFREEZE-ROLLBACK: git revert <sha> 后重新运行 pytest tests/test_billing.py
```

少一行，commit 就会被拒绝。

因为“为什么现在要改”还不够。改动已经验证过的代码之前，你还应该知道：**如果错了会坏什么**，以及 **怎么退回去**。

## 实际会改变什么

### 小任务不再轻易变成巨大 diff

```text
请求：
修一下间距

额外改动：
重命名组件
重构 API helper
简化 retry
合并类型定义
```

范围漂移会在进入主线前暴露出来。

### 看起来奇怪但有原因的代码能活下来

成熟代码库里总有“看起来应该清理”的代码，但它可能正在托住某个真实问题。`before_you_touch` 会在代理真正准备动手时把原因展示出来。

### Review 有了优先级

如果夜间代理生成 34 个 commit，其中只有 2 个带 `UNFREEZE`，先看这 2 个。

### 模型可以换，规则不换

今天 Claude，明天 Codex，下周 Gemini。规则存在 Git 里，不依赖模型记忆。

## 能省 token 吗？

gate 本身消耗 **0 个 LLM token**。它们只是本地脚本：

```sh
python scripts/check_frozen.py
python scripts/check_git_policy.py
python scripts/check_scope.py
```

真正可能减少的是错误改动之后的昂贵工作：

- 不必要的文件探索
- 越界重构
- 为这些重构生成代码
- 额外测试
- 回归问题定位
- 回滚
- 重新做任务

这里故意没有“节省 37%”之类的数字，因为结果取决于你的代理多常越界。

这不是 token 优化器。它是在阻止本来就不该产生的工作。

## 可选的任务范围限制

`check_scope.py` 可以把某个任务限制在允许路径内：

```text
任务：设置页面间距

允许：
frontend/settings/**
frontend/styles/settings.css

禁止：
backend/**
database/**
billing/**
```

scope 是可选功能。没有 scope 文件时检查处于 inactive 状态。

## 还能找出真正遗留的 Git 工作

`check_git_policy.py` 不只是数分支。它通过 patch equivalence（`git cherry`）区分：真正还没进 `main` 的工作，以及已经通过 squash/rebase 合入的工作。

在最初的项目里，这把“11 个未合并分支”缩小成了“1 个真正有未完成工作的分支”。

## 它从哪里来

这不是从一套漂亮的 agent safety 理论开始设计的。

它来自 AI 代理在真实生产代码上连续工作几个月的经验。生产环境一共坏过 60 次。每次都按下面的格式记录：

```text
Symptom   看起来发生了什么
Cause     为什么发生
Fix       怎么修
Rule      下次怎么办
```

其中可以机械执行的规则，最终变成了这些 gate。

仓库里的 `FAILURE_MODES.md` 保留了 28 个真实失败记录。

## 安装

Linux / macOS：

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /path/to/your-repo
```

Windows：

```powershell
git clone https://github.com/produckyou-design/agent-guardrails
.\agent-guardrails\install.ps1 C:\path\to\your-repo
```

诊断：

```sh
python scripts/doctor.py
python scripts/doctor.py --json
```

本地 hook 可以用 `--no-verify` 绕过，CI 不行。建议两者都用。

## 从空列表开始

不要一开始冻结整个仓库。

```json
{
  "frozen": []
}
```

第一次看到代理“顺手优化”已经完成的代码时，再把那条路径加入即可。

频繁触发的 gate 最终只会变成噪音。只保护真正完成、而且改坏成本很高的代码。

## Staging 纪律

避免：

```sh
git add -A
git add .
git add -u
```

更推荐明确写出文件：

```sh
git add src/thing.py tests/test_thing.py
```

代理不能假设共享 working tree 里的所有变更都属于自己。

## 验证意味着真的执行

`skill/SKILL.md` 处理那些无法仅从 diff 强制判断的规则。

只读代码然后说“应该能工作”不算验证。没运行就写 `NOT_RUN`；失败就如实报告失败。可视化改动在宣布完成前应该看真实渲染结果。

## 测试

```sh
python tests/test_gates.py
```

共有 16 个测试。它们创建真实的临时 Git 仓库、真实 commit，并把 gate 作为独立进程运行，而不是 mock Git 行为。

在 gate 自己身上发现的 bug 也会保留为回归测试。

## 包含内容

- `FAILURE_MODES.md` - 28 个产生这些规则的真实失败记录
- `skill/SKILL.md` - agent 运行规则
- `check_frozen.py` - 保护已完成路径
- `check_scope.py` - 可选任务范围限制
- `check_git_policy.py` - 查找真正未完成的 Git 工作
- `check_guardrail_integrity.py` - 保护 guardrail 自身
- `doctor.py` - 只读安装诊断

## 它不做什么

不扫描 secret；这类工作交给 gitleaks。

不检测一般危险代码模式；semgrep 更擅长。

不替代 code review。

也不会让 AI 写出更好的代码。

它只做一件更窄的事：

> 阻止那些“看起来很合理、实际上超出范围”的修改，悄悄进入已经正确运行的代码。

## 一句话版本

它不是再加一句 prompt：

```text
请不要无必要地修改现有代码。
```

而是当代理忽略这句话之后：

```text
commit rejected
```

## License

MIT。需要什么就拿什么。