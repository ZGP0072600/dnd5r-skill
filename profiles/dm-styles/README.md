# DM 风格预设

跑团时 AI 的行为参数。三层机制：**系统预设 → 战役引用 → override**。
完整设计见 [STEP1_DESIGN.md §5](../../STEP1_DESIGN.md)。

## 怎么用

战役 README.md frontmatter 里引用：

```yaml
dm_style:
  preset: 粉红恋爱向            # 引用本目录的预设文件
  overrides:                  # 可选，本战役独有的微调
    pc_mercy: high
    loot_generosity: high
    extra_notes: |
      额外的自然语言指示
```

字段优先级：`overrides > preset > 内置默认`。`extra_notes` 是**追加**到预设 body 末尾。

## 6 个内置预设

| 预设 | 状态 | 一句话定位 |
|---|---|---|
| [标准](标准.md) | ✅ 完整 | 中性默认，按 RAW 推进，偶尔 Rule of Cool |
| 严格RAW | 🚧 占位（阶段 D 后扩） | 规则原教旨，DC 不放水，机会攻击照触发 |
| 宽松爽团 | 🚧 占位 | 给玩家发糖，强调爽快感，Rule of Cool 优先 |
| [粉红恋爱向](粉红恋爱向.md) | ✅ 完整 | 暧昧细腻 + NPC 情感线 + 不真杀 PC |
| 黑暗残酷 | 🚧 占位 | PC 真会死，决定有不可逆代价，氛围压抑 |
| 治愈日常 | 🚧 占位 | 战斗少互动多，强调温情 |

## 5 个 frontmatter 开关

预设 / overrides 都用这 5 个字段：

| 字段 | 类型 | 含义 |
|---|---|---|
| `pc_mercy` | none / default / high | PC HP=0 时 DM 救场程度（见下方语义说明） |
| `strict_raw` | bool | 是否严守规则书（true 不通融 / false Rule of Cool 优先） |
| `loot_generosity` | low / normal / high | 宝藏慷慨度 |
| `secret_pacing` | fast / normal / slow_burn | 秘密揭示节奏 |
| `combat_lethality` | low / normal / high | 战斗致命度（怪物 HP / 伤害缩放） |

**`pc_mercy` 语义详解**：
- `none` — PC HP=0 严格按死豁规则，DM 不主动 fudge 救场
- `default` — 按 RAW 走死豁；模组指定的兜底节点可用，但 DM 不额外救场
- `high` — DM 主动 fudge 救场叙事，PC 几乎不会真死

## 自定义风格

不一定要用内置预设。两种自定义方式：

**方式 1：战役内直接 override**（无 preset）：

```yaml
dm_style:
  preset: null                # 不引用预设
  overrides:
    pc_mercy: high
    strict_raw: false
    loot_generosity: high
    secret_pacing: slow_burn
    combat_lethality: low
    extra_notes: |
      （直接写完整的自然语言指示）
```

**方式 2：新建预设文件**：在本目录新建 `<自定义风格名>.md`（参照 [标准.md](标准.md) / [粉红恋爱向.md](粉红恋爱向.md) 结构），然后用 `preset: <自定义风格名>` 引用。

## 与 H 工作流的区别

| | H 工作流（改模组） | DM 风格（本目录） |
|---|---|---|
| 改什么 | 模组**素材文件**（蓝调段、NPC 描写、战斗数据） | 跑团时 AI 的**行为参数** |
| 何时改 | 开桌前一次性 | 每桌实时 |
| 持久化位置 | `docs/modules/<原名>__<标签>/` | 本目录 + `campaigns/<X>/README.md` |
| 例子 | "把茹娜拉描写改成温柔女性 NPC" | "本桌叙事多用暧昧细腻语言、NPC 死亡前必铺垫" |

**两者可叠加**：用 H 改出"风骸岛粉红向"模组副本 + 用"粉红恋爱向"DM 风格跑——基调最一致。

## 阶段说明

本期（Step 1 阶段 A）只完整写了 [标准.md](标准.md) 和 [粉红恋爱向.md](粉红恋爱向.md) 两个示范预设。
其余 4 个（严格RAW / 宽松爽团 / 黑暗残酷 / 治愈日常）在实际跑团（阶段 D）后视需求扩充。
