#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_index.py — 从 docs/extracted 的 frontmatter 生成快查索引（法术 + 怪物）。

【构建期脚本】只在 md 资料更新后跑一次。可用 PyYAML（重依赖）。
一次 `python build_index.py` 重建全部索引：index/spells.json + index/monsters.json。
生成物是【派生产物】：md 永远是唯一真源，索引绝不手改。
配套 query.py 是【查询期脚本】，只用 stdlib，任何带 Python 的 Agent 都能直接 shell 调用。

真正的脏活在这里 —— 跨书 frontmatter 不一致需要归一化。已知坑（实测）：
  法术：
    * cantrip 的 level：PHB24 用 level:0；PHB14/珊娜萨 用 level:-1 + level_name:戏法 → 统一 0。
    * source 字段不可信（塔莎/PHB14 都填 "法术详述"）→ 来源书一律从路径推导。
    * 字段可选：塔莎只有 name/en/school/classes → 一律 .get() 容缺。
  怪物：
    * cr 形如 1/4 / 1/2 / 0 / 整数 / 30 → 额外存 cr_num 浮点供范围筛选。
    * monster_family 是族首页（无 statblock，有 members[]）→ 单独 kind=family 入库。
    * 正文标题 H1 `# 中文 English`（注意：怪物用空格，不是法术的 ｜）。
  通用：docs/extracted/SCHEMA.md 含各 type 示例（不是真数据）→ 必须排除。
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import yaml
except ImportError:
    sys.exit("[依赖缺失] 构建期需要 PyYAML：pip install pyyaml\n"
             "（仅 build_index.py 需要它；查询期 query.py 只用 stdlib。）")

SKIP_FILES = {"SCHEMA.md"}

# 来源书 → 优先级（越小越优先，实现「2024 优先」）。
PRIORITY = {
    "玩家手册2024": 0, "城主指南2024": 0, "怪物图鉴2025": 0,
    "玩家手册": 1, "城主指南": 1, "怪物图鉴": 1,
    "塔莎的万事坩埚": 2, "珊娜萨的万事指南": 2, "万象无常书": 2, "贤者谏言2025": 2,
}
MULTI_SEG = {"第三方", "模组", "其他"}


# ---------------- 通用 helper ----------------
def find_docs_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "docs" / "extracted"
        if cand.is_dir():
            return cand
    sys.exit("[定位失败] 未找到 docs/extracted，请用 --docs 指定。")


def derive_source(rel_path: str) -> str:
    parts = rel_path.replace("\\", "/").split("/")
    if parts[0] in MULTI_SEG and len(parts) > 1:
        return parts[0] + "/" + parts[1]
    return parts[0]


def source_priority(source: str) -> int:
    if source in PRIORITY:
        return PRIORITY[source]
    if source.split("/")[0] in MULTI_SEG:
        return 5
    return 3


def split_frontmatter(content: str):
    content = content.lstrip("﻿")
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, lines
    for j in range(1, len(lines)):
        if lines[j].strip() == "---":
            return "\n".join(lines[1:j]), lines
    return None, lines


def all_headings(lines):
    """正文标题 (绝对行号, 级别1/2, 文本)。H1=怪物名，H2=法术名/数据栏。"""
    out = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("## "):
            out.append((i + 1, 2, s))
        elif s.startswith("# "):
            out.append((i + 1, 1, s))
    return out


def match_heading(name, en, headings, prefer_level=None):
    name = (name or "").strip()
    en = (en or "").strip()
    cands = headings
    if prefer_level is not None:
        lv = [h for h in headings if h[1] == prefer_level]
        cands = lv or headings
    for lineno, _lvl, text in cands:
        if name and en and name in text and en.lower() in text.lower():
            return lineno
    for lineno, _lvl, text in cands:
        if name and name in text:
            return lineno
    for lineno, _lvl, text in cands:
        if en and en.lower() in text.lower():
            return lineno
    return None


def read_type(path: Path):
    if path.name in SKIP_FILES:
        return None
    try:
        with path.open(encoding="utf-8") as f:
            head = f.read(600)
    except Exception:
        return None
    m = re.search(r"^type:\s*(\S+)", head, re.MULTILINE)
    return m.group(1) if m else None


def cr_to_num(cr):
    if cr is None:
        return None
    s = str(cr).strip()
    if not s or s in ("—", "-"):
        return None
    if "/" in s:
        try:
            a, b = s.split("/")
            return round(float(a) / float(b), 4)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(s)
    except ValueError:
        return None


# ---------------- 法术 ----------------
def normalize_level(level, level_name):
    if level_name and "戏法" in str(level_name):
        return 0
    try:
        lv = int(level)
    except (TypeError, ValueError):
        return None
    # lv < 0 是占位符（合集类文件用文件级 level:-1，且 level_name 非戏法）。
    # 绝不当成 0——否则整本书的法术全塌成戏法。返回 None，交给 level_from_body 从正文兜底。
    return None if lv < 0 else lv


CN_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
          "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def level_from_body(lines, heading_lineno):
    """合集类文件每条法术的环阶只写在正文里、frontmatter 缺 per-spell level。
    从标题行往下找首个含环阶记号的内容行 —— 兼容跨书的多种写法（标签可有可无、级/派顺序不定）：
      - **学派**：一环 塑能      艾奎兹玄/费资本…  (学派标签 + 级在前)
      - **学派**：塑能 戏法       瓦尔达            (学派标签 + 级在后)
      戏法 塑能（…）             黯潮之书          (裸行，级在前)
      塑能 戏法（…）             胧忆岛/火炬克苏鲁  (裸行，级在后)
    戏法→0；中文/阿拉伯数字环阶→对应数字。取首个命中行（即声明行），避免误吃正文里的
    『升环施法』等措辞（升环不带数字前缀，不会匹配）。找不到返回 None。"""
    if not heading_lineno:
        return None
    for k in range(heading_lineno, min(heading_lineno + 12, len(lines))):
        s = lines[k].strip()
        if not s:
            continue
        if s.startswith("#"):
            break  # 撞到下一条法术标题，停止
        if "戏法" in s:
            return 0
        m = re.search(r"([零一二三四五六七八九十])\s*环", s)
        if m:
            return CN_NUM[m.group(1)]
        m = re.search(r"([0-9])\s*环", s)
        if m:
            return int(m.group(1))
    return None


def spell_flags(sp):
    dur = str(sp.get("duration") or "")
    ct = str(sp.get("casting_time") or "")
    return ("专注" in dur), (bool(sp.get("ritual")) or ("仪式" in ct))


def parse_spell_file(path: Path, docs_root: Path):
    rel = path.relative_to(docs_root).as_posix()
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return [], f"读取失败 {rel}: {e}"
    fm_str, lines = split_frontmatter(content)
    if fm_str is None:
        return [], f"无 frontmatter {rel}"
    try:
        fm = yaml.safe_load(fm_str) or {}
    except yaml.YAMLError as e:
        return [], f"YAML 解析失败 {rel}: {e}"
    spells = fm.get("spells")
    if not isinstance(spells, list):
        return [], f"spells 非列表 {rel}"
    source = derive_source(rel)
    prio = source_priority(source)
    edition = str(fm.get("edition") or "")
    headings = all_headings(lines)
    recs = []
    for sp in spells:
        if not isinstance(sp, dict):
            continue
        name = (sp.get("name") or "").strip()
        en = (sp.get("en") or "").strip()
        if not name and not en:
            continue
        conc, ritual = spell_flags(sp)
        classes = sp.get("classes") or []
        if not isinstance(classes, list):
            classes = [str(classes)]
        hl = match_heading(name, en, headings, prefer_level=2)
        level = normalize_level(sp.get("level", fm.get("level")),
                                sp.get("level_name", fm.get("level_name")))
        # 兜底：合集类文件 per-spell 无 level、文件级是占位 -1（normalize 后为 None）→
        # 环阶只写在正文「**学派**：X环」里，从正文解析，避免整本书塌成戏法。
        if sp.get("level") is None and level is None:
            level = level_from_body(lines, hl)
        recs.append({
            "name": name, "en": en,
            "level": level,
            "school": sp.get("school") or None,
            "classes": [str(c).strip() for c in classes],
            "casting_time": sp.get("casting_time") or None,
            "range": sp.get("range") or None,
            "components": sp.get("components") or None,
            "duration": sp.get("duration") or None,
            "concentration": conc, "ritual": ritual,
            "source": source, "edition": edition, "priority": prio,
            "path": rel, "line": hl,
        })
    return recs, None


def reconcile_spells(docs_root: Path, parsed_keys: set):
    master = docs_root / "速查" / "法术速查" / "5E万法大全.html"
    if not master.exists():
        return None
    html = master.read_text(encoding="utf-8", errors="replace")
    names = {n.strip() for n in re.findall(r'spell="([^"]*)"', html) if n.strip()}
    missing = sorted(n for n in names if n not in parsed_keys)
    return {"master": len(names), "missing": len(missing), "sample": missing[:10]}


def load_monster_cr_map(docs_root: Path):
    """从 5E万兽大全.html 解析 名字→CR，回填 frontmatter 缺 cr 的怪物（源转换常把巫妖/古龙等
    statblock 截断，丢了挑战等级）。TR 形如 <TR monster="半巫妖Demilich" tags ="微型 亡灵 有 18 MM25">
    —— CR 是 tags 里属于 crset 的那个 token。"""
    master = docs_root / "速查" / "5E万兽大全.html"
    if not master.exists():
        return {}
    html = master.read_text(encoding="utf-8", errors="replace")
    crset = {"0", "1/8", "1/4", "1/2"} | {str(i) for i in range(1, 31)}
    out = {}
    for mon, tags in re.findall(r'<TR\s+monster\s*=\s*"([^"]*)"[^>]*?tags\s*=\s*"([^"]*)"', html, re.I):
        cr = next((t for t in tags.split() if t in crset), None)
        if cr:
            out[mon.strip()] = cr
    return out


# ---------------- 怪物 ----------------
def parse_monster_file(path: Path, docs_root: Path, kind: str):
    """kind = 'monster' | 'family'。返回 (record_or_None, error_or_None)。"""
    rel = path.relative_to(docs_root).as_posix()
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return None, f"读取失败 {rel}: {e}"
    fm_str, lines = split_frontmatter(content)
    if fm_str is None:
        return None, f"无 frontmatter {rel}"
    try:
        fm = yaml.safe_load(fm_str) or {}
    except yaml.YAMLError as e:
        return None, f"YAML 解析失败 {rel}: {e}"

    name = (fm.get("name") or "").strip()
    en = (fm.get("en") or "").strip()
    if not name and not en:
        return None, f"无 name/en {rel}"
    source = derive_source(rel)
    line = match_heading(name, en, all_headings(lines), prefer_level=1)
    base = {
        "kind": "family" if kind == "monster_family" else "monster",
        "name": name, "en": en,
        "source": source, "edition": str(fm.get("edition") or ""),
        "priority": source_priority(source),
        "path": rel, "line": line,
    }
    if kind == "monster_family":
        base.update({
            "subtitle": fm.get("subtitle") or None,
            "members": fm.get("members") or [],
            "habitat": fm.get("habitat") or None,
        })
        return base, None
    # 普通怪物
    cr = fm.get("cr")
    base.update({
        "size": fm.get("size") or None,
        "creature_type": fm.get("creature_type") or None,
        "alignment": fm.get("alignment") or None,
        "cr": None if cr is None else str(cr),
        "cr_num": cr_to_num(cr),
        "xp": fm.get("xp"),
        "pb": fm.get("pb"),
        "ac": fm.get("ac"),
        "hp": fm.get("hp"),
        "hp_dice": fm.get("hp_dice") or None,
        "speed": fm.get("speed") or None,
        "abilities": fm.get("abilities") or None,
        "saves": fm.get("saves") or None,
        "skills": fm.get("skills") or None,
        "damage_resist": fm.get("damage_resist") or [],
        "damage_immune": fm.get("damage_immune") or [],
        "damage_vuln": fm.get("damage_vuln") or [],
        "condition_immune": fm.get("condition_immune") or [],
        "senses": fm.get("senses") or None,
        "languages": fm.get("languages") or [],
        "family": fm.get("family") or None,
    })
    return base, None


# ---------------- 构建 ----------------
def build_spells(files, docs_root, out_dir):
    recs, errors, line_miss, per_src = [], [], 0, {}
    for p in files:
        r, err = parse_spell_file(p, docs_root)
        if err:
            errors.append(err)
            continue
        for x in r:
            if x["line"] is None:
                line_miss += 1
            per_src[x["source"]] = per_src.get(x["source"], 0) + 1
        recs.extend(r)
    out = out_dir / "spells.json"
    out.write_text(json.dumps(
        {"_schema": "spell-index-v1", "spell_count": len(recs),
         "source_count": len(per_src), "spells": recs},
        ensure_ascii=False, indent=0), encoding="utf-8")
    recon = reconcile_spells(docs_root, {(r["name"] + r["en"]) for r in recs})
    print(f"\n[法术] ✅ {out}")
    print(f"   {len(recs)} 条 / {len(per_src)} 书 / 行号未命中 {line_miss}")
    if recon:
        print(f"   对账 5E万法大全: master {recon['master']} / 疑似漏收 {recon['missing']}"
              f"（含译名差异假阳性）" + (("  样本: " + "、".join(recon["sample"][:6])) if recon["sample"] else ""))
    if errors:
        print(f"   ⚠ 跳过 {len(errors)} 文件: " + "; ".join(errors[:5]))


def build_monsters(mfiles, ffiles, docs_root, out_dir):
    recs, errors, line_miss, per_src = [], [], 0, {}
    for p in mfiles:
        r, err = parse_monster_file(p, docs_root, "monster")
        if err:
            errors.append(err); continue
        if r["line"] is None:
            line_miss += 1
        per_src[r["source"]] = per_src.get(r["source"], 0) + 1
        recs.append(r)
    fam = 0
    for p in ffiles:
        r, err = parse_monster_file(p, docs_root, "monster_family")
        if err:
            errors.append(err); continue
        recs.append(r); fam += 1
    # 回填 frontmatter 缺失的 cr（源转换截断的 statblock）
    crmap = load_monster_cr_map(docs_root)
    backfilled = 0
    for r in recs:
        if r["kind"] == "monster" and r.get("cr_num") is None:
            cr = crmap.get(r["name"] + r["en"])
            if cr:
                r["cr"], r["cr_num"] = cr, cr_to_num(cr)
                backfilled += 1
    out = out_dir / "monsters.json"
    out.write_text(json.dumps(
        {"_schema": "monster-index-v1", "monster_count": len(recs) - fam,
         "family_count": fam, "source_count": len(per_src), "monsters": recs},
        ensure_ascii=False, indent=0), encoding="utf-8")
    no_cr = sum(1 for r in recs if r["kind"] == "monster" and r.get("cr_num") is None)
    print(f"\n[怪物] ✅ {out}")
    print(f"   {len(recs) - fam} 怪物 + {fam} 族首页 / {len(per_src)} 书 / 行号未命中 {line_miss}")
    print(f"   CR 回填 {backfilled} 条（从 5E万兽大全）/ 仍无CR {no_cr}")
    print("   按来源:", "、".join(f"{s}:{n}" for s, n in sorted(per_src.items(), key=lambda x: -x[1])[:8]))
    if errors:
        print(f"   ⚠ 跳过 {len(errors)} 文件: " + "; ".join(errors[:5]))


# ---------------- 职业 / 子职业 ----------------
SUBCLASS_NOISE = ("法术", "选项", "列表", "扩展", "构筑", "战技")  # 目录内非子职文件（法术列表/战技选项/战斗大师构筑 等）
CLASS_NAME_ALIAS = {"邪术师": "魔契师"}  # 扩展书译名 → PHB24 职业名


def extract_flavor(lines):
    """子职正文 H1 后第一段实质性描述（跳过标语/加粗特性行）→ 首句。"""
    started = False
    for ln in lines:
        s = ln.strip()
        if not started:
            if s.startswith("# "):
                started = True
            continue
        if not s or s[0] in "#*>|-" or len(s) < 12:
            continue
        sent = re.split(r"[。！？]", s)[0].strip()
        return (sent[:80] + "…") if len(sent) > 80 else sent
    return None


def extract_hit_die(content):
    m = re.search(r"(?:命中骰|生命骰)[^\d]{0,8}(d\d+)", content)
    return m.group(1) if m else None


# 跨书职业（PHB24 之外，逐源 bespoke）。subdir 给子职目录；噪音多的源用 subclasses 显式列名单。
CROSS_CLASSES = [
    {"name": "奇械师", "main": "塔莎的万事坩埚/玩家选项/职业/奇械师.md",
     "subdir": "塔莎的万事坩埚/玩家选项/职业/奇械师"},                          # 默认滤掉"奇械师法术列表"
    {"name": "铳士", "main": "第三方/瓦尔达的秘密尖塔/铳士/铳士职业.md",
     "subdir": "第三方/瓦尔达的秘密尖塔/铳士",
     "subclasses": ["密间客", "技枪客", "死眼客", "白帽客", "豪赌客", "魔弹客"]},   # 枪械/弹药/词条噪音多，显式列
    {"name": "血猎手", "main": "第三方/血猎手/血猎手.md",
     "subdir": "第三方/血猎手",
     "subclasses": ["化狼结社", "弑灵结社", "渎魂结社", "突变结社"]},               # 血咒是职业特性、非子职
]


def _class_records(main_path: Path, sub_paths, cls_name: str, docs_root: Path):
    """从 主文件 + 子职文件列表 生成 (class_rec, [subclass_recs])。父职业一律取 cls_name（category 不可靠）。"""
    content = main_path.read_text(encoding="utf-8")
    fm_str, lines = split_frontmatter(content)
    fm = (yaml.safe_load(fm_str) if fm_str else {}) or {}
    rel = main_path.relative_to(docs_root).as_posix()
    source = derive_source(rel)
    prio = source_priority(source)
    sub_recs, sub_names = [], []
    for f in sub_paths:
        sfm_str, slines = split_frontmatter(f.read_text(encoding="utf-8"))
        sfm = (yaml.safe_load(sfm_str) if sfm_str else {}) or {}
        sname = (sfm.get("name") or f.stem).strip()
        sen = (sfm.get("en") or "").strip()
        sub_names.append(sname)
        sub_recs.append({
            "kind": "subclass", "name": sname, "en": sen, "class": cls_name,
            "flavor": extract_flavor(slines),
            "source": source, "edition": str(sfm.get("edition") or ""), "priority": prio,
            "path": f.relative_to(docs_root).as_posix(),
            "line": match_heading(sname, sen, all_headings(slines), prefer_level=1),
        })
    class_rec = {
        "kind": "class", "name": (fm.get("name") or cls_name).strip(),
        "en": (fm.get("en") or "").strip(), "hit_die": extract_hit_die(content),
        "subclasses": sub_names, "source": source, "edition": str(fm.get("edition") or ""),
        "priority": prio, "path": rel,
        "line": match_heading(fm.get("name") or cls_name, fm.get("en"), all_headings(lines), prefer_level=1),
    }
    return class_rec, sub_recs


def build_classes(docs_root, out_dir):
    entries, errors, per_src = [], [], {}
    cls_count = sub_count = 0

    def add(crec, srecs):
        nonlocal cls_count, sub_count
        entries.append(crec)
        cls_count += 1
        per_src[crec["source"]] = per_src.get(crec["source"], 0) + 1
        entries.extend(srecs)
        sub_count += len(srecs)

    # PHB24：每职业一目录，主文件在目录内
    phb24 = docs_root / "玩家手册2024" / "角色职业"
    if phb24.is_dir():
        for cdir in sorted(p for p in phb24.iterdir() if p.is_dir()):
            main = cdir / f"{cdir.name}.md"
            if not main.exists():
                errors.append(f"无主文件 {cdir.name}")
                continue
            subs = [f for f in sorted(cdir.glob("*.md"))
                    if f.name != main.name and not any(k in f.stem for k in SUBCLASS_NOISE)]
            add(*_class_records(main, subs, cdir.name, docs_root))

    # 跨书：注册表逐源（奇械师/铳士…）
    for e in CROSS_CLASSES:
        main = docs_root / e["main"]
        if not main.exists():
            errors.append(f"跨书主文件缺 {e['name']}: {e['main']}")
            continue
        subdir = docs_root / e["subdir"]
        if "subclasses" in e:                          # 显式子职名单（噪音多的源）
            subs = [subdir / f"{n}.md" for n in e["subclasses"] if (subdir / f"{n}.md").exists()]
        else:                                          # 扫子目录、滤噪音
            subs = [f for f in sorted(subdir.glob("*.md")) if not any(k in f.stem for k in SUBCLASS_NOISE)]
        add(*_class_records(main, subs, e["name"], docs_root))

    # 跨书：给现有职业追加子职（auto-scan <职业> 目录，无独立主文件 → 只加子职记录）
    for base_rel, suffix in [("塔莎的万事坩埚/玩家选项/职业", "（TCE）"),
                             ("珊娜萨的万事指南/角色选项", "")]:
        base = docs_root / base_rel
        if not base.is_dir():
            continue
        for cdir in sorted(p for p in base.iterdir() if p.is_dir()):
            cls = cdir.name[:-len(suffix)] if suffix and cdir.name.endswith(suffix) else cdir.name
            cls = CLASS_NAME_ALIAS.get(cls, cls)
            if cls == "奇械师":          # 已由 CROSS_CLASSES 建（含主文件），避免重复
                continue
            for f in sorted(cdir.glob("*.md")):
                if any(k in f.stem for k in SUBCLASS_NOISE):
                    continue
                sfm_str, slines = split_frontmatter(f.read_text(encoding="utf-8"))
                sfm = (yaml.safe_load(sfm_str) if sfm_str else {}) or {}
                sname = (sfm.get("name") or f.stem).strip()
                if any(k in sname for k in SUBCLASS_NOISE):   # 名字也查噪音（魔能祈唤选项：stem 不含但 name 含"选项"）
                    continue
                sen = (sfm.get("en") or "").strip()
                rel = f.relative_to(docs_root).as_posix()
                source = derive_source(rel)
                entries.append({
                    "kind": "subclass", "name": sname, "en": sen, "class": cls,
                    "flavor": extract_flavor(slines),
                    "source": source, "edition": str(sfm.get("edition") or ""),
                    "priority": source_priority(source),
                    "path": rel, "line": match_heading(sname, sen, all_headings(slines), prefer_level=1),
                })
                sub_count += 1
                per_src[source] = per_src.get(source, 0) + 1

    # 第三方：给现有职业的子职选项（文件名 <职业>-<子职>，父职业取前缀；谦卑林无前缀信息故略）
    TP_SUBCLASS_DIRS = [
        "第三方/狮鹫的鞍中珍宝Ⅱ/子职", "第三方/瓦尔达的秘密尖塔/子职",
        "第三方/胧忆岛/子职", "第三方/鬼魅幽谷/玩家包/子职", "第三方/黯潮之书/子职",
    ]
    for d in TP_SUBCLASS_DIRS:
        base = docs_root / d
        if not base.is_dir():
            continue
        for f in sorted(base.glob("*.md")):
            if "-" not in f.stem or f.stem in ("职业", "子职"):
                continue
            prefix, suffix = f.stem.split("-", 1)
            cls = CLASS_NAME_ALIAS.get(prefix.replace("范型", "").strip(), prefix.replace("范型", "").strip())
            sfm_str, slines = split_frontmatter(f.read_text(encoding="utf-8"))
            sfm = (yaml.safe_load(sfm_str) if sfm_str else {}) or {}
            sname = (sfm.get("name") or suffix).strip()
            if "-" in sname:                       # frontmatter name 可能含职业前缀，去掉
                sname = sname.split("-", 1)[1].strip()
            sen = (sfm.get("en") or "").strip()
            rel = f.relative_to(docs_root).as_posix()
            source = derive_source(rel)
            entries.append({
                "kind": "subclass", "name": sname, "en": sen, "class": cls,
                "flavor": extract_flavor(slines),
                "source": source, "edition": str(sfm.get("edition") or ""),
                "priority": source_priority(source),
                "path": rel, "line": match_heading(sname, sen, all_headings(slines), prefer_level=1),
            })
            sub_count += 1
            per_src[source] = per_src.get(source, 0) + 1

    out = out_dir / "classes.json"
    out.write_text(json.dumps(
        {"_schema": "class-index-v1", "class_count": cls_count,
         "subclass_count": sub_count, "source_count": len(per_src), "entries": entries},
        ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"\n[职业] ✅ {out}")
    print(f"   {cls_count} 职业 + {sub_count} 子职业 / 来源 {len(per_src)}")
    print("   来源:", "、".join(f"{s}:{n}" for s, n in sorted(per_src.items(), key=lambda x: -x[1])))
    if errors:
        print(f"   ⚠ {len(errors)}: " + "; ".join(errors[:5]))


# ---------------- 种族 ----------------
CROSS_RACE_SOURCES = [
    {"dir": "剑湾冒险者指南/种族", "noise": ("种族",)},        # 半精灵变体/灰矮人/地底侏儒/鬼智半身人/提夫林变体
    {"dir": "费资本的巨龙宝库/玩家选项", "include": "龙裔", "noise": ("龙裔种族",)},  # 宝石/色彩/金属龙裔（排除"龙裔种族"总览页）
]


def _race_record(f: Path, docs_root: Path):
    fm_str, lines = split_frontmatter(f.read_text(encoding="utf-8"))
    fm = (yaml.safe_load(fm_str) if fm_str else {}) or {}
    rel = f.relative_to(docs_root).as_posix()
    src = derive_source(rel)
    name = (fm.get("name") or f.stem).strip()
    en = (fm.get("en") or "").strip()
    if not en:                                       # 种族 name 可能是「半精灵Half-Elf」中英黏一起
        m = re.match(r"^([一-鿿·\s]+?)\s*([A-Za-z].*)$", name)
        if m:
            name, en = m.group(1).strip(), m.group(2).strip()
    if not en:                                       # 剑湾/费资本：name 仅中文，英文在正文首个 **中文 English** 粗体行
        pat = re.compile(r"^\*\*\s*" + re.escape(name) + r"\s+([A-Za-z].*?)\s*\*\*")
        for ln in lines:
            mm = pat.match(ln.strip())
            if mm:
                en = mm.group(1).strip()
                break
    return {
        "kind": "race", "name": name, "en": en, "flavor": extract_flavor(lines),
        "source": src, "edition": str(fm.get("edition") or ""), "priority": source_priority(src),
        "path": rel, "line": match_heading(name, en, all_headings(lines), prefer_level=1),
    }


def build_races(docs_root, out_dir):
    recs, per_src = [], {}

    def emit(f):
        r = _race_record(f, docs_root)
        recs.append(r)
        per_src[r["source"]] = per_src.get(r["source"], 0) + 1

    rdir = docs_root / "玩家手册2024" / "角色起源" / "种族"
    if rdir.is_dir():
        for f in sorted(rdir.glob("*.md")):
            emit(f)
    for src in CROSS_RACE_SOURCES:
        d = docs_root / src["dir"]
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            if src.get("include") and src["include"] not in f.stem:
                continue
            if f.stem in src.get("noise", ()):
                continue
            emit(f)
    out = out_dir / "races.json"
    out.write_text(json.dumps({"_schema": "race-index-v1", "race_count": len(recs),
                               "source_count": len(per_src), "races": recs},
                              ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"\n[种族] ✅ {out}\n   {len(recs)} 种族 / {len(per_src)} 书")
    print("   来源:", "、".join(f"{s}:{n}" for s, n in sorted(per_src.items(), key=lambda x: -x[1])))


# ---------------- 装备（武器/护甲表）----------------
def split_cn_en(s):
    s = re.sub(r"\*+", "", s).strip()
    m = re.match(r"^(.*?[一-鿿])\s+([A-Za-z(].*)$", s)
    return (m.group(1).strip(), m.group(2).strip()) if m else (s, "")


def parse_equip_table(path, docs_root, kind, cols):
    rel = path.relative_to(docs_root).as_posix()
    src = derive_source(rel)
    lines = path.read_text(encoding="utf-8").split("\n")
    recs, category = [], None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells or all(set(c) <= set("-: ") for c in cells):       # 分隔行
            continue
        if cells[0] in ("名称", "护甲") or (len(cells) > 1 and "护甲等级" in cells[1]):  # 表头
            continue
        if cells[0] and all(not c for c in cells[1:]):                  # 分类行
            category = re.sub(r"\*+", "", cells[0]).strip()
            continue
        name, en = split_cn_en(cells[0])
        if not name:
            continue
        rec = {"kind": kind, "name": name, "en": en, "category": category,
               "source": src, "edition": "2024", "priority": source_priority(src),
               "path": rel, "line": i + 1}
        for j, col in enumerate(cols):
            rec[col] = cells[1 + j] if 1 + j < len(cells) else None
        recs.append(rec)
    return recs


def _parse_gear_2col(path, docs_root):
    """2024 冒险装备是【双栏】表：物品|重量|价格 ‖ 物品|重量|价格，每行两件、名字仅中文。
    法器（奥术法器/德鲁伊法器/圣徽）也是表里的普通行（重量/价格记『多类』），自然成条目。"""
    rel = path.relative_to(docs_root).as_posix()
    src = derive_source(rel)
    recs = []
    for i, ln in enumerate(path.read_text(encoding="utf-8").split("\n")):
        s = ln.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells or all(set(c) <= set("-: ") for c in cells):
            continue
        for b in (0, 4):                                 # 左栏 cells[0:3]、右栏 cells[4:7]
            if b + 2 < len(cells) and cells[b] and cells[b] not in ("物品", "名称"):
                nm = re.sub(r"\*+", "", cells[b]).strip()
                name, en = split_cn_en(nm)
                recs.append({"kind": "gear", "name": name or nm, "en": en, "category": None,
                             "source": src, "edition": "2024", "priority": source_priority(src),
                             "path": rel, "line": i + 1,
                             "weight": cells[b + 1] or None, "cost": cells[b + 2] or None})
    return recs


def _parse_tools_2024(path, docs_root):
    """2024 工匠工具/其他工具：每件名是『中文 English (价格)』（英文+价格可能换行），
    紧跟一张『| 属性：… | 重量：… |』详情表——以该表行为锚点回取上方名字。"""
    rel = path.relative_to(docs_root).as_posix()
    src = derive_source(rel)
    lines = path.read_text(encoding="utf-8").split("\n")
    pat = re.compile(r"^([一-鿿·]+)\s+([A-Za-z'’\s]+?)\s*[（(]\s*([\d,.]+\s*[A-Za-z]{2})\s*[)）]")
    recs = []
    for i, ln in enumerate(lines):
        if not ln.strip().startswith("| 属性"):
            continue
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        nb = []                                          # 名字可能跨行（易容工具 / Disguise Kit (25GP)）
        while j >= 0 and lines[j].strip() and not lines[j].strip().startswith("|") and len(nb) < 2:
            nb.insert(0, lines[j].strip())
            j -= 1
        m = pat.match(" ".join(nb))
        if m:
            recs.append({"kind": "tool", "name": m.group(1).strip(), "en": m.group(2).strip(),
                         "category": "工具", "source": src, "edition": "2024",
                         "priority": source_priority(src), "path": rel, "line": j + 2,
                         "weight": None, "cost": m.group(3).strip()})
    return recs


def build_equipment(docs_root, out_dir):
    recs = []
    edir = docs_root / "玩家手册2024" / "装备"
    if (edir / "武器.md").exists():
        recs += parse_equip_table(edir / "武器.md", docs_root, "weapon",
                                  ["damage", "properties", "mastery", "weight", "cost"])
    if (edir / "护甲.md").exists():
        recs += parse_equip_table(edir / "护甲.md", docs_root, "armor",
                                  ["ac", "strength", "stealth", "weight", "cost"])
    if (edir / "冒险装备.md").exists():                  # 冒险装备（双栏表）+ 法器
        recs += _parse_gear_2col(edir / "冒险装备.md", docs_root)
    for tf in ("工匠工具.md", "其他工具.md"):             # 工具（标题式：中文 English (价格)）
        if (edir / tf).exists():
            recs += _parse_tools_2024(edir / tf, docs_root)
    out = out_dir / "equipment.json"
    out.write_text(json.dumps({"_schema": "equipment-index-v1", "item_count": len(recs),
                               "equipment": recs}, ensure_ascii=False, indent=0), encoding="utf-8")
    by = {}
    for r in recs:
        by[r["kind"]] = by.get(r["kind"], 0) + 1
    print(f"\n[装备] ✅ {out}\n   {len(recs)} 件（PHB24）: " +
          "、".join(f"{k}:{v}" for k, v in sorted(by.items(), key=lambda x: -x[1])))


# ---------------- 专长（best-effort）----------------
FEAT_MARKERS = ("起源专长", "通用专长", "战斗风格专长", "传奇恩惠专长")

# 跨书 2014 专长（官方书；无 2024 分类词，名字是"中文 English"裸/粗体行，结构化检测）
CROSS_FEAT_FILES = [
    ("塔莎的万事坩埚/玩家选项/专长.md", "扩展"),
    ("费资本的巨龙宝库/玩家选项/龙类专长.md", "龙系"),
    ("珊娜萨的万事指南/角色选项/种族专长.md", "种族"),
]


def _feat_name_2014(s):
    s = re.sub(r"Legacy", "", re.sub(r"\*+", "", s.strip())).strip()
    if not s or s[0] in "·-#>|" or any(p in s for p in "。，：；、（）"):
        return None
    m = re.match(r"^([一-鿿][一-鿿·]{0,9})\s+([A-Z][A-Za-z' /]+)$", s)
    if not m or len(s) >= 30 or m.group(1).endswith("专长"):   # 排除章节标题（专长/种族专长/龙类专长）
        return None
    return m.group(1), m.group(2).strip()


def build_feats(docs_root, out_dir):
    recs, per_cat = [], {}
    fdir = docs_root / "玩家手册2024" / "专长"
    files = [f for f in sorted(fdir.glob("*.md")) if "概述" not in f.stem] if fdir.is_dir() else []
    for f in files:
        rel = f.relative_to(docs_root).as_posix()
        src = derive_source(rel)
        cat = f.stem.replace("专长", "")
        lines = f.read_text(encoding="utf-8").split("\n")
        for i, ln in enumerate(lines):
            s = ln.strip()
            if not any(k in s for k in FEAT_MARKERS):    # 分类词（起源专长/通用专长/…）= 每个专长引导行的通用标记
                continue
            # marker 之前的同行前缀（处理内联名「幸运 Lucky 起源专长…」「**健壮 Tough** 起源专长…」）
            cut = min([s.find(k) for k in FEAT_MARKERS if k in s], default=-1)
            inline = s[:cut].strip() if cut > 0 else ""
            name, en = split_cn_en(inline) if inline else ("", "")
            line_no = i + 1
            if not (name and en):                       # 内联不完整 → 补 marker 上方的名字行
                k = i - 1
                while k >= 0 and not lines[k].strip():   # 跳空行（粗体名与增益行间常有空行）
                    k -= 1
                above = []
                while k >= 0 and lines[k].strip():
                    above.insert(0, lines[k].strip())
                    k -= 1
                if above:
                    name, en = split_cn_en((" ".join(above) + " " + inline).strip())
                    line_no = k + 2
            if not name or name.startswith(("#", "-", "|", ">")) or len(name) > 15:
                continue
            if recs and recs[-1]["name"] == name and recs[-1]["path"] == rel:  # 去重
                continue
            recs.append({"kind": "feat", "name": name, "en": en, "category": cat,
                         "source": src, "edition": "2024", "priority": source_priority(src),
                         "path": rel, "line": line_no})
            per_cat[cat] = per_cat.get(cat, 0) + 1
    # 跨书 2014 专长（结构化检测，best-effort）
    for rel, cat in CROSS_FEAT_FILES:
        f = docs_root / rel
        if not f.exists():
            continue
        src = derive_source(rel)
        lines = f.read_text(encoding="utf-8").split("\n")
        for i, ln in enumerate(lines):
            nm = _feat_name_2014(ln)
            if not nm:
                continue
            recs.append({"kind": "feat", "name": nm[0], "en": nm[1], "category": cat,
                         "source": src, "edition": "2014", "priority": source_priority(src),
                         "path": rel, "line": i + 1})
            per_cat[cat] = per_cat.get(cat, 0) + 1

    out = out_dir / "feats.json"
    out.write_text(json.dumps({"_schema": "feat-index-v1", "feat_count": len(recs),
                               "feats": recs}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"\n[专长] ✅ {out}\n   {len(recs)} 专长（best-effort 解析，需核对）: " +
          "、".join(f"{c}{n}" for c, n in per_cat.items()))


# ---------------- 魔法物品 ----------------
MAGIC_ROOT = "城主指南2024/7.宝藏/魔法物品详述"


def build_magic(docs_root, out_dir):
    root = docs_root / MAGIC_ROOT
    recs, per_type = [], {}
    if root.is_dir():
        for f in sorted(root.rglob("*.md")):
            rel = f.relative_to(docs_root).as_posix()
            parts = f.relative_to(root).parts
            itype = parts[0] if len(parts) > 1 else "其他"   # 武器/护甲/戒指/药水/卷轴/权杖/法杖/魔杖/奇物
            rarity = f.stem                                  # 传说/非常稀有/稀有/罕见/普通/神器…
            lines = f.read_text(encoding="utf-8").split("\n")
            for i, ln in enumerate(lines):
                s = ln.strip()
                if not s.startswith("##### "):
                    continue
                name, en = split_cn_en(s[6:].strip())
                meta = ""                                    # 紧跟的斜体行：*类型，稀有度（需同调）*（可能与描述文本黏在同一行）
                for j in range(i + 1, min(i + 5, len(lines))):
                    t = lines[j].strip()
                    if not t:
                        continue
                    mm = re.match(r"^\*([^*]{1,40})\*", t)   # 行首斜体段，后面可能紧跟描述文本
                    if mm:
                        meta = mm.group(1).strip()
                    break                                    # 首个非空行即定论（是 meta，或已进入描述正文）
                if not name:
                    continue
                recs.append({
                    "kind": "magic", "name": name, "en": en, "item_type": itype, "rarity": rarity,
                    "attunement": ("需同调" in meta or "需调谐" in meta), "meta": meta or None,
                    "source": "城主指南2024", "edition": "2024", "priority": 0, "path": rel, "line": i + 1,
                })
                per_type[itype] = per_type.get(itype, 0) + 1
    out = out_dir / "magic.json"
    out.write_text(json.dumps({"_schema": "magic-index-v1", "item_count": len(recs), "magic": recs},
                              ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"\n[魔法物品] ✅ {out}\n   {len(recs)} 件 / {len(per_type)} 类")
    print("   按类:", "、".join(f"{t}:{n}" for t, n in sorted(per_type.items(), key=lambda x: -x[1])))


def main():
    ap = argparse.ArgumentParser(description="生成法术+怪物+职业+种族+专长+装备+魔法物品快查索引")
    ap.add_argument("--docs", default=None)
    ap.add_argument("--out", default=None, help="索引输出目录（默认 ./index）")
    ap.add_argument("--only", choices=["spells", "monsters", "classes", "races", "feats", "equipment", "magic"],
                    help="只建其一")
    args = ap.parse_args()

    docs_root = Path(args.docs).resolve() if args.docs else find_docs_root()
    out_dir = Path(args.out).resolve() if args.out else (Path(__file__).parent / "index")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"资料库: {docs_root}")

    spell_files, monster_files, family_files = [], [], []
    for p in docs_root.rglob("*.md"):
        t = read_type(p)
        if t == "spell_collection":
            spell_files.append(p)
        elif t == "monster":
            monster_files.append(p)
        elif t == "monster_family":
            family_files.append(p)
    print(f"扫描: 法术集 {len(spell_files)} / 怪物 {len(monster_files)} / 怪物族 {len(family_files)}")

    if args.only in (None, "spells"):
        build_spells(sorted(spell_files), docs_root, out_dir)
    if args.only in (None, "monsters"):
        build_monsters(sorted(monster_files), sorted(family_files), docs_root, out_dir)
    if args.only in (None, "classes"):
        build_classes(docs_root, out_dir)
    if args.only in (None, "races"):
        build_races(docs_root, out_dir)
    if args.only in (None, "feats"):
        build_feats(docs_root, out_dir)
    if args.only in (None, "equipment"):
        build_equipment(docs_root, out_dir)
    if args.only in (None, "magic"):
        build_magic(docs_root, out_dir)


if __name__ == "__main__":
    main()
