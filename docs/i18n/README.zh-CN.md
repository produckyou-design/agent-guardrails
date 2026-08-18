# agent-guardrails

一个在 AI 编码代理改动已完工代码时拒绝提交的工具。它由两个 Python 文件组成，
没有需要安装的依赖。

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## 这跟你有关吗？两分钟就能确认

给代理一个小而明确的任务，比如"修一下设置页的间距"。然后，在读代码之前先敲这个：

```sh
git diff --stat
```

数一下文件数。如果比你要求的多，就把多出来的打开看看。通常你会看到一次重命名、
一次重构，或者对某段本来就好好的代码做的"清理"。

这就是这个工具要解决的问题。不是代理写得烂，而是它改进了你没要求它改进的东西，
而这件事需要你在评审里每一次、一直都能发现。

如果 diff 里只有你要的那件事，你现在可能还用不上它。等哪天不是这样了再回来。

## 它解决什么问题

把代码交给 AI 代理时，麻烦通常不是出在它新写的代码上，而是出在它顺路碰到的代码上。

比如你让它修一下账单页的间距。它常常会顺手把旁边的税额计算也整理一遍。这不是马虎。
代理没有办法知道那段代码为什么长成那样，也不知道它是怎么变成现在这样的。而且这种改动
在代码评审里看起来并不奇怪。也没有测试覆盖它，因为那段代码一直好好的，没人想过要给它
写测试。

你可以在项目文档里写"不要动这个文件"。这挡不住。在这个工具诞生的那个项目里，这条规则
在文档里放了半年，一直被违反，连刚读完那句话的代理也照样违反，因为没有任何代码会去检查它。

这个工具把那条规则变成**真正会执行的东西**。

## 它怎么工作

你把已完工的路径写进 `frozen.json`。

```json
{
  "frozen": [
    {
      "label": "计费",
      "paths": ["src/billing/charge.py"],
      "reason": "已完工并在生产运行。不在任何路线图上。",
      "what_breaks": "算错了画面依然正常，只有金额会变。",
      "before_you_touch": [
        "部分退款由 refund.py 处理，不在这里。",
        "失败时会回滚整笔事务。不要削弱这一点。"
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

接着安装 pre-commit 钩子，任何改动这些路径的提交都会被拒绝。这时你上面写的内容会原样
打印在终端里：为什么锁住、改错了会坏成什么样、动手之前需要知道什么。它出现在**有人被
挡住的那一刻**，而不是躺在一个没人打开的文件里。

代理真的动手时，看到的是这样：

```
$ git commit -m "invoice: tidy up rounding"

frozen: FAIL - a frozen path was changed
  src/billing/charge.py
      [Billing] Finished and in production. Not on any roadmap.
      breaks -> Wrong math still renders a normal screen. Only the amount changes.
        - Partial refunds live in refund.py, not here.
        - Failure rolls the whole transaction back. Do not weaken that.
        - Currency rounding is decided once, at the boundary. Not per call site.
      verify -> pytest tests/test_billing.py -q
```

### 如果确实需要改

在提交信息里写三行。

```
UNFREEZE: src/billing/charge.py - 新支付方式需要在这里加一个分支
UNFREEZE-IMPACT: 算错了画面依然正常，只有金额会变
UNFREEZE-ROLLBACK: git revert <sha>，然后重跑 pytest tests/test_billing.py
```

三行少任何一行，提交都会被拒绝。

为什么是三行而不是一行？因为理由只回答"为什么现在要改"。它不说你错了会发生什么，也不说
别人怎么退回原来的状态。而真正重要的恰恰是这两件事，被省略掉的也恰恰是这两件事。

**如果你写不出影响和回滚，说明你还没准备好动那段代码。** 而且你是现在发现的，不是在生产
环境里发现的。目的不是让你填表，而是让这个判断在写这三行的过程中自己浮出来。

## 有什么变好

**你不用再读每一条提交。** 假设代理一夜之间提交了 34 次，其中两条带着 UNFREEZE 行。
先读那两条就行。代理并没有变得更谨慎，只是现在它会标出自己在哪里越出了你给的范围。

**"修一下间距"不再变成十二个文件的改动。** 你只要了一件事，而 diff 里还夹着税额计算的
重构，以及一段重试循环的"清理"——那段循环存在只是因为上游 API 不可靠。这种情况会变少。

**那段撑着东西的临时方案不会再被整理掉。** 每个代码库里都有一行看起来不对、实际上撑着
什么的代码。每隔几个月就有人把它清理掉，之后某处出问题，却没人会联想到那次清理。
`before_you_touch` 就是钉在那个位置上的警示牌。

**规则不再取决于有没有人记得。** "别动移动端布局"是建议，而一个过不去的提交是信息。
后者在凌晨三点也管用，对一个从没见过你的模型也管用，在它进入你仓库的第一分钟就管用。

## 第二个工具

`check_git_policy.py` 用来找出没有合并的分支和忘了清理的 worktree。

分支留着本身不算大问题。问题在于**真正还没合并的工作被埋在里面**。代理会不断创建分支和
worktree，然后转去做下一件事，于是这些就堆积起来。

它不是简单地列出分支。它用补丁等价性（`git cherry`）来区分：内容确实不在 main 上的分支，
和那些已经通过 squash 或 rebase 合并进去的分支。在它诞生的那个项目里，这个区分把
"11 个未合并分支"变成了"1 个真正要紧的"。

## 它从哪里来

它出自一个真实项目：AI 代理在那里连续几个月编写生产代码。这个过程中线上坏了 60 次。
每一次都记录下发生了什么、下次该怎么做，其中能变成代码的规则，就变成了这些闸门。

这个仓库带的是在那个项目之外也适用的两个，外加它们背后的 28 起事故。事故记录在
`FAILURE_MODES.md` 里。

## 安装

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /path/to/your-repo
```

Windows：

```powershell
.\agent-guardrails\install.ps1 C:\path\to\your-repo
```

想手动装的话，把 `gates/*.py` 复制到你项目的 `scripts/`，把 `hooks/pre-commit` 放进
`.git/hooks/`，再把 `examples/workflow.yml` 复制到 `.github/workflows/`。

本地钩子可以用 `--no-verify` 跳过，CI 那道跳不过。两个都装是值得的。

**一开始把冻结列表留空。** 等哪天代理动了你以为已经完工的文件，再把那条路径加进去。

## 不要什么都冻

如果冻结覆盖了整个仓库，闸门就会一直响，然后真正的违规也会跟噪音一起被忽略。你马上要
动的路径，就敞开放着。

它诞生的那个项目在几百条路径里只冻了 19 条。

## 这个工具不做什么

**它不衡量任何东西改善了多少。** 这个 README 里没有 benchmark 表格，因为没有诚实的
办法做出一张。

**它不扫描密钥，也不扫描不安全的代码写法。** gitleaks 和 semgrep 做这件事强得多。
这个工具覆盖的是它们不覆盖的问题。

**它不会让代理写出更好的代码。** 它只是让错误的改动在上线前显形。

**它不替代代码评审。** 它只过滤评审最容易漏掉的那一类：对本来就正确的代码做出的、
微小而看起来合理的改动。

## 测试

```sh
python tests/test_gates.py
```

一共 16 个。它们在临时目录里建一个真实的 git 仓库，做真实的提交，把闸门当作独立进程
运行。没有任何 mock，因为要测的正是闸门怎么读取 git。

用昂贵代价换来的 bug 也在里面。比如声明 `src/db/sync-notices.py` 曾经会悄悄把
`src/db/sync_orders.py` 也解锁，原因是一个正则表达式把连字符吃掉了。

一个主张"验证必须可执行"的仓库，应该能先在自己身上证明这一点。把三行规则放松，会有
3 个测试失败；把连字符处理弄坏，路径那个测试会失败。你可以自己试。

## 这里还有什么

**`FAILURE_MODES.md`** 收录了这些闸门来源的 28 起事故。每一起是四行。

```
症状  当时看起来是什么样
原因  为什么会这样
处置  改了什么
规则  从今往后怎么做
```

判断一件事该不该进这个文件，只有一个标准：**如果我不写下来，我会不会再犯一次？**
如果会，就写进去，哪怕什么都没坏。真正反复出现的，很少是戏剧性的故障，而是你每次都会
绊到的那件小事。

**`skill/SKILL.md`** 是代理会读的操作规则。闸门只抓那些能机械检查的东西，其余的由它
覆盖，比如只汇报你真正跑过的验证。

## 许可证

MIT。有用的拿走就行。
