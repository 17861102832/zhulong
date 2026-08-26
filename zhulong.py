#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
烛龙 (Zhulong) — 超长程任务的"锚点 + 事件溯源 + 冷续传"引擎。

设计哲学（来自对顶级方案的借鉴与合并）：
  - 事件溯源 (Event Sourcing)：状态不靠快照，靠 append-only 事件日志重建
    （借鉴 autonomous-runner / LangGraph checkpoint）
  - 账本恢复图 (Ledger as recovery map)：人类可读的进度锚点，跨上下文压缩/会话
    中断可恢复（借鉴 subagent-driven-development）
  - 子代理隔离委派：主控制器上下文永远干净，靠文件交接
    （借鉴 dispatching-parallel-agents / deer-flow）
  - 防漂移护栏：每步前后比对原始目标契约
    （借鉴 OpenAI Agents SDK Guardrails / LangGraph human-in-the-loop）

仅使用 Python 标准库。无网络、无密钥、无 eval。安全可审计。
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone, timedelta

ZHULONG_ROOT_ENV = "ZHULONG_ROOT"
TZ = timezone(timedelta(hours=8))  # Asia/Shanghai


def root():
    r = os.environ.get(ZHULONG_ROOT_ENV)
    if not r:
        r = os.path.join(os.getcwd(), "zhulong")
    os.makedirs(r, exist_ok=True)
    return r


def task_dir(tid):
    return os.path.join(root(), tid)


def events_path(tid):
    return os.path.join(task_dir(tid), "events.jsonl")


def ledger_path(tid):
    return os.path.join(task_dir(tid), "ledger.md")


def plan_path(tid):
    return os.path.join(task_dir(tid), "plan.md")


def evolution_path(tid):
    return os.path.join(task_dir(tid), "evolution.md")


def results_dir(tid):
    return os.path.join(task_dir(tid), "results")


def now_ms():
    return int(time.time() * 1000)


def now_iso():
    return datetime.now(TZ).isoformat()


def _read_last_seq(tid):
    p = events_path(tid)
    if not os.path.exists(p):
        return -1
    seq = -1
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj.get("seq"), int):
                    seq = max(seq, obj["seq"])
            except Exception:
                pass
    return seq


def cmd_init(args):
    tid = args.task_id
    d = task_dir(tid)
    os.makedirs(d, exist_ok=True)
    os.makedirs(results_dir(tid), exist_ok=True)

    seq0 = 0
    start_event = {
        "type": "task/start",
        "task_id": tid,
        "name": args.name or tid,
        "goal": args.goal or "",
        "definition_of_done": args.dod or "",
        "seq": seq0,
        "time": now_ms(),
        "iso": now_iso(),
    }
    with open(events_path(tid), "w", encoding="utf-8") as f:
        f.write(json.dumps(start_event, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())

    ledger = f"""# 烛龙 Ledger — {tid}

> 本文件是任务的"恢复地图"。每次上下文压缩或会话中断后，从这里续传。
> 最后更新：{now_iso()}

## 任务：{args.name or tid}
## 目标契约（Definition of Done）
{args.dod or args.goal or '(待填写量化完成标准)'}

## 进度锚点
- [ ] 初始化完成

## 已完成步骤
（每完成一步在此追加一行，含 seq）

## 当前状态
pending
"""
    with open(ledger_path(tid), "w", encoding="utf-8") as f:
        f.write(ledger)

    plan = f"""# 计划 — {tid}

## 目标
{args.goal or ''}

## 完成判定标准 (DoD)
{args.dod or '(必须量化：例如"写完 20 章，每章≥1500字，通过自检清单")'}

## 全局约束
- 不得偏离目标契约
- 子代理仅通过文件交接，不继承主上下文
- 每步前后写事件日志（flush 屏障）

## 子任务分解
（将目标拆为可独立验证的子任务，每任务一行，带验收标准）

1. 
"""
    with open(plan_path(tid), "w", encoding="utf-8") as f:
        f.write(plan)

    with open(evolution_path(tid), "w", encoding="utf-8") as f:
        f.write(f"# 进化档案 — {tid}\n\n> 跨轮次/跨会话沉淀的策略与教训，自动进化。\n\n")

    _regen_manifest()
    print(f"[zhulong] 已初始化任务 {tid} @ {d}")
    print(f"[zhulong] 事件日志: {events_path(tid)}")
    print(f"[zhulong] 账本: {ledger_path(tid)}")
    print(f"[zhulong] 计划: {plan_path(tid)}")


def append_event(tid, etype, payload=None, flush=True):
    seq = _read_last_seq(tid) + 1
    ev = {
        "type": etype,
        "task_id": tid,
        "seq": seq,
        "time": now_ms(),
        "iso": now_iso(),
    }
    if payload:
        ev.update(payload)
    with open(events_path(tid), "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        if flush:
            f.flush()
            os.fsync(f.fileno())
    return seq


def cmd_event(args):
    seq = append_event(args.task_id, args.type, json.loads(args.payload) if args.payload else None)
    print(f"[zhulong] event #{seq} {args.type} 已落盘 (flush 屏障)")


def fold_state(tid):
    p = events_path(tid)
    if not os.path.exists(p):
        return {"task_id": tid, "exists": False}
    state = {"task_id": tid, "steps_done": [], "tools": [], "status": "running", "last_seq": -1}
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            t = obj.get("type")
            state["last_seq"] = obj.get("seq", state["last_seq"])
            if t == "task/start":
                state["name"] = obj.get("name")
                state["goal"] = obj.get("goal")
                state["dod"] = obj.get("definition_of_done")
            elif t in ("step/done", "step"):
                state["steps_done"].append({"step": obj.get("step"), "result": obj.get("result"), "seq": obj.get("seq")})
            elif t == "task/end":
                state["status"] = obj.get("reason", "completed")
            elif t == "tool/result":
                state["tools"].append(obj)
    if state["status"] == "running" and state["last_seq"] >= 0:
        state["status"] = "running (未完成)"
    return state


def cmd_state(args):
    st = fold_state(args.task_id)
    print(json.dumps(st, ensure_ascii=False, indent=2))


def cmd_resume(args):
    tid = args.task_id
    st = fold_state(tid)
    lines = []
    lines.append(f"# 续传提示 — 任务 {tid}")
    lines.append(f"当前状态: {st.get('status')}")
    lines.append(f"目标: {st.get('goal', '')}")
    lines.append(f"完成判定: {st.get('dod', '')}")
    lines.append(f"已完成步骤数: {len(st.get('steps_done', []))}")
    if st.get("steps_done"):
        lines.append("最近完成:")
        for s in st["steps_done"][-10:]:
            lines.append(f"  - seq{s['seq']}: {s['step']} ({s['result']})")
    lines.append("")
    lines.append("## 请执行")
    lines.append("1. 读取 ledger.md 与 plan.md")
    lines.append("2. 从第一个未完成/失败的子任务继续（不要重跑已完成步骤）")
    lines.append("3. 每步前后调用 zhulong event 落盘")
    lines.append("4. 运行对齐检查：当前工作是否仍服务于 DoD？有漂移则纠正")
    print("\n".join(lines))


def cmd_archive(args):
    tid = args.task_id
    seq = append_event(tid, "evolution/lesson", {"lesson": args.lesson})
    with open(evolution_path(tid), "a", encoding="utf-8") as f:
        f.write(f"- (seq{seq}, {now_iso()}) {args.lesson}\n")
    print(f"[zhulong] 已沉淀进化教训 → {evolution_path(tid)}")


def _run_check(check_cmd, tid, timeout=600):
    """运行 shell 校验命令，返回 (returncode, 截断输出)。用于自动验证。"""
    import subprocess
    try:
        r = subprocess.run(check_cmd, shell=True, capture_output=True, text=True,
                           cwd=task_dir(tid), timeout=timeout)
        out = (r.stdout + r.stderr)[-4000:]
        return r.returncode, out
    except Exception as e:
        return -1, str(e)[:4000]


def cmd_verify(args):
    """自动验证：跑校验命令或内置结构检查，落 step/verify 事件。"""
    tid = args.task_id
    check = args.check
    if check:
        rc, out = _run_check(check, tid)
        passed = (rc == 0)
        seq = append_event(tid, "step/verify", {
            "check": check, "rc": rc, "passed": passed, "output": out
        })
        print(f"[zhulong] verify #{seq} passed={passed} rc={rc}")
        if not passed:
            print("---- verify output ----")
            print(out)
    else:
        rdir = results_dir(tid)
        has = os.path.isdir(rdir) and bool(os.listdir(rdir))
        # 内置结构检查：结果目录非空即视为通过
        passed = has
        seq = append_event(tid, "step/verify", {"builtin": "structural", "passed": passed})
        print(f"[zhulong] verify #{seq} (structural) passed={passed}")


def cmd_reflect(args):
    """反思闭环：分析事件日志，产出结构化 lesson 并沉淀到 evolution.md。"""
    tid = args.task_id
    p = events_path(tid)
    events = []
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
    steps = [e for e in events if e.get("type") == "step/done"]
    fails = [e for e in events if e.get("type") == "step/verify" and not e.get("passed")]
    goal = next((e.get("goal", "") for e in events if e.get("type") == "task/start"), "")
    last = events[-1] if events else None
    last_iso = last.get("iso") if last else None
    # 启发式反思：失败优先；无步骤即阻塞；否则正常。LLM 深化的接口留在 SKILL。
    if fails:
        suggestion = (f"检测到 {len(fails)} 次验证失败，优先排查最近失败: "
                      f"{fails[-1].get('check', '内置结构检查')}")
    elif not steps:
        suggestion = "尚无完成步骤，任务可能被阻塞——检查 ledger 中'进度锚点'与依赖。"
    else:
        suggestion = "进度正常，按 plan.md 继续；每完成子任务后 verify，每 K 步 reflect。"
    lesson = {
        "steps_done": len(steps),
        "verifies_failed": len(fails),
        "last_event": last_iso,
        "goal": goal,
        "suggestion": suggestion,
    }
    seq = append_event(tid, "evolution/lesson", {"reflection": lesson})
    with open(evolution_path(tid), "a", encoding="utf-8") as f:
        f.write(f"- (seq{seq}, {now_iso()}) REFLECT: {json.dumps(lesson, ensure_ascii=False)}\n")
    print(json.dumps(lesson, ensure_ascii=False, indent=2))


def _regen_manifest():
    r = root()
    tasks = []
    if os.path.isdir(r):
        for name in os.listdir(r):
            ep = os.path.join(r, name, "events.jsonl")
            if os.path.isfile(ep):
                st = fold_state(name)
                tasks.append({
                    "id": name,
                    "name": st.get("name", name),
                    "status": st.get("status"),
                    "last_seq": st.get("last_seq"),
                    "steps_done": len(st.get("steps_done", [])),
                })
    with open(os.path.join(r, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"tasks": tasks, "generated_at": now_iso()}, f, ensure_ascii=False, indent=2)


def cmd_manifest(args):
    _regen_manifest()
    print(f"[zhulong] manifest 已重建 @ {os.path.join(root(), 'manifest.json')}")


def main():
    ap = argparse.ArgumentParser(description="烛龙 Zhulong Orchestrator")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("task_id")
    p.add_argument("--name", default="")
    p.add_argument("--goal", default="")
    p.add_argument("--dod", default="")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("event")
    p.add_argument("task_id")
    p.add_argument("type")
    p.add_argument("--payload", default="")
    p.set_defaults(func=cmd_event)

    p = sub.add_parser("state")
    p.add_argument("task_id")
    p.set_defaults(func=cmd_state)

    p = sub.add_parser("resume")
    p.add_argument("task_id")
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("archive")
    p.add_argument("task_id")
    p.add_argument("lesson")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("verify")
    p.add_argument("task_id")
    p.add_argument("--check", default="")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("reflect")
    p.add_argument("task_id")
    p.set_defaults(func=cmd_reflect)

    p = sub.add_parser("manifest")
    p.set_defaults(func=cmd_manifest)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
