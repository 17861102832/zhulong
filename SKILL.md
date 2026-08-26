---
name: "zhulong"
description: "烛龙·超长程永昼编排器。睁眼为昼、闭眼为夜——天生操控昼夜、永不停歇的守护者。合并 long-task-orchestrator + autonomous-runner，借鉴 LangGraph checkpoint、deer-flow 子代理、OpenAI Agents SDK Guardrails、subagent-driven-development 账本恢复图、Reflexion 自进化。用 append-only 事件溯源 + 账本锚点 + 子代理隔离委派，保证任务突破上下文/轮数限制、自主运行 24h+ 跨昼夜不中断，并通过防漂移护栏与自动进化闭环持续修正，防止累积偏离导致最终失败。已内置 verify 自动验证与 reflect 启发式反思闭环；当用户需要'一直跑到完成'、后台昼夜运行、跨会话断点续传、长程不偏航、防目标漂移、自动进化、合并多个长程技能时触发。"
---

# 烛龙 · 超长程永昼编排器 (Zhulong — Perpetual-Day Orchestrator)

烛龙者，睁眼为昼，闭眼为夜。一条龙守住一场远征，昼夜不息，路标不失，方向不偏。
把长程任务当成被烛龙盯着的远征：有地图、有路标、会自我纠偏、且永不停歇。

## 它从哪里来（合并 + 借鉴，直接站在巨人肩上）

| 来源 | 借鉴的机制 | 本技能如何用它 |
|------|-----------|---------------|
| `long-task-orchestrator`（本地） | 定时调度 / 目标驱动 / 任务看板 | 保留触发词与模式 |
| `autonomous-runner`（本地） | **append-only 事件日志 + fold 重建 + flush 屏障** | "描点/状态存档"核心地基 |
| `subagent-driven-development`（本地） | **账本即恢复地图**、每任务审查闸、修复循环升级 | "防漂移 + 冷续传"核心 |
| `dispatching-parallel-agents`（本地） | 子代理隔离上下文、按领域分派 | "突破上下文限制"核心 |
| LangGraph（GitHub, 38k★） | checkpoint / durable execution / replay / human-in-the-loop | 断点精确恢复 + 人工校准点 |
| deer-flow（GitHub, 字节 74k★） | 沙箱 + 持久记忆 + 子代理协作 + 消息网关 | 子代理并行 + 状态持久化 |
| OpenAI Agents SDK（GitHub） | **Guardrails 输入/输出校验** | 防漂移护栏 |
| CrewAI / MS Agent Framework（GitHub） | 角色化分工、会话状态 | 子代理角色化 |
| Google ADK（GitHub） | Workflow Runtime 图执行 + 人工 checkpoint | 长程工作流编排 |
| Reflexion / Generative Agents（论文） | 自反思循环、记忆流 + 反思 | 自动进化闭环 |

一句话：**状态写文件不写上下文、子代理隔离保主上下文干净、每步前后比对目标防漂移、跨轮次沉淀教训自动进化、靠心跳自动化撑满一天一夜。**

## 三大支柱

### 1. 锚点事件溯源（Anchoring / Event Sourcing）
- 任务状态 = `fold(事件日志)`，状态不靠内存或快照，全从 `events.jsonl` 重建。
- 每行一个 JSON 事件，`seq` 单调递增，`time` 毫秒戳，**只追加不覆盖**。
- **flush 屏障**：任何"不可逆操作"（模型请求、写文件、发消息、进入下一步）之前，先把事件落盘 + fsync。中断任意时刻都可恢复。
- 思考状态也写进事件（`reasoning` 类型），实现"每次思考的状态都存入档案"。

### 2. 账本恢复图（Ledger as Recovery Map）
- `ledger.md` 是人类可读的进度锚点：目标契约、已完成步骤、当前状态。
- 上下文压缩 / 会话中断后，**只信 ledger + events，不信自己的记忆**。
- 这是"描点"的可视化层；events 是真相源，ledger 是导航图。
- 这一步直接解决你当年研究过的痛点：superpowers 原话——"controllers that lost their place have re-dispatched entire completed task sequences — the single most expensive failure observed. Track progress in a ledger file."

### 3. 子代理隔离委派（Isolated Subagent Delegation）
- 每个子任务派发一个**全新、上下文隔离**的子代理，只通过 brief 文件交接，绝不继承主会话历史。
- 主控制器上下文永远只装：计划 + 账本 + 当前任务 brief。跑 24h 也不溢出。
- 这是"突破上下文限制 / 突破轮数限制"的关键。

## 防漂移（核心痛点：每次偏一点 → 最终完不成）

漂移是长程任务的第一杀手。本技能用四道防线：

1. **目标契约（DoD）先行**：启动时写下量化"完成判定标准"，作为唯一比对基准。
2. **每任务审查闸**：子代理返回后，主控制器跑 spec 合规 + 质量双审，并用 `verify` 自动校验产物达标，未过不入账本。
3. **对齐检查点（每 K 步）**：重读 plan.md + ledger.md，自问"当前工作是否仍服务原始 DoD？"列出漂移并纠正，写 `alignment/check` 事件。
4. **终局回归校验**：收尾时把最终产物与 DoD 逐项比对，不符则进修复循环，绝不在漂移态写 `task/end reason=goal_reached`。

## 自动进化（不断进步）

- **修复循环（Fix Loop）**：审查不过 → 升级处理（R1-3 续派原代理 / R4-5 换新代理+更强模型 / 触顶裁决）。每轮写入 ledger。
- **反思闭环（reflect 指令）**：`zhulong reflect <tid>` 自动分析 events.jsonl——统计已完成步骤、失败验证数、最后事件时间、目标漂移信号，产出结构化 `suggestion` 并落 `evolution/lesson` 事件 + 追加 evolution.md。**这是启发式基底**：真正的 LLM 深化由 agent 读 evolution.md 后调整策略完成（stdlib 不调模型，保持零依赖可审计）。
- **进化档案（evolution.md）**：跨轮次/跨会话沉淀策略与教训，下次启动自动加载。这就是"自动进化"的载体。

## 24h+ 昼夜运行（突破轮数 / 跨昼夜不中断）

- **后台承载**：重循环用 `run_in_background` 的后台代理跑，不阻塞主会话。
- **心跳续传**：为目标窗口建**周期性自动化（cron/rrule）**，到点检查 manifest 里 `running` 的任务并续传——即使前台会话关了，烛龙也替你睁着眼，跨越白天黑夜。
  - 例：`automation_update` 建 recurring，rrule `FREQ=MINUTELY;INTERVAL=30`，prompt 让控制器读 ledger 续传未完成任务。
- **幂等**：fold 出已完成的步骤，重复触发自动跳过，不产生副作用。
- **资源节制**：并行子代理默认 ≤5；单步超 30min 标记超时；空闲期做维护不抢资源。
- **不眠机制**：把"继续"做成可重入函数——任何新回合/新会话读 ledger 即可无脑续上，因此昼夜不断。

## 快速开始

```bash
# 用托管 python 绝对路径（或任意 python3，脚本仅用标准库）
PY="C:/Users/赵锡坤/.workbuddy/binaries/python/versions/3.13.12/python.exe"

# 1) 初始化（写目标契约 + 账本 + 计划骨架 + 事件日志）
$PY zhulong.py init <task_id> --name "..." --goal "..." --dod "量化完成标准"

# 2) 每完成一步 / 每次思考，落盘（flush 屏障）
$PY zhulong.py event <task_id> step/done --payload '{"step":"抓取数据","result":"ok"}'
$PY zhulong.py event <task_id> reasoning --payload '{"thought":"发现X更优，调整策略"}'

# 3) 任意时刻看状态（fold 重建）
$PY zhulong.py state <task_id>

# 4) 新会话/压缩后续传（打印续传提示）
$PY zhulong.py resume <task_id>

# 5) 每步后自动验证（差距②：自动验证）
$PY zhulong.py verify <task_id> --check "shell命令返回0即通过，如: test -f results/report.md"
$PY zhulong.py verify <task_id>            # 无 --check 时跑内置结构检查(结果目录非空)

# 6) 反思闭环（差距④：启发式反思 → 沉淀 evolution.md）
$PY zhulong.py reflect <task_id>

# 7) 沉淀进化教训
$PY zhulong.py archive <task_id> "教训：子任务3应拆更细，否则超时"

# 8) 重建任务索引
$PY zhulong.py manifest
```

## 生命周期协议（照做即不偏航）

1. **启动（Plan）**：`init` → 填 plan.md（目标/DoD/全局约束/子任务分解，每任务带验收标准）。
2. **委派（Delegate）**：每个子任务用 `Agent` 工具派发全新子代理，brief 写文件，只给"任务+接口+约束+验收"，不给历史。
3. **执行（Execute + Flush）**：子代理干活；主控制器在其返回前后都写事件（flush 屏障）。
4. **审查（Review Gate）**：spec 合规 + 质量双审。不过 → 修复循环。
5. **记账（Ledger）**：通过才在 ledger.md 追加完成行 + 写 `step/done`。
6. **对齐（Align）**：每 K 步跑对齐检查点，检测并纠正漂移。
7. **反思（Reflect）**：里程碑写 `reflection` + 沉淀 `evolution.md`。
8. **续传（Resume）**：靠 ledger/events 跨会话/压缩无脑续上。
9. **收尾（Finish）**：终局回归 DoD 校验 → 写 `task/end reason=goal_reached` + 汇总报告。

## 事件类型速查

```
task/start        启动（含 goal + definition_of_done）
step/done         步骤完成（step, result）
reasoning         思考状态存档（thought）
tool/result       工具产出（tool, ok, summary）
step/verify       自动验证（check, rc, passed）   # 新增：每步后校验
alignment/check   对齐检查（drift: none|minor|major, action）
reflection        反思（worked, failed, next_strategy）
evolution/lesson  进化教训 / 反思闭环输出（reflection）
task/end          终止（reason: goal_reached|failed|cancelled）
```

## 与既有技能的关系

- **supersedes** `long-task-orchestrator` 与 `autonomous-runner`：JSON 快照升级为事件溯源+账本双轨；新增防漂移护栏与自动进化闭环。旧技能可并存，简单定时任务仍可用。
- **互补** `brainstorming` / `writing-plans`：启动阶段用它们做发散与计划；本技能负责计划的超长程落地与纠偏。
- **互补** `dispatching-parallel-agents` / `subagent-driven-development`：本技能把它们"隔离委派 + 账本恢复 + 审查闸"固化进同一协议。

## 与顶尖方案的差距（诚实版，2026-08 校准）

本技能是**个人单机、零基建、单 agent** 环境下的耐久纪律层，**不是运行时、不是平台**，明确弱于生产级方案。已知差距：

1. **无自动 durable 运行时**（最核心）：每步需 agent 自觉调 `event`/`verify`/`resume`，非运行时自动落日志。Temporal 式"进程死也续"靠外部 cron 心跳近似，非内建。
2. **无真沙箱/隔离执行**：子代理隔离仅为"文件交接"约定，无容器、无资源限制、无进程隔离。
3. **验证为外挂式**：`verify` 依赖你写 `--check` shell 命令或内置结构检查；无 Codex 式"跑测试+录屏+开PR"内建验证。
4. **反思为启发式**：`reflect` 做失败计数/漂移信号，非 Reflexion 式 LLM 自改行为；深度进化需 agent 读 evolution.md 后主动调整。
5. **无 human-in-the-loop 审批闸 / 无观测 UI**：仅 ledger.md 纯文本，无 LangSmith 式追踪。
6. **无分布式并行 fan-out + 幂等/版本化**：子代理委派未含健壮重试/合并。
7. **未实战 24h**：仅冒烟测试，无规模验证。

**定位**：把 LangGraph/Temporal/Codex 的耐久思想浓缩成可审计小工具+纪律，贴合"只用一个 agent"偏好。要逼近生产级，优先补①（心跳自动化已建）+③（verify 已建）+④（reflect 已建）。

## 铁律

1. 事件日志**只追加**，历史不可篡改。
2. 不可逆操作前**必 flush**（落盘+fsync）。
3. 子代理**绝不继承**主上下文；一切走文件。
4. 漂移**不过账**——未通过审查与对齐的步骤不标记完成。
5. 跨会话/压缩后**只信 ledger + events**。
6. 不靠"一直开着"保证连续——靠**可重入续传**保证昼夜不中断。
