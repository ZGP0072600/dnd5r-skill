---
campaign: 风骸岛之龙-demo
module: 风骸岛之龙                       # 引用原版模组（非 H 改写副本）
created: 2026-05-20
players: []                              # 阶段 B 占位；G1 时填实际玩家阵容
dm_style:
  preset: 标准                          # 默认引用标准风格；G1 时玩家可改
  overrides: {}
session_count: 0
status: active
---

# 风骸岛之龙-demo

> 这是 **示范战役**，由 Step 1 阶段 B 生成作为模板。
> 实际跑团请走 G1 工作流创建新战役（命名如 `风骸岛之龙-<队伍标识>`）；不要在本目录里跑团，避免污染示范数据。

## 模组概要

- **原名**：风骸岛之龙 / Dragons of Stormwreck Isle（D&D 5e 入门套装 2022）
- **设定**：被遗忘国度 · 剑湾 · 风骸岛（无冬城附近）
- **推荐等级**：1 → 3 级（第二章末升 2 级、第三章末升 3 级）
- **推荐人数**：3–5 名玩家
- **时长**：约 3–5 次 4 小时桌
- **章节数**：4 主章 + 2 附录

详见 [docs/modules/风骸岛之龙/README.md](../../docs/modules/风骸岛之龙/README.md)。

## 玩家阵容

（占位 — G1 时按实际玩家填写）

示例格式：
```yaml
players:
  - { name: 羽痕, char_file: players/羽痕.md, sheet_html: players/羽痕.html }
  - { name: 凯尔, char_file: players/凯尔.md, sheet_html: players/凯尔.html }
```

## 当前 DM 风格

**标准** 风格（中性默认，按 RAW 推进，偶尔 Rule of Cool）。

引用文件：[.claude/skills/dnd5r/profiles/dm-styles/标准.md](../../.claude/skills/dnd5r/profiles/dm-styles/标准.md)

如要切换风格，改本文件 frontmatter 的 `dm_style.preset`，可选项见 [profiles/dm-styles/README.md](../../.claude/skills/dnd5r/profiles/dm-styles/README.md)。

## 房规

见 [house-rules.md](house-rules.md)。本示范目录里全部段为「(空，按 RAW)」。

## 续接指引（AI 看这里）

任何 AI 续接时按 G7 顺序读：
1. 本文件 → 2. profiles/dm-styles/&lt;引用风格&gt;.md → 3. house-rules.md → 4. progress.md
5. world-state.md → 6. sessions/ 最近 1-2 个 → 7. players/*.md 全员
8. combat/active.md（若存在）→ 9. dm-only/dm-notes.md → 10. 询问玩家状态变化 → 11. 上回提要开场
