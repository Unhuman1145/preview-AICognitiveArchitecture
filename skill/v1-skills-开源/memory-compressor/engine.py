#!/usr/bin/env python3
"""
V1 Memory Compressor — 开源版
─────────────────────────────
V8.0 AI心智架构 · 动态权重 · 艾宾浩斯衰减 · 窄门复活

用法:
  python3 engine.py store "一段需要记住的文字"
  python3 engine.py recall "关键词"
  python3 engine.py decay
  python3 engine.py status

MIT License · © 2026 宇宸
"""

import json, os, sys, time, math, hashlib, re
from pathlib import Path
from datetime import datetime

DATA_FILE = Path.home() / ".v1_memory.json"

# ── 存储 ──────────────────────────────────────────

def load():
    if DATA_FILE.exists():
        return json.load(open(DATA_FILE))
    return {"memories": [], "meta": {"created": datetime.now().isoformat(), "version": "v1.0"}}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ── 权重计算 ──────────────────────────────────────

def calc_weight(text: str) -> int:
    """根据内容分析赋予初始权重"""
    score = 50  # 基线

    # 情感强度：情绪词越多越重要
    emotional = ["爱", "恨", "愤怒", "激动", "哭", "崩溃", "震惊", "超", "重要",
                 "必须", "永远", "一生", "梦想", "恐惧", "绝望", "狂喜", "心疼"]
    e_score = sum(1 for w in emotional if w in text)
    if e_score >= 3:  score += 15
    elif e_score >= 1: score += 8

    # 篇幅：长内容通常包含更多信息
    length = len(text)
    if length >= 100:  score += 10
    elif length >= 50:  score += 5
    elif length >= 30:  score += 2

    # 特定标记：提到"记住"、"重要"、"别忘"加权重
    markers = ["记住", "重要", "别忘", "关键", "核心", "重点", "mark"]
    if any(m in text.lower() for m in markers):
        score += 10

    # "永久"标记 → 直接 101
    if "永久记忆" in text or "#101" in text:
        return 101

    return min(score, 100)

def weight_label(w: int) -> str:
    if w == 101: return "🔒 永久"
    if w >= 76:  return "🔴 高权重"
    if w >= 41:  return "🟡 中权重"
    if w >= 11:  return "🟢 低权重"
    return "⚫ 遗忘区"

# ── 关键词提取 ────────────────────────────────────

def extract_keywords(text: str, n=4) -> list[str]:
    """简单关键词提取（无外部依赖）"""
    # 中文 2-4 字词组
    cn = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
    # 英文单词
    en = re.findall(r'[a-zA-Z]{3,}', text)
    # 去重 + 排序：按频率取最高频的
    from collections import Counter
    freq = Counter(cn + en)
    # 去掉太短的、太通用的
    stop = {"这是", "可以", "这个", "一个", "什么", "不是", "我们", "他们",
            "the", "and", "for", "that", "this", "with", "was", "are", "not"}
    keywords = [w for w, _ in freq.most_common(n*2) if w.lower() not in stop][:n]
    return keywords

# ── 摘要生成 ──────────────────────────────────────

def summarize(text: str, n=50) -> str:
    """简单截取摘要（开源版不依赖 LLM）"""
    # 取前 n 个有效字符
    clean = text.strip()
    if len(clean) <= n:
        return clean
    # 尝试在标点处截断
    cut = clean[:n]
    for sep in ["。", "；", "，", "!", ".", "?", "\n"]:
        idx = cut.rfind(sep)
        if idx > n // 2:
            return cut[:idx+1]
    return cut + "..."

# ── 艾宾浩斯衰减 ──────────────────────────────────

EBBINGHAUS_HALF = 3600  # 1小时半衰期（可调）

def ebbinghaus_decay(initial_weight: int, elapsed_seconds: float) -> float:
    """艾宾浩斯曲线：S(t) = S₀ × e^(-t/τ)"""
    if initial_weight == 101:
        return 101.0
    tau = EBBINGHAUS_HALF
    return initial_weight * math.exp(-elapsed_seconds / tau)

def time_since_creation(created_at: str) -> float:
    """距创建时间的秒数"""
    try:
        created = datetime.fromisoformat(created_at)
        return (datetime.now() - created).total_seconds()
    except:
        return 0

# ── 窄门复活 ────────────────────────────────────

def narrow_gate(memory: dict) -> bool:
    """
    窄门机制：权重在 8-10 区间时，15% 概率复活回 15。

    "差点被遗忘但又被激活"——模拟人类记忆中的
    模糊但又被唤醒的体验。
    """
    w = memory["weight"]
    if 8 <= w <= 10:
        # 使用内容的 hash 作为确定性种子（同一记忆每次行为一致）
        seed = int(hashlib.md5(memory["content"].encode()).hexdigest()[:8], 16)
        if seed % 100 < 15:  # 15% 概率
            return True
    return False

# ── 命令：store ───────────────────────────────────

def cmd_store(text: str):
    data = load()
    w = calc_weight(text)
    now = datetime.now().isoformat()
    mem = {
        "id": hashlib.md5(f"{text}{now}".encode()).hexdigest()[:8],
        "content": text.strip(),
        "weight": w,
        "initial_weight": w,
        "keywords": extract_keywords(text),
        "summary": summarize(text),
        "created_at": now,
        "last_active": now,
        "recall_count": 0,
    }
    data["memories"].append(mem)
    save(data)

    print(json.dumps({
        "action": "store",
        "id": mem["id"],
        "weight": w,
        "label": weight_label(w),
        "keywords": mem["keywords"],
        "summary": mem["summary"],
    }, ensure_ascii=False))
    return mem

# ── 命令：recall ──────────────────────────────────

def cmd_recall(query: str):
    data = load()
    results = []

    for m in data["memories"]:
        score = 0
        # 关键词匹配
        for kw in m["keywords"]:
            if kw.lower() in query.lower() or query.lower() in kw.lower():
                score += 2
        # 内容全文搜索
        if query.lower() in m["content"].lower():
            score += 3
        # 摘要匹配
        if query.lower() in m["summary"].lower():
            score += 1

        if score > 0:
            m["recall_count"] += 1
            m["last_active"] = datetime.now().isoformat()
            # 回忆激活 → +2 权重缓冲
            if m["weight"] < 100:
                m["weight"] = min(m["weight"] + 2, 100)
            results.append({**m, "match_score": score})

    results.sort(key=lambda x: (x["match_score"], x["weight"]), reverse=True)
    save(data)

    if not results:
        print(json.dumps({"action": "recall", "found": 0, "query": query}, ensure_ascii=False))
        return []

    print(json.dumps({
        "action": "recall",
        "found": len(results),
        "query": query,
        "results": [{
            "id": r["id"], "weight": r["weight"], "label": weight_label(r["weight"]),
            "keywords": r["keywords"], "summary": r["summary"],
            "match": r["match_score"],
        } for r in results[:5]]
    }, ensure_ascii=False))
    return results

# ── 命令：decay ───────────────────────────────────

def cmd_decay():
    data = load()
    now = datetime.now().isoformat()
    report = {"action": "decay", "time": now, "decayed": 0, "forgotten": 0, "revived": 0, "permanent": 0}

    for m in data["memories"]:
        if m["weight"] == 101:
            report["permanent"] += 1
            continue

        old_w = m["weight"]

        # 窄门检查：在衰减前检查，用衰减前的权重
        if 8 <= old_w <= 10 and narrow_gate(m):
            m["weight"] = 15
            m["last_active"] = now
            report["revived"] += 1
            continue  # 复活了，本轮不衰减

        # 距离上次活跃的时间
        try:
            elapsed = (datetime.now() - datetime.fromisoformat(m["last_active"])).total_seconds()
        except:
            elapsed = 3600

        # 艾宾浩斯衰减：基于当前权重衰减
        new_w = ebbinghaus_decay(old_w, elapsed)
        # 每次回忆过的记忆衰减更慢（回忆加固）
        if m["recall_count"] > 0:
            new_w = new_w * (1 + m["recall_count"] * 0.05)
        # 自然衰减上限：不能超过当前权重
        new_w = min(new_w, old_w)
        # 每轮最低保证：不会一个衰减周期直接掉出窄门区
        if old_w <= 10:
            new_w = max(new_w, old_w - 1)  # 低权重区缓慢衰减

        m["weight"] = round(new_w, 1)
        m["last_active"] = now  # 更新活跃时间，防止指数叠加

        if abs(old_w - m["weight"]) > 0.1:
            report["decayed"] += 1
        if m["weight"] < 8:
            report["forgotten"] += 1
        if m["weight"] < 5:
            m["_forgotten"] = True

    save(data)
    print(json.dumps(report, ensure_ascii=False))
    return report

# ── 命令：status ──────────────────────────────────

def cmd_status():
    data = load()
    mems = data["memories"]
    active = [m for m in mems if not m.get("_forgotten")]
    forgotten = [m for m in mems if m.get("_forgotten")]
    permanent = [m for m in mems if m["weight"] == 101]
    by_label = {}
    for m in active:
        lbl = weight_label(m["weight"])
        by_label[lbl] = by_label.get(lbl, 0) + 1

    print(f"🧠 V1 Memory Status")
    print(f"   总计: {len(mems)}  |  活跃: {len(active)}  |  遗忘: {len(forgotten)}  |  永久: {len(permanent)}")
    order = {"🔒 永久": 0, "🔴 高权重": 1, "🟡 中权重": 2, "🟢 低权重": 3, "⚫ 遗忘区": 4}
    for lbl, cnt in sorted(by_label.items(), key=lambda x: order.get(x[0], 99)):
        print(f"   {lbl}: {cnt}")

# ── main ──────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 engine.py [store|recall|decay|status] [参数]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "store":
        text = " ".join(sys.argv[2:])
        if not text.strip():
            print("❌ 需要提供内容")
            sys.exit(1)
        cmd_store(text)

    elif cmd == "recall":
        query = " ".join(sys.argv[2:])
        if not query.strip():
            print("❌ 需要提供搜索词")
            sys.exit(1)
        cmd_recall(query)

    elif cmd == "decay":
        cmd_decay()

    elif cmd == "status":
        cmd_status()

    else:
        print(f"❌ 未知命令: {cmd}")
        sys.exit(1)
