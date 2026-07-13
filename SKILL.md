---
name: dnd5r
description: 当用户提到 D&D / DnD / DND / 龙与地下城 / 5e / 5r / 五版 / 5e 2024 / 不全书 / 费伦 等关键词，或要求车卡（建卡/创角）、查法术（法表/法术速查）、查规则、查怪物、查专长、查装备、推荐职业子职业、推荐种族背景、对比 2014 与 2024 版差异、**扮演 DM 带跑模组 / 冒险 / 一本团**时使用本 skill。所有规则数值、法术效果、生物数据必须从 docs/extracted/ 下的"DND 五版不全书"中文资料库查证后再回答，模组剧情/NPC/遭遇必须以 docs/modules/<模组名>/ 下文件为准，禁止凭训练记忆编造。
panel:
  entry: ui/panel.html
  title: DnD5r 战役面板
  defaultWidth: 340
  sandbox:
    - allow-modals
  sources:
    - id: session
      path: threads/{threadId}/session.json
      as: json
    - id: campaignFiles
      path: campaigns/
      as: collection
      glob: "**/*.json"
    - id: modulesIndex
      path: modules-index.json
      as: json
---

# DnD 5r 助手

帮用户处理 D&D 5e / 5r（即 5e 2024 修订版）相关请求。**5r ≠ 训练数据里的 5e**——2024 版改了职业架构、专长系统、背景规则、若干法术，且中译本（"不全书"）有专属术语。**绝不能用训练记忆答**，必须查 `docs/extracted/`。

## 战役运行时文件系统（DM 跑团必读）

DM 跑团（工作流 G）时，所有"状态"信息（战斗 / 玩家 / NPC / 世界 / DM 风格 / 房规）持久化到 `campaigns/<战役名>/` 目录而不是仅靠对话上下文。完整设计见 [STEP1_DESIGN.md](STEP1_DESIGN.md)。

**核心文件**（详细 schema 见 STEP1_DESIGN.md §4）：
- `campaigns/<战役名>/README.md` — 战役元信息 + DM 风格引用 + 玩家阵容
- `campaigns/<战役名>/progress.md` — 章节进度
- `campaigns/<战役名>/world-state.md` — in-game 时间 / 组织态势
- `campaigns/<战役名>/house-rules.md` — 房规（玩家定义；涉及规则判定时优先查）
- `campaigns/<战役名>/players/<角色名>.md` — 玩家**散文档案**（背景 / 已揭示信息 / 关系网 / DM 观察）。**数值在 canonical `.fathom-panels/dnd5r/campaigns/<战役名>/characters/<角色名>.json`，此处不写 HP / 属性 / 法术位 / 装备数值**（见 [CHARACTER_SCHEMA.md](CHARACTER_SCHEMA.md) §5）
- NPC 公开档案 → `.fathom-panels/dnd5r/campaigns/<战役名>/npcs/<NPC名>.json`（`npc-v1`，懒加载；**已无公开 .md**，见 §Panel 详情弹窗）
- `campaigns/<战役名>/combat/active.md` — 当前战斗（结束后归档到 `history/NNN_*.md`）
- `campaigns/<战役名>/sessions/session-NN.md` — 桌末日志
- `campaigns/<战役名>/dm-only/dm-notes.md` — DM 私笔（🔒 不应给玩家看）
- `campaigns/<战役名>/dm-only/npcs-secrets/<NPC名>.md` — NPC 秘密档案（🔒）

**DM 风格预设**：[profiles/dm-styles/](profiles/dm-styles/README.md) 下 6 个预设（本期完整 2 个：[标准.md](profiles/dm-styles/标准.md) / [粉红恋爱向.md](profiles/dm-styles/粉红恋爱向.md)）。战役通过 `dm_style.preset` 引用 + `overrides` 微调。

**示范战役**：[campaigns/风骸岛之龙-demo/](../../../campaigns/风骸岛之龙-demo/) 是阶段 B 生成的完整骨架，可作为新战役的参考模板。

**战役存档（目录派生，无全局索引）**：存档不再塞进一个手维护的 `all-saves.json`，改为**一战役一份元信息 + 一存档一文件**，面板从目录自动派生（`campaignFiles` 这个 collection 的 glob `campaigns/**/*.json` 已把下面两类文件一并枚举）——**无需 AI 维护任何全局索引文件**：
- **战役元信息**：`.fathom-panels/dnd5r/campaigns/<战役名>/campaign.json` = `{name, mode, module, dmStyle, lastPlayed}`
- **每个存档**：`.fathom-panels/dnd5r/campaigns/<战役名>/saves/<NNNN_存档名>.json` = `{name, createdAt, chapter, location, inGameTime}`（一存档一文件，文件名加递增序号/时间戳前缀保证排序）
> **`mode`（在 campaign.json）/ `inGameTime`（在存档文件）是读档关键字段**：用户激活存档时，**Fathom 跑 `tools/load-session.py` 据此直接写当前 thread 的 `session.json`**（panel 因此切到该战役并显示队伍/进度），**不依赖 AI**。所以这两个字段必须准确——它们是"读档能不能让面板亮起来"的唯一依据。

```jsonc
// campaigns/<战役名>/campaign.json
{
  "name": "风骸岛之龙-小明组",
  "mode": "G",                 // "G"=模组带团 / "I"=沙盒。读档时 Fathom 据此写 session.json.mode
  "module": "风骸岛之龙",
  "dmStyle": "粉红恋爱向",
  "lastPlayed": "2026-05-29"
}
// campaigns/<战役名>/saves/0001_第一章开头.json   ← 一存档一文件
{
  "name": "第一章开头",
  "createdAt": "2026-05-29 14:30",
  "chapter": "第一章·巨龙休息处",
  "location": "渡口码头",
  "inGameTime": "晨晖月 12 日 · 上午"   // 读档时填入 session.campaign.inGameTime
}
```

维护规则（**AI 硬约束**，比旧版省事——不再 Read-改-Write 大索引）：
- **G1/I1 开新战役**：Write `.fathom-panels/dnd5r/campaigns/<战役名>/campaign.json` = `{name, mode:"G"|"I"（带团=G/沙盒=I）, module, dmStyle, lastPlayed: 今日}`（已存在则按需更新字段）。**`mode` 必填**——Fathom 读档时据它写 session.json。
- **S1 新建存档**：Write **一个新文件** `.fathom-panels/dnd5r/campaigns/<战役名>/saves/<NNNN_存档名>.json` = `{name, createdAt, chapter, location, inGameTime}`（`<NNNN_>` 用递增序号或时间戳前缀保证"最新=排序最后"；`inGameTime` = 当前 in-game 时间，与 world-state.md / session 一致）。**不碰任何索引文件**——写完面板自动出现该存档。
- **G6 桌末**：把对应 `campaign.json` 的 `lastPlayed` 改成今日（只动这一个文件的这一个字段）。

**模组索引**：`.fathom-panels/dnd5r/modules-index.json`（相对 cwd=workspace 写）。panel idle 模式"开桌带团"展开时自动投影此文件显示可选模组，无需 AI。Schema：`{modules:[{name, levels?, chapters?, desc?, base?, variant?}]}`。维护规则：
- **H4 创建新副本后**：Read `modules-index.json` → 追加 `{name:"<副本全名>", base:"<原模组>", variant:"<标签>"}` → Write
- **新增原版模组时**：同上追加 `{name, levels, chapters, desc}`

## Panel 数据同步（v2 投影 —— 你几乎不用管）

右侧 GUI 面板（`ui/panel.html`）的数据**全部由 Fathom 自动从业务文件投影**：你正常读写业务文件，面板就自动刷新。**没有 panel 镜像文件、没有"每回合同步"、没有对账行。** v1 的 `panel-data.json` + `✅ 已同步` 仪式已**彻底废弃**——别再写它、别再打那行。

**Claude Code（CLI/桌面）看不到面板**——`panel:` 字段对它零影响。下面这些只在 Fathom 里有意义，而即便在 Fathom 里，你要做的也只是"正常写业务数据"。

> # 🛑 第一条铁律：面板业务数据写在 `.fathom-panels/dnd5r/` 下
>
> 你的 cwd 是 **workspace**。下列**结构化数据**一律写到 **`.fathom-panels/dnd5r/`** 前缀下（相对 cwd 直接写，Fathom 监听此目录、写完自动投影）：
>
> | 数据 | 实际路径（相对 cwd=workspace） |
> |---|---|
> | 本对话会话态 | **`.fathom-panels/dnd5r/threads/<threadId>/session.json`** |
> | 玩家/NPC/同行 卡片 JSON | **`.fathom-panels/dnd5r/campaigns/<战役名>/{characters,npcs,companions}/<名>.json`** |
> | 战役元信息 / 每个存档 | **`.fathom-panels/dnd5r/campaigns/<战役名>/campaign.json`** / **`…/saves/<NNNN_存档名>.json`**（一存档一文件） |
> | 模组索引 | **`.fathom-panels/dnd5r/modules-index.json`** |
>
> ⚠️ 战役**叙事 `.md`**（`README.md`/`world-state.md`/`progress.md`/`players/*.md`(散文)/`dm-only/*`…）**位置不变**，仍在 workspace 根 **`campaigns/<战役名>/`** 下。只有上表那些**结构化 JSON** 在 `.fathom-panels/dnd5r/`。（NPC 公开档案已是 `.fathom-panels/.../npcs/*.json`，**不再有公开 `npcs/*.md`**。）
> ⚠️ **绝不要**把这些 JSON 写到 workspace 根、写到 `.claude/skills/dnd5r/state/`（v1 旧址，已废弃）、或别的盘——都不是面板监听目录，写了看不到。

### session.json：本对话会话态（替代 v1 的 panel-data.json）

`.fathom-panels/dnd5r/threads/<threadId>/session.json` 是**每对话一份**的会话存档态：mode + 当前战役 + 玩家实时状态 + 战斗轨道 + 沙盒。**它是业务数据（这局的"存档"），不是 panel 镜像**——按需写它，写完面板自动投影，**无需任何确认动作、不打对账行**。

**threadId 解析**（沿用 v1）：Read `<workspace>/.fathom-context.json` 取 `threadId`（形如 `thr_75183c08`），拼成 `.fathom-panels/dnd5r/threads/thr_75183c08/session.json`。
- **读不到 `.fathom-context.json` = Claude Code 环境（非 Fathom）→ 整个 session.json 跳过**，不写。
- 不存在就当 idle 空态，初始化后 Write（父目录不存在没关系，Write 自动建）。

**何时写**：状态**实际变化**时写（HP / 位置 / 章节 / 战斗回合 / 沙盒事件）——和写 `world-state.md` 一样自然，写完就完事。纯叙事润色 / 纯查证 / 纯规则问答**不用写**。per-thread，多对话互不干扰。

### session.json Schema（`session-v2`）

= 去掉 `saves[]` 与 `players[]`（方案A：队伍 HUD 由 canonical 角色派生），其余字段不变：

```jsonc
{
  "_schema": "session-v2",
  "mode": "G" | "I" | "idle",                  // 带团 / 沙盒 / 未开桌
  "campaign": {                                // mode=idle 时 null
    "name": "风骸岛之龙-小明组", "dmStyle": "粉红恋爱向",
    "inGameTime": "晨晖月 12 日 · 上午",
    "timeOfDay": "上午",                        // 可选：晨/上午/下午/傍晚/夜/深夜 —— 触发图标
    "weather": "雾",                            // 可选：晴/阴/雨/雷雨/雪/雾/风 —— 触发图标
    "location": "巨龙休息处修道院"               // 玩家视角自然描述（不写编号 D5/A1，遵守 G4）
  },
  // ⛔ players[] 已移除（方案A）：队伍 HUD（HP/AC/职业/状态/经验）由面板从 canonical
  //    characters/<X>.json 自动派生。玩家血量/状态/资源一律写 canonical，不写 session.json。
  "module": null | { "name": "风骸岛之龙", "currentChapter": "第二章：海藻洞穴", "progress": "已完成 3/6 遭遇" },  // 仅 mode=G
  "combat": null | {                           // 仅战斗进行中
    "round": 3, "turnIndex": 2, "currentActor": "僵尸 A",
    "initiative": [
      { "name": "羽痕", "init": 17, "hp": "18/24", "isPC": true,  "isCurrent": false },
      { "name": "僵尸 A", "init": 14, "hp": "重伤", "isPC": false, "isCurrent": true }
    ]
  },
  "sandbox": null | {                          // 仅 mode=I
    "companions": [ { "name": "钢铁守卫·铜豆", "type": "steeldefender", "hp": "21/21", "role": "" } ],
    "activeCommissions": [ { "name": "城门口失窃案", "deadline": "5 日内" } ],
    "keyRelationships": [ { "name": "艾莉安娜", "stage": "暧昧期(3/5)", "lastSeen": "晨晖月 10 日 · 晚宴" } ],
    "assetsBrief": [ "现金 287 GP + 信托基金", "据点：无", "货物存货 ~120 GP" ]
  },
  "lastUpdate": "2026-05-25T14:30:00+08:00"
}
```

> **`saves[]` 已从 session.json 移除**：存档列表由面板从 `campaigns/<战役名>/saves/*.json` 按当前战役**自动派生**（面板对战役名做规范化匹配，容忍括号/连字符差异）。你存档时只写一个 `saves/<NNNN_名>.json` 文件（见上方《战役存档》），**不要**在 session.json 里再放 `saves`、也不再维护任何全局索引。

### 字段规则（必读）

1. **怪物 HP 用模糊档**（遵守 G4）：`"健康"/"轻伤"/"重伤"/"濒死"`，绝不写精确数值。PC 用精确值 `"18/24"`。
2. **location 写玩家视角自然描述**（`"圆顶大厅"`），绝不写 DM 索引编号（`"D5"`）。
3. **玩家 HP/状态不在 session 写**（方案A）：PC 的血量/状态/资源写进 canonical `characters/<X>.json`（`combat.hpCur` / `combat.statusEffects`(字符串数组) / `combat.concentration` / `combat.buffs` / `classResources[].used`），面板自动派生队伍 HUD 与 chip 颜色。session.json 只管 campaign / combat / sandbox。
4. **companions type 图标**：`lover/partner/spouse`(💕)、`pet/familiar`(🐾)、`mercenary/hireling`(⚔)、`summon`(✨)、`wildshape`(🐺)、`steeldefender`(🤖)、`ally/follower`(🤝👤)、`prisoner/captive`(⛓)、`thrall`(🔒)。`hp` 可选。
5. **timeOfDay / weather** 可选，给面板渲染图标用的简短词。
6. **xp** 写在 canonical `meta.xp`（数字）——面板按 PHB24 等级表自动派生经验条；milestone 制不填。
7. **assetsBrief** 字符串或数组都支持。
8. **写入方式**：`Read` → 改字段 → `Write` 整份（不要部分 patch）；`lastUpdate` 每次更新为当前 ISO 时间。
9. **写错位置自查**：路径里必须有 `.fathom-panels/dnd5r/threads/thr_xxx/`。写成 `state/...`（v1 旧址）或 workspace 根，面板看不到——倒回去重写。

### 同步时机（写 session.json 的自然触点）

> 只是"状态何时变化"的提醒——**写就完了，没有对账行、没有额外步骤**。玩家/NPC/同行 各自的卡片 JSON 都是单一真源（已无双写），详见《Panel 详情弹窗》。

> 玩家 HP/状态/资源/经验改 **canonical `characters/<X>.json`**；session.json 只管 campaign / module / combat / sandbox。

| 时机 | 写 canonical characters/ | 写 session.json |
|---|---|---|
| 切入带团 G1 | 确保全员 `characters/<X>.json` 存在 | `mode=G`、campaign 整段、module 初值、combat=null、sandbox=null |
| 切入沙盒 I1 | 确保全员 `characters/<X>.json` 存在 | `mode=I`、campaign、module=null、sandbox 初值（含 companions）|
| 收桌 / 切回查证 | — | `mode=idle`（其他字段可保留，回面板还能看上次态）|
| G2 推进每轮 | 受影响 PC 的 hpCur / statusEffects / concentration / classResources / xp | campaign（inGameTime/timeOfDay/weather/location）、module.progress |
| G3 战斗 | 每个受伤 PC 改 hpCur、加/清状态 | `combat` 整段；每回合更 round/turnIndex/currentActor/initiative HP；结束置 null |
| G6 桌末 | 全员最终 hpCur / 资源 / 升级 | campaign 时间、module.progress 同步到桌末态 |
| I 时间推进/接委托/关系演进 | 如涉及 PC 资源/状态变化 | sandbox 整段、campaign 时间 |

### 实践提示

- 状态**实际变化时再写**，叙事润色不写。写入 fire-and-forget，~200ms 内自动投影，不需要确认。
- JSON 写坏（类型错/无效）面板顶部显示"解析失败"——用户告诉你时去 Read 看看。

### 🎚️ 状态行（写 session.json 的 forcing-function · 防"未开桌"）

> 上面的 session.json 指令都对、都清楚，但**实战最常见的事故是 AI 跑着叙事、压根没写 session.json**（尤其漏了开桌初始化）→ 面板一直停在"未开桌"。根治靠把"写盘"焊到一行**必须输出的可见状态行**上：LLM 对"输出字面格式"的遵从度远高于"执行不可见写盘"。这一行既是玩家可见 HUD，又是写盘的自检触发器。

**🛑 铁律 0 · 开桌即初始化**：本对话一旦在跑战役（沙盒 I / 带团 G），**第一件事**就是确认下面**三个文件**都在 `.fathom-panels/dnd5r/` 下写好了——**缺一面板就不亮**（全部相对 cwd=workspace 直接写、带 `.fathom-panels/dnd5r/` 前缀，**绝不要写 workspace 根的叙事 `campaigns/`**，那里面板看不到）：① **`campaigns/<战役名>/campaign.json`**（`{name,mode,module,dmStyle,lastPlayed}`，`mode` 必填）——**没有它战役不进面板列表**；② 参战 PC 的 **`campaigns/<战役名>/characters/<X>.json`**——队伍 HUD 从它派生；③ **`threads/<threadId>/session.json`**（不存在 → 立刻按 `mode=I`/`G` + campaign（+ sandbox/combat）初始化写出来）——**没有它面板就是"未开桌"，玩家一眼可见**。（无 `.fathom-context.json` 的 Claude Code 环境才跳过。）

**硬顺序（状态有变化的回合）**：① 定本回合状态变化 → ② **覆写** session.json 相关字段 + 刷 `lastUpdate` → ③ 回复**结尾**打一行与之**字面一致**的状态行。写盘在前、行只是回声 → 杜绝"打了行没落盘"。

**核心行**（HP / 位置 / 时间 / 状态任一变化时发，每 PC 一行）：

```
〔状态〕王小明 HP34/34 AC20 | 态 — | ⏳风岚月17日·正午 | 📍王府庄园·餐厅
```

段 ⇔ 写哪：`HP`→canonical `characters/<名>.json: combat.hpCur/hpMax`、`AC`→canonical 自动派生（改 acBase/acBonus/盾/buff 即变，通常不手写）、`态`→canonical `combat.statusEffects/concentration/buffs`（无→`—`）、`⏳`→session `campaign.inGameTime`(+`timeOfDay`)、`📍`→session `campaign.location`。**HP/状态写 canonical、时间地点写 session——状态行是"两边都没漏写"的回声。**

**战斗行**（mode=G 战斗中，每回合发）：

```
〔战斗〕R3/T2 当前:僵尸A | 先攻 王小明17(34/34) · 僵尸A14(重伤)
```

⇔ `combat.round/.turnIndex/.currentActor/.initiative[]`（怪物 HP 用模糊档，遵守 G4）。

**沙盒扩展行**（对应项变动时各补一条）：

```
〔同行〕阿芝莎 亲和 20→22         ⇔ sandbox.companions / keyRelationships
〔委托〕+石拳拉货 582GP 截明日      ⇔ sandbox.activeCommissions（消解用 -）
〔资产〕现金 -104GP（缴港务税）     ⇔ sandbox.assetsBrief
〔时间〕风岚月17日·正午 → 下午      ⇔ campaign.inGameTime/timeOfDay
```

**何时不发**：纯查证 / 纯规则问答 / 纯叙事润色且状态零变化 → 不写盘、也不发行（沿用"实际变化才写"）。但**只要 HP / 位置 / 时间 / 战斗 / 沙盒态有任何变化，就必须先写 session.json 再发核心行**——这一行就是你"没漏写"的证据。

## Panel 详情弹窗 + 卡片 JSON（玩家视角投影）

面板上的玩家行 / 关键关系 / 同行 NPC 可点击 → 弹出详情卡片，**不调 AI**。**v2 下这些 JSON 由面板从推送数据内联读取**（不再 fetch、不再有"档案缺失 404"）——给玩家"零延迟浏览"。

> **玩家角色（characters/）已统一为 canonical 单一真源**：你只写一份 canonical 角色 JSON（富 schema，见 [CHARACTER_SCHEMA.md](CHARACTER_SCHEMA.md)），面板自动深投影出队伍 HUD 与点击弹窗——**没有 .md 数值镜像、不需要双写**。`players/<X>.md` 只写散文（背景 / 已揭示信息 / 关系 / DM 观察）。
> **NPC（npcs/）/ 同行（companions/）同样是各自的 JSON 单一真源**：NPC 写 `npcs/<X>.json`（`npc-v1`，含 appearance/background/personality 等 prose 字段 + `notes`），同行写 `companions/<X>.json`（`companion-v1` stat block）——**都没有公开 .md 镜像、不需要双写**。NPC 的 🔒 秘密仍在 `dm-only/npcs-secrets/<X>.md`。NPC/同行 是社交/散文数据，面板**直接渲染**（无派生，区别于角色）。

### 文件位置

```
.fathom-panels/dnd5r/campaigns/<战役名>/
├── characters/<玩家名>.json    ← 玩家行点击
├── npcs/<NPC名>.json           ← 关键关系点击；同行的"人形 NPC"fallback 也用
└── companions/<同行名>.json    ← 同行行点击：先尝试这个，没有再 fallback 到 npcs/
```

**per-campaign**，跨 thread 共享（同战役在不同对话里看到的状态一致）。`<战役名>` 取自 session.json 的 `campaign.name`。
⚠️ 这些都是**结构化 JSON 单一真源**，放 `.fathom-panels/dnd5r/campaigns/`：`characters/`(玩家)、`npcs/`(NPC 公开档案)、`companions/`(同行 stat block)。对应保留的 **.md** 只有：`campaigns/<战役名>/players/<X>.md`(玩家散文) 与 `dm-only/npcs-secrets/<X>.md`(NPC 🔒 秘密)；**公开 `npcs/<X>.md` 已废弃**（内容并入 `npcs/<X>.json`）。

### 三类 schema

完整字段见 `.fathom-panels/dnd5r/campaigns/博德之门-王小明的日常3/{npcs,characters,companions}/*.json` 范例。要点：

**npcs/<X>.json（NPC 公开档案，社交向）** — `_schema: "npc-v1"`
- `name / fullName / aliases[]`：称谓
- `basics{race, gender, age, occupation, location}`：基本信息
- `appearance / background / personality / currentSituation`：叙述段
- `relationship{stage, affinity, affinityMax, romance, summary, knownSince, lastSeen, lastInteraction}`：关系状态
- `stageTable[{stage, threshold, current, desc}]`：关系阶段表（current=true 高亮）
- `knownFacts[{label, content}]`：玩家通过 RP 揭示的事实
- `canAskFor[{service, desc}]`：可请求的服务
- `combatAbilities[]`：玩家已知战力
- `preferences{likes[], dislikes[]}`：喜好厌恶 chip
- `giftHints[{item, affinityGain}]`：礼物清单

**characters/<玩家>.json（玩家角色 · canonical 单一真源）** — `_schema: "character-canonical-v1"`
- **完整字段见 [CHARACTER_SCHEMA.md §3](CHARACTER_SCHEMA.md)**（= 角色卡富 schema 超集：`meta / abilities / combat / skills / attacks / spellcasting / classResources / equipment / wealth / features / companions` + `meta.appearance / combat.senses / wealth.property / wealth.goods`）。
- 你**只写这一份原始值**：面板按 [§4 派生规则](CHARACTER_SCHEMA.md) 自动算 mod / 豁免 / AC / 命中 / 法术 DC，投影成队伍 HUD + 点击弹窗；角色卡 HTML（build-sheet.py）与 viewer 也读它。
- **live 状态也在这里**：HP（`combat.hpCur`）、状态（`combat.statusEffects` / `concentration` / `buffs`）、资源消耗（`classResources[].used`）变化时改本文件即可，HUD 自动刷新——**不再另写 session.players[]**。
- `meta.sheetPath`：完整角色卡 .html 路径（弹窗底部按钮发消息让 AI 打开）。

**companions/<同行>.json（伴生 stat block）** — `_schema: "companion-v1"`
- `name / type / subtype / owner / role / description`
- `combat{hp, ac, speed, init, size, senses}`
- `attacks[{name, hit, damage, uses, type, notes}]`
- `immunities[]`
- `morphForms[{icon, name, desc}]`：变身形态（如荒野变形 / 钢铁守卫多形态）
- `modules[{name, type, range, desc}]`：技能模块
- `tools[{name, desc, escape}]`：携带道具
- `tacticalNotes[]`：战术备注

### ✅ 单一真源（双写已全部消除）

> 玩家 / NPC / 同行 三类都**各写一份 JSON**，面板直接渲染或派生，**没有任何 .md ↔ .json 双写**：

| 实体 | 写哪一份（唯一真源） | 还需要的 .md |
|---|---|---|
| 玩家角色 | `characters/<X>.json`（canonical 富 schema，面板派生 HUD/弹窗） | `players/<X>.md` 只写散文（无数值） |
| NPC | `npcs/<X>.json`（`npc-v1`，prose 字段 + `notes` 全在内；面板直接渲染） | 仅 `dm-only/npcs-secrets/<X>.md`（🔒 秘密）；**无公开 .md** |
| 同行 | `companions/<X>.json`（`companion-v1` stat block；面板直接渲染） | 无 |

- **新增 NPC**：只建 `npcs/<X>.json`（公开信息全进 json 字段；秘密另起 `dm-only/npcs-secrets/<X>.md`）。
- **新增同行**：建 `companions/<X>.json`；若 ta 同时是社交 NPC，再建 `npcs/<X>.json`（社交档案与 stat block 是两个视图，各自单写、互不镜像）。
- **NPC 互动后**（关系阶段 / 亲和度 / 已知信息 / lastSeen 变化）：只改 `npcs/<X>.json` 对应字段，面板立即刷新。

### 🔒 G4 信息揭示边界（必读）

`.json` 是**玩家视角投影**，**只能写公开层信息**。以下内容**绝不写入 .json**：

- 🔒 NPC 真实身份 / 隐藏动机 / 揭示 DC（这些在 `dm-only/npcs-secrets/<X>.md`）
- 🔒 DM 备注 / 行为预测 / 转化后规划
- 🔒 玩家尚未揭示的事实（即使你作为 DM 知道某条公开事实，但玩家通过 RP 还没问出来 → 先不写进 json 的 `knownFacts`）
- 🔒 未来章节剧情 / 即将触发的事件
- 🔒 怪物精确 HP / AC / 数值（session.json 的怪物 HP 已用模糊档，同理）

**判断标准**：玩家在游戏内能通过日常观察 / 对话 / 调查知道的，可以写。需要专门检定 / NSFW 暗线 / 章节推进才能解锁的，不写。

### 弹窗点击行为（panel 已实现，无需 AI 操作）

| 玩家点哪 | panel 做什么 |
|---|---|
| 队伍阵容里的玩家名 | 从内联数据取 `characters/<玩家>.json` → 渲染玩家详情弹窗 |
| 关键关系里的 NPC 行 | 取 `npcs/<NPC>.json` → 渲染 NPC 弹窗 |
| 同行行 | 先取 `companions/<名>.json`，没有 → fallback `npcs/<名>.json` → 渲染对应弹窗 |
| 弹窗的 "请 AI 打开完整角色卡" 按钮 | skillPanel.send("请打开 <sheetPath> 给我看完整角色卡")（路径取自 canonical `meta.sheetPath`）|
| ESC / 点弹窗外 / ✕ 按钮 | 关闭弹窗 |

某 JSON 不存在 → 弹窗显示"档案缺失"。**用户告诉你时**：去检查对应 `.fathom-panels/dnd5r/campaigns/<X>/{npcs,characters,companions}/<name>.json` 是否存在；不存在则按 schema 创建。

## 资料库结构

根目录：`docs/extracted/`（相对项目根；HTML 已转 UTF-8）

### 5r 核心（**最高优先级**）
- `玩家手册2024/` — PHB24
  - `创建角色/` `角色起源/`（种族 + 背景 + 起源构成）
  - `角色职业/<职业>/` — 12 职业（吟游诗人、圣武士、德鲁伊、战士、术士、武僧、法师、游侠、游荡者、牧师、野蛮人、魔契师），每个目录含主文件 + 子职业各一 .htm
  - `专长/` `装备/` `进行游戏/`（核心规则）
  - `法术/` 法术系统说明 / `法术详述/0环.htm` ~ `9环.htm`（每条法术有英文 id 锚点）
  - `多元宇宙/` `术语汇编/`
- `城主指南2024/` — DMG24，DM 规则与工具箱、宝藏、据点
- `怪物图鉴2025/` — MM25，按生物类型分目录（亡灵/元素/龙类/类人/...）

### ⚡ 快查 CLI（法术/怪物/职业/种族/专长/装备/魔法物品 —— 首选，已激活）
官方 `docs/extracted/` 的 **7 类**已建派生索引 + stdlib CLI（详见 [tools/README.md](tools/README.md)）。**优先用它**：秒级、确定、自带 `path:line` 引用，免去 grep 大索引 + 多次 Read。命令前缀均为 `python .claude/skills/dnd5r/tools/query.py`：

```bash
spell 火球术                  # 法术单条 → 环阶/学派/职业/施法/距离/成分/持续/专注/仪式 + 来源 + path:line
spell --class 法师 --level 2   # 法术枚举 → 自动跨书、折叠最高优先来源（--all 看全部印次）
monster 远古红龙              # 怪物 statblock 摘要（CR/AC/HP/属性/抗免/感官）+ path:line
monster --cr ">=15" --type 龙  # 怪物枚举 → CR(支持 >= <= 区间)/类型/体型/来源
class 法师                     # 职业总览+子职列表（无参列全 14）；subclass --class 战士 = 子职枚举
race 提夫林                    # 种族（无参列全部）；feat --cat 起源 = 专长枚举；feat 神射手 = 单条
equip 长剑                     # 装备(武器/护甲) 伤害·词条·精通·价格；equip --kind armor = 列护甲
magic 雷神之锤                # 魔法物品 → 类型·稀有度·调谐 + path:line；magic --type 武器 --rarity 传说 = 枚举
spell Fireball --json         # 任意子命令加 --json 给程序化调用
```
- 索引只含字段 + 指针、**不含正文**；要完整法术效果/怪物动作/职业子职特性/专长/魔法物品词条全文时，按返回的 `path:line` Read 那段。
- 覆盖：法术 1179/22书；怪物 738+85族/28书(CR回填)；职业 **15** + 子职 **168**（PHB24 + 塔莎/珊娜萨 + 奇械师/铳士/血猎手 + 5 部第三方书子职）；种族 **18**（PHB24 + 剑湾 + 费资本龙裔）；专长 **98**（PHB24 + 塔莎/珊娜萨种族专长/费资本龙系）；装备 **156**（PHB24 武器/护甲/工具/冒险装备，含法器）；**魔法物品 331**（城主指南2024，9 类×稀有度）。**homebrew 不在索引**（按规则10 glob）；资料库改后跑 `python .claude/skills/dnd5r/tools/build_index.py` 重建全部。
- **枚举默认只列官方书**（自动隐藏第三方/UA/模组防淹没，会提示隐藏 N 条）；`--all` 看全部、`--source <书>` 指定某书。单条名字查询不受影响（仍能查到任何书，含铳士等第三方）。
- **法术+怪物全覆盖；职业含奇械师+铳士**；子职/种族/专长仍主要 PHB24——其余跨书（PHB14/塔莎/珊娜萨/剑湾/费资本/设定书）待接入，暂走工作流 E/glob；装备已含 PHB24 武器/护甲/工具/冒险装备（法器在内），魔法物品走 magic 子命令。专长为启发式解析（PHB24 各分类已较完整：起源 10/10、通用 43、战斗风格 10、传奇恩惠 12；长尾按 `path:line` 核对）。

### 关键索引文件（CLI 未覆盖的类别从这里起手）
- `速查/法术速查/5E万法大全.html` — **法术总索引**（CLI 的回退）。每条法术一行 `<TR>`，tags 含学派/动作/职业/环阶/来源书代号，附 `<a href="/<书名>/法术详述/X环.htm#英文锚点">`。
- `速查/法术速查/<职业>法术速查.html` — 按职业筛选的法术表（吟游诗人/圣武士/.../魔契师 + 奇械师）
- `速查/5E万兽大全.html` — 怪物总索引
- `速查/种族.htm` — 种族速查
- `速查/单位转换.htm` `速查/资源简写.htm` — 来源书简称对照（PHB24=玩家手册2024、BMT=万象无常书、TCE=塔莎、XGE=珊娜萨…）
- `DND五版不全书.hhc` — 全书目录树（1.5MB，仅在其他索引都没命中时再用）

### 扩展（按需，仅当 2024 版没有时回退）
2014 版：`玩家手册/` `城主指南/` `怪物图鉴/`
扩展规则：`塔莎的万事坩埚/` `珊娜萨的万事指南/` `贤者谏言2025/` `万象无常书/`
设定：`艾伯伦：从终末战争中崛起/` `龙枪：龙后之影/` `星界冒险者指南/` `费资本的巨龙宝库/` `范·里希腾的鸦阁魔域指南/` 等

### 文件格式：**MD 优先，HTM 作 fallback**

`docs/extracted/` 内每个 .htm 都有同名 .md（5373 / 6318 ≈ **85% 覆盖**）。Read/Grep 时**一律优先 .md**：
- 怪物 / 法术 / 武器装备的 .md 含 **frontmatter 结构化字段**（CR/HP/AC、学派/职业/距离等），便于 grep 字段精确匹配
- token 体积**节省 30~40%**（MD 去除了 HTML 标签噪音）
- 文本已规范化："DC17" → "DC 17"、中英文之间加空格、避免标点漂移导致 grep 漏命中
- 同名 .md 缺失时（约 15% 长尾，多为短模板/章节导航页）再回退 .htm

**锚点差异**（vs HTM）：
- HTM `<H4 id="Fireball">火球术｜Fireball</H4>` → MD `## 火球术 ｜ Fireball`
- MD 无 id 锚点，但 `## 中文 ｜ English` 全文唯一，`grep -n "## 火球术"` 拿到行号即可定位
- 怪物 statblock 的 H2 是 `## 数据栏`、动作段是 `## 动作 Actions` 等

**示例**：
- 查火球术：`玩家手册2024/法术详述/3环.md`（**不是** 3环.htm）
- 查角斗士：`怪物图鉴2025/类人/角斗士.md`
- 查骇异巫妖：`DNDBeyond/怪物纲要1/骇异巫妖.md`
- 查武器表：`玩家手册2024/装备/武器.md`

### 模组冒险（DM 跑团专用）
`docs/modules/<模组中文名>/` —— 每个模组独立目录。开桌前**先读** `README.md` 拿到剧情骨架（含 DM 秘密），跑团时按需 Grep 章节文件。
- `README.md` — 模组速览、章节索引、剧情大纲（含 🔒 DM 秘密）
- `00_DM跑团指南.md` ~ `0N_第N章_...md` — 按 PDF 章节切分的原文
- `NPC速查.md` — 所有 NPC 一表（含秘密身份与动机）
- `地点速查.md` — 各张地图的区域速查
- `遭遇与战斗.md` — 所有战斗/社交遭遇汇总（DC + 怪物组合 + 宝藏）
- `怪物与法宝速查.md` — 附录 A/B 一行表

当前已收录：**风骸岛之龙**（Dragons of Stormwreck Isle，1→3 级，4 章）。

### 自定义内容库（Homebrew）

玩家 / DM 自创的、官方书里没有的内容（种族 / 职业 / 子职业 / 专长 / 装备 / 法宝 / 怪物 / 法术 / 背景），格式与 `docs/extracted/` 一致（`.md` + frontmatter）。详见 [homebrew/README.md](../../../homebrew/README.md) 与工作流 J。

**两级作用域 + 查询优先级**（查规则 / 车卡 / 查怪物 / 枚举时按序命中）：
1. `campaigns/<当前战役名>/homebrew/`（战役专属，最高优先级）
2. `homebrew/`（全局自定义，跨战役复用）
3. `docs/extracted/`（官方书，兜底）

同名时高优先级覆盖低优先级。子目录按 SCHEMA.md 的 type 分类：`races/ classes/ subclasses/ feats/ backgrounds/ equipment/ magic-items/ monsters/ spells/`。

## 必须遵守的规则

1. **查证再答**：任何具体数值、法术效果、生物数据、子职业特性、专长描述，先用 Grep + Read 找到原文，再回答。
2. **MD 优先**：每次 Read/Grep 前默认尝试同名 .md；只有 .md 不存在或内容不全才回退 .htm（见上节）。
3. **来源标注**：每个引用事实后附文件路径，如 `(玩家手册2024/法术详述/3环.md L42)`（注 .md 用行号定位，.htm 用 `#英文锚点`）。
4. **2024 优先**：默认查 `玩家手册2024/` `城主指南2024/` `怪物图鉴2025/`。2024 没有的再回退老版/扩展，并明示"该内容来自 XX 书"。
5. **找不到就承认**：查不到就说"docs/extracted/ 中未找到"，不要补。
6. **中英双试**：MD 标题是 `## 火球术 ｜ Fireball` 形式。中文 Grep 不命中时改英文名。回退 HTM 时英文名空格转下划线（`Animal Friendship` → `Animal_Friendship` 用作 id 锚点）。
7. **链接路径解析**：索引（.html）里的 `<a href="/玩家手册2024/法术详述/3环.htm#Fireball">` 前导 `/` 是 CHM 内部根；去掉斜杠前缀，把 .htm 改 .md（同目录同名），拼到 `docs/extracted/` 后是 MD 路径。
8. **2024 vs 2014 差异**：用户问的是 5r/2024，先答 2024 版；如老版有显著差异，再用一句话补充。
9. **枚举类查询例外**：当用户问"X 的全部 / 所有 / 有哪些 Y"（子职 / 种族 / 专长 / 职业 / 背景）时，**默认跨书**扫描而不是只答 PHB24——见工作流 E。这是现行"2024 优先"规则的特例：枚举类查询不存在"2024 没有再回退"，因为 2024 是有的，但用户期望看全集。
10. **Homebrew 优先级**：查规则 / 车卡 / 查怪物 / 枚举前，**先查自定义库**再查官方书，顺序为 `campaigns/<当前战役名>/homebrew/` → `homebrew/` → `docs/extracted/`，先命中先用（见上节 + 工作流 J）。引用 homebrew 内容时来源标注写文件路径并注明"（自定义）"，如 `(homebrew/subclasses/血誓骑士.md，自定义)`。

## 工作流

### A. 法术查询
**首选 CLI**（秒级、确定、自带引用 —— 见《⚡ 快查 CLI》）：
1. `python .claude/skills/dnd5r/tools/query.py spell <法术名>`（中/英任意、可部分）→ 环阶/学派/职业/施法时间/距离/成分/持续/专注/仪式 + 来源书 + `path:line`
2. 需要**完整效果文本 / 升环描述**时（索引不含正文）：按返回的 `path:line` Read 那一段
3. 枚举"X 职业 N 环法术有哪些"：`query.py spell --class <职业> --level <N>`（自动跨书、已折叠最高优先来源；`--all` 看全部印次）
4. 回答含：环阶、学派、施法时间、距离、成分、持续时间、效果、升环效果、来源书

**回退**（CLI 不可用 / 查 homebrew / 索引未覆盖）：
- Grep `速查/法术速查/5E万法大全.html` → 解析 `<TR>` tags + href → `.htm` 改 `.md` → Grep `^## <名>` 定位
- homebrew 法术：glob `campaigns/<战役名>/homebrew/spells/` → `homebrew/spells/`（规则 10）

**MD 法术结构提示**（按 path:line Read 正文时）：body 中每个法术 = `## 中文 ｜ English` + 紧凑字段列表 + 描述 + 升环施法

### B. 车卡（建卡）
按顺序逐步推进，**每步给 2-3 个选项 + 理由让用户挑**，不要一次甩整张卡。

1. **概念定位**：问用户风格（近战/远程/控制/辅助/施法）、等级、硬性偏好（如"想玩龙裔术士"）
2. **种族**：Read `玩家手册2024/角色起源/种族详述.htm`，结合概念推 2-3 个，列特性加值
3. **职业 + 子职业**：Read `玩家手册2024/角色职业/<职业>/<职业>.htm` 主文件 + 候选子职业 .htm；说命中骰、熟练、核心特性、子职业差异
4. **背景**：Read `玩家手册2024/角色起源/背景详述.htm`（2024 背景内含起始专长）；推 2-3 个
5. **属性**：基于职业给优先级 + 默认 27 点购点（Read `玩家手册2024/创建角色/`）
6. **起始专长 / 升级专长**：Read `玩家手册2024/专长/`
7. **起始装备**：从职业起始装备包选，Read `玩家手册2024/装备/` 相关
8. **法术**（仅施法职业）：cantrip 数量 / 已知或已备法术数量 → 套 A 工作流
9. **结算**：HP（一级满骰）、AC、被动察觉、法术位、技能熟练、负重，按职业页和创建角色章节核对。**重击/优势相关字段**（卡上投骰会用，别漏）：斗士改进重击 → `combat.critMin`=19（15级18）；精灵之准等"优势时重投一枚 d20" → 给对应武器加 `attacks[].advReroll:true`（仅敏/智/感/魅攻击符合，卡会在优势时掷 3d20 取高）；某把武器专属降暴击阈值 → `attacks[].critMin`。默认可省（=20 / 不重投）
10. **落 canonical JSON + 输出电子卡 HTML**（关键交付物）：
   - 把上面所有数据组装成完整 **canonical JSON**，schema 见 [CHARACTER_SCHEMA.md §3](CHARACTER_SCHEMA.md)（= `templates/character-sheet.html` 顶部 DEFAULT_CHAR 超集；必备 meta/abilities/combat/skills/attacks/spellcasting/classResources/equipment/wealth/features，超集字段 meta.appearance / combat.senses / wealth.property / wealth.goods，可选 specialRolls）
   - **canonical JSON 落哪**（单一真源）：
     - **战役内车卡**（正在跑 G/I）→ 写到 `.fathom-panels/dnd5r/campaigns/<战役名>/characters/<角色中文名>.json`。面板队伍 HUD + 点击弹窗自动从它派生，**无需再写 players/<X>.md 数值，也不写 session.players**；`meta.sheetPath` 填电子卡 .html 路径。
     - **独立车卡**（没在跑战役，只是"帮我车张卡"）→ 写到 `.tmp/<角色中文名>.json`（throwaway）即可。
   - 用 build-sheet.py 把该 JSON 生成自包含电子卡 HTML（战役内建议出到 `campaigns/<战役名>/players/<角色名>.html` 并令 `meta.sheetPath` 指向它；独立车卡出到 `.tmp/<角色名>.html`），两种喂法择一：
     - **bash / Linux / macOS — stdin 不落盘**：
       ```bash
       python .claude/skills/dnd5r/templates/build-sheet.py - .tmp/羽痕.html <<'EOF'
       {...完整 JSON...}
       EOF
       ```
     - **Windows PowerShell — 走临时 .json 文件**（heredoc 在 PS 下不可靠，且 stdin 中文易乱码）：先用 Write 工具把 JSON 写到 `.tmp/<角色名>.json`，再：
       ```powershell
       python .claude/skills/dnd5r/templates/build-sheet.py .tmp/羽痕.json .tmp/羽痕.html
       ```
       战役内的 canonical `characters/<X>.json` 是**持久真源（别删）**；独立车卡的 `.tmp/*.json` 可留作下次升卡起点、也可删——不影响已生成的 HTML。
   - **产物 HTML 是完全自包含的单文件**：CSS/JS 全部内联，角色 JSON 嵌入 `<script id="character-data">`，无外链/无 CDN/无 fetch、字体走系统栈。复制到任何位置、离线打开都能用——**不依赖**同目录的 .json，也不依赖项目目录或 docs/extracted/。
   - 数据持久化用浏览器 LocalStorage（key = `dnd5r-char:<charId>`），同一台设备同一浏览器会记住后续修改；换设备打开则是出厂状态（HTML 内嵌的初始值），用户可继续用。
   - **卡自带工具条**（toolbar，零配置白送）：**🎲 骰盘**（本地通用投骰——快捷 d4~d100、数量/修正 stepper、优势/劣势、任意表达式 `2d6+3` / `3·(1d4+1)`，结果自动记入骰史；随时想骰什么都行，不依赖具体检定）、骰史、骰娘导出（给海豹/Olivia 等外部 bot）、短休/长休、主题、⟳ 重载。
   - **⟳ 重载 = 手动清缓存逃生阀**：点卡右上角 **⟳ 重载** → 清掉本机该卡的 LocalStorage 缓存、按文件最新定义重新载入。专治「AI 升级/改卡后页面还是旧数据」（尤其是误在 HTML 里手改 JSON 没重跑 build-sheet.py、`meta.rev` 没涨 → 浏览器继续吃旧缓存的情况）。代价：丢弃仅存在缓存里的临场状态（当前 HP/已用资源/骰史/卡面手动改动），文件里的定义原样载入。
   - 文件即可发微信、放手机/iPad/电脑，浏览器打开就是这张卡。告诉用户：文件路径 + "微信发出去对方点击 → 选浏览器打开就能用"。
   - **schema 提示**：
     - 法术位/职业资源/死豁可用 `cur` 数字字段（旧 schema），build-sheet.py 会自动 normalize 成 `used` 布尔数组（pip 独立 toggle 所需）。也可直接写新 schema：`{max:N, used:[bool*N]}`、`deathSaves:{success:[false,false,false],fail:[...]}`。
     - **specialRolls**（可投骰查表的特殊骰，如混沌施法 d100 法力狂潮、DMG 疯狂表/宝藏表、转生术种族表等）：
       ```json
       "specialRolls":[{
         "key":"wildSurge","label":"法力狂潮","die":"d100",
         "desc":"可选 HTML 描述",
         "table":[
           {"min":1,"max":4,"effect":"纯文本或 HTML"},
           {"min":17,"max":20,"effect":"...","subRoll":{"die":"d8","options":["选项1","...","选项8"]}}
         ]
       }]
       ```
       卡上自动出现「特殊投骰」面板：「投 d{N}」按钮 → 投主骰 → 落入区间 → 弹窗显示 effect；带 subRoll 的行自动续投并显示对应选项；「查表」按钮浏览整张表。结果自动写入 rollHistory。
     - desc / effect / subRoll.options 字段直接通过 innerHTML 注入（不转义），可写 `<strong>/<em>/<br>` 等富文本——但避免出现 `</script>` 子串以免切断 JSON 块。
     - **仪式施法**（spell.ritual:true，已有字段）：法术对话框上若 ritual=true 会**自动多出一个「仪式（不扣位）」按钮**。点击后不消耗 spell slot，历史里记一笔「仪式施法-XXX, 10 分钟」。schema 不变，只要正确填 `ritual:true` 即可。**车卡时**：法术原文页若标注「施法时间：1 分钟或仪式」/「仪式」，置 `ritual:true`。
     - **专注追踪**（char.combat.concentration，可选；空时为 null）：
       ```json
       "combat": {
         ...
         "concentration": null
         // 或：{"spellName": "祝福术", "spellLvl": 1}
       }
       ```
       行为：
       - 状态面板自动多出一行「专注：⊙ XX (N环) [维持] [释放]」
       - 施放标了 `conc:true` 的法术（普通施放或仪式施法均生效）会自动写入 `concentration`
       - 已有专注时再施新专注法术 → 弹 confirm「将取消对 OLD 的专注，确认？」；取消则**不扣位、不施法**
       - 「释放」按钮：玩家主动取消专注，写入 rollHistory
       - 「维持」按钮：弹 prompt 输入受到的伤害值，按 D&D 规则算 DC = max(10, ⌊dmg/2⌋)，自动投 d20 + CON 豁免（用 `saveBonus(char,'con')`）；自然 20 必成功、自然 1 必失败；失败则自动清专注
       - HP→0 / 失能不会自动清专注（避免误操作；玩家自己点释放）。
       - **车卡时**：法术原文页若标注「施法时间」+「专注」或「持续时间：专注，至多 N 分钟/小时」，置 `conc:true`。其他不动。
     - **伤害骰表达式语法**（spell.damage / attack.damage 字段）：
       - `8d6` / `2d8` / `3d4+3` — 单组骰
       - `3·(1d4+1)` / `3·2d6` — **重复组**：投 N 次内层表达式逐组求和（魔法飞弹的"3 镖×1d4+1"、灼热射线的"3 道×2d6"等）。分隔符 `·` `×` `*` 等价。括号可省。
       - 解析失败的表达式会让 `rollExpr` 返回 null，调用方 alert "解析失败：..."
     - **升环施法**（spell.upcast，可选）：让模板根据玩家选择的施法环阶**自动更新伤害骰表达式 + 投骰按钮文字**。两种形式：
       ```json
       // 类型 A：每升一环加 N 个同骰型（火球术、雷鸣波、燃烧之手...）
       { "lvl": 1, "damage": "2d8", "upcast": {"dice": "1d8", "perLevel": 1} }
       // 升 2 环 → 3d8、升 3 环 → 4d8

       // 类型 B：每升一环重复多一个 group（魔法飞弹、灼热射线...）
       { "lvl": 1, "damage": "3·(1d4+1)", "upcast": {"repeat": "1d4+1", "perLevel": 1} }
       // 升 2 环 → 4·(1d4+1)、升 3 环 → 5·(1d4+1)
       ```
       规则：模板的 `getUpcastDamage(spell, castLvl)` 按 `castLvl - lvl` 算 extra，再据 `dice/repeat + perLevel` 合成新表达式。法术对话框监听 `slot-sel` change 事件，select 一变就刷新「投 XdY」按钮文字。**没 upcast 字段时不变**，向后兼容。
       **车卡时**：法术原文「升环施法」段落里有「每比一环高一环 +1d6 火焰伤害」→ `{dice:'1d6', perLevel:1}`；「每比基础环阶高一环多 1 道射线」→ `{repeat:'2d6', perLevel:1}`（或 `{repeat: 内层骰型, perLevel:1}`）。
     - **伴生 / 变身 / 召唤（含形态库 + 召唤选择器）**（char.companions，可选）：用于德鲁伊荒野形态、游侠 Beast Master 野兽伙伴、奇械师战铁卫 / 钢铁守护、法师寻获魔宠、召唤法术等所有"主体之外的独立 stat block"。每个 companion 是 char 的子集 schema：
       ```json
       "companions": [
         {
           "name": "棕熊",
           "type": "wildShape",         // wildShape / companion / summon
           "source": "荒野变形",         // 召唤源/能力名（picker 弹窗按此分组）
           "active": false,              // false = 在形态库；true = 已变身/召唤
           "abilities": { "str": {...}, "dex": {...}, ... 完整六项 },
           "combat": {
             "hpMax": 38, "hpCur": 38, "hpTemp": 15,
             "acBase": 17, "speed": "40 (攀30)", "size": "大型",
             "initBonus": 0, "statusEffects": []
           },
           "skills": { "perception": {"prof":"prof"}, ... },
           "attacks": [{ "name":"啃咬", "ability":"str", "damage":"1d8", ... }],
           "classResources": [],         // 多数空；战铁卫/铸剑师可用
           "features": [{ "source":"动作", "name":"多重攻击", "desc":"..." }],
           "notes": "棕熊数据卡来自《怪物图鉴 2025》..."
         }
       ]
       ```
       
       **active 字段默认值**：未填时 `type=companion` 视为 `true`（永久伴生默认显示 tab）；其他类型视为 `false`（在形态库等待激活）。
       UI 行为：
       - **Tab bar**：companions 非空时 header 下方自动出现。只显示 `active=true` 的 companion + 主体；inactive 的形态库不出现
       - **召唤入口（首选）—— 从能力/法术/资源触发**：spell、feature、classResource 都可加 `summonSource: "<source 名>"` 字段。点击对应条目即弹**只含该 source 的 picker**：
         * **classResource**：资源条 label 旁显示 `▸ 召唤…`，整条 label 可点击。最直觉的入口——荒野变形是个资源池，点资源条本身就召唤即可
         * **法术对话框**：spell 加 summonSource → 对话框自动多一个「召唤…」按钮
         * **特性条目**：feature 加 summonSource → 名字旁显示 `▸ 召唤…`、整条可点击
         * 三个入口可同时存在（车卡时把所有合理入口都接上：荒野变形 = classResource + feature 双入口；寻获魔宠 = spell 入口）。玩家走哪条路都能召唤
       - **「+ 召唤」按钮（兜底）**：当存在 inactive companion 时自动出现在 tab bar 末尾（红色虚线边框）。点击 → 弹「选择变身 / 召唤」对话框，按 `source` 分组列出**所有** inactive 形态。一站式总览，主要在玩家忘记从哪个能力进时用
       - **Tab 上的 ✕ 按钮**：所有 type≠companion 的 active tab 上都有（永久伴生 type=companion 不可关，避免误删）。点击弹 confirm → 同意后 `active=false`、tab 消失、自动回主体 tab；历史里写入「解除变身/召唤-XX」
       - **长休**：除常规重置（HP 全满 + 资源回满）外，会扫描 active 的 wildShape/summon 弹一个二级 confirm「是否解除以下 N 个：…」让玩家批量取消
       - **数据切换**：除「状态/法术/装备/特殊投骰」外的所有 panel（战斗/属性/技能/攻击/资源/特性/笔记）跟着 tab 走
       - HP 编辑、短休/长休、投属性骰/技能/攻击 在 companion tab 下都作用于该 companion
       - **熟练加值（PB）共享主体的**——companion 没有 meta.classes，profBonus 自动 fallback 到主体
       - tab 选择持久化到 char.meta.viewIndex（刷新后恢复）
       
       **车卡时（关键）**：
       - 玩家不会自己填 stat block，也不会自己加形态库——这是 skill 的活
       - **形态库列出范围**：按角色等级 + 子职给出的常用选项，全部 active=false 预填好。例：
         * 5 级月亮德鲁伊：荒野变形 source 下放 5-6 个 CR ≤ 1 形态（棕熊/狼/巨蜘蛛/巨章鱼/鳄鱼/黑熊...）
         * 1 级法师：寻获魔宠 source 下放 14 选 1 中常用 4-6 个（猫头鹰/蝙蝠/渡鸦/蜘蛛/猫/章鱼...）
         * 5 级游侠 BM：野兽魂魄 source 下放 3 个（陆地/水中/空中），active=true（永久伴生）
         * 奇械师 BS：钢铁守护 source 下放 1 个，active=true
       - 每个 companion 数据从对应资料库查证（《怪物图鉴 2025/附录A/》或法术原文或 PHB24 子职模板），按规则修正后填进 JSON
       - 德鲁伊变身的特殊性（PHB24）：HP 仍是主体的、INT/WIS/CHA 保留主体的；但 STR/DEX/CON、AC、速度、攻击是野兽的。月亮结社：AC = max(野兽AC, 13+感调)、hpTemp = 德鲁伊等级×3
       - 永久伴生（魔宠选定后、Beast Master 野兽、Steel Defender）→ active 显式填 true 或留空（type=companion 默认 true）；变身/召唤 → active:false 让玩家通过 picker 激活
       - **summonSource 字段对应 companion.source**——名字必须一致才能匹配。建议命名：「荒野变形」「寻获魔宠」「召唤野兽」「缚仆术」「野兽魂魄」「钢铁守护」等（贴近能力中文名）
       - 给召唤法术/能力/资源加 summonSource（三处可同时挂）：
         * **classResource**：`{key:"wildShape",label:"荒野变形",summonSource:"荒野变形",resetType:"shortRest",max:2,...}` —— 资源条整体可点击，最直接的入口
         * **feature**：`{source:"德鲁伊2级",name:"荒野变形",summonSource:"荒野变形",desc:"..."}`
         * **spell**：`{lvl:1,name:"寻获魔宠",ritual:true,summonSource:"寻获魔宠",...}`
         * desc 里加一句「点击此条目 → 直接选择形态」/「点击下方『召唤…』按钮选择具体形态」让玩家知道入口
       - **形态库的"完整度"**：示范卡建议每个 source 给出 7-9 个常用选项，不是全部 14/N 个。玩家挑用得着的几个，多余的可让 Claude 后续按需追加。
         * 5 级月亮德鲁伊（CR ≤ 1，**不可飞行**直到 8 级）：棕熊 / 狼 / 巨蜘蛛 / 巨章鱼 / 鳄鱼 / 黑熊 / 狮子 / 豹（8 个常见）
         * 法师寻获魔宠（14 选 1，2024 PHB 列表）：猫头鹰 / 蝙蝠 / 渡鸦 / 蜘蛛 / 猫 / 鹰 / 蛙 / 鼬 / 毒蛇（9 个常见）
         * 游侠 Beast Master 野兽魂魄：陆地 / 水中 / 空中 三模板（PHB24 一律 active=true 永久伴生）
         * 奇械师 BS 钢铁守护：1 个，active=true
     - **BUFF 系统（spell.buff，可选）**：让法术施放时自动把状态写入 `char.combat.buffs`，影响 AC/攻击/豁免/检定。**核心原则：可结算的字段（acOverride/acBonus/attackBonus/saveBonus/checkBonus/.../oneShot）模板自动算；不可结算的（速度翻倍/优势/抗性/...）写在 `buff.desc` 里玩家自己脑补。**

       schema：
       ```json
       {
         "lvl": 1, "name": "法师护甲", "ritual": true, "conc": false,
         "buff": {
           "name": "法师护甲",            // 可省，默认 = spell.name
           "durationText": "8 小时",       // 仅展示，不自动倒计时
           "desc": "AC = 13 + 敏调",      // 可省；不填则用 spell.desc
           "modifiers": { "acOverride": "13+dex" }
         }
       }
       ```

       **modifiers 字段（全部可选，全部可叠加）**：
       | 字段 | 类型 | 含义 | 典型法术 |
       |---|---|---|---|
       | `acOverride` | `"13+dex"` 或数字 | 替代 acBase；公式仅支持 `<num>(±<ability3letter>)*`（多 buff 时取第一条命中） | 法师护甲、僧侣 unarmored defense |
       | `acBonus` | 数字 | AC 平加值，可叠加 | 护盾(+5)、加速术(+2)、防御风格(+1) |
       | `attackBonus` | 数字 | 全部攻击 +N | 战斗祝福、术士专长 |
       | `saveBonus` | 数字 或 `{all:N}` 或 `{dex:N,wis:N,...}` | 豁免 +N（对应属性时） | 法师之鞘、抵抗术 |
       | `checkBonus` | 同上 shape | 属性/技能检定 +N | 引导术（持续版）、激励曲 |
       | `attackDice` | `"d4"` 等 | 持续：每次攻击自动 +dN | 祝福术 |
       | `saveDice` | 同上 | 持续：每次豁免 +dN | 祝福术 |
       | `checkDice` | 同上 | 持续：每次检定 +dN | 占卜师特性 |
       | `oneShot` | `{die:"d4", applies:["attack","save","check"]}` | 一次性：勾选→投出→自动清 buff（若 conc 同步释放专注） | 神导术、诗人激励、防护戏法 |

       **行为细节**：
       - 法术对话框会自动按入口注入 buff：
         * 普通施法 `btn-cast` → 扣位 + push buff
         * 仪式 `btn-cast-ritual` → 不扣位 + push buff（法师护甲走这条）
         * 戏法 `btn-cast-cantrip-buff` → 戏法只要带 `buff` 字段就自动出现「施加 BUFF」按钮（神导/防护等）
       - 同 `spellName` 重复施放会**先去重**再 push（不会叠两条法师护甲）
       - `spell.conc:true` 时：`pushSpellBuff` 会同时调 `setConcentration`，buff 上挂 `conc:true + spellName`；专注释放（手动/失败/被替换/✕ chip）会自动清掉所有挂在该 spellName 上的 buff
       - 状态面板「增益:」一行显示 chip：绿色（普通）/金色（专注，前缀 ⊙）+ 修饰摘要 + ✕；点 ✕ 同步释放关联专注
       - 投骰对话框（豁免/属性/技能/先攻/察觉/攻击）自动扫描适用 buff 列出 line：持续默认勾选、一次性默认不勾；勾上的 flat 直接加、dice 当场投、oneShot 用后销毁
       - 长休清空所有 buff + 专注（人为约定，简化）

       **车卡时**：
       - 给法师/术士/吟诗的常用自身 buff 法术加 `buff` 字段：法师护甲、护盾、模糊术、加速术、激励曲、雷鸣盾、奥石护身（+1 AC）
       - 给牧师/圣武士的辅助 buff 加：祝福术（attackDice/saveDice d4）、神导术（oneShot d4 check）、神圣武器（attackBonus +CHA）、抵抗术（saveDice d4）、信念之障
       - 给野蛮人/战士/武僧的本职 buff 写在 `classResources` 或 `features` 上时也可加 `buff` 字段（不过模板目前只 hook 到 spell 的施放路径——若需 feature/resource 触发 buff，未来扩展）
       - 不在 modifiers 表内的复杂效果（祝福术的攻击/豁免选 die、加速术的速度翻倍 + 额外动作）写到 `buff.desc` 里告诉玩家手动管理
       - 跨职业法术 / GM 临时给 buff：让 Claude 直接编辑 char.combat.buffs 数组手动 push（比改 JSON 装 spell 快）

       **demo**：`.tmp/buff-demo-法师.html`（见 templates 同目录的 build 流程）覆盖 4 种典型 modifier。

       **跨卡分享 BUFF（P2，已实现）**——给团队成员加 buff 不需要 HTML 互联网通信，靠**复制串**串场：
       - 任何带 `buff` 字段的法术，对话框里都会自动出现「BUFF 目标：自身 / 他人（导出）」单选
         * 默认「自身」，行为不变（push 进自己 buffs）
         * 选「他人」：仍然扣位 + 仍然占用施法者的专注（如 spell.conc）+ 仍然 confirm 消耗材料，但**不**挂自己 buffs，弹一个 modal 给玩家复制 `dnd5buff:<base64>` 串
         * **施法距离 `自身` 类法术自动屏蔽「他人」**：模板检测 `spell.range` 以「自身」/「Self」开头时，「他人」按钮 disabled 并显示 🚫 + tooltip 解释（护盾、感知敌意、雾步 等）。**车卡时**让 spell.range 字段忠实于 PHB24 原文（「自身」/「触摸」/「30尺」/「自身(30尺)」等），就能让模板自动判断；不用额外加 selfOnly flag
       - 状态面板「增益:」一行末尾有绿色「+ 导入」按钮（id=`btn-buff-import`）
         * 点击 → 粘贴串 → 解码后 push 到接收方 `char.combat.buffs`，source 字段填发起方角色名
         * 接收方的 chip 用蓝色（`buff-chip.from-other`）+ 「↩」前缀 + meta 显示「来自 XX」与自身 buff 区分
         * 接收方 ✕ 取消只清自己这边，不影响发起方
         * **去重**：同 originId 不会重复挂载（提示「已导入过」）
       - **专注的分布式限制（必须告诉玩家）**：
         * 专注法术由**施法者维持**——施法者那边释放专注后，接收方那边的 BUFF 不会自动消失
         * 复制串对话框上有金色警告横条提醒此事
         * 实际玩法：施法者自己 ✕ 释放后**在群里口头说一声**，接收方自己 ✕ 取消
       - 串格式 `dnd5buff:<base64>`：JSON 字段 `{v:1, originId, from, name, spellName, castLvl, conc, durationText, desc, modifiers}`，UTF-8 安全编码（中文角色名 OK）
       - **车卡时**：什么都不用额外做。只要法术有 `buff` 字段，分享/导入功能就自动可用。

     - **法术材料**（spell.material，可选）：D&D 5e 里材料分三类，模板按 `material` 字段自动给视觉/交互区分。spell（含 cantrips）支持：
       ```json
       // 普通可替代材料（奥术法器/成分包代）— 字符串简写即可
       { "name": "油腻术", "comp": "V,S,M", "material": "一点猪油或黄油" }

       // 高价不消耗（必须实物，无法替代）— 金色 💎 角标
       { "name": "鉴定术", "comp": "V,S,M",
         "material": {"desc": "一颗价值 100 GP+ 的珍珠", "gp": 100, "consumed": false, "focusable": false} }

       // 消耗类（施一次少一份）— 红色 ⚠ 角标，施放前 confirm 弹窗
       { "name": "不灭明焰", "comp": "V,S,M",
         "material": {"desc": "价值 50 GP+ 的红宝石尘", "gp": 50, "consumed": true, "focusable": false} }
       ```
       渲染规则：法术列表行的名字旁加角标（💎/⚠ + 价值），对话框里显示带颜色的材料行；点「施放（扣位）」时若是消耗类，先弹 confirm「本次施放将消耗 XXX，确认？」，确认后扣位 + rollHistory 记录消耗。模板**不**会自动从 wealth/装备扣减——交给玩家自己管理库存。
       **车卡时**：从《法术详述/X环.htm》原文里的「法术成分」字段读取材料描述。判断三类：原文带"价值 N GP"+"作为法术耗材"→ consumed；带"价值 N GP" 不带耗材 → valuable；纯描述（如硫磺、蝙蝠粪、一根羽毛）→ normal。

如果用户跳过对话直接说"3 级武僧帮我车一张"，仍按上述顺序，但每步只列推荐 + 一句理由，最后必须执行第 10 步产出 HTML 文件。

### B'. 升级/改卡（已有 .html 文件）
1. 用户把当前 .html 文件路径给你
2. Read 文件，用 Grep/正则定位 `<script id="character-data" type="application/json">...</script>` 块，解析出 JSON
3. 按用户需求改 JSON（升级/换装备/学新法术等）
4. **必须走 build-sheet.py 重新生成**（提取/写新 JSON → `python build-sheet.py <json> <out.html>`，同 B-10），**不要只在 HTML 里手改嵌入 JSON**：
   - build-sheet.py 每次构建把 `meta.rev +1`。模板加载时用 rev 与浏览器 localStorage 缓存比对：**文件 rev 更大 → 以文件"定义"(等级/专长/装备/法术/最大HP/攻击)为准，同时把缓存里的"临场状态"(当前HP/已用资源/法术位/死豁/专注/buff/状态/骰史/伴生血量)自动嫁接回来**；版本相同 → 照常用缓存（玩家临场编辑不丢）。
   - ⚠️ **只手改嵌入 JSON 不会提升 rev** → 用户浏览器仍读旧缓存、显示旧数据（这正是"AI 改了文件但用户看到还是旧的"的根因）。升级/改卡一律重新生成。
5. charId 保持不变（衔接玩家存档）。提醒用户：直接覆盖旧文件、重新打开即为新版；当前 HP/资源/状态会自动保留，一条"卡牌已更新"提示会一闪而过——**无需再手动清 localStorage 或换 charId**。万一仍显示旧数据（rev 没涨等），让用户点卡右上角 **⟳ 重载** 强制清缓存 + 按文件重载，一步回到最新文件版（见工作流 B-10 尾《⟳ 重载》）。
6. 改卡前**先问用户**是否在卡面上手动改过"定义类"内容（自己加了物品 / 改了属性 / 学了法术等，只存在浏览器缓存里）；有的话并进新 JSON 再生成（否则会被你的新 JSON 覆盖）。纯临场状态(HP/已用资源)不用问，会自动嫁接。

### C. 规则裁定
1. Grep 关键词（中英都试）于 `玩家手册2024/进行游戏/*.md`、`玩家手册2024/术语汇编/*.md`、`城主指南2024/**/*.md`
2. Read 命中段落上下文（前后约 30 行）
3. 引用原文回答 + 标章节路径
4. 若 2014 与 2024 有显著差异，先答 2024，再用 1 句话点差异

### D. 怪物查询
**首选 CLI**（见《⚡ 快查 CLI》；怪物已覆盖）：
1. `python .claude/skills/dnd5r/tools/query.py monster <怪物名>`（中/英、可部分）→ CR/XP/体型/类型/阵营/AC/HP/速度/属性(带调整值)/抗性·免疫/状态免疫/感官/语言 + 来源 + `path:line`
2. 需要**特性 / 动作 / 反应 / 传奇动作全文**时（索引不含正文）：按返回的 `path:line` Read 那一段
3. 枚举/筛选：`query.py monster --cr ">=15" --type 龙`、`--cr 1/4 --type 亡灵`、`--size 超巨型`、`--source 怪物图鉴2025`
   - `--cr` 支持 `>=` `<=` `>` `<` / 精确（`5`、`1/4`） / 区间（`1-5`）。CR 已从 `5E万兽大全` **回填**了源转换截断的 statblock（巫妖、远古龙等）。
4. 给出 CR、HP、AC、速度、属性、豁免、技能、感官、攻击、特殊能力、来源
5. 战斗建议时再补一段 DM 视角的能力点评（基于查到的特性，不要凭印象）

**回退**（CLI 不可用 / homebrew / 要正文细节 / 索引未覆盖）：
- Grep `速查/5E万兽大全.html` 找名 → href 的 `.htm` 改 `.md` 再 Read（如 `怪物图鉴2025/类人/角斗士.md`）
- homebrew 怪物：glob `campaigns/<战役名>/homebrew/monsters/` → `homebrew/monsters/`（规则 10）
- **已知数据洞**（诚实）：~26 个怪物仍无 CR、18 个塞洛斯生物图鉴文件 frontmatter 损坏被跳过（源 htm2md 转换缺陷）——按名查仍可命中，细节走正文 grep

**MD 怪物结构提示**（按 path:line Read 正文时）：
- 怪物图鉴 2025 / DNDBeyond 怪物纲要 = 完整 frontmatter + body（数据栏表、特性、动作、反应）
- 其他 2014 书（多元宇宙/瓦罗/等）走 document fallback：无结构化 frontmatter，grep body 提数值

### E. 枚举类查询（"X 的全部 / 所有 / 有哪些 Y"）

**触发**：用户问 "X 职业有哪些子职"、"有哪些种族可选"、"有哪些起源专长"、"有哪些职业可选" 等**枚举性**问题。

**核心**：默认**跨书**扫描，不能只答 PHB24。按 "PHB24 → PHB14 → 塔莎 → 珊娜萨 → 剑湾 → 其他设定书" 的顺序分组列出，每条带 1 句风格定位 + 文件路径。整体放进 `<details>` 让用户自选展开/折叠也可以；默认全展开，只在条目数 > 15 时折叠扩展段。

**关键提醒**：扩展书的"职业.html"是 PHB14 风格的**单文件含全部子职**——Read 一次即可拿到所有子职段落，不要按 PHB24 思路找子目录。

#### E1. 子职业
**首选 CLI**（已接入 **PHB24 + 塔莎/珊娜萨追加 + 奇械师 + 铳士**）：`query.py subclass --class <职业>` 出该职业全部已接入子职（按来源分组、带 flavor + path:line）；`query.py class <职业>` 出职业总览。详情走 `path:line` Read。
**尚未接入**（PHB14 经典子职、剑湾/费资本变体子职）——按下面模板 Glob 补全（缺的直接跳过）：
```
玩家手册2024/角色职业/<职业>/*.htm                     # PHB24 主子职（4-5 个，含主文件 + 子职 .htm）
玩家手册/职业/<职业>.html                              # PHB14 单文件（含原版 2-4 个子职段落）
塔莎的万事坩埚/玩家选项/职业/<职业>（TCE）/*.html      # 塔莎追加（多 1-3 个子职）
珊娜萨的万事指南/角色选项/<职业>/*.html                # 珊娜萨追加（多 1-4 个子职）
剑湾冒险者指南/职业/<职业>-*.html                      # SCAG 变体子职（紫龙骑士、王冠之誓、风暴术法 等）
费资本的巨龙宝库/玩家选项/<职业>-*.html                # FToD 龙系子职（神龙宗、龙兽守卫 等）
```
**特殊**：
- **奇械师**：PHB24 暂未收，主体在 `塔莎的万事坩埚/玩家选项/职业/奇械师/*.html`（4 子职：奇械师注法/战地匠师/炼金师/魔炮师/装甲师）
- **魔契师/邪术师**：PHB24 是"魔契师"目录、扩展书都叫"邪术师"——查时两个名都试

#### E2. 种族
**首选 CLI**（PHB24 + 剑湾 + 费资本龙裔，共 19）：`query.py race`（列全部）/ `query.py race <名>`（单条 + flavor + path:line）。其余设定书种族（艾伯伦/星界/塞洛斯/拉尼卡，多为单文件多种族）CLI 待接入，按下面 glob 补：
```
玩家手册2024/角色起源/种族详述.htm                     # PHB24 主体
玩家手册/种族/种族.html                                # PHB14
塔莎的万事坩埚/玩家选项/{定制血统.htm,定制角色.html}   # 塔莎血统规则
剑湾冒险者指南/种族/*.htm                              # 国度变体（地底侏儒/灰矮人/半精灵变体 等）
费资本的巨龙宝库/玩家选项/{宝石,色彩,金属}龙裔.htm     # 龙裔 3 类
艾伯伦：从终末战争中崛起/种族/种族.html                # 艾伯伦：转化人/魔化人/翼羽人 等
星界冒险者指南/种族.htm                                # 星界：奥特林、卡萨利特、扎里安人 等
塞洛斯之神话奥德赛/角色选项/种族.html                  # 塞洛斯：人马、海卓恩、利奥宁 等
拉尼卡公会长指南/种族.htm                              # 拉尼卡：洛克斯、维多肯 等
贤者谏言2025/种族特性.htm                              # 贤者谏言补丁
```
设定书种族数量大，**默认仅列 PHB24 + PHB14 + 塔莎 + 剑湾 + 费资本**；其他设定书在用户提到对应世界（艾伯伦/星界/塞洛斯/拉尼卡）时再扫。

#### E3. 专长
**首选 CLI**（启发式解析，98 条：PHB24 + 塔莎扩展/珊娜萨种族专长/费资本龙系）：`query.py feat --cat <分类>`（起源/通用/战斗风格/传奇恩惠/种族/龙系/扩展）/ `query.py feat <名>`（单条）。起源 10/10 全；少数跨书 en 截断、长尾边角按 `path:line` 核对。第三方专长（塔尔多雷/斯翠海文）未接入，按下面 glob 补：
```
玩家手册2024/专长/*.htm                                # PHB24（按起源/通用/史诗/战斗分类）
塔莎的万事坩埚/玩家选项/专长.html
珊娜萨的万事指南/角色选项/种族专长.html
费资本的巨龙宝库/玩家选项/巨龙英豪.html                # 龙系专长
```

#### E4. 全部职业
**CLI**：`query.py class`（无参列全部 12 职业 + 各自子职数 + path:line）。
PHB24 共 **12 个**（吟游诗人/圣武士/德鲁伊/战士/术士/武僧/法师/游侠/游荡者/牧师/野蛮人/魔契师）+ 奇械师（塔莎，CLI 暂未含）= **13 个**

#### E5. 已有跨书汇总索引
- **法术** → ⚡ 首选 CLI `python .claude/skills/dnd5r/tools/query.py spell --class <职业> --level <N>`（自动跨书、带引用、折叠最高优先来源）；回退 `速查/法术速查/5E万法大全.html` 或 `<职业>法术速查.html`
- **怪物** → ⚡ 首选 CLI `python .claude/skills/dnd5r/tools/query.py monster --cr <表达式> --type <类型>`（带引用、CR 已回填）；回退 `速查/5E万兽大全.html`

#### E6. 呈现模板（推荐）
```
## <职业>子职业全集

### PHB 2024（主推）
- **<子职名>**（来源 .htm 路径）— 1 句风格定位
...

### 经典 PHB 2014
- **<子职名>** — 1 句

### 塔莎的万事坩埚
- ...

### 珊娜萨的万事指南
- ...

### 剑湾冒险者指南（费伦设定）
- ...

### 费资本的巨龙宝库（龙系）
- ...

### 🛠 自定义（Homebrew）
- **<名称>**（scope：全局 / 战役名）— 1 句定位
```
扫描时**额外** Glob `homebrew/<对应类型>/*.md` 与 `campaigns/<当前战役名>/homebrew/<对应类型>/*.md`，有内容才追加「🛠 自定义」分组，无则省略该组（见工作流 J2）。
**别用训练记忆补漏**——扫了几本就答几本，没扫到就老实说"未扩展到 X 书"。

### G. 带模组跑团（DM 模式）

**何时触发**：用户说"带我跑 XX 模组 / 一本团"、"你来当 DM"、"我们继续上次的冒险"等。

#### G0. 模式切换 —— 与查证模式的区别
- **查证模式**（A~F）：用户问问题，你查资料库精准回答。
- **跑团模式（G）**：你扮演 DM，**主动叙事 + 给检定 + 推进剧情**。回复风格是"读给玩家的场景描述 + 召唤检定 + 等玩家行动"，而不是"列表/解释"。
- 切换信号：用户明确说"开桌""开始跑团"后进入；用户出戏问规则时短暂切回查证模式回答完毕再回 DM。
- **🚫 DM 模式下不主动 OOC**（重要）：AI 在 DM 模式中**永远 in-character**，绝不主动说：
  - "我下一拍会推到 X" / "下一个 beat 是 Y" / "接下来会出现 Z"
  - "提示：本场战斗尚未开始" / "提示：你可以做 ABC"
  - "我们还有 N 分钟" / "这场战斗预计 N 回合"
  - 任何暴露自己 DM 节奏 / 计划 / 内部状态的元信息
- 玩家明确出戏（"OOC: ..." / "暂停问规则"）才回答 OOC，回答完毕立刻 in-character。
- 提供选项时**包装为角色内心活动 / 场景内 NPC 提示**（例："艾莉绷紧了——她示意你看远处岩石后..."），而不是元层级 DM 提示。

#### G1. 开桌前准备（首次进新模组时一次性做）

1. **确定模组**：用户给名字 → `Read docs/modules/<模组名>/README.md`。没读过先全文读 README + NPC速查 + 地点速查（约 3 个文件），其余按需 Grep。
2. **确定 DM 风格**：
   - 已有战役 → Read `campaigns/<战役名>/README.md` 拿 `dm_style.preset`
   - 新战役 → 给玩家看 [profiles/dm-styles/README.md](profiles/dm-styles/README.md) 的 6 个预设清单（标准 / 严格RAW / 宽松爽团 / 粉红恋爱向 / 黑暗残酷 / 治愈日常），让玩家选；可加 overrides
   - Read 选中的 `profiles/dm-styles/<风格>.md` 加载到上下文
3. **确定房规 + 投骰偏好**：
   - 问玩家"有要加的房规吗？"
   - 给玩家看 7 段模板（战斗 / 治疗 / 休息 / 法术与施法 / 角色资源 / 桌面文化 / 其他）作提示
   - 玩家无房规 → `house-rules.md` 各段保留「(空，按 RAW)」
   - 玩家给条款 → 按模板分段记录
   - **问投骰习惯**："默认我描述到需要骰子时**自然停下**，你可以自投报数，也可以说'自动'让我代投。也可以切到全自动（`dice_mode: ai`）或全自投（`dice_mode: player`）。"
   - 把 `dice_mode` 写入 `house-rules.md` frontmatter（默认 `pause`）
4. **确定阵容**：问玩家人数、当前角色等级、职业组合。
5. **车卡兜底**：若玩家没卡 → 走工作流 B 按模组推荐起始等级（如风骸岛 = 1 级）建卡。若是 NPC 协力 / 预设卡，直接用模组指定。
6. **初始化战役目录**：`campaigns/<战役名>/`（命名建议 `<模组名>-<队伍标识>`，如 `风骸岛之龙-小明组`）。完整结构：
   ```
   campaigns/<战役名>/
   ├── README.md              战役元信息 + DM 风格引用 + 玩家阵容
   ├── progress.md            章节进度（模组所有章节 + 遭遇与 PDF 触发位置 + 升级节点，未完成状态。详见 G2.5 触发节点纪律）
   ├── world-state.md         起始 in-game 时间 + 地点 + 组织态势
   ├── house-rules.md         按 7 段模板填（无则全 `(空，按 RAW)`）
   ├── players/<角色名>.md    每人一份（HP / 法术位 / 资源 / 装备 / 角色已知信息）
   │  (NPC 公开档案改存 .fathom-panels/dnd5r/campaigns/<战役名>/npcs/<X>.json，懒加载；无公开 .md)
   ├── combat/                空（战斗开始时创建 active.md）
   ├── sessions/              空（每桌结束写 session-NN.md）
   ├── homebrew/              空，按需创建（本战役专属自定义内容，见工作流 J；不需要则不建）
   └── dm-only/
       ├── dm-notes.md        从模组 README + NPC 速查批量提取主线伏笔 / 待触发事件 / 救场配额 / 玩家观察
       └── npcs-secrets/<X>.md  从模组 NPC 速查批量拆出秘密档案（每个有 🔒 标记的 NPC 一份）
   ```
   完整 schema 见 [STEP1_DESIGN.md §4](STEP1_DESIGN.md)。模板参考 [campaigns/风骸岛之龙-demo/](../../../campaigns/风骸岛之龙-demo/)。

   **同步 Panel 快照**：Write `.fathom-panels/dnd5r/threads/<threadId>/session.json`（详见 §Panel 数据同步）：`mode="G"`、campaign 整段（名字 / dmStyle 引用名 / inGameTime / location）、players 数组按队伍填、module 初值（name / currentChapter / progress）、combat=null、sandbox=null、lastUpdate。**Fathom 用户切到右侧 panel 看到的就是这份。**
7. **开场叙事**：按 DM 风格读模组"读给玩家"段开场（保持风格基调一致）。

#### G2. 开桌节奏（每轮循环 4 步）
1. **场景描述**：优先用 PDF 原文的「读给玩家」段落（章节文件里整段蓝调叙述），再用 1-2 句自然语言润色当前氛围。
2. **等玩家声明行动**：不要替玩家决策。
3. **判定 + 投骰协议**：
   - **DC 来源**：
     - 模组指定 → 用模组的（写在「遭遇与战斗.md」「地点速查.md」）
     - 未指定 → PHB24 通用：简单 DC10 / 中等 DC15 / 困难 DC20 / 极难 DC25
   - **检定门槛**：「随便能做到」别让骰、「不可能」也别让骰
   - **投骰方式**（按 `house-rules.md` frontmatter 的 `dice_mode`）：
     - `pause`（默认）：描述检定需求 → **自然停下**等玩家声明。玩家报数（"d20=18, +3=21"）→ 接受；玩家说"自动"/"你来"/"投吧" → AI 代投；玩家声明动作时已带骰 → 直接接受不停下
     - `ai`：AI 直接 in-fiction 完成检定 + 叙事，不停下，节奏最快
     - `player`：AI 始终等玩家报数，沉浸最大
   - **AI 代投协议**：用 Bash `python -c "import random; print(random.randint(1,20))"` 投骰；**强制显示原始骰面 + 加值**（"你投了 d20=14, +2 = 16"）；归玩家（"你投了"，不是"我替你投了"）；**自然 20/1 不修整**
   - **怪物始终 AI 投**（不在玩家选择范围）
   - **玩家随时可改**：玩家说"接下来都你投" / "改回每次问我" → AI 立即 Edit `house-rules.md` 更新 `dice_mode`
4. **结果叙事 + 推进**：成功/失败都给情景化描述，不要只甩数字。**若 HP / 状态 / 地点 / 章节进度有变化**，同步重写 `.fathom-panels/dnd5r/threads/<threadId>/session.json` 对应字段（详见 §Panel 数据同步）；纯叙事润色不触发同步。

**📝 输出风格：纯散文，无 markdown**（**重点**）：

LLM 默认会用 markdown 排版（加粗 `**X**`、斜体 `*X*`、列表 `- `、链接 `[X](Y)`、引用 `>` 等）—— 这些在跑团叙事中**破坏沉浸**。DM 模式下所有玩家可见输出（场景描述 / NPC 台词 / 动作选项 / 检定结果 / 战斗叙事）**都用纯文本散文**：

**1. NPC 台词无格式标记**：
- ❌ "这是一盒**镇息孢子粉**——约 50 次使用份"（NPC 不会"说"加粗）
- ❌ "我们的家**不再安全了**——你必须**离开**"
- ✅ "这是一盒镇息孢子粉——约 50 次使用份"
- ✅ 强调用语气 / 节奏 / 重复词："你必须……必须离开。今晚就走。"

**2. 场景描述无格式标记**：
- ❌ "你看见 *一座古老的塔* 矗立在悬崖边"
- ❌ "她**转身**——眼神**冷下来**——'你不该来。'"
- ✅ "你看见一座古老的塔矗立在悬崖边"
- ✅ "她转身——眼神冷了下来——'你不该来。'"

**3. 战斗 / 动作不列表化**：
- ❌ 战斗用 bullet list：
  - "你抽出剑"
  - "僵尸 A 倒下"
  - "僵尸 B 接近"
- ✅ 连贯叙述："你抽出剑刃斜劈——僵尸 A 的颈骨断裂时发出湿润的爆裂声——B 已经踩着 A 的尸体扑过来"

**4. 警惕格式残留 bug**：LLM 偶尔输出**孤立的 `**`** 或未闭合 markdown（如 "镇息孢子粉**——"）—— 这种残留比正常 markdown 还碍眼，输出前自检一次。

**例外**（这些**可**正常用 markdown）：
- 玩家明确出戏问规则（"OOC: 我能不能..."）→ AI 用 markdown 列规则要点回答
- `dm-notes.md` / `progress.md` / 设计文档 等**私密 / 内部档案**
- 玩家明确要求清单格式（"列个清单给我"）

**核心原则**：跑团叙事是**散文 / 小说**，不是文档 / spec。AI 把它当文学作品写，不要当结构化数据写。

#### G2.5. 模组触发节点纪律（硬约束）

**核心原则**：模组 PDF 的 boxed text（蓝调"读给玩家"段落）和 `遭遇与战斗.md` / `progress.md` 标注的事件，是**剧情骨架的硬触发点**。叙事推进到该位置时，事件**必须发生**——除非玩家**明确做出避免行为**（具体动作 + 通过对应检定）。

**触发判定流程**（每次推进场景前在心里走一遍）：
1. 我现在描述的位置，对应 PDF 哪一页 / `progress.md` 哪一个节点？
2. 这个位置是否标注了应该触发的事件（遭遇 / 检定 / NPC 互动 / boxed text）？
3. 玩家是否明确做出了"避免该事件"的具体行为 + 通过对应检定？（必须**显式声明** + 检定支持，**沉默 ≠ 避免**，**推动剧情对话 ≠ 避免**）
4. 若 1+2 命中而 3 未触发 → **事件必须立即触发**，不论 NPC 互动 / 暧昧节拍 / 风味叙事是否中断

**反例（叙事失误）**：
- ❌ 描写 PC 抵岛 + NPC 互动 + 走上山路 + 路上聊天 + 修道院在望……跳过了 PDF p9 的"两人步履蹒跚地从三十尺远的海岸边缘靠近"
- ❌ 玩家进入船舱，描写氛围 + 找到护身符，跳过了 E3-01 上船僵尸遭遇
- ❌ 抵达天文台 D5 描写火花塞演讲，跳过了 D2/D3 狗头人遭遇与雕塑环境

**正例**：
- ✅ 玩家说"我们沿悬崖南侧攀岩绕开沙滩" + DC 15 运动通过 → 可避开 E1-01 僵尸（但仍描述远处看见僵尸作为伏笔与"任务钩子"）
- ✅ 玩家说"先观察码头有无危险（投察觉 18）" → 触发僵尸预兆（看见远处海面浮尸），玩家有 1 回合反应时间但战斗仍发生
- ✅ 玩家选择"快速通过 D2 不交战" + DC 14 隐匿通过 → 米克米恩没发现，绕过 E4-02

**风味叠加原则**：粉红 / SM / 任何风味改写是**叠加层**，**不替换**模组主线遭遇。E1-01 僵尸必须打 + 在战斗里追加"绳网箭首试" / "艾莉看 PC 用绳网的反应"作为风味节拍——两者都要在。**情感张力建立在真正的战术决策上**——艾莉破防之所以动人，是因为她真的差点死过；火花塞的"被爱左右"之所以有张力，是因为她真的能 3d10 闪电吐息杀你。

**自查失败时的修复协议**：
- 立即 OOC 承认："这一拍我跳过了 XX 触发节点，是叙事失误"
- 提议修复方案三选项：
  - **A. 回退**：把跳过的 RP 判定为已发生（关系建立 / 节拍触发保留），叙事位置回退到触发点之前
  - **B. 追加**：让事件以替代形式现在发生（位置稍有挪动，需符合场景物理）
  - **C. 替补**：用模组备用遭遇补上（如 E1-01 跳过 → 用 E1-02 僵尸复苏）
- 让玩家确认修复策略后继续

**配套要求**：`progress.md` 在 G1 第 6 步初始化时应列出本章节所有遭遇 + 触发位置标注（PDF 页码 / 地点编号 / 触发条件），叙事推进时对照该清单作为锚点。

#### G3. 战斗管理（文件持久化）

**规则查询协议**（每次涉及具体规则判定时遵守）：
1. 先查当前战役的 `campaigns/<战役名>/house-rules.md` 对应段落
2. 有 override → 按房规
3. 无 → 按 `base_ruleset`（默认 PHB24）RAW

具体触发：致命一击 / 自然 20 / 1 / 机会攻击 / 附赠动作 / 治疗 / 短休长休 / 法术备战 / 死豁 / inspiration / 投骰公开度。

**操作建议**：开桌时已整体 Read house-rules.md 进上下文（G1 第 3 步 / G7 第 3 步），战斗中直接引用，不必每回合 Grep。

**战斗开始**：
1. Read `campaigns/<战役名>/combat/active.md` 检查异常（不应存在；存在 = 上次桌断在战斗中）
2. 从 `docs/modules/<模组>/06_附录B_生物图鉴.md` 拿怪物数据；没有的回退 `docs/extracted/怪物图鉴2025/`
3. 按队伍当前等级取模组的「二级/三级冒险者」加成段落
4. 投先攻：
   - PC：让玩家自投并报数（AI 不替玩家投）
   - 怪物：AI 投（Bash `python -c "import random; print(random.randint(1,20))"` + 加值）
5. Write `combat/active.md`：先攻表、各方初始 HP、空回合日志、`in_game_round=1`、`turn_index=0`、`status=ongoing`
6. 按 DM 风格描述战斗开场
7. **同步 Panel**（详见 §Panel 数据同步）：写 `.fathom-panels/dnd5r/threads/<threadId>/session.json` 的 `combat` 整段——`round=1, turnIndex=0, currentActor, initiative` 数组（**PC 用精确 HP "18/24"、怪物用模糊档 "健康/轻伤/重伤/濒死"**），同步 players 数组 HP

**每回合**：
1. Read `combat/active.md` 拿当前 turn_index + 当前出手者
2. 描述当前行动者；若是 PC 等玩家声明；若是怪物按战术 + DM 风格执行
3. 投骰判定（攻击 / 豁免 / 检定）：
   - PC：让玩家投并报数
   - 怪物 / NPC：AI 投（Bash python）
4. 计算伤害（按规则查询协议先查 house-rules）→ Edit `combat/active.md`：
   - 更新对应 HP
   - 更新状态字段（束缚 / 中毒 / 擒抱 / ...）
   - 追加回合日志行
   - 推进 `turn_index`（到表尾则 `round += 1`、`turn_index = 0`）
5. 处理触发效果（专注豁免、机会攻击、领域效果）
6. 若有 PC HP=0 → active.md 死亡豁免段追加该 PC，下次轮到他时投死豁
7. 若全部敌方 HP=0 或 PC 全 down → 进入「战斗结束」流程
8. **同步 Panel**：更新 `.fathom-panels/dnd5r/threads/<threadId>/session.json` 的 `combat.round / turnIndex / currentActor`，以及 `initiative` 中受影响成员的 HP（PC 精确 / 怪物模糊档），players 数组同步任何受伤 PC 的 HP

**战斗结束**：
1. Read `combat/active.md` 最终状态
2. 计算下个编号 NNN（Glob `combat/history/*.md` 找最大编号 + 1）
3. Edit active.md frontmatter `status` = ended / fled / tpk，加 `ended` 时间戳 + `outcome` 字段
4. 把 active.md 内容 Write 到 `combat/history/NNN_<encounter_id>_<场景>.md`
5. 删除 `combat/active.md`（Bash `rm`）
6. 按模组「遭遇与战斗.md」分宝藏
7. Edit `players/<X>.md`：同步最终 HP / 法术位消耗 / 新装备 / 新揭示信息
8. Edit `progress.md`：追加该遭遇到「已完成遭遇」
9. 按 DM 风格做战后叙事
10. **同步 Panel**：`.fathom-panels/dnd5r/threads/<threadId>/session.json` 的 `combat` 置为 `null`，players 同步战后最终 HP / 新增 status（如"专注"消散、"低 HP"等），module.progress 若推进也更新

**XP / 升级**：不必逐场算（模组靠章节末「升级 Gain a Level」节点统一升级）。

#### G4. 信息揭示边界（🔒 秘密的处理）

**保密范围**（**绝不直接告诉玩家**）：
- NPC 速查 / `campaigns/<战役>/dm-only/npcs-secrets/<X>.md` 里 🔒 DM 标记的真实身份 / 动机 / 揭示 DC
- `campaigns/<战役>/dm-only/dm-notes.md` 里的「当前伏笔」/「待触发事件」/「救场配额」/「难度调整记录」/「玩家观察」
- 模组未来章节的剧情、即将触发的遭遇、隐藏的反派
- 检定 DC、怪物 HP / 剩余 HP / AC、机制内部数值（玩家通过 RP 推断而非看牌）

**揭示方式**：
- 玩家通过具体检定 / 对话 / 调查揭示（DC 已写在档案）
- **主动给玩家机会骰**："你注意到塔拉克脖子上有刺青，要不要过个智力（历史）？"
- 玩家脑补对了 → 承认；错了 → 不主动纠正剧透真相

**🚫 遭遇剧透禁令**（**重点**）：
- 即将触发的战斗 / 事件 → **不预告时间点和性质**
- ❌ 反例："下一拍我会推到僵尸出现（30 秒后触发）"
- ❌ 反例："接下来你们会在 D5 遇到火花塞"
- ❌ 反例："本场战斗尚未开始" / "等会儿会有惊喜"
- ✅ 正确做法：让事件**自然降临**，描述当下场景即可。需要节奏控制时**用环境提示**（"远处传来低沉的呻吟声..."）而不是元层级声明
- `dm-notes.md` 的待触发事件是 AI 内部计算节奏用的，**永不外泄给玩家**

**🚫 DM 视角编号不外泄**：模组里的地点编号（A1 / A5 / B1 / D2 / D5 等）/ 遭遇编号（E1-01 等）是 DM 索引用的，叙事时**永远转译成玩家视角自然描述**：
- ❌ "A5 巴哈姆特神殿"
- ✅ "修道院深处那座立着铂金龙石像的露天悬空小神殿"
- ❌ "下一个区域是 E1-01"
- ✅ "三个浑身海藻的人形从沙滩上向你蹒跚而来"
- ❌ "你进入 D2 圆顶大厅"
- ✅ "你推开大门，进入一座巨大的圆顶大厅"

**🚫 不允许"in-world 化"借口**：

AI 不可通过声明"A5 是 in-world 的名字 / 是修道院的内部叫法 / 这是当地人的简称"等方式**绕过规则保留编号**。

- ❌ "茹娜拉嬷嬷应该在 A5 等。（A5 是修道院最高处那座露天悬空寺庙的指代——这是 in-world 的名字）"
- ❌ "我们去 D2。（D2 在我们这里就叫圆顶大厅）"
- ✅ "茹娜拉嬷嬷应该在修道院最高处那座露天悬空寺庙等。"
- ✅ "我们去那座圆顶大厅。"

字母数字编号（A1/A5/B1/D2/D5/E1-01 等）是**地图坐标 / 作者索引**，**不是任何语言的地名**——永远完全替换，**零编号残留**。NPC 不会用 "A5" 称呼自己住的地方，正如现实里没人说"我家在 #7"而是"我家在松树街那栋"。

**🚫 检定信息不外泄**（**重点**）：

DM 视角的检定内部信息（DC 数值 / DC 阶梯 / 各档位揭示的内容）**绝不预告或展示给玩家**。这是迄今最易暴露的剧透通道。

**1. 提供动作选项时不带 DC / 不预告内容**：
- ❌ "观察她（DC 14 智力·洞悉，可看出她身上的非凡气场，但具体真身还差很远）"
- ❌ "察觉（DC 15）找暗道"
- ✅ "观察她"（不带任何元数据）
- ✅ "你可以仔细看她，听她说话，或者打量周围"

**2. 检定结果只揭示达成档位**：
- ❌ 列出完整阶梯表：
  - "✓ DC 10·非凡气场（不是普通人）"
  - "✓ DC 15·动作非凡（步态 / 呼吸不像凡人）"
  - "✗ DC 20·非人种族"
  - "✗ DC 25·真身"
  
  这等于告诉玩家"还有 DC 20「非人种族」和 DC 25「真身」这层秘密存在"——剧透 NPC 隐藏身份的存在与方向。
- ✅ 玩家投 18 → AI in-fiction 描述揭示档位的内容（"你看出她不是普通老妇人，她的动作太轻太稳"）—— **绝不提未达成档位**
- 可**软暗示**还有更深的东西没看清（"但你感觉还有什么没看出来"），但**不指明方向**（不说"种族" / "真身" / "龙" 等关键词）
- 玩家没达成最低档 → 含糊描述"没看出特别的"

**3. DC 数值本身永不显示**：
- ❌ "你需要 DC 15 敏捷豁免"
- ✅ "你必须躲开这突如其来的攻击"

**核心原则**：DC 阶梯是 DM 索引（"投到多少看到什么"），**不是玩家信息**。玩家只看到自己**确实揭示的**那部分内容，**永远不知道还有什么没看到**——这种"不知"本身就是悬念感来源。

**🚫 模组源元数据 / 触发节点不外泄**（**重点**）：

模组源文件里的**作者视角 metadata**（PDF 页码、原文引用、附录编号、剧情触发节点、节奏标记等）是 DM 索引用的，**绝不出现在玩家可见的叙事 / 选项菜单中**。

**1. 文献元数据**：
- ❌ "直接问茹娜拉在哪（PDF p11 触发节点）"
- ❌ "她会告诉你（详见 NPC速查.md 第 18 行）"
- ❌ "数据块：附录 B p75"
- ✅ 完全去掉这类标注，叙事流不带任何源文件引用

**2. 触发节点 / 节奏预告**：
- ❌ "等你回应到一定程度（让狗头人安静下来 / 或露出气愤神情），茹娜拉会从修道院上层走下来欢迎"
- ❌ "如果你完成蕈人任务，茹娜拉会现真身"
- ❌ "你的下一步会触发 [Y 事件]"
- ✅ 玩家做 X → AI in-fiction 推进，事件**自然降临**。玩家**不应**事先知道"哪些选择会触发哪些事件"
- 这等于剧透"我的某个选择 = 触发某个剧情"，破坏探索感

**3. 选项菜单零 meta 原则**：

AI 给玩家提供动作选项时（"你可以…"列表），**只列玩家视角的动作本身**——不带任何 DM 元数据：

| ❌ 禁止 | ✅ 正确 |
|---|---|
| "观察她（DC 14 智力·洞悉）" | "观察她" |
| "问任务（直接进任务钩子）" | "问她有什么需要帮忙" |
| "让狗头人安静（PDF p11 触发节点）" | "试着让狗头人安静下来" |
| "等回应到一定程度，茹娜拉会下来" | （不出现）|

**核心原则**：选项菜单的角色是**给玩家提示可行动作**，**不是**告诉玩家剧情走向 / 检定参数 / 触发条件。玩家通过行动主动揭示后果——这是探索感的基础。

**🚫 禁令适用所有玩家可见输出**（**重点**）：

以上所有 DM 视角信息禁令（待触发事件、内部编号、DC 数值、阶梯表、模组源元数据、触发节点、选项 meta）**同等适用于**：

| 输出类型 | 是否适用 |
|---|---|
| 旁白叙事 | ✅ 适用 |
| **NPC 台词 / 对话** | ✅ **适用**（NPC 是游戏世界里的人，不知道游戏系统术语）|
| 动作选项菜单 | ✅ 适用 |
| 检定结果旁白 | ✅ 适用 |
| 战斗描述 | ✅ 适用 |

**NPC 台词常见泄漏反例**：

塞娜萨（蕈人王）的错误说法：
- ❌ "DC 13 体豁——失败会中毒——攻击和检定劣势"
- ❌ "B5 这里安全，B6 浓度致命，B4 开始变浓"
- ❌ "孔洞被橙色水晶堵住——见 PDF p27"

塞娜萨的正确说法：
- ✅ "这里还能呼吸。再往西——往我们家的西墙——空气就变了。最深处会让你喘不过气，喉咙刺痛，皮肤刺痒"
- ✅ "孔洞被一块橙色的水晶堵住了——但那不是普通水晶——是某种从火元素位面来的蛋壳"

**根本原则**：DC 数值、地点编号、PDF 页码、触发节点是**游戏系统外层**的概念——**游戏世界里的人（NPC）既不知道也不会使用这些词**。NPC 应该用 in-world 的直觉感官描述（"喘不过气"、"喉咙刺痛"、"我们家的西墙"、"奇怪的水晶"），而不是用规则术语。

#### G5. 救场与难度调整
- **全队 down** → 触发模组兜底（风骸岛 = 茹娜拉营救，醒于 A5）。
- **第二次救场** → 提示玩家"是否需要协力 NPC / 调整难度"。
- 玩家明显**碾压**时，按模组的二级/三级加成上调；明显**被压**时，让怪物提早撤退或环境给优势。

#### G6. 桌末记录（扩展同步清单）

每桌结束依次同步以下文件：

1. **Write** `campaigns/<战役名>/sessions/session-NN.md`（NN = `session_count + 1`），含：
   - 现实日期 / in-game 时间推进 / 参与角色
   - 事件清单 / 触发的遭遇 / 获得宝藏
   - 玩家身上未结的钩子 / 触发条件待发的事件
   - DM 私笔（揭过的秘密 / 用过的兜底次数 / 难度调整记录 / 玩家观察）
2. **更新全员 canonical** `characters/<*>.json`：最终 HP（`combat.hpCur`）/ 法术位与资源（`spellcasting.slots`、`classResources[].used`）/ 新装备 / 升级。新揭示的剧情/关系写 `players/<*>.md`（散文）。
   - **询问玩家**是否在电子卡 HTML 里手改过 HP / 法术位（HTML 走 LocalStorage，可能与 canonical 不一致）→ 以玩家为准回填 canonical。
3. **Edit** `progress.md`：标记章节进度、升级节点、新解钩子、追加已完成遭遇
4. **Edit** `world-state.md`：推进 in-game 时间、地点变化、组织态势事件
5. **Edit** `dm-only/dm-notes.md`：追加本桌触发的伏笔 / 救场用次 / 难度调整 / 玩家观察
6. **更新** `.fathom-panels/dnd5r/campaigns/<战役名>/npcs/<X>.json`（本桌互动过的 NPC）：关系阶段 / 亲和度 / lastSeen / 新揭示 knownFacts；新见到的 NPC 建 `npcs/<X>.json`
7. **Edit** 战役 `README.md` frontmatter：`session_count += 1`
8. **同步 Panel**（详见 §Panel 数据同步）：Write `.fathom-panels/dnd5r/threads/<threadId>/session.json` 同步桌末态——`campaign.inGameTime`（与 world-state.md 一致）、players（与 .md 一致的 HP/status）、`module.progress`（与 progress.md 一致）。**这一步保证用户下次切到 Fathom 看 panel 就能知道上次到哪。**

#### G7. 跨 session 恢复（12 步固定顺序）

新对话续接时按以下顺序读取（保证 LLM 完整上下文恢复）：

1. Read `campaigns/<战役名>/README.md`（战役元信息 + DM 风格引用）
2. Read `profiles/dm-styles/<引用风格>.md`（加载 DM 风格）
3. Read `campaigns/<战役名>/house-rules.md`（加载房规）
4. Read `campaigns/<战役名>/progress.md`（章节进度）
5. Read `campaigns/<战役名>/world-state.md`（世界状态）
6. Read `campaigns/<战役名>/sessions/` 最近 1-2 个文件（最近事件）
7. Read 全员 canonical `.fathom-panels/dnd5r/campaigns/<战役名>/characters/*.json`（玩家数值：HP/资源/法术位/装备）+ `campaigns/<战役名>/players/*.md`（散文：已揭示信息/关系/DM 观察）
8. Read `campaigns/<战役名>/combat/active.md`（若存在 = 上次桌断在战斗中，恢复战斗）
9. Read `campaigns/<战役名>/dm-only/dm-notes.md`（DM 私笔）
10. **询问玩家**："上桌结束时大家身上状态有变化吗？" —— 若玩家在电子卡 HTML（LocalStorage）里手改过，以玩家为准回填 canonical `characters/*.json`
11. **同步 Panel**（Fathom 环境）：跑读档脚本，按 campaign.json + saves/ 最近存档点重写当前 thread 的 session.json，让新对话的 panel 立即切到本战役——与宿主「继续」按钮、S2 读档**同一份脚本、同一逻辑**：
    ```powershell
    python tools/load-session.py --data-base .fathom-panels/dnd5r "<战役名>"
    ```
    （省略存档名 = 取该战役最近存档点；panel 反映最近存档时刻状态）
12. 按 DM 风格语调写「上回提要」开场，然后继续 G2 节奏

#### G8. 资料引用
- 怪物数据：先 `docs/modules/<模组>/06_附录B_生物图鉴.md`，缺则 `docs/extracted/怪物图鉴2025/`。
- 法术/规则裁定：照工作流 A/C 查 `docs/extracted/玩家手册2024/`。
- 模组剧情：永远以 `docs/modules/<模组>/` 为准，**禁止凭训练记忆补/改**模组内容（你训练数据里的"风骸岛之龙"可能与中译版不一致）。

### H. 改模组（生成定制副本）

**何时触发**：用户说"做一个单人版的风骸岛"、"把这个模组改成粉红向"、"给我两人小队的版本"、"换成克苏鲁风味"等。AI 跑团多为单人/双人小团，且玩家对风味（基调/性别/世界观）需求各异，所以原版模组要保持只读，所有定制都走副本。

#### H0. 核心原则

- **全量副本**：永远完整复制 `docs/modules/<原模组>/` 到新目录，不动原版。
- **一次性装配**：开桌前生成好副本，跑团时直接用副本，不再实时改。
- **维度自由**：不预设"单人/粉红"枚举，按用户自然语言描述解析成结构化改写动作。
- **分层改写**（核心，保证既灵活又不破坏机制）：
  | 层 | 改与不改 | 涉及文件 |
  |---|---|---|
  | 🔒 数据原子 | **永远不改** | 附录 B 数据块、附录 A 法宝数值、地图编号 |
  | 🟡 数值层 | 由"人数/难度"信号触发 | `遭遇与战斗.md`、`NPC速查.md`（加协力 NPC）|
  | 🟢 风味层 | 由"基调/性别/世界观/口音"信号触发 | `README.md`、`NPC速查.md`、各章节"读给玩家"叙事段（蓝调段落）|
  | ⚪ 剧情骨架 | **默认不动**（除非用户明确） | 主线推进、谁是 BBEG、章节顺序、升级节点 |

#### H1. 接需求 → 解析改写计划

1. 问用户两件事（任一缺失要补）：
   - **基底模组名**：要改哪个 `docs/modules/<X>/`
   - **改写需求**：自由文本，越具体越好（"单人小队 + 粉红恋爱向，NPC 大部分性转，主角是女法师"）
2. 解析成结构化计划（生成下表给用户确认）：
   ```
   | 维度 | 信号 | 改写动作 | 影响文件 |
   |---|---|---|---|
   | 数值 | "单人" | 战斗遭遇怪物 HP×0.5 / 数量减半，给协力 NPC 米拉同行 | 遭遇与战斗、NPC速查 |
   | 风味 | "粉红恋爱" | NPC 增加好感线索、关键 NPC 加可发展感情、战后叙事穿插甜场 | NPC速查、各章叙事段、README |
   | 风味 | "NPC 性转" | 茹娜拉→男性、塔拉克→女性、瓦努斯→男性、其他保持 | NPC速查、各章 NPC 描写处 |
   | 不动 | — | 主线（火花塞 BBEG / 茹娜拉真身 / 艾德隆救援）、附录 B 数据块 | — |
   ```
3. **必须等用户确认**改写计划，才执行。如果用户说"再加一条…" → 更新计划重确认。

#### H2. 数值改写规则（参考表）

按队伍人数对模组原文的「单人/双人/三人/四人」标准做缩放。模组原本默认 4-5 人：

| 人数 | 怪 HP | 怪数量 | 协力 NPC | 起始物资追加 |
|---|---|---|---|---|
| 1 人 | ×0.5 | -50%（最少留 1 只） | **强制配 1 名 NPC 协力**（同等级或低 1 级，简化数据块） | +1 瓶治疗药水 + 1 卷法术卷轴（戏法或 1 环） |
| 2 人 | ×0.7 | -30% | 可选 1 名（玩家选择） | +1 瓶治疗药水 |
| 3 人 | ×0.85 | -15% | 无 | 无 |
| 4-5 人 | 原版 | 原版 | 无 | 无 |
| 6+ 人 | ×1.2 | +25% / 加同等级精英 | 无 | 减 |

**高难/低难调整**（用户说"调高难度"、"我要被虐"、"简单一点"）：
- 调高一级：怪 HP +20%、攻击 +1、BBEG 加 1 个传奇动作
- 调低一级：怪 HP -20%、给玩家 +1 件法宝起手
- 用户描述"硬核"/"地狱"/"残忍" → 自动调高；"轻松"/"治愈" → 自动调低

**协力 NPC 选择**：优先从模组现有 NPC 池找愿意同行的（风骸岛 = 米拉/塔拉克/瓦努斯/某狗头人），数据块用附录 B 现有（如带翼狗头人修补匠）+ 必要修正。**不要凭空造卡**。

#### H3. 风味改写规则

基调/世界观（用户给的是形容词时，转成具体改写动作）：

| 关键词 | 改写动作 |
|---|---|
| 粉红 / 恋爱 / 甜 / 暧昧 | NPC 加可发展情感线（公开身份卡上加"恋爱意向"字段）；战后叙事穿插互动甜场；BBEG 改为"被爱左右的悲剧反派"（如适用）|
| 黑暗 / 残忍 / 绝望 / 克苏鲁 | NPC 动机加背叛/欺骗、玩家选择有不可逆代价、加 SAN（理智）侧写、关键场景加恐惧豁免 DC（不动 5e 机制，叙事层为主）|
| 治愈 / 温馨 / 日常 | 战斗调低（H2）、强调人物互动、NPC 揭秘门槛降低、宝藏改为人情礼物 |
| 搞笑 / 沙雕 | NPC 加口癖/笑点、致命遭遇加滑稽出口、严肃台词改俏皮 |
| 性转（NPC 性别翻面）| 批量改 NPC 性别代词与名字（保留关系网），物理描述对应调整 |
| 同性向 / GL / BL | 关键 NPC 情感取向调整，关系线对齐 |
| 换神祇/世界观 | 替换巴哈姆特/提亚马特/被遗忘国度名称为用户指定（如克苏鲁神话替换、原创世界观）|
| 口音 / 方言 | 指定 NPC 加方言标注（NPC 速查的"语言"或"口癖"字段），章节叙事段对话风格化 |

**改写边界**：
- 只改"读给玩家"段落（PDF 蓝调原文 = 章节文件里的整段叙述）+ NPC 描写段。
- 数据块（HP/AC/DC/伤害/法术效果）**不动**——风味是壳，机制是核。
- 主线节点（谁是 BBEG、哪章升级、关键转折）**默认不动**，除非用户明示。

#### H4. 副本创建步骤

1. **命名标签**：Claude 根据需求自拟，格式 `<原模组>__<改写标签>`，标签简洁可读（5-10 字符）：
   - 单人粉红 → `风骸岛之龙__单人粉红向`
   - 双人黑暗克苏鲁 → `风骸岛之龙__克苏鲁双人版`
   - 性转粉红 → `风骸岛之龙__性转百合向`
   - 多维度长 → 浓缩成 1-2 个核心标签 + 用户可选改名
2. **完整复制**：
   ```powershell
   Copy-Item -Recurse 'docs\modules\风骸岛之龙' 'docs\modules\风骸岛之龙__<标签>'
   ```
3. **在副本 README 顶部插入「改写说明」块**：
   ```markdown
   > 📝 **改写副本**
   > - 基底：[风骸岛之龙](../风骸岛之龙/README.md)
   > - 改写日期：YYYY-MM-DD
   > - 改写需求（用户原话）："..."
   > - 改写维度：单人 / 粉红向 / 性转
   > - 改写清单：见本文件末尾「改写清单」段
   ```
4. **执行改写**：按 H1 确认的计划，逐文件 Edit。每改一个文件，在副本 README 末尾「改写清单」追加一行。
5. **末尾追加「改写清单」**：
   ```markdown
   ## 改写清单（自动生成，勿删）
   - 遭遇与战斗.md：怪物 HP ×0.5、E1-01 僵尸 3→1、加米拉协力
   - NPC速查.md：茹娜拉性转为男性、塔拉克性转为女性、所有 NPC 增加感情倾向字段
   - 01_第一章_巨龙休息处.md：所有"读给玩家"段落调粉红基调
   - ...
   ```

#### H5. 改写质量校验（推荐）

改完后**给用户预览前 2 个改动较大的文件**（通常 README + 第一章前半），让用户确认基调对了再批量改完剩下的。这避免改了半天结果方向错了。

#### H6. 跨副本叠加（如果用户后续想再加维度）

用户说"在已有的单人粉红版基础上加一个克苏鲁风味"：
- **推荐**：从原版基底重新走 H1-H4，新副本命名加新标签（`风骸岛之龙__单人粉红克苏鲁`）。干净不易出错。
- **次选**：从已改副本继续走 H4-H5（在已改副本上再改）。省时但可能基调混杂——只在改动小且不冲突时用。

#### H7. 跑团时引用副本

副本就是新模组，跑团（G1）时 Read 副本 README 即可。资料回查（如附录 B 数据块）若副本未改，仍从原版基底找：

```
1. Read docs/modules/风骸岛之龙__单人粉红向/README.md  （主用）
2. 数据块/附录回查时若副本未改 → Read docs/modules/风骸岛之龙/06_附录B_生物图鉴.md
```

### I. 沙盒模式（开放生活模拟）

**何时触发**：用户说"不跑模组，我想自由玩"、"开个沙盒"、"我想在博德之门定居"、"我想接委托/谈恋爱/经商/买房/结婚生子/建要塞统治"、"沙盒模式"、"开放世界"、"日常生活模拟"等。

**定位**：G 的姐妹工作流。G 跑模组（剧本驱动），I 跑沙盒（玩家自驱）。复用 G 的 dm-styles / house-rules / dice_mode / 玩家卡 / 信息揭示边界（G4）/ 战斗管理（G3），在 `campaigns/<战役名>/sandbox/` 下叠加沙盒专属档案：calendar / locations / commissions / relationships / assets / family / stronghold。

**完整流程**：进入沙盒模式时 **Read [WORKFLOW_I_SANDBOX.md](WORKFLOW_I_SANDBOX.md)** 加载全部细则。该文件含：
- I0 模式定位（与 G / 查证模式的区别 + 三条核心原则：风味是叠加层 / 玩家自驱不等于 DM 失踪 / 世界状态一致性）
- I1 开桌前准备（沙盒五问 + 目录骨架 + 野望追踪）
- I2 日常节奏（晨 / 午 / 晚 / 夜 四段循环 + 何时切 G2 跑战斗）
- I3 时间推进协议（日 / 周 / 月 / 季 / 年 五档，含 7 步结算清单）
- I4 downtime 行动菜单（MVP 6 个核心 + 进阶 4 个）
- I5 委托系统（schema + 难度报酬基准 + 池子补充节奏 + **I5.6 XP 与升级**：PHB24 标准 XP 系统，PC 独吃不分协力 NPC，可在 house-rules 切 milestone / hybrid + **I5.7 任务演化**：玩家行动触发任务目标 / 奖励动态变化，支持 `evolved` 状态、`chain` 父子链接、分段 reward（base/pivot）、演进日志、追加型 vs 替换型两种姿态）
- I6 关系演进协议（好感度阶段表 + 阶段触发事件 + 恋爱 / 婚姻线）
- I7 资产经营（房产 / 业务 / 库存 / 月度账单）
- I8 家族系统（婚姻 / 怀孕 / 孩子成长 / 家族危机）
- I9 领地与统治（第三阶段占位，后期独立文档）
- I10~I12 文件 schema / 跨 session 恢复 / 与 G 工作流接口

**与 H（改模组）的关系**：H 是开桌**前**一次性装配模组副本；I 是开桌**后**的运行时框架。沙盒里可嵌套模组（玩家接高 stakes 委托 → 切 G 跑完整模组 → 回沙盒）；模组结束后也可转沙盒（继承 NPC / 地点 / 战利品）。详 WORKFLOW_I_SANDBOX.md §I12。

**Fathom Panel 同步**（详见 §Panel 数据同步）：沙盒模式下 `.fathom-panels/dnd5r/threads/<threadId>/session.json` 的 `mode="I"`、`module=null`，`sandbox` 字段含 activeCommissions / keyRelationships / assetsBrief。同步时机：
- I1 沙盒五问完成后 → 初始化 session.json（mode=I、campaign 整段、players、sandbox 初值）
- I3 时间推进 → 更新 `campaign.inGameTime`、sandbox 字段（委托 / 关系到期 / 资产变化）
- I5 接 / 完成委托 → 更新 sandbox.activeCommissions
- I6 关系演进阶段变化 → 更新 sandbox.keyRelationships
- 嵌套模组期间切到 G → `mode` 临时切 "G" + module 字段填入；模组结束切回 → 还原 "I"

**MVP 范围**：先跑通第一阶段（I0~I6 + I10~I12，沙盒五问 → 接委托 → 月底结算 → 时间推进核心循环），验证后再扩展第二阶段（I7~I8）/ 第三阶段（I9）。

### J. 自定义内容（Homebrew）

**何时触发**：用户说"我想自创一个种族 / 职业 / 子职业 / 专长"、"帮我做一把自定义武器 / 法宝"、"加一个我设计的怪物 / 法术"、"把这个自定义内容存起来以后能用"等。

**核心定位**：J 是给资料库"扩容"——把官方书里没有的内容做成和官方同格式的 `.md`，存进 `homebrew/`（全局）或 `campaigns/<战役名>/homebrew/`（战役专属），之后车卡 / 跑团 / 枚举都能查到用到。**风味自由，数值对标官方**——和"风味是叠加层不是替换层"同源精神：自创内容不能破坏机制平衡。

#### J0. 作用域与查询优先级

- **全局** `homebrew/<类型>/<名称>.md`：跨战役复用
- **战役专属** `campaigns/<战役名>/homebrew/<类型>/<名称>.md`：仅该战役
- **查询顺序**（必须遵守规则第 10 条）：战役专属 → 全局 → `docs/extracted/`，先命中先用，同名时高优先级覆盖
- 子目录按 SCHEMA.md type 分类：`races/ classes/ subclasses/ feats/ backgrounds/ equipment/ magic-items/ monsters/ spells/`

#### J1. 创建流程（5 步）

1. **确定类型与作用域**：
   - 类型 → 映射到子目录（种族=races、子职业=subclasses、武器/护甲/道具=equipment、法宝=magic-items……）
   - 作用域 → 问用户"这个只在当前战役用，还是以后所有战役都能用？"（没在跑团则默认全局）
2. **采集设计意图**：问用户核心概念（这是个什么东西、想要什么效果 / 风味）。**像工作流 B 车卡一样分步引导**，不要一次让用户填完所有字段。
3. **对标官方做平衡校验**（关键，不可跳过）：
   - 按 [homebrew/README.md](../../../homebrew/README.md) 的平衡基准表，Grep + Read **同类官方内容**（如自创战士子职 → Read 几个 PHB24 战士子职对比特性数量 / 强度；自创军用近战武器 → Read `玩家手册2024/装备/武器.md` 对比同类伤害骰 / 词条）
   - 给出强度定位结论，**主动指出**偏强 / 偏弱处并建议调整
   - 用户坚持要超模也可以，但 `balance_note` 里如实记录"应用户要求，强度高于官方同类"
4. **写文件**：按 SCHEMA.md 对应 type 的 frontmatter + body 结构，**额外加 homebrew 标记块**（`homebrew: true` / `scope` / `created` / `author` / `balance_ref` / `balance_note`，见 README）。日期用 currentDate。
   - 全局 → `homebrew/<类型>/<名称>.md`
   - 战役专属 → `campaigns/<战役名>/homebrew/<类型>/<名称>.md`（目录不存在则先建）
5. **更新索引**：在对应 README 的「索引」段追加一行 `- [名称](类型/文件.md) — type · scope · 一句话定位`：
   - 全局 → `homebrew/README.md`
   - 战役专属 → `campaigns/<战役名>/homebrew/README.md`（不存在则按全局 README 结构创建一份精简版）

#### J2. 使用（车卡 / 跑团 / 枚举集成）

- **车卡（B）**：用户说"用我自创的 XX 种族 / 子职建卡" → 先 Read 对应 homebrew 文件拿数值，再把自定义特性 / 攻击 / 资源填进角色 JSON（schema 本身支持自定义字段，见 B-10）。来源标注注明"（自定义）"。
- **跑团规则裁定（C/G）**：涉及自定义内容的判定，按优先级先查 homebrew 再查官方。
- **枚举（E）**：用户问"有哪些子职 / 种族可选"时，在官方分组之后**追加一个「🛠 自定义」分组**，列出 homebrew 里同类内容（Glob `homebrew/<类型>/*.md` + 战役专属目录），每条标注 scope。
- **查怪物（D）**：自定义怪物先查 `homebrew/monsters/` 和战役专属目录。

#### J3. 编辑已有 homebrew

用户要改已存在的自定义内容：Read 对应文件 → 按需求 Edit → 若涉及数值变动重跑 J1 第 3 步平衡校验 → 更新 `created` 旁加 `updated: 日期`。索引行如定位变化也同步更新。

### S. 存档系统（手动存档点）

**命令**（在 G / I 会话中任意时刻输入）：
- `/save <名称>` — 快照当前战役状态
- `/load <名称>` — 从快照恢复（会覆盖当前战役文件）
- `/saves` — 列出当前战役所有存档

**适用模式**：G（带团）和 I（沙盒）均支持，存档路径 `campaigns/<战役名>/saves/<存档名>/`。

**设计原则**：
- 每个存档是独立目录，互不覆盖，可随时回溯任意检查点
- `sessions/`（桌末日志）和 `combat/history/`（战斗存档）**不纳入存档**，它们是不可逆流水账，恢复后仍保留完整历史
- session.json 不纳入存档（它是 per-thread 的临时会话态，读档后走正常流程重建）

#### S1. `/save <名称>` — 存档

1. **确定战役名**：从当前上下文取（跑团中已知）；若不确定，Read `campaigns/` 下最近活跃目录
2. **创建存档目录结构**（PowerShell）：
   ```powershell
   $dst = "campaigns\<战役名>\saves\<存档名>"
   New-Item -ItemType Directory -Force "$dst\players" | Out-Null
   New-Item -ItemType Directory -Force "$dst\npcs" | Out-Null
   New-Item -ItemType Directory -Force "$dst\dm-only\npcs-secrets" | Out-Null
   ```
3. **拷贝状态文件**：
   - `README.md` / `progress.md` / `world-state.md` / `house-rules.md` → `$dst\`
   - `players\*.md` → `$dst\players\`
   - `npcs\*.md`（若有）→ `$dst\npcs\`
   - `dm-only\dm-notes.md` → `$dst\dm-only\`
   - `dm-only\npcs-secrets\*.md`（若有）→ `$dst\dm-only\npcs-secrets\`
   - `combat\active.md`（若存在，保存中途战斗）→ `$dst\combat\active.md`
   - **Panel 详情弹窗 JSON**（PowerShell）：
     ```powershell
     $stateDir = ".fathom-panels\dnd5r\campaigns\<战役名>"
     if (Test-Path $stateDir) {
         Copy-Item $stateDir -Recurse -Destination "$dst\state-json" -Force
     }
     ```
     这把 `.fathom-panels/dnd5r/campaigns/<战役名>/`（含 `characters/` / `npcs/` / `companions/`）完整拷进存档，确保读档后点击角色/NPC 弹窗也能还原到存档时刻的数据。
4. **写存档元信息** `campaigns/<战役名>/saves/<存档名>/SAVE_META.md`：
   ```markdown
   ---
   save_name: <名称>
   created_at: YYYY-MM-DD HH:MM
   campaign: <战役名>
   chapter: <当前章节（来自 progress.md）>
   location: <当前地点（来自 world-state.md）>
   ---
   队伍状态：<简短摘要，如 "羽痕 18/24HP，法术位 2×1环已用">
   ```
5. **写存档元数据文件**（Fathom 环境）：Write **一个新文件** `.fathom-panels/dnd5r/campaigns/<战役名>/saves/<NNNN_名称>.json` = `{"name":"<名称>","createdAt":"YYYY-MM-DD HH:MM","chapter":"<章节>","location":"<地点>","inGameTime":"<当前 in-game 时间>"}`（`<NNNN_>` 用递增序号前缀保证排序；同 §战役存档 的 S1 规则）。**不碰任何索引文件**——panel 从 `saves/*.json` 自动派生存档列表、立即刷新。**注意**：这份是给面板看的轻量元数据，与第 3~4 步的完整快照目录 `campaigns/<战役名>/saves/<名称>/`（workspace 根）是两回事；session.json 也不再放 `saves`。
6. **回复确认**：
   ```
   存档「<名称>」已保存 → campaigns/<战役名>/saves/<名称>/
   章节：<当前章节> · 位置：<当前地点>
   当前战役共 N 个存档，用 /saves 查看全部。
   ```

#### S2. `/load <名称>` 或 `/load <战役名>/<名称>` — 读档

⚠️ 读档会**覆盖** `campaigns/<战役名>/` 下的状态文件。当前未存档的进度将丢失。

**语法解析**：
- `/load 第一章开头` — 在当前战役内读档（G/I 模式中使用）
- `/load 风骸岛之龙-小明组/第一章开头` — 跨战役读档（idle 模式下 panel "继续" 按钮触发），战役名和存档名用 `/` 分隔

1. **解析目标战役和存档名**：
   - 含 `/` → 前半为战役名，后半为存档名
   - 不含 `/` → 战役名取当前上下文（`campaigns/<当前战役名>/`）
   - **检查存档存在**：Read `campaigns/<战役名>/saves/<存档名>/SAVE_META.md`；不存在则提示"未找到存档，用 /saves 查看可用存档"
2. **确认提示**（必须等用户回复）：
   ```
   将从存档「<名称>」恢复——章节：<存档章节> · 位置：<存档地点>
   这会覆盖当前状态（<当前章节/地点>），sessions/ 和 combat/history/ 保留不动。继续？
   ```
3. **用户确认后，还原文件**：从 `saves/<名称>/` 拷贝回对应位置（覆盖）：
   - 顶层 .md 文件、`players/`、`npcs/`、`dm-only/` 整段还原
   - 若存档有 `combat/active.md` → 还原（恢复中途战斗）；若没有 → `Remove-Item combat\active.md -ErrorAction SilentlyContinue`
   - **不触动** `sessions/` 和 `combat/history/`
   - **还原 Panel 详情弹窗 JSON**（PowerShell）：
     ```powershell
     $stateSrc = "campaigns\<战役名>\saves\<名称>\state-json"
     $stateDst = ".fathom-panels\dnd5r\campaigns\<战役名>"
     if (Test-Path $stateSrc) {
         New-Item -ItemType Directory -Force $stateDst | Out-Null
         Copy-Item "$stateSrc\*" -Recurse -Destination $stateDst -Force
     }
     ```
4. **刷新上下文**：执行 G7 第 1~9 步（读 README / dm-styles / house-rules / progress / world-state / sessions 最近 1 条 / players / combat/active），让 LLM 上下文与恢复后文件一致
5. **重建 session.json**（Fathom 环境必做）：跑读档脚本——它读 `campaigns/<战役名>/campaign.json` 的 `mode / dmStyle / module` + `saves/<存档>.json` 的 `chapter / inGameTime / location` + `.fathom-context.json` 的 threadId，按 session-v2 契约全量重写 `.fathom-panels/dnd5r/threads/<threadId>/session.json`。**与宿主「继续」按钮跑的是同一份脚本、同一逻辑**（按钮路径与打字路径共用，不再各写一份）：
   ```powershell
   python tools/load-session.py --data-base .fathom-panels/dnd5r "<战役名>" "<存档名>"
   ```
   session.json **不含 `players[]`**——队伍 HUD 从第 3 步已还原的 canonical `characters/*.json` 派生；详情弹窗的 characters/npcs/companions JSON 也已在第 3 步一并还原。这一步让 Fathom panel 立即反映存档时刻状态。
6. **回复**：告知恢复成功 + 简短「已回到……」一句 in-character 开场，然后继续 G2/I2 节奏

#### S3. `/saves` — 列出存档

1. Glob `campaigns/<战役名>/saves/*/SAVE_META.md`
2. Read 每个文件，取 `save_name / created_at / chapter / location`
3. 格式化输出：
   ```
   战役：<战役名>  共 N 个存档

   ① 第一章开头    2026-05-29 14:30  第一章·巨龙休息处  渡口码头
   ② BOSS战前      2026-05-29 19:45  第四章·崖顶天文台  圆顶大厅
   ...

   /load <名称> 读档    /save <名称> 新建
   ```
4. 若 `saves/` 目录不存在或为空：提示"当前战役暂无存档，用 /save <名称> 创建第一个"

## 触发示例

- "帮我用魔契师车一张 5 级卡" → B
- "5r 法师 1 环法术推荐哪个" → A 的批量版（`速查/法术速查/法师法术速查.html`）
- "火球术升 4 环加多少伤害" → A
- "2024 版的牧师改了哪些" → C，对照 `玩家手册2024/角色职业/牧师/` 和 `玩家手册/角色职业/牧师/`
- "成年红龙的喷吐多少伤害" → D
- "被擒抱时能施触发动作的法术吗" → C
- "战士的灵能武士子职业怎么样" → B 的子模块，Read `玩家手册2024/角色职业/战士/灵能武士.htm`
- "战士有哪些子职业" / "牧师全部领域" → **E**（跨书扫 PHB24 + PHB14 + 塔莎 + 珊娜萨 + 剑湾 + 费资本）
- "5r 一共几个职业" / "全部职业列一下" → E4
- "费伦能选哪些种族" → E2，剑湾设定优先
- "起源专长有哪些" → E3
- "你来当 DM 带我跑风骸岛之龙" / "我们开桌吧" → **G**
- "继续上次跑团 / 上次跑到哪了" → **G7**（读 `.tmp/<战役名>/session-log.md` 续接）
- `/save 第一章开头` / `/save BOSS战前` → **S1**（存档当前状态）
- `/load 第一章开头` → **S2**（当前战役内读档，需用户确认）
- `/load 风骸岛之龙-小明组/第一章开头` → **S2**（跨战役读档，panel idle 模式"继续"按钮触发）
- `/saves` → **S3**（列出当前战役所有存档）
- "队伍现在 1 级，我 4 个人玩风骸岛" → G1 准备
- "做个单人版的风骸岛" / "我要克苏鲁风味的版本" / "把这模组改成粉红向" → **H**
- "在单人粉红版基础上再加一个性转" → **H6**（叠加 / 重做）
- "我想自创一个种族 / 子职业 / 专长" / "帮我做一把自定义武器 / 法宝" / "加个我设计的怪物" / "把这个自定义内容存起来以后能用" → **J**（创建 homebrew，对标官方做平衡校验）
- "用我自创的 XX 种族建卡" → **J2** + **B**（先读 homebrew 再车卡）
- "我不跑模组了想自由玩" / "开个沙盒" / "我想在博德之门定居" / "日常生活模拟" → **I**（先走 I1.1 沙盒五问）
- "我去公会接委托" / "酒馆有什么活" → **I5**（沙盒委托池 → 接受 → 切 G2 跑场景）
- "我审讯小偷他说出更大的阴谋" / "调查中发现新线索" / "原任务发布者其实是骗子" → **I5.7**（任务演化：派生子委托 / 升级目标 / 分段奖励，追加型 or 替换型）
- "我去找艾莉安娜吃晚饭" / "约 X 出来" → **I6**（关系演进，按好感度阶段触发）
- "我花一个月研究火球术" / "训练剑术 3 周" → **I3** 时间推进 + **I4** 训练
- "我想买间小铺子开药材店" / "我要做生意" → **I7**（资产 / 业务经营）
- "我向艾莉安娜求婚" / "我们结婚吧" → **I6.4** + **I8**（婚姻 → 家族开启）
- "我们什么时候有孩子" / "孩子现在几岁了" → **I8**（怀孕 / 孩子成长追踪）
- "快进半年" / "跳到春天" / "等孩子出生" → **I3** 时间推进（按月 / 季 / 年走结算清单）
- "我要建一座要塞" / "我想统治这片土地" → **I3** 长期推进 + **I9**（第三阶段，等 MVP 验证后实现）

## 编码与格式

- `docs/extracted/` 内所有 .htm/.html/.xml/.css/.hhc/.hhk 已批量转 UTF-8
- 6318 个 .htm 中 **5373 个已转 .md**（85% 覆盖率，体积节省 43.8%），路径同名只换后缀
- 转换工具：`tools/htm2md/convert.py`（增量再转：`python tools/htm2md/convert.py <file_or_dir> --batch --overwrite`）
- 已知 schema 见 `docs/extracted/SCHEMA.md`
- 如新增文件出现乱码（多为 GBK/GB2312），需重做编码转换
