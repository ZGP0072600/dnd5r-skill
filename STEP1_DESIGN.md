# Step 1 设计：跑团运行时文件结构

> **状态**：草案 v1，待 review 定稿
> **创建日期**：2026-05-20
> **范围**：本期仅 Step 1（纯文件目录方案）；构想 2（HTML↔Agent 双向通信）不在内
> **上游讨论**：基于对话「构想 1 vs 构想 2」「DM 风格设计」决议

---

## 1. 目标与背景

### 1.1 痛点

SKILL.md 现有 G3 「每场战斗内自管理」完全靠 LLM 对话上下文。实测痛点：

- **状态丢失**：战斗超 5-8 轮 / 跨 session 续接时，LLM 会算错 HP、忘记 buff 来源、丢失死亡豁免记录
- **NPC 态度漂移**：多 NPC 同时在场时，谁知道什么、对玩家什么态度容易前后不一致
- **DM 风格摇摆**：没有持久化设定时，AI 在严格规则与 Rule of Cool 之间漂移
- **跨 session 还原成本高**：当前只有 `session-N.md` + `玩家状态.md` 两个粗粒度文件，续接时需要 LLM 推断很多东西

### 1.2 解决思路

文件持久化承载所有"状态"信息，让 LLM 只负责：叙事 / 裁定 / 怪物决策 / 文件读写本身。

文件作为 single source of truth：
- 跨 agent 工具（Claude Code / Cursor / 用户自研 agent）都能读
- 跨 session 续接零成本（按固定顺序读几个文件即可）
- 跨设备一致（git 同步或手动迁移）

---

## 2. 范围

| 做 | 不做 |
|---|---|
| 战役目录的完整 schema 定义 | UI（构想 2 范畴） |
| DM 风格三层机制（预设 / 引用 / override） | 实时双向通信 |
| 改造 SKILL.md 的 G1/G3/G6/G7 工作流 | 老战役迁移工具（当前无在运行战役） |
| 一个示范战役骨架（基于风骸岛之龙） | 自动化数据校验 |

---

## 3. 总目录结构

### 3.1 项目级新增

```
项目根/
├── campaigns/                              ← 新增，每个战役一个子目录，git 跟踪
│   └── <战役名>/
├── .claude/skills/dnd5r/
│   ├── SKILL.md                            （改造 G1/G3/G6/G7）
│   ├── STEP1_DESIGN.md                     ← 本文件
│   ├── templates/                          （现有，车卡 HTML 模板）
│   └── profiles/                           ← 新增
│       └── dm-styles/
│           ├── README.md                   机制说明
│           ├── 标准.md
│           ├── 严格RAW.md
│           ├── 宽松爽团.md
│           ├── 粉红恋爱向.md
│           ├── 黑暗残酷.md
│           └── 治愈日常.md
```

### 3.2 单战役结构

```
campaigns/<战役名>/
├── README.md                       战役元信息 + DM 风格引用 + 玩家阵容
├── progress.md                     章节进度 / 升级节点 / 未解钩子 / 完成的遭遇
├── world-state.md                  in-game 时间 / 组织态势 / 地点状态变化
├── house-rules.md                  房规（玩家定义，公开档案；涉及规则判定时优先查）
├── players/
│   ├── <角色名>.md                 玩家状态（AI 视角的快照）
│   └── <角色名>.html               车卡 HTML（玩家自管理，AI 不读写）
├── npcs/
│   └── <NPC 名>.md                 公开信息 + 玩家已揭示部分 + 互动历史
├── combat/
│   ├── active.md                   当前战斗（无战斗时不存在）
│   └── history/
│       └── 001_E1-01_溺水的水手.md 战斗归档
├── sessions/
│   └── session-01.md               每桌结束日志
└── dm-only/                        🔒 玩家不应看到的内容（物理隔离）
    ├── dm-notes.md                 伏笔 / 待触发事件 / 难度调整记录 / 玩家观察
    └── npcs-secrets/
        └── <NPC 名>.md             该 NPC 的秘密身份 / 动机 / DC 揭示条件
```

> **关键设计**：`npcs/<NPC 名>.md` 与 `dm-only/npcs-secrets/<NPC 名>.md` 同名分两份。AI 在跑团叙事时**默认只读 `npcs/`**；需要判定是否揭示秘密时才读 `dm-only/npcs-secrets/`。这样防止 LLM 一次性把全部 NPC 数据塞进上下文，间接降低剧透风险，也让"秘密内容物理隔离"在文件系统层面就成立——玩家若直接看战役目录，至少不会一眼瞄到 dm-only/。

---

## 4. 文件 Schema 详述

每个文件给：用途 → frontmatter schema → body 结构 → 示例 → 读写时机。

### 4.1 战役 README.md

**用途**：战役入口，AI 跨 session 续接时第一个读的文件。

**Schema 示例**：

```yaml
---
campaign: 风骸岛之龙-小明组            # 战役唯一标识，等同目录名
module: 风骸岛之龙__单人粉红向         # 引用的模组目录（可能是 H 工作流改写的副本）
created: 2026-05-20
players:
  - { name: 羽痕, char_file: players/羽痕.md, sheet_html: players/羽痕.html }
  - { name: 凯尔, char_file: players/凯尔.md, sheet_html: players/凯尔.html }
dm_style:
  preset: 粉红恋爱向                   # 引用 .claude/skills/dnd5r/profiles/dm-styles/<X>.md
  overrides:                          # 可选，本战役独有的微调
    pc_mercy: high
    loot_generosity: high
    extra_notes: |
      强调茹娜拉与艾德隆的姐弟羁绊
      塔拉克身世线作为主感情副线
session_count: 0                       # 完成的桌数
status: active                         # active / paused / completed
---

# 风骸岛之龙-小明组

> 战役简介（一段话）

## 玩家阵容
- **羽痕**（高等精灵 · 法师 · 唤起师）— 偏 RP，对 NPC 关系敏感
- **凯尔**（人类 · 战士 · 战斗大师）— 偏战术，希望复杂战斗

## 当前进度
第二章 海藻洞穴，2 级；详情见 [progress.md](progress.md)

## 续接指引（AI 看这里）
任何 AI 续接时按 G7 顺序读：
1. 本文件 → 2. profiles/dm-styles/<引用风格>.md → 3. progress.md → 4. world-state.md
5. sessions/ 最近 1-2 个 → 6. players/*.md 全员 → 7. combat/active.md（若存在）
8. dm-only/dm-notes.md → 9. 询问玩家状态变化 → 10. 上回提要开场
```

**读**：每次开桌 / 续接的第 1 步。
**写**：开桌前 G1 创建；之后只在 session_count / status / 玩家阵容变化时改 frontmatter。

### 4.2 progress.md

**用途**：章节推进、升级节点、未解钩子、完成的遭遇——AI 一眼掌握"现在打到哪了"。

**Schema 示例**：

```yaml
---
current_chapter: 第二章
current_location: 海藻洞穴 入口
party_level: 2
next_level_at: 第二章结束
---

## 章节进度
- [x] 第一章 巨龙休息处（Session 1-2）
- [ ] 第二章 海藻洞穴（进行中，Session 3）
- [ ] 第三章 罗盘玫瑰号
- [ ] 第四章 崖顶天文台

## 升级节点
- [x] 1→2 级：第一章结束（Session 2）
- [ ] 2→3 级：第二章结束
- [ ] (3 级到顶 — 模组上限)

## 已完成遭遇
- E1-01 溺水的水手（Session 1，3 僵尸全灭）
- E1-额 温泉之家（Session 2，3 烟雾龙，回收 4 株风孢蘑菇）
- E1-额 狗头人叛徒（Session 2，谈判收买，未战）

## 未解钩子
- 茹娜拉真身（玩家已有疑心，未揭示）
- 红石榴菌（塔拉克订单待交付）
- 火花塞计划（玩家完全不知）

## 待办（玩家视角）
- 找到艾德隆的下落
- 帮塔拉克做治疗药水
```

**读**：每次开桌第 2 步。
**写**：完成遭遇、升级、章节结束、揭示新钩子时——增量改。

### 4.3 world-state.md

**用途**：in-game 时间 + 地理 / 组织级别的态势变化。

**Schema 示例**：

```yaml
---
in_game_date: 风岚月 第 5 日
in_game_time: 黄昏
weather: 海雾，能见度 50 尺
party_location: 海藻洞穴 入口（B1 区域）
---

## 时间线
- 风岚月 第 1 日：玩家在大陆港口上船
- 风岚月 第 3 日：抵达风骸岛，进入第一章
- 风岚月 第 4 日：清理巨龙休息处周边，结识茹娜拉
- 风岚月 第 5 日：深入海藻洞穴

## 组织态势
- **火花塞势力**：仍在崖顶天文台准备仪式（玩家未知）。倒计时 5 in-game 日。
- **茹娜拉的庇护所**：5 名常住 NPC，对玩家友好。
- **狗头人内部分裂**：部分追随火花塞、部分听茹娜拉教导。

## 地点状态
- 巨龙休息处 A 区：已清扫安全
- 海藻洞穴 B1：已探索；B2 未探索
- 罗盘玫瑰号：未访问
- 崖顶天文台：未访问
```

**读**：开桌后 / 玩家询问"现在是什么时候"时。
**写**：in-game 时间推进、地点变化、组织事件触发时。

### 4.4 players/&lt;角色名&gt;.md

**用途**：单个玩家角色的当前状态（AI 视角的快照）。

**Schema 示例**：

```yaml
---
char_name: 羽痕
char_id: yuhen-2026
class: 法师
subclass: 唤起师
level: 2
race: 高等精灵
sheet_html: 羽痕.html
last_synced: 2026-05-20 桌末
---

## 当前数值
- HP: 12/14（临时 HP 0）
- AC: 13
- 法术位: 1 环 2/3, 2 环 1/3
- 灵感: 0
- 死亡豁免: 成功 0 / 失败 0

## 职业资源
- 奥术回复（短休）: 已用

## 持续状态
- 专注：祝福术（自施于自己 + 凯尔，剩 8 分 30 秒）

## 重要装备 / 库存
- 治疗药水 ×1
- 50 gp
- 风孢蘑菇 ×2（DC15 自然识别过，知道用法）

## 角色已知信息（仅本角色视角，**不是** DM 全知）
- 茹娜拉是龙人（亲眼见过她半变形）
- 塔拉克身世有疑（DC15 历史失败，未明）
- **不知道** 火花塞计划
- **不知道** 艾德隆存在
```

**读**：开桌后 G1 第 3 步、战斗开始、玩家询问自己状态时。
**写**：HP 变化、法术位消耗、装备变化、揭示新信息时——尽量在战斗结束 / 桌末批量同步而不是每次小变动都写。

> **HTML 同步策略（关键）**：本文件由 AI 维护，HTML 角色卡由玩家维护。开桌前 G1 第 3 步 AI **主动**问玩家："羽痕当前 HP / 法术位 / 临时增益 是否与上桌末一致？有变化请告诉我。"——以玩家口述为准更新本文件。**HTML 永远不被 AI 读写**（避免双源不一致），构想 2 实现后再自动化。

### 4.5 npcs/&lt;NPC 名&gt;.md（公开版）

**用途**：NPC 公开信息 + 玩家已揭示的部分 + 互动历史。

**Schema 示例**：

```yaml
---
npc_name: 茹娜拉
location: 巨龙休息处 A5
attitude:
  羽痕: friendly       # hostile / unfriendly / indifferent / friendly / helpful
  凯尔: indifferent
last_seen_session: 2
has_secret: true       # 提示 AI："此 NPC 在 dm-only/npcs-secrets/ 有秘密档案"
---

## 公开身份
庇护所老板，温和的中年女性，似乎对周边龙类生物特别了解。

## 玩家已揭示
- (Session 1) 玩家亲眼见过她半变形为龙人状态
- (Session 1) 她承认自己是青铜龙

## 互动历史
- Session 1: 接待玩家，给治疗药水 ×2。塔拉克 DC15 说服失败，未问出更多。
- Session 2: 玩家归来后，她对羽痕私下透露"还有一位龙类同伴在岛上"（未具名）。

## 当前态度细节
- 对羽痕（friendly）：愿意分享情报，但敏感话题需 DC12 说服
- 对凯尔（indifferent）：戒备，敏感话题 DC15
```

**读**：玩家与 NPC 互动时。
**写**：互动后 / 揭示新内容后。

### 4.6 dm-only/npcs-secrets/&lt;NPC 名&gt;.md（秘密版）

**用途**：该 NPC 的秘密身份 / 动机 / DC 揭示条件 / 与剧情的关系。

**Schema 示例**：

```yaml
---
npc_name: 茹娜拉
true_identity: 青铜龙艾德隆的姐姐
faction: 自由方
hooks:
  - 弟弟艾德隆被火花塞囚禁
  - 自己受龙誓约不能直接出手营救
---

## 真实身份
青铜龙，艾德隆（青铜龙雏龙）的姐姐。500 岁。

## 真实动机
找到能营救艾德隆的中立第三方（玩家）。无法直接出手是因为远古龙誓约
（与火花塞所在的提亚马特后裔有相互不干涉条款）。

## 揭示条件
- 玩家通过 DC15 洞察 + 表现真诚 → 透露弟弟存在
- 玩家直接质询是否青铜龙 → DC10 说服可让她承认
- 第三章完成后无条件全盘托出

## 与主线关系
- 是引导玩家进入第四章的关键角色
- 若玩家始终对她敌对 → 模组进入兜底分支（玩家自行发现艾德隆）

## DM 笔记
- 她不会主动施法帮玩家战斗
- 但她可以提供：补给、情报、紧急传送（每战役 1 次救场）
```

**读**：玩家与该 NPC 互动**到关键判定时**——不是默认读。
**写**：揭示秘密给玩家后（同时改公开版的「已揭示」段）。

### 4.7 combat/active.md（核心）

**用途**：当前战斗的实时状态。LLM 每回合 Edit 一次。

**Schema 示例**：

```yaml
---
encounter_id: E1-01
encounter_name: 溺水的水手
scene: 巨龙休息处入口
started: 2026-05-20 15:30 (现实时间)
in_game_round: 3
in_game_turn_index: 2          # 当前先攻表的第几位（0-indexed）
status: ongoing                # ongoing / ended / fled / tpk_pending
party_level: 2
---

## 先攻表

| 顺位 | 出手者 | HP | AC | 状态 |
|---|---|---|---|---|
| 22 | 羽痕 (PC) | 8/12 | 13 | 专注 祝福术 |
| 18 | 僵尸 A | 14/22 | 8 | - |
| 18 | 僵尸 B | 0/22 | 8 | 倒地（已死） |
| 12 | 凯尔 (PC) | 11/14 | 16 | 祝福 (d4) |
| 9  | 僵尸 C | 22/22 | 8 | - |

## 持续效果
- 羽痕施放 祝福术（专注，剩 9/10 分钟）→ 影响：羽痕、凯尔（每次攻击/豁免 +1d4）

## 玩家死亡豁免
- (空)

## 回合日志

### Round 1
- **T22 羽痕**：施放 祝福术（扣 1 环位），目标 羽痕 + 凯尔
- **T18 僵尸 A**：重击 羽痕，命中 18 ≥ 13，6 钝击
- **T18 僵尸 B**：攻击 凯尔，命中 11 < 16，未中
- **T12 凯尔**：长剑攻击 僵尸 B，致命一击 14 伤害（22→8）
- **T9 僵尸 C**：移动接近，未到攻击距离

### Round 2
- **T22 羽痕**：燃烧之手 5 尺锥，僵尸 A + B 各 8 火焰（A 失败全伤 22→14；B 失败 8→0 死亡）
- **T18 僵尸 A**：（HP 14）重击 凯尔，未中
- **T12 凯尔**：长剑 僵尸 A，10 伤害（14→4）
- **T9 僵尸 C**：靠近 羽痕 5 尺，重击未中

### Round 3
- **T22 羽痕**：（已行动）魔法飞弹 僵尸 C，3 道 3+4+2 = 9 伤害（22→13）
- **T18 僵尸 A**：（当前回合）...
```

**读**：每回合开始时第 1 步（拿当前状态）+ 战斗结束时归档。
**写**：每个角色 / 怪物行动后立即 Edit；战斗结束后归档为 history/ 并删除 active.md。

### 4.8 combat/history/NNN_&lt;编号&gt;_&lt;场景&gt;.md

**用途**：已结束战斗的归档，便于回溯。

**Schema**：与 active.md 几乎一致，frontmatter 多两个字段：

```yaml
ended: 2026-05-20 16:15
outcome: 全灭怪物            # 全灭怪物 / 玩家撤退 / TPK / 和谈 / ...
```

`status` 改为 `ended` / `fled` / `tpk`。

**编号规则**：001/002/... 按战斗发生顺序，独立于章节。便于 `ls combat/history/` 一眼看完整战斗序列。

**读**：玩家问"上次怎么打的那场" / DM 想参考过去战斗节奏。
**写**：战斗结束时一次性 Write，原 active.md 删除。

### 4.9 sessions/session-NN.md

**用途**：每桌结束的整体日志。

**Schema 示例**：

```yaml
---
session: 03
date: 2026-05-20
in_game_dates: 风岚月 第 4 日 黄昏 → 第 5 日 黎明
players_present: [羽痕, 凯尔]
encounters: [E1-额-温泉之家, E1-额-狗头人叛徒]
outcome: 章节 1 完成，升 2 级
---

## 事件清单
1. 玩家清理温泉之家烟雾龙
2. 谈判收买狗头人叛徒
3. 茹娜拉私下对羽痕透露"还有一位龙类同伴"
4. 章节 1 结束，玩家升 2 级

## 获得宝藏
- 4 株风孢蘑菇（30 gp/株）
- 50 gp（狗头人贿赂收）

## 未解钩子
- 茹娜拉提到的"另一位龙类"
- 红石榴菌未采集

## 玩家身上未结的钩子
- 塔拉克的治疗药水订单（心顶蘑菇 + 红石榴菌）

## DM 私笔
- 玩家 A（羽痕）：对 NPC 关系敏感，可加重感情线
- 玩家 B（凯尔）：偏战术，下次准备复杂战斗
- 救场配额：本桌未用（剩 2/2）
- 难度调整：无
```

**读**：续接桌时读最近 1-2 个。
**写**：每桌结束时 Write。

### 4.10 dm-only/dm-notes.md

**用途**：DM 私笔——伏笔、待触发事件、难度调整记录、玩家观察。

**Schema 示例**：

```markdown
# DM 私笔

## 当前伏笔（待引爆）
- [ ] 茹娜拉真身全揭示（章节 2 末 / 玩家直接质询）
- [ ] 火花塞仪式倒计时（剩 5 in-game 日）
- [ ] 塔拉克的诅咒护身符（章节 3 关键道具）

## 待触发事件
- 玩家长休 ≥ 3 次 → 火花塞仪式准备完成
- 玩家揭示茹娜拉身份 → 茹娜拉提供艾德隆位置
- 玩家进入海藻洞穴 B2 → 紫蕈伏击

## 救场配额
- 本战役共 3 次：风骸岛兜底救场 / 茹娜拉营救 / 自定义
- 已用：0 次

## 难度调整记录
- (空)

## 玩家观察
- 羽痕（玩家 A）：偏 RP，喜欢社交，对 NPC 关系敏感
- 凯尔（玩家 B）：偏战术，希望复杂战斗

## 风格执行注记
- 本战役风格：粉红恋爱向（preset） + 不真杀 PC（override） + 慷慨宝藏（override）
- 实际执行注意：(空，待跑团后填)
```

**读**：开桌前 G1 + 难度调整 / 玩家揭示秘密时。
**写**：每桌结束 / 关键事件触发时。

### 4.11 house-rules.md（公开房规）

**用途**：战役级规则覆盖。玩家定义。LLM 在涉及具体规则判定前**必须**先查此文件：有 override 按房规，无则按 `base_ruleset` RAW。

**Schema 示例**（分段模板，玩家在每段下填条款；无房规则保留「(空，按 RAW)」占位行）：

```yaml
---
campaign: 风骸岛之龙-小明组
base_ruleset: PHB24                  # 基础规则版本（PHB24 / PHB14 / 自定义）
last_updated: 2026-05-20
---

# 房规

> 本文件由玩家定义。AI 跑团时**涉及具体规则判定前必须先查此文件**：
> 有 override 按房规，无则按 base_ruleset 走 RAW。
> 玩家中途想加房规时，告诉 AI 加哪段哪条，AI 增量 Edit 本文件。

## 战斗
- (空，按 RAW)
<!-- 候选例：致命一击双倍骰 + 基础骰子最大化 / 自然 20 always 命中 / 脱离不触发机会攻击 -->

## 治疗
- (空，按 RAW)
<!-- 候选例：治疗药水作附赠动作 / 生命骰可在战斗中花费 -->

## 休息
- (空，按 RAW)
<!-- 候选例：短休 5 分钟 / 长休每 in-game 日最多一次 -->

## 法术与施法
- (空，按 RAW)
<!-- 候选例：法师每次长休可改备战法术 / 仪式不需事先备战 -->

## 角色资源
- (空，按 RAW)
<!-- 候选例：每 in-game 日给玩家 1 次免费 inspiration / 死豁失败 3 次后给 1 次救场 -->

## 桌面文化
- (空，按 RAW)
<!-- 候选例：死豁结果公开 / 玩家可为他人死豁求骰 -->

## 其他
- (空) 玩家自由追加
```

**LLM 使用映射**（涉及以下情景必须先查对应段落）：
- 战斗判定（致命一击、自然 20/1、机会攻击、附赠动作、攻击范围）→ 「战斗」段
- 治疗类操作（药水、施法治疗、生命骰）→ 「治疗」段
- 短休 / 长休触发 → 「休息」段
- 法术备战 / 施法时间 / 仪式 → 「法术与施法」段
- 死亡豁免 / inspiration / 灵感使用 → 「角色资源」段
- 信息揭示方式 / 投骰公开度 → 「桌面文化」段

**操作建议**：开桌时把本文件全文 Read 进上下文一次（通常 50-150 行），跑团中直接引用，不必每回合 Grep。

**读**：每次开桌 / 续接时（G1 第 3 步、G7 第 3 步）；战斗中如不确定可重读。
**写**：G1 初始化时（玩家定义房规后）；玩家中途追加条款时增量 Edit。

---

## 5. DM 风格机制

### 5.1 三层结构

```
[系统级预设]  .claude/skills/dnd5r/profiles/dm-styles/<风格>.md
      ↓ 战役 README 通过 dm_style.preset 字段引用
[战役级配置] campaigns/<战役名>/README.md frontmatter
      ↓ dm_style.overrides 字段
[战役级覆盖] 该字段直接列出要 override 的 key/value 和 extra_notes
```

**解析顺序**（开桌时 AI 执行）：
1. Read 战役 README，拿到 `dm_style.preset` 名字 + overrides
2. Read 对应预设文件 `profiles/dm-styles/<preset>.md`
3. **合并**：
   - frontmatter 字段：`overrides` 中的 key 覆盖预设里同名字段
   - 自然语言段：以预设 body 为底；`overrides.extra_notes` 追加
4. 缓存到当前对话上下文，本桌跑团时按此风格行事

### 5.2 预设文件 schema

预设文件统一结构：frontmatter（少量关键开关）+ body（自然语言描述）。

```yaml
---
name: <风格名>
pc_mercy: default            # PC HP=0 时 DM 救场程度（none / default / high）
strict_raw: false            # 是否严守规则书（true 不通融 / false Rule of Cool 优先）
loot_generosity: normal      # 宝藏慷慨度（low / normal / high）
secret_pacing: normal        # 秘密揭示节奏（fast / normal / slow_burn）
combat_lethality: normal     # 战斗致命度（low 怪 HP/伤害打折 / normal 原版 / high 加成）
---

# 叙事风格
（基调、用词、氛围倾向）

# 规则裁定倾向
（如何处理玩家 RP 想做但规则书没明确说的事；DC 给得严不严）

# 战斗节奏
（叙事偏战术 vs 偏氛围；是否提醒机会攻击；怪物撤退条件）

# NPC 行为
（NPC 互动占比；敌对 NPC 是否有人性面；友方 NPC 主动支援程度）

# 信息揭示
（秘密憋多久；是否主动给检定机会；玩家脑补错了是否纠正）

# 死亡与失败
（PC 死亡前是否铺垫；TPK 处理；不可逆代价的态度）

# 不做的事
（明确边界）
```

### 5.3 6 个内置预设

| 预设 | 一句话定位 | pc_mercy | strict | loot | pacing | lethal |
|---|---|---|---|---|---|---|
| 标准 | 中性，按 RAW 推进，偶尔 Rule of Cool | default | false | normal | normal | normal |
| 严格 RAW | 规则原教旨，DC 不放水，机会攻击照触发 | none | true | normal | normal | normal |
| 宽松爽团 | 给玩家发糖，强调爽快感，Rule of Cool 优先 | high | false | high | fast | low |
| 粉红恋爱向 | 暧昧细腻 + NPC 情感线 + 不真杀 PC | high | false | normal | slow_burn | low |
| 黑暗残酷 | PC 真会死，决定有不可逆代价，氛围压抑 | none | true | low | normal | high |
| 治愈日常 | 战斗少互动多，强调温情 | high | false | high | normal | low |

> **pc_mercy 字段语义**：
> - `none` — PC HP=0 严格按死豁规则，DM 不主动 fudge 救场（严格 RAW / 黑暗残酷）
> - `default` — 按 RAW 走死豁；模组指定的兜底节点可用，但 DM 不额外救场（标准）
> - `high` — DM 主动 fudge 救场叙事，PC 几乎不会真死（宽松 / 粉红 / 治愈）

> **本期阶段 A 只完整写「标准」和「粉红恋爱向」两个**作示范 + schema 验证。其他 4 个先在 `profiles/dm-styles/README.md` 列名字 + 一句话定位（占位），实际跑团后视需求扩。

### 5.4 战役级 override 用法

```yaml
# campaigns/风骸岛之龙-小明组/README.md
dm_style:
  preset: 粉红恋爱向
  overrides:
    pc_mercy: high                   # 覆盖预设字段（本例预设本来就是 high，仅示范）
    loot_generosity: high            # 比预设更慷慨（本战役专属）
    extra_notes: |
      强调茹娜拉与艾德隆的姐弟羁绊
      塔拉克身世线作为主感情副线
      不引入除模组指定外的强力法宝
```

字段优先级：`overrides > preset > 内置默认`。`extra_notes` 是**追加**（不替换 preset 的 body）。

### 5.5 与 H 工作流（改模组）的关系

| | H 工作流 | DM 风格 |
|---|---|---|
| 改什么 | 模组**素材文件**（蓝调段、NPC 描写、战斗数据） | 跑团时 AI 的**行为参数** |
| 何时改 | 开桌前一次性 | 每桌实时 |
| 持久化位置 | `docs/modules/<原名>__<标签>/` | `profiles/dm-styles/` + `campaigns/<X>/README.md` |
| 例子 | "把茹娜拉描写改成温柔女性 NPC" | "本桌叙事多用暧昧细腻语言、NPC 死亡前必铺垫" |

**两者可叠加**：H 改出"风骸岛粉红向"模组副本，再用"粉红恋爱向"DM 风格跑——基调最一致。
**也可单用其一**：原版模组 + 粉红 DM 风格（素材中性、跑团时调味）。

---

## 6. 工作流改造（伪代码）

### 6.1 G1 开桌前准备（改）

**旧 4 步** → **新 7 步**：

```
1. 确定模组：用户给名字 → Read docs/modules/<模组名>/README.md
2. 确定 DM 风格：
   - 已有战役 → Read 战役 README 拿风格
   - 新战役 → 问用户从 6 个预设里选 / 或自定义；可加 overrides
3. 确定房规（新）：
   - 问玩家"有要加的房规吗？"
   - 给玩家看 7 段模板（战斗 / 治疗 / 休息 / 法术与施法 / 角色资源 / 桌面文化 / 其他）作为提示
   - 玩家无房规 → house-rules.md 各段保留「(空，按 RAW)」
   - 玩家给条款 → 按模板分段记录
4. 确定阵容：问玩家人数、当前角色等级、职业组合
5. 车卡兜底：若玩家没卡 → 走工作流 B
6. 初始化战役目录：
   campaigns/<战役名>/
   ├── README.md           （含 frontmatter + 玩家阵容 + DM 风格引用）
   ├── progress.md         （含模组的章节大纲，未完成状态）
   ├── world-state.md      （含起始 in-game 时间地点）
   ├── house-rules.md      （房规模板 + 玩家给的条款；无房规也建文件，各段「(空，按 RAW)」）
   ├── players/<X>.md      （每人一份）
   ├── npcs/               （空，懒加载）
   ├── combat/             （空，只有 history/ 子目录）
   ├── sessions/           （空）
   └── dm-only/
       ├── dm-notes.md     （含模组主线伏笔 + 待触发事件 + 救场配额）
       └── npcs-secrets/<X>.md  （从模组 NPC 速查文件批量拆出秘密档案）
7. 开场叙事：按 DM 风格读"读给玩家"段开场
```

### 6.2 G3 战斗管理（重写）

**规则查询协议**（每次涉及具体规则判定时遵守）：
1. 先查当前战役的 `house-rules.md` 对应段落
2. 有 override → 按房规
3. 无 → 按 `base_ruleset`（默认 PHB24）RAW

具体触发：致命一击 / 自然 20 / 1 / 机会攻击 / 附赠动作 / 治疗 / 短休长休 / 法术备战 / 死豁 / inspiration / 投骰公开度 等。

**操作建议**：开桌时已整体 Read house-rules.md 进上下文（G1 第 3 步、G7 第 3 步），战斗中直接引用，不必每回合 Grep。

```
战斗开始：
  1. Read combat/active.md 检查异常（不应存在；存在 = 上次桌断在战斗中）
  2. 从 docs/modules/<模组>/06_附录B_生物图鉴.md 拿怪物数据
  3. 投先攻：
     - PC：让玩家自投并报数（AI 不替玩家投）
     - 怪物：AI 投（用 Bash `python -c "import random; print(random.randint(1,20))"` + 加值）
  4. Write combat/active.md 初始化：先攻表、各方 HP、空回合日志
  5. 按 DM 风格描述战斗开场
     （粉红向 → 紧张氛围 + 角色担忧；严格 RAW → 直接报敌人位置和距离）

每回合：
  1. Read combat/active.md 拿当前 turn_index + 当前出手者
  2. 描述当前行动者；若是 PC 等玩家声明；若是怪物按战术 + 风格执行
  3. 投骰判定（攻击 / 豁免 / 检定）：
     - PC：让玩家投并报数（AI 不替玩家投）
     - 怪物 / NPC：AI 投（Bash python）
  4. 计算伤害 → Edit combat/active.md：
     - 更新对应 HP
     - 更新状态字段（束缚 / 中毒 / 擒抱 / ...）
     - 追加回合日志行
     - 推进 in_game_turn_index（到表尾则 round + 1, index 回 0）
  5. 处理触发效果（专注豁免、机会攻击、领域效果）
  6. 若有 PC HP=0 → active.md 死亡豁免段追加该 PC，下次轮到他时投死豁
  7. 若全部敌方 HP=0 或 PC 全 down → 进入「战斗结束」流程

战斗结束：
  1. Read combat/active.md 最终状态
  2. Edit active.md frontmatter status = ended/fled/tpk + 加 ended 时间戳 + outcome
  3. 计算下个编号 NNN（Glob combat/history/*.md 找最大编号 + 1）
  4. 把 active.md 内容 Write 到 combat/history/NNN_<encounter_id>_<场景>.md
  5. 删除 active.md（Bash `rm`）
  6. 按模组「遭遇与战斗.md」分宝藏
  7. Edit players/<X>.md：同步最终 HP、法术位消耗、新装备、新揭示信息
  8. Edit progress.md：追加该遭遇到「已完成遭遇」
  9. 按 DM 风格做战后叙事
     （治愈系 → 玩家互相疗伤场景；黑暗残酷 → 描述血污与代价；粉红向 → NPC 情感反应）
```

### 6.3 G6 桌末记录（扩展）

```
每桌结束：
  1. Write sessions/session-NN.md（按 4.9 schema）
  2. Edit players/<*>.md 全员同步最终状态（HP / 法术位 / 资源 / 装备 / 新揭示）
     - 询问玩家是否需要修正（HTML ↔ .md 同步策略，见 4.4 注）
  3. Edit progress.md：标记章节进度、升级节点、新解钩子
  4. Edit world-state.md：推进 in-game 时间、地点变化
  5. Edit dm-only/dm-notes.md：追加本桌新伏笔触发 / 救场用次 / 难度调整
  6. Edit npcs/<X>.md（本桌互动过的 NPC）：更新态度、互动历史
  7. Edit 战役 README.md：session_count += 1
```

### 6.4 G7 跨 session 恢复（扩展）

新对话续接时按固定顺序：

```
1. Read campaigns/<战役名>/README.md             (战役元信息 + DM 风格引用)
2. Read profiles/dm-styles/<引用风格>.md         (加载 DM 风格)
3. Read campaigns/<战役名>/house-rules.md        (加载房规)
4. Read campaigns/<战役名>/progress.md           (章节进度)
5. Read campaigns/<战役名>/world-state.md        (世界状态)
6. Read sessions/ 最近 1-2 个                    (最近事件)
7. Read players/*.md 全员                        (玩家状态)
8. Read combat/active.md（若存在 = 上次桌断在战斗中） (恢复战斗)
9. Read dm-only/dm-notes.md                      (DM 私笔)
10. 询问玩家"上桌结束时大家身上状态有变化吗？"  (HTML ↔ .md 同步)
11. 按 DM 风格语调写「上回提要」开场
```

---

## 7. 数据流与读写时机表

| 场景 | 读 | 写 |
|---|---|---|
| 战役首开桌 | 模组 README、玩家卡 | 战役 README、house-rules.md、初始 players/、progress、world-state、dm-notes、批量 npcs-secrets、(读)DM 预设 |
| 每次开桌 | 战役 README、DM 预设、house-rules.md、progress、最近 session、players/、dm-notes | (只读) |
| 玩家中途加房规 | house-rules.md | house-rules.md（增量追加条款） |
| 进入战斗 | active.md（检查不存在）、附录 B 怪物 | 新 active.md |
| 每回合 | active.md | active.md（HP / 状态 / 日志 / turn_index） |
| 战斗结束 | active.md | history/NNN_*.md、players/、progress、删 active.md |
| NPC 互动 | npcs/<X>.md | npcs/<X>.md（追加互动历史） |
| 揭示 NPC 秘密 | dm-only/npcs-secrets/<X>.md | dm-only/npcs-secrets/<X>.md + npcs/<X>.md（同步「已揭示」段） |
| in-game 时间推进 | world-state | world-state |
| 玩家升级 | progress、players | players、progress |
| 桌末 | （汇总） | sessions/、players/全员、progress、world-state、dm-notes、npcs/、战役 README |

---

## 8. 实施步骤

按阶段，每阶段单独 review 后再进入下一阶段：

### 阶段 A：骨架文件创建

- 新建 `.claude/skills/dnd5r/profiles/dm-styles/`
- 写 `README.md`（机制说明 + 6 个预设清单）
- 写 `标准.md` 和 `粉红恋爱向.md` 两个完整预设
- 其余 4 个预设只在 README.md 列名字 + 一句话定位（占位）
- 新建 `campaigns/` 空目录（`.gitkeep` 占位）

**交付**：用户可看完整 DM 风格机制 + 2 个示范预设

### 阶段 B：示范战役骨架

- 基于风骸岛之龙建 `campaigns/风骸岛之龙-demo/`
- 完整填充所有文件骨架：
  - README / progress（含 4 章未完成状态）/ world-state（起始）
  - dm-notes（从模组 README + NPC 速查批量提取主线伏笔 + 待触发事件 + 救场配额）
  - dm-only/npcs-secrets/（从模组 NPC 速查批量拆出秘密档案，每个 NPC 一份）
  - npcs/（空，跑团时懒加载）
  - players/（空，跑团时按车卡填）
  - combat/、sessions/（空目录）
- **不实际跑团**，仅作为模板

**交付**：用户可对照看一个真实战役长什么样

### 阶段 C：改造 SKILL.md

- 在 SKILL.md 的 G1/G3/G6/G7 各段落改写为本设计的伪代码
- 其他工作流（A/B/C/D/E/F/H）不动
- 在 SKILL.md 顶部加一段「战役运行时文件系统」简介，链向本设计文档

**交付**：skill 实际具备文件持久化跑团能力

### 阶段 D：实际跑团验证（用户决定何时）

- 用户开一桌风骸岛之龙
- 跑通"开桌 → 1 场战斗 → 桌末"完整流程
- 暴露问题 → 在本设计文档 v2 中记录 + 修正
- 视实际需求补足剩余 4 个 DM 预设

**交付**：第一桌跑团 + 设计文档迭代到 v2

---

## 9. 已知限制 / 未来扩展

| 限制 | 现状方案 | 未来解决方向 |
|---|---|---|
| HTML 卡 ↔ .md 双源不一致 | 桌前 AI 主动问玩家状态，以口述更新 .md | 构想 2：HTML↔Agent 双向通信 |
| 投骰可信度 | PC 让玩家自投并报数；怪物 AI 投（Bash python） | 构想 2：在 HTML 里投，结果自动回流 |
| 多战役管理 | AI 每次问用户跑哪个战役 | 加 `~/.dnd5r-state.json` 记录当前活跃战役 |
| 玩家直接编辑文件破坏一致性 | 信任玩家不乱动 | 构想 2：UI 操作，玩家不直接接触文件 |
| 跨设备同步 | git push/pull 或手动 | 构想 2 / 云同步 |

---

## 10. 审阅 checklist

请逐项确认或反驳：

- [ ] 总目录结构（章节 3）
- [ ] 文件 schema：README / progress / world-state（4.1-4.3）
- [ ] 文件 schema：players（4.4）+ HTML 同步策略
- [ ] 文件 schema：npcs 公开/秘密双份（4.5-4.6）
- [ ] 文件 schema：**combat/active.md**（4.7）—— 核心，建议重点看
- [ ] 文件 schema：sessions / dm-notes（4.9-4.10）
- [ ] DM 风格三层机制（5.1）
- [ ] 预设 schema（5.2）—— frontmatter 字段是否够用 / 太多
- [ ] **6 个预设的命名 + 一句话定位 + 5 个开关的值**（5.3）—— 要加 / 改 / 删 哪个
- [ ] 与 H 工作流的区分（5.5）
- [ ] G1/G3/G6/G7 改造伪代码（章节 6）
- [ ] 实施步骤分阶段（章节 8）

review 完后告诉我哪些 OK / 哪些要改，我按你的反馈出 v2，确认后再进入阶段 A 实施。
