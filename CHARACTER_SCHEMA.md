# 角色数据 Canonical Schema（v2 重构 · 阶段1 定稿草案）

> 状态：**草案，待审**。这是 dnd5r 数据层重构的地基文档。
> 背景：见数据层重构调查（panel/viewer/跑团/沙盒 的重复问题）。阶段0 已验证「panel 可深投影富 schema 替代手抄镜像」（22/22 派生字段一致 + 真实渲染通过）。

## 0. 一句话原则

> **每个角色的结构化数据 = 一份 canonical JSON（唯一真源）；四个渲染面都读它；散文 `.md` 只留 JSON 装不下的东西（背景/已揭示/关系/秘密），一个数值都不写。**

这消灭了旧架构的「双写硬约束」——同一个 HP/AC/属性不再被手抄进 `character-v1` 镜像 + `.md` 数值表 + 角色卡 JSON 三处。

## 1. 谁读这份 canonical（四个消费者）

| 消费者 | 宿主 | 读取方式 | 怎么用 canonical |
|---|---|---|---|
| `ui/panel.html` | Fathom 桌面 | Fathom 投影 `characters/<X>.json` | **深投影**（标准 5e 公式算 mod/豁免/AC/命中/DC）→ HUD + 点击弹窗 |
| `templates/character-sheet.html` | 任意浏览器 | build-sheet 注入内嵌 JSON | **原生渲染器**——canonical 本就脱胎于它的 `DEFAULT_CHAR` |
| `viewer/`（私用，不发布） | 本地 node | 改后读 `characters/<X>.json` | 结构化精确读，**替代**现在从 `.md` 正则「尽力抽」HP/AC |
| `templates/build-sheet.py` | CLI | `characters/<X>.json` | 注入模板产出 portable 电子卡 HTML |

> 关键：canonical = **角色卡富 schema（`DEFAULT_CHAR`）的超集**。所以 character-sheet.html / build-sheet.py **几乎不用改**；panel 加一道深投影；viewer 改数据源。

## 2. 文件位置

```
# 结构化层（唯一真源，Fathom 监听并投影）
.fathom-panels/dnd5r/campaigns/<战役名>/characters/<角色名>.json   ← 玩家角色 canonical
.fathom-panels/dnd5r/campaigns/<战役名>/companions/<名>.json        ← 同行（char 子集，见 §6）
.fathom-panels/dnd5r/campaigns/<战役名>/npcs/<名>.json              ← NPC（社交 schema，见 §6）

# 散文层（workspace 根，AI 叙事恢复读；只留散文，无数值）
campaigns/<战役名>/players/<角色名>.md                              ← 见 §5 散文契约
```

> 旧的 `_schema:"character-v1"`（手抄精简快照）**废弃**——panel 改为深投影 canonical。

## 3. Canonical 角色 Schema（完整字段）

以 `templates/character-sheet.html` 的 `DEFAULT_CHAR` 为底，🆕 标记的是为统一四个消费者而**新增的超集字段**（阶段0 投影时发现 panel/镜像需要、富 schema 缺）。

```jsonc
{
  "_schema": "character-canonical-v1",          // 🆕 版本标识

  "meta": {
    "name": "白凰",
    "charId": "baihuang-hegu",                  // build-sheet 缺则按 <name>-<time> 生成
    "rev": 3,                                   // build-sheet 每次构建 +1；加载时与 localStorage 缓存比对，文件 rev 更大则以文件定义为准 + 嫁接缓存临场状态（勿手改，靠 build-sheet.py 递增）
    "player": "",                               // 玩家名（空=NPC/陪伴）
    "alignment": "混乱善良",
    "faith": "",
    "xp": 6500,                                 // 数字；HUD 经验条由此 + 等级表派生
    "notes": "",
    "appearance": "",                           // 🆕 外貌散文（弹窗/卡片副标题、viewer 用）
    "classes": [{ "name": "超越者", "subclass": "钢铁之躯", "level": 5 }],
    "race": { "name": "女神后裔", "subrace": "" },
    "background": "私家侦探",
    "inspiration": false,
    "viewIndex": -1                             // 运行时 UI 态（角色卡 tab），可省
  },

  "abilities": {                                // 只存原始值；mod/豁免一律派生（§4）
    "str": { "score": 18, "saveProf": false, "saveBonus": 0 },
    "dex": { "score": 24, "saveProf": false, "saveBonus": 0 },
    "con": { "score": 20, "saveProf": true,  "saveBonus": 0 },
    "int": { "score": 19, "saveProf": false, "saveBonus": 0 },
    "wis": { "score": 18, "saveProf": false, "saveBonus": 0 },
    "cha": { "score": 19, "saveProf": true,  "saveBonus": 0 }
  },

  "combat": {
    "hpMax": 56, "hpCur": 56, "hpTemp": 0, "hdMax": 5, "hdCur": 5,
    "acBase": 22, "acBonus": 0,                 // AC 基础；持盾 AC 派生（§4）
    "speed": 30, "size": "中型", "initBonus": 0,
    "deathSaves": { "success": [false,false,false], "fail": [false,false,false] },
    "resistance": "", "immunity": "", "advantage": "",
    "senses": "",                              // 🆕 黑暗视觉 60尺 等（弹窗"战斗速查"、viewer 用）
    "statusEffects": [], "concentration": null, "buffs": [],
    "critMin": 20                              // 🆕 全局重击门槛：斗士改进重击=19（15级=18）；缺省=20。单把武器可用 attacks[].critMin 覆盖
  },

  "skills": {                                  // 只列有熟练度的；bonus 派生（§4）
    "investigation": { "prof": "expertise", "bonus": 0 },   // prof: none|prof|expertise
    "perception":    { "prof": "prof",      "bonus": 0 },
    "globalBonus": 0, "jackOfAllTrades": false
  },

  "attacks": [                                 // hit/damage 显示值派生（§4）
    { "name": "徒手打击", "ability": "dex", "attackBonus": 1,
      "damage": "2d8", "damageBonus": 11, "damageType": "钝击",
      "properties": "近战恒优势；命中另 +5 光耀；附赠动作可再攻击", "mastery": "", "attuned": false,
      "critMin": 20, "advReroll": false }       // 🆕 critMin=可选覆盖此武器重击门槛；advReroll=精灵之准（优势掷3d20取高，仅敏/智/感/魅攻击）
  ],

  "spellcasting": {                            // 非施法者 castingAbility:"" + slots 全 0
    "castingAbility": "int", "extraDcBonus": 0, "extraAttackBonus": 0,
    "slots": { "1": {"max":4,"used":[false,false,false,false]}, "...": "2-9 同形" },
    "cantrips": [ { "name":"火焰矢","school":"唤法","ct":"1动作","range":"120尺","comp":"V,S","dur":"瞬间","damage":"2d10","desc":"..." } ],
    "spells":   [ { "lvl":1,"name":"法师护甲","prepared":true,"ritual":false,"conc":false,"buff":{...},"desc":"..." } ],
    "spellPoints": { "cur": 0, "max": 0 }
  },

  "classResources": [                          // cur 派生 = max - count(used==true)
    { "key": "superEnergy", "label": "超能量点", "resetType": "shortRest",
      "max": 12, "used": [/*12×bool*/], "desc": "...", "summonSource": "" }   // summonSource 可选
  ],

  "specialRolls": [],                          // 特殊投骰表（d100 法力狂潮等），见 SKILL.md B-10
  "equipment": {
    "armor":  { "name": "", "ac": 0, "dexLimit": null, "weight": 0, "attuned": false, "equipped": false },
    "shield": { "name": "", "ac": 0, "weight": 0, "attuned": false, "equipped": false },  // equipped=true 才计入持盾 AC
    "items":  [ { "name": "匕首", "weight": 1, "qty": 1, "attuned": false, "desc": "", "category": "" } ]  // category 🆕 可选: weapon|armor|tool|consumable|other
  },

  "wealth": {
    "cp": 0, "sp": 0, "ep": 0, "gp": 3500, "pp": 0,
    "property": "",                            // 🆕 房产散文（据点/庄园）
    "goods": ""                                // 🆕 货物/资产散文
  },

  "features": [ { "source": "种族", "name": "英灵之躯", "desc": "..." } ],

  "companions": [ /* char 子集，见 §6 */ ],
  "rollHistory": []
}
```

### 新增字段汇总（🆕）

| 字段 | 类型 | 给谁用 | 为什么加 |
|---|---|---|---|
| `_schema` | string | 全部 | 版本化，迁移可识别 |
| `meta.appearance` | string | 弹窗副标题 / viewer | 旧 v1 镜像有，富 schema 缺 |
| `combat.senses` | string | 弹窗战斗速查 / viewer | 同上（黑暗视觉等） |
| `wealth.property` / `wealth.goods` | string | 弹窗财富 / viewer | 富 schema 只有币值 |
| `equipment.items[].category` | string（可选） | 装备分组渲染 | 让 weapons/armor/tool 分组更准（不填则按 §4 兜底） |

## 4. 派生规则（深投影的全部公式）

> 这些是确定性纯函数，**绝不让 AI 算**。参考实现：阶段0 spike 的 `rich-to-v1.js`（阶段2 内联进 panel.html，并抽成 panel/viewer 共享模块）。

| 派生量 | 公式 |
|---|---|
| 属性调整值 `mod` | `floor((score - 10) / 2)` |
| 熟练加值 `PB` | `ceil(总等级 / 4) + 1`（总等级 = Σ classes[].level） |
| 豁免 | `mod + (saveProf ? PB : 0) + saveBonus` |
| 技能加值 | `mod(ability) + mult*PB + globalBonus + skill.bonus`；`mult`: prof=1 / expertise=2 |
| AC（基础） | `acBase + acBonus` |
| AC（持盾） | `shield.equipped && shield.ac>0 ? 基础 + shield.ac : 基础` |
| 先攻 | `mod(dex) + initBonus` |
| 被动察觉 | `10 + 察觉技能加值` |
| 攻击命中 | `mod(ability) + PB + attackBonus` |
| 攻击伤害（显示） | `"<damage>" + (damageBonus?+号拼) + " " + damageType` |
| 攻击重击判定（投骰时） | 掷骰 ≥ `min(combat.critMin‖20, attacks[].critMin‖20)` → 重击；`advReroll` 时优势掷 3d20 取高；天然20 必中·天然1 必失（属性检定/豁免无自动成败，仅角标） |
| 法术 DC | `8 + PB + mod(castingAbility) + extraDcBonus` |
| 法术攻击 | `PB + mod(castingAbility) + extraAttackBonus` |
| 资源当前值 | `max - count(used == true)` |
| HUD 经验条 | `cur=meta.xp`，`level=总等级`，`next=PHB24_XP表[level]` |

**装备归类兜底**（无 `category` 时，给 panel 弹窗的 weapons/armor/other 分组）：
- weapons ← `attacks[].name`
- armor ← `equipment.armor.name` + `equipment.shield.name`（非空）
- other ← `equipment.items[].name`（带 qty）

## 5. 散文 `.md` 契约（彻底去数值）

`campaigns/<战役名>/players/<角色名>.md` 改为**纯散文**，AI 叙事恢复（G7）时读它拿"软信息"。

**保留**（JSON 装不好、LLM 叙事需要）：
- 背景叙事（DM 视角）、性格、口头禅
- 已揭示信息 / 玩家当前已知（区别于 dm-only 秘密）
- 关系网（与各 NPC 的关系、亲和、已知秘密）
- DM 视角观察、升级计划（`upgradePlan`）、平衡备注（`balance_note`）

**删除**（改由 canonical JSON 唯一承载）：
- HP / AC / 属性 / 豁免 / 熟练加值表
- 技能加值表、攻击表、法术位、职业资源、装备清单数值、财富数值

**允许保留一行指针**（方便人/viewer 跳转）：
> `数值见 .fathom-panels/dnd5r/campaigns/<战役>/characters/<X>.json · 电子卡 <sheet.html 路径>`

> 这样 `.md`（散文）与 JSON（数值）**零重叠** → 双写约束消失。viewer 改读 JSON 拿数值、读 `.md` 只渲染叙事/NPC 段。

## 6. NPC / 同行（canonical 单一真源）

与玩家角色同源精神，但 NPC/同行**是社交/散文为主、几乎无可计算字段** → **不做派生，面板直接渲染 JSON**。各写一份，**无 .md 镜像、无双写**。

### npcs/<X>.json — NPC 公开档案（`_schema: "npc-v1"`，canonical）
- 字段：`name / fullName / aliases[] / basics{race,gender,age,occupation,location} / appearance / background / personality / currentSituation / relationship{stage,affinity,affinityMax,romance,summary,knownSince,lastSeen,lastInteraction} / stageTable[] / knownFacts[] / canAskFor[] / combatAbilities[] / preferences{likes,dislikes} / giftHints[]`
- 🆕 `notes`（string，可选）：放不进上述字段的自由散文（NPC 日常作息、互动史片段等）。
- **唯一真源**：NPC 公开信息全写这里（含 prose 字段）→ 面板弹窗直接渲染。**不再有公开 `npcs/<X>.md`**（旧的并入本 json）。
- 🔒 G4 边界：只写玩家视角公开信息；真实身份 / 动机 / 揭示 DC / 未揭示事实 → 仅 `dm-only/npcs-secrets/<X>.md`。

### companions/<X>.json — 同行 stat block（`_schema: "companion-v1"`，canonical）
- 字段：`name / type / subtype / owner / role / description / combat{hp,ac,speed,init,size,senses} / attacks[{name,hit,damage,uses,type,notes}] / immunities[] / morphForms[] / modules[] / tools[] / tacticalNotes[]`
- hit/damage 已是显示串（无派生）。本就 JSON 单源、无 .md。
- **双重身份**（既是同行又是社交 NPC，如人形伙伴）：`companions/<X>.json`(战斗视图) + `npcs/<X>.json`(社交视图) 两份并存，各自单写、互不镜像。

## 7. 迁移要点（阶段4 执行）

- 旧 `characters/<X>.json`（`character-v1` 镜像）→ 由 canonical 取代；panel 不再读它。
- **多数迁移近乎"搬运"**：`.tmp/<X>-sheet.json` 已是富 schema（≈canonical），补上 §3 的 🆕 字段即可。
- `migrate.py`：读 旧 v1 + 角色卡内嵌 JSON + `.md` 数值表 → 合成 canonical；同时把 `.md` 的数值段剥离。
- **兼容期**：老战役未迁移（仍 `character-v1`）也不崩、可懒迁移——两条派生路径都兼容 v1：
  - **弹窗**：`richToV1` 对 v1 输入幂等原样返回，`renderCharacterModal` 直接渲染。
  - **队伍 HUD**：`hudFromCanonical` 同时认 canonical（`combat.hpCur`）与 v1（`combat.hp.cur`）——v1 从 `combat.hp.cur/ac.base/classSummary` 派生 HP/AC/职业；v1 没有的 live 状态/经验从 session 同名角色并入。**这修复了"读档后未迁移战役 HUD 变空"的回归**（session 重建不带 players[] 时，仍能从 v1 角色 json 派生）。

---

> **已决议**：`equipment.items[].category` 加但可选（不填则按 §4 兜底分组）；schema 命名 — 角色 `character-canonical-v1`、NPC `npc-v1`、同行 `companion-v1`。
