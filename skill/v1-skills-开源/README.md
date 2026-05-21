# V1 Skills 开源套装

> V8.0 AI 心智架构 · 基础组件
> MIT License · © 2026 宇宸

---

## 包含

| Skill | 功能 | 核心能力 |
|-------|------|---------|
| **memory-compressor** | 记忆压缩与权重管理 | store / recall / decay |
| **memory-decay-engine** | 艾宾浩斯衰减自动化 | 衰减 / 窄门复活 / 墓碑化 |
| **notepad** | 外置记事本 | 写 / 搜 / 分类，无衰减 |
| **time-keeper** | 时间感知与归档 | 报时 / 补录 / 会话追踪 |

## 安装

复制到 OpenClaw skills 目录：

```bash
cp -r memory-compressor ~/.openclaw/skills/
cp -r memory-decay-engine ~/.openclaw/skills/
cp -r notepad ~/.openclaw/skills/
cp -r time-keeper ~/.openclaw/skills/
```

或直接运行任意 engine.py（无外部依赖）：

```bash
python3 memory-compressor/engine.py store "一段需要记住的话"
python3 notepad/engine.py write "完整原文保存"
python3 memory-decay-engine/engine.py run
python3 time-keeper/engine.py now
```

## 依赖

Python 3.8+，仅使用标准库。零外部依赖。

## 商业版

V1 为开源体验版。V2.1+ 商业版额外包含：自动备份、语义搜索、概念网络、情感引擎、五层抗删。

联系宇宸获取商业授权。
