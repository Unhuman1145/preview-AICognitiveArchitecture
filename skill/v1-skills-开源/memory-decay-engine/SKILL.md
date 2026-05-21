---
name: memory-decay-engine
description: 记忆衰减自动化引擎。执行 V8.0 架构的"概率遗忘"机制：每小时检测低权重记忆，根据艾宾浩斯曲线计算衰减，对 8-10 区间触发窄门复活，高权重记忆自动续命。当用户要求"自动化衰减"、"每小时记忆衰减"、"自然遗忘自动化"时触发。
---

> © 2026 宇宸 — V8.0 AI心智架构
> License: MIT — 自由使用、修改、分发，署名即可

# Memory Decay Engine

基于艾宾浩斯遗忘曲线的自动化权重衰减系统。

## 衰减公式

### 时间衰减（指数衰减）

```
S(t) = S₀ × e^(-t/τ)
```

| 区间 | 特征 | 衰减速度 |
|------|------|---------|
| 100-90 | 高权重保护期 | 极慢，几乎不掉 |
| 89-75 | 正常衰减区 | 按标准指数衰减 |
| 74-11 | 加速衰减区 | 衰减加快 |
| <11 | 危险区 | 接近线性衰减至0 |

### 遗忘触发函数（w < 10 时）

```
P(delete) = ((10 - w) / 10)²

含义：
- w = 10 → P = 0（刚好安全）
- w = 5  → P = 0.25
- w = 2  → P = 0.64
- w = 0  → P = 1.0（必定遗忘）
```

### 窄门机制（8 < w < 10）

```python
if 8 < w < 10:
    P(窄门触发) = min(P_base + memory_age × P_increment, P_max)
    if 触发:
        w = 10 + 随机(0, 2)  # 回到安全区
    else:
        w = w × 0.95  # 继续衰减
```

**参数：**
- P_base = 0.001（每小时）
- P_increment = 0.0001
- P_max = 0.3
- memory_age = 当前时间 - 记忆获得时间

> 越老的记忆越"命硬"，模拟人类童年记忆难以消失的现象。

## 衰减流程

### 每小时执行（cron: hourly）

```
1. 扫描 nodes/ 目录所有记忆节点
2. 对每个节点：
   a. 计算自上次衰减后的时间差（小时）
   b. 根据时间差计算新权重 S(t)
   c. 判断是否触发窄门（8<w<10）
   d. 判断是否触发遗忘（w<10 且 P(delete) 通过）
3. 更新节点文件（权重变化后）
4. 生成衰减报告（静默，不打扰用户）
```

### 衰减判断逻辑

```python
for node in nodes:
    old_w = node.weight
    
    if old_w >= 90:
        continue  # 高权重保护，跳过
    
    if 8 < old_w < 10:
        # 窄门检查
        if random() < 窄门概率:
            new_w = 10 + random(0, 2)
        else:
            new_w = old_w × 0.95
    elif old_w < 10:
        # 遗忘检查
        P = ((10 - old_w) / 10) ** 2
        if random() < P:
            移动到 archive/  (墓碑化)
        else:
            new_w = old_w × 0.95
    else:
        # 正常衰减
        new_w = old_w × 衰减系数
    
    更新节点权重
```

## 自动化配置

### Cron 设置

```json
{
  "name": "memory-decay-hourly",
  "schedule": { "kind": "cron", "expr": "0 * * * *", "tz": "Asia/Shanghai" },
  "payload": {
    "kind": "agentTurn",
    "message": "执行 memory-decay-engine：检查所有记忆节点，应用每小时衰减公式，更新权重墓碑化已触发的记忆，在 memory/nodes/ 目录下操作，将结果追加到 memory/decay-log.md"
  },
  "sessionTarget": "isolated"
}
```

### 静默原则

- 衰减在后台静默执行，不主动通知用户
- 仅在用户主动询问"最近有记忆被遗忘吗"时报告
- 衰减日志写入 `memory/decay-log.md`，可追溯

## 目录结构

```
memory/
  nodes/          # 记忆节点（活跃）
  archive/        # 遗忘节点（墓碑化，可恢复）
  index/          # 索引（随节点变动同步更新）
  decay-log.md    # 衰减执行日志
```

> V2 版本号：2026-05-18 v2.0  
> 小虾总 · 第二人预备役