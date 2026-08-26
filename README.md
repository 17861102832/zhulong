# 烛龙 Zhulong · 超长程永昼编排器

> 睁眼为昼，闭眼为夜，操控昼夜永不停歇。
> 一个给 AI Agent 用的**长程任务编排器**：让任意 agent 跑一天一夜也不丢状态、不偏航、能冷续传。

---

## 它解决什么痛点

你让 AI 干一件"大活"——写一本书、重构一个项目、盘点几万文件——常常卡在这几件事：

- **上下文爆炸**：聊到第 50 轮，前面的决策全忘了。
- **轮数限制**：平台有对话轮数上限，跑到一半被砍。
- **目标漂移**：每次偏一点，最后离目标十万八千里（最贵的失败）。
- **半夜断线**：机器休眠、会话被杀，第二天从头来。

烛龙不替你干活，它是**记分牌 + 伤病恢复协议**：把"任务进度、每次思考、每步验证"全部落盘成账本，让**任何 agent**（包括你自己手写循环）都能跨会话、跨中断接着干。

> 它不是运行时，是**纪律 + 工具**。真正"崩溃自愈"的是 Temporal 那种 durable execution 引擎；烛龙用最小代价在**零基建、个人单机、单 agent** 环境给你"死掉也能从账本续上"的能力。

---

## 核心机制（六大支柱）

1. **事件溯源（Event Sourcing）**：状态 = 对事件日志的折叠。所有进展只追加写 `events.jsonl`（单调递增 seq），**绝不覆盖**。
2. **flush 屏障**：每次落盘 `f.flush()` + `os.fsync()`，进程被杀也不丢已写事件。
3. **账本恢复图（Ledger）**：`ledger.md` 是人类可读的进度锚点。上下文压缩、换会话后，**只信 ledger + events**。
4. **子代理隔离委派**：长任务拆子任务，派全新隔离子代理，只通过文件交接——主上下文永远干净，从而突破上下文/轮数限制。
5. **四道防漂移防线**：DoD 量化契约 → 每任务审查闸 → 每 K 步对齐检查点 → 终局回归校验。
6. **自动进化闭环**：`reflect` 分析事件流产出教训，沉淀 `evolution.md`；下一个会话自动加载。

---

## 快速开始

零依赖，只要 Python 3.8+（标准库即可，无需 pip install）。

```bash
# 初始化一个长任务
ZHULONG_ROOT=./zhulong python zhulong.py init my_task \
  --name "写一本小说" \
  --goal "完成全书 30 章" \
  --dod  "chapter 数 == 30 且每章 >= 2000 字"

# 每干完一步，落盘
ZHULONG_ROOT=./zhulong python zhulong.py event my_task step/done \
  --payload '{"step":"第1章","result":"ok"}'

# 自动验证（重要：验证完全依赖 check 命令的退出码）
ZHULONG_ROOT=./zhulong python zhulong.py verify my_task \
  --check "python check_chapters.py"

# 每推进几步，反思一次
ZHULONG_ROOT=./zhulong python zhulong.py reflect my_task

# 断线/换会话后，从账本冷续传
ZHULONG_ROOT=./zhulong python zhulong.py resume my_task

# 看当前状态（事件溯源折叠重建）
ZHULONG_ROOT=./zhulong python zhulong.py state my_task
```

---

## 命令参考

| 命令 | 作用 |
| --- | --- |
| `init <id>` | 建任务，生成 events/ledger/plan/evolution |
| `event <id> <type>` | 追加一条事件（step/done、step/verify、task/end…） |
| `state <id>` | 从 events 折叠出当前状态 |
| `resume <id>` | 输出续传提示（下一步该干啥） |
| `verify <id> [--check "shell"]` | 自动验证；无 check 时跑内置结构检查 |
| `reflect <id>` | 反思闭环，产出教训并写入 evolution.md |
| `archive <id> <lesson>` | 沉淀一条进化教训 |
| `manifest` | 重建任务索引 manifest.json |

---

## 实战验证（不粉饰）

在 4403 文件 / 3.70 GB 的真实资产库盘点任务上跑过：

- 前台首段 → 后台 agent → **每小时心跳自动化接手**，用 `--all-left` 补齐剩余块。
- 自动化**无人值守时不仅续传，还自修了一个扫描器 bug**（漏扫根级文件导致计数不符），复跑后终验通过。
- 共 3 次 `verify` 失败被 DoD 闸拦下，**没有一次误判完成**。

诚实结论：本任务实际有效工时约 1 小时，但证明了"中断可冷续传 + 自动验证 + 自动进化"三件套在真实中断下成立。

---

## 与顶级方案的诚实对比（差距）

| 维度 | 烛龙 | LangGraph+Temporal / Codex |
| --- | --- | --- |
| 运行时 | 手动调 event/resume | 自动 durable execution |
| 自动验证 | 外挂式（靠 check 退出码） | 内建自测 / 沙箱验证 |
| 沙箱隔离 | 仅文件交接概念 | 容器化进程隔离 |
| 反思闭环 | evolution.md 被动日志 | 强制规则编码进 lint |
| 可观测性 | ledger.md 纯文本 | LangSmith / Langfuse |
| 实战规模 | 单任务实测 | 百万行生产 |

**定位**：把 LangGraph / Temporal / Codex 的核心耐久思想，浓缩成一个你看得懂每一行的小工具。它不是平台，不比 Codex 先进；它的价值是零依赖、可审计、贴合"单 agent"偏好。

---

## 作为 WorkBuddy 技能使用

仓库自带 `SKILL.md`。把本目录放入 `~/.workbuddy/skills/zhulong/`（用户级=全局），即可在 WorkBuddy 技能列表直接使用；`zhulong.py` 仍为独立 CLI，两者共用。

---

## License

MIT © Zhao Xikun（赵锡坤）。自由使用、修改、再发布。
