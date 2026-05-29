# 自定义内容库（Homebrew）

玩家 / DM 自创的、不存在于任何官方书的内容——种族、职业、子职业、专长、装备、法宝、怪物、法术、背景。
和 `docs/extracted/`（官方资料库）格式一致：`.md` + frontmatter 结构化字段，AI 可 Grep 索引、Read 全文。

## 两级作用域

| 位置 | 作用域 | 用途 |
|---|---|---|
| `homebrew/<类型>/<名称>.md` | **全局**，跨战役复用 | 你想在任何战役里都能用的自创内容 |
| `campaigns/<战役名>/homebrew/<类型>/<名称>.md` | **战役专属**，仅该战役 | 只属于某个战役世界观的内容（特制法宝、本地 NPC 种族等）|

## 查询优先级（AI 必须遵守）

回答规则 / 车卡 / 查怪物 / 枚举时，按此顺序查找，**先命中先用**：

1. `campaigns/<当前战役名>/homebrew/`（战役专属，最高优先级）
2. `homebrew/`（全局自定义）
3. `docs/extracted/`（官方书，兜底）

同名时战役专属覆盖全局，全局覆盖官方——这让玩家能在特定战役里"重定义"官方内容而不污染其他战役。

## 子目录（按 SCHEMA.md 的 type 分类）

```
homebrew/
├── races/          种族        type: race
├── classes/        职业        type: class
├── subclasses/     子职业      type: subclass
├── feats/          专长 / 特质  type: feat
├── backgrounds/    背景        type: background
├── equipment/      武器/护甲/道具(非魔法)  type: weapon | armor | item
├── magic-items/    法宝/魔法物品  type: magic_item
├── monsters/       怪物        type: monster
└── spells/         法术        type: spell
```

## 通用 frontmatter（每个 homebrew 文件必含）

在 SCHEMA.md 对应类型字段的基础上，额外加 **homebrew 标记块**：

```yaml
type: <见上表>          # 与 SCHEMA.md 一致
name: <中文名>
en: <英文名，可选>
homebrew: true          # 标记为自定义内容
scope: global           # global 或 campaign:<战役名>
created: 2026-05-29
author: <玩家名 / DM>
balance_ref: <对标的官方内容>   # 如 "对标 PHB24 战士子职 / 军用近战武器"
balance_note: <平衡性说明>      # 一句话说明强度定位，见下方平衡原则
```

其余字段严格按 [docs/extracted/SCHEMA.md](../docs/extracted/SCHEMA.md) 对应类型填写——这样 AI 查 homebrew 和查官方书的解析体验完全一致。

## 平衡原则（创建时必须校验）

自创内容**不能破坏机制平衡**——风味可以天马行空，数值必须对标官方同类。创建时 AI 会做一次对标校验：

| 类型 | 对标基准 |
|---|---|
| 子职业 | 同职业官方子职的特性数量 / 强度曲线 |
| 种族 | PHB24 种族的特质数量（通常 3-4 条）/ 速度 / 无属性加值（2024 属性加值归背景）|
| 专长 | 同类官方专长（起源 / 通用 / 史诗）|
| 武器 | 同类别（简易/军用 · 近战/远程）官方武器的伤害骰 / 词条 |
| 法宝 | 同稀有度（普通/非凡/稀有/罕见/传奇/神器）官方法宝 |
| 怪物 | 同 CR 官方怪物的 HP / AC / 伤害输出 |
| 法术 | 同环阶官方法术的伤害 / 效果强度 |

`balance_note` 字段记录这次校验结论（如"伤害对标长剑 1d8，多一条「重击恢复 1 体」属轻微增益，CR 影响可忽略"）。

## 索引（AI 创建内容后追加一行）

<!-- 格式：- [名称](类型/文件.md) — type · scope · 一句话定位 -->

（暂无自定义内容。用 AI 创建后此处自动追加。）
