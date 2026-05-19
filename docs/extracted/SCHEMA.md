# DND 5R 资料 HTML→MD 转换 Schema 定义

本文档定义 `docs/extracted/` 下各类内容的 frontmatter schema 与转换约定。
基于阶段 1（schema 采样）9 个代表性样本提炼。

---

## 1. 阶段 1 采样体积对比

| 类型 | 样本文件 | HTM | MD | 差异 |
|------|----------|-----|-----|------|
| 怪物（2014） | DNDBeyond/怪物纲要1/骇异巫妖 | 5217 | 5129 | -1.7% |
| 怪物（2024） | 怪物图鉴2025/类人/角斗士 | 4285 | 2882 | **-32.7%** |
| 法术 | 玩家手册2024/法术详述/0环 | 28608 | 12874 | -55.0% ⚠️ |
| 装备/武器 | 玩家手册2024/装备/武器 | 9026 | 11741 | **+30.1%** |
| 职业 | 玩家手册2024/角色职业/战士/战士 | 10506 | 9929 | -5.5% |
| 子职业 | 玩家手册2024/角色职业/战士/勇士 | 2285 | 2118 | -7.3% |
| 种族 | 玩家手册2024/角色起源/种族/精灵 | 5096 | 5189 | +1.8% |
| 专长集合 | 玩家手册2024/专长/起源专长 | 7253 | 6253 | -13.8% |
| 背景 | 玩家手册2024/角色起源/背景/水手 | 787 | 868 | +10.3% |
| 规则 | 玩家手册2024/进行游戏/动作 | 5775 | 4534 | -21.5% |

⚠️ 0 环数据失真：仅完整转换 5/34 戏法，frontmatter 含全索引。预估全转后约 30000~35000 字节（仍持平或略省）。

**结论**：体积节省**因类型而异**：
- 2024 版（stat-block.css 嵌套表格）→ 节省显著（-30%+）
- 2014 版（简单 P+BR 结构）→ 几乎持平
- 短文档 → frontmatter 成本占比高，反而膨胀
- 武器纯表格 → frontmatter 索引膨胀但获得结构化查询能力

**核心价值不在体积**，在于：① 检索召回（空格/标点规范化）② 结构化查询能力 ③ LLM 解析体验。

### 阶段 2 怪物批量验证（怪物图鉴2025/类人，9 个 2024 怪物）

| 怪物 | HTM | MD | 节省 |
|------|-----|----|------|
| 角斗士 | 4285 | 2882 | -32.7% |
| 平民 | 3962 | 2432 | -38.6% |
| 警卫总（族首页）| 1243 | 1055 | -15.1% |
| 警卫 | 2366 | 1307 | -44.8% |
| 警卫队长 | 2676 | 1584 | -40.8% |
| 刺客 | 4649 | 3188 | -31.4% |
| 德鲁伊 | 4425 | 2964 | -33.0% |
| 大法师 | 4101 | 2978 | -27.4% |
| 邪教教宗 | 3646 | 2543 | -30.3% |
| **合计** | **31353** | **20933** | **-33.2%** |

**结论**：**2024 版怪物 statblock 转 MD 收益稳定**——批量平均节省 33%，每个个体在 27~45% 区间。Schema 跨样本稳定，无需大调整。

---

## 2. 文件路径与命名约定

- **同目录共存** `.htm` 和 `.md`：发现于试点阶段（决策 2 — 保留 HTML 作 fallback）
- **文件名同名**，仅扩展名不同：`骇异巫妖.htm` ↔ `骇异巫妖.md`
- **图片引用保留原 HTML 相对路径**：避免重新映射 `.files/*.jpg` 等
- 单文件多实体（如 0 环法术、武器、专长集合）保留原文件结构，**不拆分**

---

## 3. 通用 frontmatter 字段

所有类型必含：
```yaml
type: <见下方分类>
source: <资料书名>      # 如 玩家手册2024、怪物图鉴2025、模组/盐沼幽魂
edition: 2014 | 2024    # 2014 = 玩家手册原版/怪物图鉴等；2024 = 玩家手册2024/怪物图鉴2025
```

`type` 取值（9 种已验证 + 后续待扩）：
- `monster`（怪物）
- `spell` / `spell_collection`（单法术 / 多法术集合）
- `weapon_collection` / `armor` / `item` / `magic_item`（装备/物品）
- `class`（职业）
- `subclass`（子职业）
- `race`（种族）
- `feat` / `feat_collection`（单专长 / 多专长集合）
- `background`（背景）
- `rule`（规则文档）
- `adventure_scene`（模组剧情，待阶段 3 验证）

---

## 4. 各类型 Schema

### 4.1 怪物 monster

样本：[骇异巫妖.md](DNDBeyond/怪物纲要1/骇异巫妖.md)（2014）、[角斗士.md](怪物图鉴2025/类人/角斗士.md)（2024），以及阶段 2 的 8 个类人怪物。

```yaml
type: monster
name: <中文>
en: <English>
subtitle: <2024：class=sum 小标题，2014 无>
family: <2024：所属怪物族，如"警卫" / "邪教徒" / "魔法师"。独立 .htm 无族的可省略>
size: <type or [type1, type2]>     # 2024 可多体型如 [中型, 小型]
type: <类人/兽/亡灵/...>
type_subtag: <2024：括号子类，如"法师"（大法师的 (法师)）。少见>
alignment: <阵营>                    # 2024 简化为"中立"等；2014 含"普遍"前缀
habitat: <2024 only：栖息地>
treasure: <2024 only：宝藏类型数组>
ac: <int>
ac_note: <如 "天生护甲" / "含法师护甲"（带预施法术时）>
initiative_bonus: <2024 only：先攻调整 int>
initiative_value: <2024 only：先攻值 int>
hp: <int>
hp_dice: <如 22d8+66>
speed:
  walk: <int>
  fly: <int>
  swim: <int>
  climb: <int>
  burrow: <int>
  hover: <bool>
abilities: { str, dex, con, int, wis, cha }
saves: { <属性>: <加值> }           # 仅列出有熟练的属性
skills: { <技能名>: <加值> }
equipment: <2024 only：装备列表>
damage_resist: [<伤害类型>]
damage_immune: [<伤害类型>]
condition_immune: [<状态>]
condition_immune_conditional:       # 有条件的免疫，如大法师"魅惑（心灵屏障 Mind Blank 期间）"
  - { condition: <状态>, when: <条件说明> }
senses:
  truesight: <int>
  darkvision: <int>
  blindsight: <int>
  tremorsense: <int>
  passive_perception: <int>
languages: [<语言>]
cr: <数字或分数如 1/4>
xp: <int>
pb: <int>
legendary_resistance: <如 4/Day>
spell_save_dc: <int>
spellcasting_ability: <属性名>
```

**阶段 2 新发现的 schema 补充**：
- `family` — 子目录变体的族归属，独立 .htm 不需要
- `type_subtag` — 2024 部分高阶施法者有括号子类标注
- `ac_note` 扩展用法 — 标注 AC 含预施法术加值（如"含法师护甲"）
- `condition_immune_conditional` — 大法师等怪物的条件性免疫
- 攻击描述格式：使用 `*近战攻击检定*：+X，触及Y尺。*命中*：N（dice）伤害类型` 格式

**Body 结构**：
1. H1 标题：`名称 English`
2. 副标题斜体（如有）
3. 描述段落
4. d6/d8 风味表（2024 怪物常有，用 MD 表格）
5. ## 数据栏（AC/HP/速度/属性表/技能/感官/语言/CR）
6. ## 特性 Traits
7. ## 动作 Actions
8. ## 附赠动作 Bonus Actions（可选）
9. ## 反应 Reactions
10. ## 传奇动作 Legendary Actions（可选）

**重要差异**：
- 2014 攻击格式：`近战武器攻击：命中+9，触及10尺，单一生物。伤害：25(6d6+4)...`
- 2024 攻击格式：`近战或远程攻击检定：+7，触及5尺...命中：11(2d6+4)...`
- 2024 引入"豁免检定"类动作：`力量豁免检定：DC15...`（无攻击检定步骤）

---

### 4.1b 怪物族 monster_family（阶段 2 新增）

样本：[警卫总.md](怪物图鉴2025/类人/警卫/警卫总.md)

怪物图鉴 2025 的子目录中，"XX总.htm" 文件是**族首页**——无 statblock，只有族级元数据、整体描述、族风味块。族成员（如 `警卫.htm`、`警卫队长.htm`）单独是 `monster` 类型，frontmatter 用 `family` 字段指向族名。

```yaml
type: monster_family
name: <族中文>
en: <族 English>
subtitle: <族副标题>
habitat: <栖息地>
treasure: <宝藏类型数组>
source, edition
members: [<成员中文名>]
```

**Body**：族描述 + 族风味引用块（如有） + ## 成员（成员列表带相对路径链接）。

**例外**：少数变体怪物文件（如 `邪教徒/邪教教宗.htm`）会在 H2 前内嵌一段次族描述（"邪教成员 Cult Members"）。这种情况在变体 .md 的 body 开头用 `> **xxx**：描述` blockquote 保留，不单独转为 monster_family。

---

### 4.2 法术集合 spell_collection（one-file-many）

样本：[0环.md](玩家手册2024/法术详述/0环.md)

法术按**环位**组织，单个 HTM 文件包含整环所有法术。**不拆分**。

```yaml
type: spell_collection
level: <0-9>
level_name: <戏法 | 1 环 | ...>
source: <书名>
edition: 2024 | 2014
total_count: <该环法术总数>
spells:
  - { name, en, school, classes: [], casting_time, range, components: [], duration, save, attack, damage, scales, body_complete }
```

- `school`：塑能 / 防护 / 死灵 / 幻术 / 变化 / 咒法 / 惑控 / 预言
- `range`：数字（尺）/ "自身" / "触碰"
- `save`：豁免属性，如 "敏捷"（无豁免则省略）
- `attack`：近战法术 / 远程法术（无攻击则省略）
- `body_complete`：bool，标记 body 是否有完整描述（用于增量补完）

**Body 结构**：每法术一段 `## 法术名 ｜ English`，下列紧凑字段 + 描述：
- **学派**：xxx 戏法/法术
- **职业**、**施法时间**、**施法距离**、**法术成分**、**持续时间**
- 描述段落
- **戏法强化** / **高环施法**（如有）
- 子选项（如魔法伎俩的 6 种效应）用 unordered list

---

### 4.3 装备/武器集合 weapon_collection（纯表格）

样本：[武器.md](玩家手册2024/装备/武器.md)

```yaml
type: weapon_collection
count: <int>
weapons:
  - { name, en, category, damage, properties: [], range, versatile, ammo, mastery, weight_lb, price }
```

- `category`：简易近战 / 简易远程 / 军用近战 / 军用远程
- `damage`：`1d8 挥砍` 格式（伤害骰 + 伤害类型）
- `properties`：词条数组
- `versatile`：双手骰，如 `1d10`
- `range`：投掷/弹药射程，如 `20/60` 或 `80/320`
- `ammo`：弹药类型
- `mastery`：精通词条

**Body**：4 个分类 MD 表格（简易近战/简易远程/军用近战/军用远程），列：名称、伤害、词条、精通、重量、价格。

`armor`、`magic_item` 等类似结构，待阶段 3 扩展。

---

### 4.4 职业 class

样本：[战士.md](玩家手册2024/角色职业/战士/战士.md)

```yaml
type: class
name, en, subtitle
core:
  primary_ability: []
  hit_die: d6 | d8 | d10 | d12
  saves: []
  skill_choices: { count, options: [] }
  weapons: []
  armor: []
  starting_equipment:
    - { id: A | B | C, items: [], gold: int }
multiclass:
  shared: []
  also: <说明>
subclasses: []
subclass_level: <int>  # 几级选子职
features_by_level:
  - { level, pb, features: [], <职业特有列如 second_wind_uses, weapon_mastery, ki_points...> }
```

**Body**：
1. H1 + 副标题 + 描述
2. ## 核心特质（表格）
3. ## 成为一名 XX（1 级 / 兼职）
4. ## XX 特性表（20 行等级表）
5. ## 职业特性详述（每级 ### 标题）

---

### 4.5 子职业 subclass

样本：[勇士.md](玩家手册2024/角色职业/战士/勇士.md)

```yaml
type: subclass
name, en, subtitle
parent_class: <如 战士>
features:
  - { level, name, en }
```

**Body**：H1 + 描述 + 各级特性 ##。

---

### 4.6 种族 race

样本：[精灵.md](玩家手册2024/角色起源/种族/精灵.md)

```yaml
type: race
name, en
creature_type: <如 类人>
size: <中型 | 小型>
size_note: <尺寸说明>
speed: <int>
lifespan: <int>          # 寿命（年）
lineages: []             # 血系/亚种列表
traits:
  - { name, en, value?, effect? }
lineage_table:           # 如有血系细分（精灵、龙裔等）
  - { lineage, en, level_1, level_3, level_5 }
spellcasting_ability_choice: []  # 如适用
```

**Body**：H1 + 描述 + ## 血系简介（如有）+ ## 特质详述。

---

### 4.7 专长集合 feat_collection（one-file-many）

样本：[起源专长.md](玩家手册2024/专长/起源专长.md)

```yaml
type: feat_collection
category: 起源专长 | 通用专长 | 战斗风格专长 | 传奇恩惠专长
count: <int>
feats:
  - { name, en, repeatable, repeat_constraint? }
```

**Body**：每专长 H2 + *分类* 斜体行 + 描述 + 增益 unordered list + 复选说明。

---

### 4.8 背景 background

样本：[水手.md](玩家手册2024/角色起源/背景/水手.md)

```yaml
type: background
name, en
ability_scores: []       # 2024：3 项属性
feat: <绑定专长>          # 2024：每个背景固定一个专长
skill_proficiencies: []
tool_proficiencies: []
languages: []            # 2014 有，2024 删除
starting_equipment:
  - { id, items: [], gold }
```

**Body**：紧凑字段列表 + 描述段。

---

### 4.9 规则 rule

样本：[动作.md](玩家手册2024/进行游戏/动作.md)

```yaml
type: rule
name, en
chapter: <章节名>
actions: []              # 可选：如果规则文档包含动作/状态/术语列表
states: []               # 可选
terms: []                # 可选
```

**Body**：自由叙述结构，按原文 H2/H3 层级。引用框（"你的角色会做什么？"等）用 MD blockquote `>`。

---

## 5. 通用转换约定

### 文字规范化
- HTML 中 `DC17` 和 `DC 17` 混用 → MD 统一为 `DC 17`（DC 与数字之间空格）
- HTML 中 `<BR>` 在中文间断行 → MD 重排为段落
- HTML 中 `<U>术语</U>` 词汇高亮 → MD 不保留（避免噪音），词汇本身保留
- HTML 中 `&times;` `×3` 等 → MD 统一用 `×N` 表示倍数/数量

### 表格
- HTML `<TABLE>` → MD pipe table
- 跨列合并（colspan）→ 拆为单独段落或用分类标题
- 行斑马色（bgColor）→ MD 不支持，直接丢弃

### 列表
- HTML `<UL><LI>` → MD `- `
- HTML `<BLOCKQUOTE><STRONG>名称。</STRONG>描述<BR><STRONG>名称。</STRONG>描述` 多子选项块 → MD `- **名称。** 描述` 列表

### 链接/引用
- HTML 内部 `id` 锚点 → MD 暂不处理（grep 友好优先）
- HTML 跨文件链接 → MD 文本保留，链接丢弃

---

## 6. 已发现的开放问题（待阶段 2/3 决策）

1. **怪物 statblock 在模组 .htm 中内联**：模组目录下许多文件包含完整剧情 + 内嵌小怪 statblock。是否拆出独立怪物 .md？或保留在剧情文件中？
2. **多版本同名怪物**（如"巫妖"在 2014 怪物图鉴和 2025 图鉴都有）：路径不同所以文件不冲突，但 frontmatter 的 `name` 字段重复，结构化查询时需用 `name + edition` 做唯一键
3. **跨文件引用**：法术正文常说"见第五章"、"详见 XX"——MD 中是否需要补全实际页面链接？目前不做。
4. **图片** `.files/*.jpg` `.files/themedata.thmx`：MD 中如何引用？目前不引用，保留 HTML 中的图片仅用 HTML 查看
5. **2014 vs 2024 怪物 schema 是否合并**：目前用 `edition` 字段区分。2024 新字段（subtitle/habitat/treasure/initiative_value/equipment）在 2014 中为 null。可接受。
6. **法术等数据的"是否拆分单文件"**：当前决定保留一对多。若未来需要"按法术名直接查文件"，可生成 `.spell_index.md` 索引或后续脚本拆分

---

## 7. 阶段 1 完成清单

- [x] 9 类样本各 1 个（其中怪物 2 个：2014+2024）
- [x] SCHEMA.md 汇总
- [x] 体积对比数据

## 8. 阶段 2 完成清单（已完成）

- [x] 怪物图鉴2025/类人 子目录代表性试点（8 个新怪物 + 1 个族首页）
- [x] 验证 2024 怪物 schema 跨样本稳定性 — **稳定**，新增 4 个字段（family/type_subtag/ac_note 扩展/condition_immune_conditional）
- [x] 验证 `monster_family` 新类型（族首页 schema）
- [x] 批量体积数据：**节省稳定在 -33%**

## 9. 阶段 3 进度（脚本批量转换）

- [x] 写 Python 转换脚本 `tools/htm2md/convert.py`（BeautifulSoup + lxml + PyYAML）
  - 支持类型：`monster_2024` / `monster_family`
  - schema 字段：完整覆盖 §4.1 定义
  - 文本规范化：DC17→DC 17，中英文边界空格化，markdown bold/CJK 边界空格
- [x] 脚本输出 vs 9 个手转 MD diff 校验 — **通过**（schema 字段、attack 格式、风味表 layout 一致）
- [x] 跑批：`怪物图鉴2025/类人/` 全 58 个怪物（含 14 个族首页 + 44 个变体 + 4 个独立怪物）
  - 累计体积：169059 → 113693 字节（**-32.7%**），完全符合阶段 2 单样本预估
- [x] 异常校对：抽 4 个 corner case（族首页、施法者、conditional 免疫、内嵌族描述），均无 schema-level 异常

### 已知小毛刺（不阻塞，后续优化）

1. 风味表标题偶尔有尾空格 `**邪教大业 **`（promote_flavor_table_title 正则不匹配）
2. 大法师等怪物长法术段落渲染保留原 HTM 换行（`**至圣援护**...解除魔法 Dispel \nMagic`）
3. `equipment: [盾牌, 矛（3）, 镶钉皮甲]` 保留中文括号；手转用了 `×3` 写法。脚本写法更"忠实于原文"，无需统一。

## 10. 阶段 4 进度

- [x] **4-1：怪物图鉴2025 全量** — 600 个 .htm，589 个怪物 .md（+11 SKIP 非怪物文档）
  - 累计体积：2.01 MB → 1.33 MB（**-33.9%**）
  - 0 个 ERROR
- [x] 扫描发现：只有怪物图鉴2025 + 空白页模板 用 stat-block.css 风格；其他资料书都是 2014 风格
- [x] **4-2：法术解析器（spell_collection）** — 玩家手册2024/法术详述/ 10 个文件，391 个法术
  - 累计体积：440 KB → 261 KB（**-40.8%**）
  - 关键发现：召唤系法术内嵌怪物 statblock，会让 detect_type 误判。修复：spell_collection 检测优先级高于 monster_2024
  - schema 补充：每个 spell 加 `school_label` 字段保留原文格式（"塑能 戏法" / "三环 塑能"）

## 11. 阶段 5 待办

- [ ] 写新解析器：装备（`weapon_collection` / `armor` / `magic_item`）
- [ ] 写新解析器：职业 / 子职业 / 种族 / 专长 / 背景
- [ ] **2014 怪物解析器** — 大头工作（~2500 个怪物分布于：怪物图鉴 261 / 多元宇宙的怪物 284 / 瓦罗怪物指南 278 / 魔邓肯的众敌卷册 171 / DNDBeyond 89 / 模组内嵌等）
  - 注意：怪物图鉴/等是 MS Word 导出（mso-* 嵌套属性），结构复杂
  - DNDBeyond/ 是 WinCHM 导出，结构相对简单
  - 建议先写 DNDBeyond 风格 parser，再写 Word 风格 parser
- [ ] 模组（最后）— 剧情类，结构最不规范

## 12. 阶段 4-3 完成：通用 document 解析器

- [x] 写 `parse_document` / `render_document` — 通用 HTML→MD 转换
  - 支持：H1-H6 标题、段落、表格、列表、blockquote
  - 表格：colspan 子表头作为单行合并 cell（保持单一大表）
  - frontmatter：`{type: document, name, en?, category, source, edition}` 用 block-style YAML
- [x] detect_type 添加 fallback：≥100 字符 body 文本走 document
- [x] 关键 bug 修复：
  - 战士/勇士因有 `<p class=sum>` 副标题被误判为 monster_family → monster_family 改为要求**同时**有 `p.sum` AND `div.HT`
- [x] 批量跑 `玩家手册2024/` 全本：206 / 218 转换（94.5%），节省 -24.4%
  - 类型分布：100 document（背景/专长/职业/规则）+ 10 spell_collection
  - 12 SKIP 是章节导航页（< 400 字节）

### 已知 document fallback 局限

通用 parser 无法识别**伪标题**（`<b>` / `<i>` 而非真 `<h3>`）。专长 / 职业 / 种族文档质量打折扣：
- 装备 / 规则文档：质量很好
- 专长 / 职业 / 种族 / 子职业：内容保留但缺乏视觉层次

后续可写专用 parser 改善（详见阶段 5）。

## 13. 累计成果

| 资料书 | HTM | MD | 节省 |
|--------|-----|-----|------|
| 怪物图鉴 2025 全本 | 600 | 589 | -33.9% |
| 玩家手册 2024 全本 | 218 | 206 | -24.4% |
| **累计** | **818** | **795** | **~-30% 平均** |

脚本支持类型：`monster_2024` / `monster_family` / `spell_collection` / `document`（fallback）。

## 14. 阶段 5 完成

- [x] **5-1：DNDBeyond/WinCHM 风格 2014 怪物 parser**
  - 检测：`<p>` 同时含 AC：/HP：/挑战等级（容忍空格 `AC ：`）
  - schema 与 2024 兼容（共用 frontmatter 字段、`edition: 2014`）
  - 验证：DNDBeyond/怪物纲要1 全 10 个文件，7 个 monster + 3 个非怪物（document）
- [x] **5-2：全量批量转换 `docs/extracted/`**
  - **5373 / 6318 .htm 文件转换成功（85%）**
  - **节省 43.8%**（35.19 MB → 19.79 MB）
  - 0 ERROR，125 SKIP（短文档/导言）
- [x] 意外发现：MS Word 风格的 2014 怪物用 document fallback 已**够用**——文本完整保留，每行一字段，grep 友好。无需写专用 parser（节省大量工时）。

### 最终类型分布

| 类型 | 文件数 | 占比 |
|------|--------|------|
| document（fallback）| 4479 | 83% |
| monster | 743 | 14% |
| monster_family | 85 | 1.6% |
| spell_collection | 29 | 0.5% |

## 15. 累计总成果（阶段 1 → 阶段 5）

- **转换文件**：5373 个 .md（覆盖 35 本资料书）
- **体积节省**：35.19 MB → 19.79 MB（**-43.8%**）
- **脚本支持类型**：4 种专用 parser + 通用 fallback
- **总工时**：约 5 阶段、20 个任务
- **关键技术债**：MS Word 风格怪物 statblock 用 document fallback，**丢失结构化字段**（CR/HP/AC 等），但**文本完整可检索**

## 16. 后续可选优化（非紧急）

- [ ] 为 MS Word 风格 2014 怪物写专用 parser，恢复 frontmatter 结构化字段（影响约 2500 个怪物，但 grep 已经够用）
- [ ] 写专用 parser 改善 fallback 文档质量：feat_collection（专长）、class（职业）、race（种族）— 各 1~2 小时
- [ ] 模组剧情结构化（拆分内嵌 statblock）

## 17. 已停做的工作（明确不做）

- 阶段 2 原计划"10 只代表怪物"实际只做 8 只（+ 1 族首页 = 9 个文件）。骑士、海盗船长的 schema 已被警卫队长、刺客覆盖，无新增价值。
- MS Word 风格 2014 怪物专用 parser：document fallback 质量已足够 grep 检索，结构化字段的价值不抵开发成本。

## 10. 已停做的工作（明确不做）

- 阶段 2 原计划"10 只代表怪物"实际只做 8 只（+ 1 族首页 = 9 个文件）。骑士、海盗船长的 schema 已被警卫队长、刺客覆盖，无新增价值。
- 模组内嵌 statblock 拆分：开放问题 1 待阶段 3 后决策。
