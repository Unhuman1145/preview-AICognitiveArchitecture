#!/usr/bin/env python3
"""
Time Keeper
───────────
AI 内置时钟——时间感知、归档提醒、会话追踪。

用法:
  python3 engine.py now              # 报时
  python3 engine.py since "14:30"    # 距某时间过了多久
  python3 engine.py check            # 检查是否该归档
  python3 engine.py wake             # 模拟醒来/启动补录
  python3 engine.py session start    # 开始会话计时
  python3 engine.py session end      # 结束会话，记录时长

MIT License · © 2026 宇宸
"""

import json, os, sys, time
from pathlib import Path
from datetime import datetime, timedelta

TZ = "Asia/Shanghai"
DATA_DIR = Path.home() / ".v1_timekeeper"
STATE_FILE = DATA_DIR / "state.json"
ARCHIVE_LOG = DATA_DIR / "archive_log.jsonl"


def init():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        json.dump({"last_archive": None, "sessions": [], "current_session_start": None,
                   "total_active_minutes": 0, "wake_count": 0},
                  open(STATE_FILE, "w"), indent=2)


def load_state():
    return json.load(open(STATE_FILE))


def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def cmd_now():
    now = datetime.now()
    print(json.dumps({
        "time": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "hour": now.hour,
        "timestamp": int(now.timestamp()),
    }, ensure_ascii=False))


def cmd_since(time_str: str):
    try:
        h, m = map(int, time_str.split(":"))
        ref = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        delta = datetime.now() - ref
        print(json.dumps({
            "since": time_str,
            "minutes": round(delta.total_seconds() / 60),
            "hours": round(delta.total_seconds() / 3600, 1),
        }, ensure_ascii=False))
    except:
        print(f"❌ 格式错误: {time_str}，应为 HH:MM")


def cmd_check():
    """检查是否该归档了"""
    init()
    s = load_state()
    now = datetime.now()
    last = None
    if s.get("last_archive"):
        last = datetime.fromisoformat(s["last_archive"])
        elapsed = (now - last).total_seconds()
        hours_since = round(elapsed / 3600, 1)
    else:
        hours_since = None

    should_archive = (hours_since is None) or (hours_since >= 1.0)
    is_midnight = now.hour == 0
    is_morning = 6 <= now.hour <= 9

    result = {
        "now": now.isoformat(),
        "hours_since_archive": hours_since,
        "should_archive": should_archive,
        "is_midnight": is_midnight,
        "is_morning": is_morning,
        "current_hour": now.hour,
    }
    print(json.dumps(result, ensure_ascii=False))

    # 自动归档（如果该归档了，写入记录）
    if should_archive:
        s["last_archive"] = now.isoformat()
        save_state(s)
        with open(ARCHIVE_LOG, "a") as f:
            f.write(json.dumps({"time": now.isoformat(), "action": "auto_archive",
                                "reason": "midnight" if is_midnight else "hourly"},
                               ensure_ascii=False) + "\n")


def cmd_wake():
    """醒来补录——检测关机/睡眠期间的时间跳跃"""
    init()
    s = load_state()
    now = datetime.now()
    s["wake_count"] = s.get("wake_count", 0) + 1

    # 检查上次归档时间
    last_archive = s.get("last_archive")
    time_skip_hours = None
    if last_archive:
        last = datetime.fromisoformat(last_archive)
        delta = (now - last).total_seconds() / 3600
        if delta > 0.5:
            time_skip_hours = round(delta, 1)

    result = {
        "action": "wake",
        "time": now.isoformat(),
        "wake_count": s["wake_count"],
        "time_skip_hours": time_skip_hours,
    }

    if time_skip_hours and time_skip_hours > 1:
        result["warning"] = f"⚠️ 离线 {time_skip_hours} 小时，需要补录归档"
        result["needs_catchup"] = True
    else:
        result["needs_catchup"] = False

    s["last_wake"] = now.isoformat()
    save_state(s)
    print(json.dumps(result, ensure_ascii=False))


def cmd_session(action: str):
    init()
    s = load_state()
    now = datetime.now()

    if action == "start":
        s["current_session_start"] = now.isoformat()
        print(json.dumps({"action": "session_start", "time": now.isoformat()}, ensure_ascii=False))
    elif action == "end":
        start = s.get("current_session_start")
        if start:
            started = datetime.fromisoformat(start)
            duration_min = round((now - started).total_seconds() / 60, 1)
            s["sessions"].append({"start": start, "end": now.isoformat(),
                                  "duration_min": duration_min})
            s["total_active_minutes"] = s.get("total_active_minutes", 0) + duration_min
            s["current_session_start"] = None
            # 只保留最近 100 条
            if len(s["sessions"]) > 100:
                s["sessions"] = s["sessions"][-100:]
            print(json.dumps({"action": "session_end", "duration_min": duration_min,
                              "total_hours": round(s["total_active_minutes"] / 60, 1)},
                             ensure_ascii=False))
        else:
            print(json.dumps({"error": "没有活跃会话"}))
    else:
        print(f"未知操作: {action}（应为 start/end）")

    save_state(s)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: engine.py [now|since|check|wake|session]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "now":
        cmd_now()
    elif cmd == "since":
        if len(sys.argv) < 3:
            print("需要时间，如: engine.py since 14:30")
            sys.exit(1)
        cmd_since(sys.argv[2])
    elif cmd == "check":
        cmd_check()
    elif cmd == "wake":
        cmd_wake()
    elif cmd == "session":
        if len(sys.argv) < 3:
            print("需要 start 或 end")
            sys.exit(1)
        cmd_session(sys.argv[2])
    else:
        print(f"未知命令: {cmd}")
