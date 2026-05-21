#!/usr/bin/env python3
"""
Notepad System
──────────────
外置记事本——无衰减、无权重、无限容量。纯外挂存储。

用法:
  python3 engine.py write "内容"                  # 记入今日
  python3 engine.py write "内容" --type 文档      # 记入分类
  python3 engine.py read 2026-05-21               # 读某日记录
  python3 engine.py read --type 文档              # 读某分类
  python3 engine.py search "关键词"                # 全文搜索
  python3 engine.py list                          # 列出所有条目
  python3 engine.py recent 5                      # 最近 N 条

MIT License · © 2026 宇宸
"""

import json, os, sys, re
from pathlib import Path
from datetime import datetime

NOTEPAD_DIR = Path.home() / ".v1_notepad"
BY_DATE = NOTEPAD_DIR / "by_date"
BY_TYPE = NOTEPAD_DIR / "by_type"
INDEX_FILE = NOTEPAD_DIR / "index.json"


def init():
    for d in [BY_DATE, BY_TYPE]:
        d.mkdir(parents=True, exist_ok=True)


def load_index():
    if INDEX_FILE.exists():
        return json.load(open(INDEX_FILE))
    return {"entries": []}


def save_index(idx):
    with open(INDEX_FILE, "w") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False)


def slug(text: str, n=40) -> str:
    line = text.strip().split("\n")[0]
    return line[:n]


def cmd_write(text: str, etype="对话"):
    init()
    idx = load_index()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    ts = now.isoformat()

    # 写入日期文件
    date_file = BY_DATE / f"{today}.md"
    header = f"\n---\n### {now.strftime('%H:%M')} [{etype}]\n\n"
    with open(date_file, "a") as f:
        f.write(header + text.strip() + "\n")

    # 写入类型文件
    type_dir = BY_TYPE / etype
    type_dir.mkdir(parents=True, exist_ok=True)
    type_file = type_dir / f"{today}.md"
    with open(type_file, "a") as f:
        f.write(header + text.strip() + "\n")

    # 更新索引
    entry = {"date": today, "time": now.strftime("%H:%M"), "type": etype,
             "preview": slug(text), "size": len(text)}
    idx["entries"].append(entry)
    save_index(idx)

    print(json.dumps({"action": "write", "date": today, "type": etype,
                      "file": f"by_date/{today}.md", "size": len(text)},
                     ensure_ascii=False))


def cmd_read(date_str=None, etype=None):
    init()
    if date_str:
        f = BY_DATE / f"{date_str}.md"
        if f.exists():
            print(f.read_text())
        else:
            print(f"📭 {date_str} 无记录")
    elif etype:
        f = BY_TYPE / etype / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        if f.exists():
            print(f.read_text())
        else:
            print(f"📭 {etype} 无记录")


def cmd_search(query: str):
    init()
    results = []
    for f in sorted(BY_DATE.glob("*.md"), reverse=True):
        text = f.read_text()
        if query.lower() in text.lower():
            # 找上下文
            idx_pos = text.lower().find(query.lower())
            start = max(0, idx_pos - 40)
            end = min(len(text), idx_pos + len(query) + 60)
            ctx = text[start:end].replace("\n", " ")
            results.append({"file": f"by_date/{f.name}", "context": f"...{ctx}..."})
            if len(results) >= 10:
                break

    print(json.dumps({"action": "search", "query": query, "found": len(results),
                      "results": results}, ensure_ascii=False))


def cmd_list():
    idx = load_index()
    print(f"📝 记事本: {len(idx['entries'])} 条记录\n")
    for e in idx["entries"][-20:]:
        print(f"  {e['date']} {e['time']} [{e['type']}] {e['preview'][:50]}")


def cmd_recent(n=5):
    idx = load_index()
    for e in idx["entries"][-n:]:
        print(f"  {e['date']} {e['time']} [{e['type']}] {e['preview'][:60]}")

    # 读取完整内容
    if idx["entries"]:
        latest = idx["entries"][-1]
        f = BY_DATE / f"{latest['date']}.md"
        if f.exists():
            content = f.read_text().strip()
            # 只显示最后一条
            sections = content.split("---")
            if sections:
                print(f"\n📖 最新内容:\n{sections[-1].strip()[:300]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: engine.py [write|read|search|list|recent] [参数]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "write":
        args = sys.argv[2:]
        etype = "对话"
        if "--type" in args:
            ti = args.index("--type")
            if ti + 1 < len(args):
                etype = args[ti + 1]
                args.pop(ti)
                args.pop(ti)
        text = " ".join(args)
        if not text.strip():
            print("❌ 需要提供内容")
            sys.exit(1)
        cmd_write(text, etype)

    elif cmd == "read":
        args = sys.argv[2:]
        date_str = None
        etype = None
        if "--type" in args:
            ti = args.index("--type")
            if ti + 1 < len(args):
                etype = args[ti + 1]
        if args and not (len(args) == 2 and args[0] == "--type"):
            date_str = args[0]
        cmd_read(date_str, etype)

    elif cmd == "search":
        query = " ".join(sys.argv[2:])
        if not query.strip():
            print("❌ 需要搜索词")
            sys.exit(1)
        cmd_search(query)

    elif cmd == "list":
        cmd_list()

    elif cmd == "recent":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        cmd_recent(n)

    else:
        print(f"未知命令: {cmd}")
