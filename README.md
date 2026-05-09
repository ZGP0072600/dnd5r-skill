# dnd5r-skill

> **Claude Code skill**：让 Claude 成为你的中文 DnD 5e 2024（5r）助手——查证规则、车卡、查法术、跑 d100 法力狂潮，全部基于"DND 五版不全书"中文资料库，**绝不靠训练记忆瞎编**。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 这是什么

一个针对 [Claude Code](https://docs.claude.com/en/docs/claude-code) 的 [skill](https://docs.claude.com/en/docs/claude-code/skills)。装上之后，你可以这样和 Claude 对话：

- "帮我用魔契师车一张 5 级卡" → 自动从 PHB24 查职业、子职、专长，给你一张可点可投骰的 HTML 电子卡
- "5r 法师 1 环法术推荐哪个" → 直接读《玩家手册2024/法术速查/法师法术速查》给推荐
- "火球术升 4 环加多少伤害" → 翻 `法术详述/3环.htm#Fireball` 引用原文回答
- "战士的灵能武士子职业怎么样" → 读 `灵能武士.htm` 给评价
- "成年红龙的喷吐多少伤害" → 翻怪物图鉴 2025

**关键约束：所有规则数值都先 grep 资料库再回答**——SKILL.md 第一条规则就是「绝不能用训练记忆答」，因为 5e 2024（5r）和训练数据里的 5e 2014 已经有大量差异。

---

## 已实现的能力

### 1. 资料查证

`docs/extracted/` 下是完整的"DND 五版不全书"，已转 UTF-8 + 解开锚点，包含：

- 玩家手册 2024（PHB24）— 12 职业 + 子职、种族、背景、专长、装备、所有环阶法术详述
- 城主指南 2024（DMG24）
- 怪物图鉴 2025（MM25）
- 法术速查（按职业分表）、怪物速查、种族速查
- 旧版 PHB14 / DMG14 / MM14、塔莎、珊娜萨、贤者谏言、万象无常等扩展
- 多个设定集（艾伯伦、龙枪、星界、费资本、范·里希腾...）

### 2. HTML 电子角色卡

`templates/character-sheet.html` 是一个**完全自包含**的单文件交互卡：

- 单文件、零外链：CSS/JS/字体/数据全部内联，离线可用
- 复制到任何位置都能用——发微信、放手机/iPad/电脑、浏览器打开即是
- 内置投骰对话框（属性、技能、攻击、伤害、法术）支持优势/劣势
- HP / 法术位 / 职业资源（pip 池）/ 死豁 / 状态 / 抗性 / 装备负重 / 历史骰史
- 短休 / 长休一键、自动恢复对应资源
- 主题切换（深色/浅色）
- LocalStorage 自动存档（同设备同浏览器记得状态）
- **兼职支持**：混合 HD 显示（如 `d8×3 + d6×2`），短休时按骰型分组依次询问消耗
- **特殊投骰面板**：例如混沌施法术士的 d100 法力狂潮表，点按钮自动投骰、查表、续投子骰、写入历史

### 3. 通过 build-sheet.py 出卡

```bash
# 输入：JSON（schema 见 SKILL.md）
# 输出：自包含 HTML
python templates/build-sheet.py - output.html <<'EOF'
{ "meta": {...}, "abilities": {...}, ... }
EOF
```

或者 Windows PowerShell 走文件方式（heredoc 不可靠）：

```powershell
python templates/build-sheet.py character.json output.html
```

---

## 安装

### 方式 A：用户级（所有项目都可用）

```bash
# 克隆到用户级 skills 目录
git clone https://github.com/ZGP0072600/dnd5r-skill.git ~/.claude/skills/dnd5r
```

### 方式 B：项目级

```bash
# 在你的项目目录下
mkdir -p .claude/skills
git clone https://github.com/ZGP0072600/dnd5r-skill.git .claude/skills/dnd5r
```

装完之后，启动 Claude Code，提"帮我车一张 3 级武僧"或"5r 火球术升 4 环加多少伤害"，skill 会自动触发。

---

## 用法示例

详细工作流见 [SKILL.md](SKILL.md)，简要：

| 你说 | Claude 做的 |
|---|---|
| 帮我用 X 车一张 N 级卡 | 按 SKILL.md 第 B 节流程：种族 → 职业/子职 → 背景 → 属性 → 专长 → 装备 → 法术 → HP/AC 结算 → 出 HTML 卡 |
| 改卡 / 升级 | Read 旧 HTML 提取嵌入 JSON → 改 → 重生成 |
| X 法术怎么样 | A 工作流：grep 法术速查 → 读详述 → 给环阶/学派/施法时间/距离/成分/持续/效果/升环/来源 |
| X 怪物 CR 多少 | D 工作流：grep 万兽大全 → 读详细页 |
| 某规则怎么裁定 | C 工作流：grep `进行游戏` / `术语汇编` |

`examples/` 下放了几张已生成的示范卡（兼职吟3术2、单职 7 级战斗大师、7 级混沌施法术士）可以直接打开浏览器看。

---

## 数据来源 / 版权说明

`docs/` 下的中文规则内容来自社区合作翻译项目「**DND 五版不全书**」。

- **原版权**：D&D 5e 系列规则归 Wizards of the Coast 所有
- **翻译版权**：中文翻译归不全书翻译团队及参与者所有
- **本仓库的角色**：仅作为 Claude Code skill 的数据源，让 Claude 在回答时能从原文查证而非凭训练数据瞎编。本仓库不主张对这些内容的任何权利，也不收取任何费用
- **如有侵权**：如版权方或翻译团队认为本仓库的引用方式侵犯权益，请提 [Issue](https://github.com/ZGP0072600/dnd5r-skill/issues) 或联系仓主，会立即下架相关内容

请尊重原创：**支持购买 WotC 官方书籍**，并在能力范围内**支持不全书翻译团队**的工作。

---

## 已知限制

- **法术位池单字段**：兼职多种施法者时，DC/法术攻击只用一个 `castingAbility`（一般兼职都同主属，问题不大；多施法属性混合时需玩家选主一个）
- **兼职 HD 共享一个 hdCur**：玩家自己心里记每种骰型用了多少（短休消耗时模板会按骰型分组询问，但不强约束某骰型的剩余）
- **豁免熟练自动化**：兼职规则只继承 1 级出身职业的豁免；玩家在 `abilities[ab].saveProf` 自己填
- **不全书更新**：当上游有新内容时，需要手动更新 `docs/extracted/`

---

## 贡献

欢迎 issue / PR：

- **Bug 反馈**：模板渲染异常、JS 报错、规则数值算错——开 issue 附上重现步骤
- **新功能**：模板加新 panel（比如奇械师炼金物清单、武僧专注点池可视化、Eldritch Invocations 选择器等）
- **数据更新**：上游不全书更新时同步资料库
- **文档完善**：SKILL.md 工作流补充、README 翻译

---

## License

代码（SKILL.md、templates/）使用 [MIT License](LICENSE)。

`docs/` 下的规则文本不在本仓库的 license 涵盖范围内——见上文「数据来源/版权说明」。
