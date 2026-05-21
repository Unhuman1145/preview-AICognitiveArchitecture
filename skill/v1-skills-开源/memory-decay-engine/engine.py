#!/usr/bin/env python3
"""
Memory Decay Engine
───────────────────
每小时执行艾宾浩斯衰减 + 窄门复活 + 遗忘墓碑化

用法:
  python3 engine.py run          # 执行一轮衰减
  python3 engine.py status       # 查看所有记忆状态
  python3 engine.py revive ID    # 手动复活已遗忘的记忆
  python3 engine.py log          # 查看衰减历史

MIT License · © 2026 宇宸
"""

import json, os, sys, math, time, hashlib
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / ".v1_memory"
DATA_FILE = DATA_DIR / "compressor_data.json"
DECAY_LOG = DATA_DIR / "decay_log.json"
ARCHIVE_DIR = DATA_DIR / "archive"

EBBINGHAUS_TAU = 3600  # 1 小时半衰期


def load_data():
    if DATA_FILE.exists():
        return json.load(open(DATA_FILE))
    return {"memories": [], "meta": {"version": "v1.0"}}


def save_data(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_log():
    if DECAY_LOG.exists():
        return json.load(open(DECAY_LOG))
    return {"runs": []}


def save_log(log):
    with open(DECAY_LOG, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def ebbinghaus_decay(weight: float, elapsed_seconds: float) -> float:
    if weight >= 100:
        return weight
    return weight * math.exp(-elapsed_seconds / EBBINGHAUS_TAU)


def narrow_gate_probability(weight: float, memory_age_days: float) -> float:
    """窄门触发概率：越老越容易复活"""
    if not (8 < weight < 10):
        return 0
    p_base = 0.08
    p_increment = 0.002
    p_max = 0.30
    return min(p_base + memory_age_days * p_increment, p_max)


def deletion_probability(weight: float) -> float:
    if weight >= 10:
        return 0
    return ((10 - weight) / 10) ** 2


def seed_from_content(content: str) -> int:
    return int(hashlib.md5(content.encode()).hexdigest()[:8], 16)


def cmd_run():
    data = load_data()
    log = load_log()
    now = datetime.now()
    run_record = {"time": now.isoformat(), "decayed": 0, "revived": 0,
                  "tombstoned": 0, "protected": 0, "permanent": 0}

    for m in data["memories"]:
        if m.get("_forgotten"):
            continue  # 已墓碑

        w = m.get("weight", 50)
        if w == 101:
            run_record["permanent"] += 1
            continue

        if w >= 90:
            run_record["protected"] += 1
            continue

        # 计算时间差
        try:
            last = datetime.fromisoformat(m.get("last_active", m.get("created_at")))
            elapsed = (now - last).total_seconds()
        except:
            elapsed = 3600

        memory_age_days = elapsed / 86400

        # 窄门检查（8 < w < 10）
        if 8 < w < 10:
            p_gate = narrow_gate_probability(w, memory_age_days)
            seed = seed_from_content(m.get("content", m.get("summary", "")))
            if seed % 1000 < int(p_gate * 1000):
                m["weight"] = 10 + (seed % 3)  # 复活到 10-12
                m["last_active"] = now.isoformat()
                run_record["revived"] += 1
                continue

        # 遗忘检查（w < 10）
        if w < 10:
            p_del = deletion_probability(w)
            seed = seed_from_content(m.get("content", m.get("summary", "")))
            if seed % 100 < int(p_del * 100):
                # 墓碑化：移到 archive
                ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                archive_file = ARCHIVE_DIR / f"{m.get('id', 'unknown')}.json"
                with open(archive_file, "w") as f:
                    json.dump(m, f, indent=2, ensure_ascii=False)
                m["_forgotten"] = True
                run_record["tombstoned"] += 1
                continue

        # 正常衰减
        new_w = ebbinghaus_decay(w, elapsed)
        if m.get("recall_count", 0) > 0:
            new_w = new_w * (1 + m["recall_count"] * 0.02)
        new_w = min(new_w, w)  # 不升
        if w <= 10:
            new_w = max(new_w, w - 0.5)  # 低权重慢衰减

        old_w = w
        m["weight"] = round(new_w, 1)
        m["last_active"] = now.isoformat()

        if abs(old_w - m["weight"]) > 0.1:
            run_record["decayed"] += 1

    save_data(data)
    log["runs"].append(run_record)
    if len(log["runs"]) > 500:
        log["runs"] = log["runs"][-500:]
    save_log(log)

    print(json.dumps(run_record, ensure_ascii=False))


def cmd_status():
    data = load_data()
    mems = [m for m in data["memories"] if not m.get("_forgotten")]
    forgotten = [m for m in data["memories"] if m.get("_forgotten")]
    by_zone = {">=90": 0, "75-89": 0, "11-74": 0, "8-10": 0, "<8": 0, "永久": 0}

    for m in mems:
        w = m.get("weight", 50)
        if w == 101:
            by_zone["永久"] += 1
        elif w >= 90:
            by_zone[">=90"] += 1
        elif w >= 75:
            by_zone["75-89"] += 1
        elif w >= 11:
            by_zone["11-74"] += 1
        elif w >= 8:
            by_zone["8-10"] += 1
        else:
            by_zone["<8"] += 1

    print(f"🧠 衰减引擎状态")
    print(f"   活跃记忆: {len(mems)}  |  墓碑: {len(forgotten)}")
    for zone, cnt in by_zone.items():
        print(f"   {zone}: {cnt}")


def cmd_revive(mid: str):
    data = load_data()
    archive_file = ARCHIVE_DIR / f"{mid}.json"
    if not archive_file.exists():
        print(f"❌ 未找到记忆: {mid}")
        return
    mem = json.load(open(archive_file))
    mem["weight"] = 15
    mem["last_active"] = datetime.now().isoformat()
    mem["_forgotten"] = False
    # 找原位置恢复
    for i, m in enumerate(data["memories"]):
        if m.get("id") == mid and m.get("_forgotten"):
            data["memories"][i] = mem
            break
    else:
        data["memories"].append(mem)
    save_data(data)
    archive_file.unlink()
    print(json.dumps({"action": "revive", "id": mid, "weight": 15}, ensure_ascii=False))


def cmd_log(limit=10):
    log = load_log()
    for r in log["runs"][-limit:]:
        print(f"  {r['time'][:19]} | 衰减:{r['decayed']:>2} 复活:{r['revived']:>2} "
              f"墓碑:{r['tombstoned']:>2} 保护:{r['protected']:>2}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: engine.py [run|status|revive|log]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "run":
        cmd_run()
    elif cmd == "status":
        cmd_status()
    elif cmd == "revive":
        if len(sys.argv) < 3:
            print("需要记忆 ID")
            sys.exit(1)
        cmd_revive(sys.argv[2])
    elif cmd == "log":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_log(limit)
    else:
        print(f"未知命令: {cmd}")
