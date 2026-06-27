# dnd5r 快查工具（fast query layer）

在已有 frontmatter 上架的一层**派生索引 + 薄 CLI**，把"grep 大文件 + 多次 Read"的查询
压成"一次命令出结构化记录"。当前覆盖：**法术 + 怪物 + 职业/子职 + 种族 + 专长 + 装备**（职业起的均仅 PHB24；跨书 + 装备工具/魔法物品待接入）。

```
tools/
├── build_index.py   构建期：读 docs/extracted frontmatter → 生成索引（用 PyYAML）
├── query.py         查询期：只读索引、只用 stdlib，任何带 Python 的 Agent 可直接调
├── index/
│   ├── spells.json    ← 派生产物，勿手改
│   ├── monsters.json  ← 派生产物，勿手改
│   ├── classes.json   ← 派生产物（职业 + 子职业）
│   ├── races.json     ← 派生产物（种族）
│   ├── feats.json     ← 派生产物（专长，启发式）
│   ├── equipment.json ← 派生产物（武器 + 护甲）
│   └── magic.json     ← 派生产物（魔法物品）
└── README.md        本文件
```

## 用法

```bash
# 法术
python query.py spell 火球术                 # 单条：默认最高优先来源 + 其他版本，带 path:line
python query.py spell --class 牧师 --level 2  # 枚举：职业 + 环阶（-l 0 = 戏法；可叠加 -s 学派）
python query.py spell 火球术 --all --json    # 全部印次 / 机器可读

# 怪物
python query.py monster 巫妖                  # 单条：statblock 摘要（CR/AC/HP/属性/抗免/感官）+ path:line
python query.py monster --cr ">=15" --type 龙 # 枚举：CR(>= <= > < / 精确 / 1-5 区间) + --type + --size + --source
python query.py monster --family              # 枚举时含怪物族首页（默认排除）

# 职业 / 子职业（目前仅 PHB24）
python query.py class                         # 列全部 12 职业（+ 子职数 + path:line）
python query.py class 法师                     # 职业总览 + 子职列表
python query.py subclass --class 战士          # 某职业的子职枚举（带 flavor）
python query.py subclass 战斗大师              # 子职单条（flavor + 所属职业 + path:line）

# 种族 / 专长 / 装备（目前仅 PHB24）
python query.py race                          # 列全部 10 种族；race 提夫林 = 单条
python query.py feat --cat 起源               # 专长按分类枚举（启发式）；feat 神射手 = 单条
python query.py equip 长剑                     # 武器/护甲单条（伤害/AC/词条/价格）
python query.py equip --kind armor            # 列护甲（--kind weapon = 列武器）

# 魔法物品（城主指南2024，331 件）
python query.py magic 雷神之锤                 # 单条（类型/稀有度/调谐 + path:line）
python query.py magic --type 武器 --rarity 传说 # 枚举：类型 + 稀有度（普通/非普通/珍稀/极珍稀/传说/神器）
python query.py magic --attune                # 只看需同调的
```

重建索引（**docs/extracted 的法术/怪物 md 改动后**）：
```bash
python build_index.py                 # 重建全部（spells.json + monsters.json）
python build_index.py --only monsters # 只重建其一
```

## 维护契约（代码 --help 之外、不易漂移的部分）

### 1. 索引 schema（`spell-index-v1`）
`spells.json` = `{_schema, spell_count, source_count, spells:[record]}`。每条 record：

| 字段 | 说明 | 可能为 null |
|---|---|---|
| `name` / `en` | 中 / 英文名 | en 偶缺 |
| `level` | **已归一**：0=戏法，1–9=环阶 | 极少数 |
| `school` `classes[]` `casting_time` `range` `components` `duration` | 法术字段 | **常缺**（仅 PHB24/部分书给全；塔莎/PHB14 只有 school/classes）|
| `concentration` `ritual` | 由 duration 含「专注」/ casting_time 含「仪式」**派生** | 否 |
| `source` | **从路径推导**的来源书（frontmatter 的 source 不可信）| 否 |
| `priority` | 0=2024核心 1=2014核心 2=扩展 3=设定 5=第三方/UA/模组 | 否 |
| `path` `line` | 正文 md 路径 + `## 中文 ｜ English` 标题行号（供引用/读全文）| line 极少缺 |

字段常缺是**数据本身**就缺，不是 bug。缺字段时 query 不显示该行；要全文走 `path:line` 读原 md。

### 1b. 怪物 schema（`monster-index-v1`）
`monsters.json` = `{_schema, monster_count, family_count, source_count, monsters:[record]}`。两种 `kind`：
- `kind:"monster"`：`name/en/size/creature_type/alignment/cr/cr_num/xp/pb/ac/hp/hp_dice/speed{}/abilities{}/saves{}/skills{}/damage_resist[]/damage_immune[]/damage_vuln[]/condition_immune[]/senses{}/languages[]/family/source/edition/priority/path/line`。`cr_num` 是 cr 浮点（`1/4`→0.25）供范围筛选。
- `kind:"family"`（族首页，无 statblock）：`name/en/subtitle/members[]/habitat/source/path/line`。枚举默认排除，`--family` 含入。
- 龙的 `creature_type` 是 **龙类**（`--type 龙` 子串匹配可命中）；正文标题是 H1 `# 中文 English`（怪物用空格，非法术的 ｜）。

### 1c. 职业/子职 schema（`class-index-v1`）
`classes.json` = `{_schema, class_count, subclass_count, source_count, entries:[record]}`。两种 `kind`：
- `kind:"class"`：`name/en/hit_die(best-effort，常 null)/subclasses[名]/source/edition/priority/path/line`。
- `kind:"subclass"`：`name/en/class(所属职业)/flavor(正文首句)/source/edition/priority/path/line`。
- **无结构化 frontmatter**：职业/子职文件全是 `type:document`，索引靠**目录结构 + 文件名 + 正文**提取（name/en/category 取 frontmatter，flavor 取 H1 后首段，命中骰/特性走正文）。这是"目录档"——枚举 + 指针，详情读 `path:line`。
- 过滤：目录内含 `法术/选项/列表/扩展` 的文件（`<职业>法术列表`/`超魔法选项`/`魔能祈唤选项`）非子职，排除。

### 1d. 种族/专长/装备 schema
- `races.json`(`race-index-v1`)：`kind:"race"`，`name/en/flavor/source/edition/priority/path/line`。一文件一种族（同子职模式）。
- `feats.json`(`feat-index-v1`)：`kind:"feat"`，`name/en/category(起源/通用/战斗风格/传奇恩惠/种族/龙系/扩展)/source/path/line`。**启发式解析**（98 条）。PHB24（前 4 类）以**分类词**为 marker，名字 = 同行前缀（剥分类词）+ marker 上方非空行（处理「大厨\nChef」拆行、「幸运 Lucky 起源专长…」内联）。跨书 2014（种族/龙系/扩展，`CROSS_FEAT_FILES`）用 `_feat_name_2014` 检测"中文 English"裸/粗体名行（去 Legacy 标、排除句子和"专长"结尾标题）。起源 10/10 全；少数跨书 en 截断；长尾按 path:line 核对。
- `equipment.json`(`equipment-index-v1`)：`kind:"weapon"`(name/en/damage/properties/mastery/weight/cost) 或 `"armor"`(name/en/ac/strength/stealth/weight/cost) + category/source/path/line。解析 `装备/武器.md`、`护甲.md` 的表格行。仅 PHB24 武器+护甲；冒险装备(双列表格)/工具未含。
- `magic.json`(`magic-index-v1`)：`kind:"magic"`，`name/en/item_type(武器/护甲/戒指/药水/卷轴/法杖/魔杖/权杖/奇物)/rarity/attunement(bool)/meta/source/path/line`。解析 `城主指南2024/7.宝藏/魔法物品详述/<类型>/<稀有度>.md` 里的 `##### 名 En` (H5) + 紧跟的 `*类型，稀有度（需同调）*` 元数据行。331 件。

### 2. 已知归一化坑（build_index.py 处理，扩展时照抄思路）
- **戏法 level 不一致**：PHB24 `level:0`，PHB14/珊娜萨 `level:-1 + level_name:戏法` → 统一 0。
- **source 字段不可信**：塔莎/PHB14 都填 `source:法术详述` → 一律从路径首段推导。
- **SCHEMA.md 排除**：它含各 type 示例，不是真数据（法术 + 怪物都排除）。
- **怪物 CR 回填**：巫妖/远古龙等的源 statblock 被 htm2md 截断、frontmatter 丢了 cr → 从 `5E万兽大全.html` 的 TR tags 按名回填（44 条）。

### 3. 覆盖率 caveat（不许静默漏）
- 当前 **1179 条 / 22 书**。`build_index.py` 末尾对账 `5E万法大全.html`，疑似漏收数会打印；
  目前 ~8 条，**全是中英译名差异的假阳性**（master 与 collection 译名偶有出入）。数量级才是信号——
  若某次重建后漏收数突然变大，说明真漏了书，去查。
- **不索引散文**：5237 个 `type:document`（规则正文/模组剧情）永远走 grep/read，不进索引。
- 怪物 **738 + 85 族首页 / 28 书**。已知洞（构建报告会打印）：~26 个怪物回填后仍无 CR（多为模组/第三方）；**18 个塞洛斯生物图鉴文件 frontmatter 被源转换损坏**（正文吞进 frontmatter）被跳过 → 这些按名查不到，需修 htm2md 重转。
- 职业/子职 **14 职业 + 119 子职**（PHB24 + 塔莎/珊娜萨追加 + 奇械师 + 铳士）。跨书职业用 `CROSS_CLASSES` 注册表（noise 多的源显式列子职）；追加子职 auto-scan `<职业>（TCE）`/角色选项目录、attach 到现有职业。**待接入**：PHB14 经典子职（单文件多子职、H2 难区分）、剑湾/费资本变体子职。
- 种族 **19**（PHB24 + 剑湾 + 费资本龙裔，`CROSS_RACE_SOURCES`）/ 装备 **38武器+13护甲**（仅 PHB24）/ 专长 **98**（PHB24 + 塔莎/珊娜萨/费资本，跨书 2014 用 `_feat_name_2014` 结构化检测，`CROSS_FEAT_FILES`）/ 魔法物品 **331**（城主指南2024）。待接入：设定书单文件多种族（艾伯伦/星界）、PHB14 经典子职/种族、装备冒险装备/工具、第三方专长。

### 5. 枚举默认只列官方书（防第三方/UA 淹没）
`spell`/`monster` 的**枚举**（带 `--class`/`--level`/`--cr`/`--type` 等过滤、无具体名字）默认排除第三方/UA/模组（`priority>=5`），只列官方 WotC 书，并提示「已隐藏 N 条」。`--all` 看全部、`--source <书>` 指定某书。**单条名字查询不受影响**——`spell <名>`/`monster <名>` 仍能命中任何书（含第三方）。这是「2024 优先」在枚举上的延伸（单查折叠到最高优先来源，枚举默认官方全集）。

### 6. 术语别名（query.py `ALIASES`）
资料库译名与社区习惯不一致时，怪物查询自动归一并提示。已收：哥布林→地精(Goblin)、鹰身女妖→鸟妖(Harpy)、豺狼人→鬣狗人(Gnoll)。substring 生效（"哥布林老大"→"地精老大"）。新增别名直接往 `ALIASES` 字典加。Orc/Drow 等在 MM2025 无通用 statblock 的不收（无目标）。

### 4. 🛑 stdlib-only 护栏（破坏即失去可移植性）
`query.py` **只准用** `json/argparse/sys/pathlib` 等标准库——目标是任何自带 Python 的 AI Agent
都能 `python query.py ...` 零安装调用。需要 YAML 等第三方库的脏活**只能放 build_index.py**（构建期）。
索引经 `Path(__file__)` 自定位，整个 `tools/` 拷到别处即可用。
