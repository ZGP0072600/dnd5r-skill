#!/usr/bin/env python3
"""HTML → Markdown converter for DND 5R reference docs.

MVP scope: 2024 monster statblocks from 怪物图鉴2025 (stat-block.css format),
including monster_family pages (XX总.htm).

Usage:
    python convert.py <htm_file>                 # convert single file
    python convert.py <htm_file> --dry-run       # print to stdout
    python convert.py <dir> --batch              # convert all .htm in dir
    python convert.py <htm_file> --check <md>    # diff against expected MD
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag
import yaml


# --------- detection ---------------------------------------------------------

def detect_type(soup: BeautifulSoup) -> str:
    """Return one of: monster_2024, monster_family, monster_2014_winchm,
    spell_collection, document, unknown.

    Order matters: check spell_collection BEFORE monster_2024 because some
    spell files embed monster statblocks inline. 'document' is the fallback.
    """
    # Spell collection: ≥3 H4 with format '中文｜English' (full-width pipe).
    h4s = soup.find_all("h4")
    if len(h4s) >= 3:
        pipe_h4s = sum(1 for h in h4s if "｜" in h.get_text())
        if pipe_h4s >= 3:
            return "spell_collection"
    if soup.find("div", class_="stat-block"):
        return "monster_2024"
    # monster_family: must have BOTH p.sum AND div.HT, AND no H3 (subclass
    # pages also use p.sum but always have H3 sub-sections).
    if soup.find("p", class_="sum") and soup.find("div", class_="HT"):
        if not soup.find("h3"):
            return "monster_family"
    # 2014 WinCHM-style monster: a single <p> containing all of "AC：", "HP：",
    # "挑战等级". This is the DNDBeyond 怪物纲要 format.
    if is_monster_2014_winchm(soup):
        return "monster_2014_winchm"
    # Generic document fallback.
    body = soup.body
    if body:
        text_len = len(body.get_text(strip=True))
        if text_len >= 100:
            return "document"
    return "unknown"


_AC_RE = re.compile(r"AC\s*[：:]")
_HP_RE = re.compile(r"HP\s*[：:]")
_CR_RE = re.compile(r"挑战等级\s*[：:]")


def is_monster_2014_winchm(soup: BeautifulSoup) -> bool:
    """Detect a 2014 DNDBeyond/WinCHM-style monster statblock.

    Looks for a single <p> containing AC, HP, and CR field markers (allowing
    optional whitespace around the colon: 'AC ：' or 'AC:' both match).
    """
    for p in soup.find_all("p"):
        text = p.get_text()
        if _AC_RE.search(text) and _HP_RE.search(text) and _CR_RE.search(text):
            return True
    return False


def detect_source_edition(htm_path: Path) -> tuple[str, str]:
    """Infer source book and edition from path."""
    parts = htm_path.parts
    for p in parts:
        if p == "怪物图鉴2025":
            return "怪物图鉴2025", "2024"
        if p == "玩家手册2024":
            return "玩家手册2024", "2024"
    # fallback: parent dir name
    for p in reversed(parts[:-1]):
        if p in {"DNDBeyond", "extracted"}:
            continue
        return p, "2014"  # default
    return "unknown", "2014"


def detect_family(htm_path: Path) -> str | None:
    """If file is in a subdirectory of 类人/亡灵/etc, the dir name is the family."""
    parent = htm_path.parent.name
    # Categories under 怪物图鉴2025 are not "family", they're "type"
    type_dirs = {
        "类人", "亡灵", "元素", "多类型", "天族", "妖精", "巨人",
        "异怪", "怪兽", "构装", "植物", "泥怪", "邪魔", "龙类",
        "前言", "附录A", "附录B",
    }
    if parent in type_dirs:
        return None
    # Otherwise the parent is the family name
    if parent in {"DNDBeyond", "怪物纲要1", "怪物纲要2"}:
        return None
    return parent


# --------- helpers -----------------------------------------------------------

def clean_text(s: str) -> str:
    """Normalize whitespace and remove zero-width chars."""
    s = s.replace("​", "").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def split_zh_en(text: str) -> tuple[str, str]:
    """Split '怪物名 EnglishName' into (zh, en).

    Handles formats:
        '角斗士 Gladiator'
        '角斗士\n  Gladiator'
        '邪教教宗Cultist Hierophant'  (no space)
    """
    text = clean_text(text)
    # Match: leading CJK run, optional space, trailing ASCII run
    m = re.match(r"^([一-鿿·]+)\s*([A-Za-z][A-Za-z\s'·]*?)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return text, ""


def normalize_dc(s: str) -> str:
    """Normalize 'DC17' → 'DC 17'.

    Note: cannot use \\b because in Python's re, CJK chars are word chars,
    so '\\bDC' fails to match '免DC'. Use lookbehind instead.
    """
    return re.sub(r"(?<![A-Za-z])DC(\d)", r"DC \1", s)


def add_zh_en_space(s: str) -> str:
    """Insert a space between adjacent CJK and ASCII letters.

    '矛Spear' → '矛 Spear'  ;  'Spear矛' → 'Spear 矛'
    Skip when separator already exists (space, dash, punctuation).
    """
    s = re.sub(r"([一-鿿])([A-Za-z])", r"\1 \2", s)
    s = re.sub(r"([A-Za-z])([一-鿿])", r"\1 \2", s)
    return s


def add_md_boundary_space(s: str) -> str:
    """Space inserts at **bold**/CJK boundaries.

    '**xx**y' → '**xx** y' (CJK after bold close)
    'x**yy**' → 'x **yy**' (CJK before bold open)

    Single * (italic) is intentionally NOT handled: in markdown, regex can't
    distinguish opening from closing *, and rule attempts inevitably misclassify
    two adjacent italics' inner contents as one long italic.
    """
    s = re.sub(r"(\*\*[^*]+\*\*)([一-鿿])", r"\1 \2", s)
    s = re.sub(r"([一-鿿])(\*\*[^*])", r"\1 \2", s)
    return s


# --------- monster_2024 parser -----------------------------------------------

def parse_monster_2024(soup: BeautifulSoup, htm_path: Path) -> dict[str, Any]:
    """Parse a 2024 monster statblock to a dict with 'frontmatter' and 'body_sections'."""
    source, edition = detect_source_edition(htm_path)
    family = detect_family(htm_path)

    fm: dict[str, Any] = {"type": "monster"}

    # ---- name / en ----
    # Prefer the stat-block's H5 (the canonical monster name) over body H1/H2
    # because H1/H2 may be a family/super-section header (e.g. 邪教教宗.htm has
    # <H2>邪教成员 Cult Members</H2> at top, but the actual monster is in H5).
    sb_first = soup.find("div", class_="stat-block")
    h5 = sb_first.find("h5") if sb_first else None
    h_title = h5 or soup.find(["h1", "h2"])
    if h_title:
        zh, en = split_zh_en(h_title.get_text())
        fm["name"] = zh
        if en:
            fm["en"] = en

    # ---- family (if subdir variant) ----
    if family:
        fm["family"] = family

    # ---- subtitle ----
    sum_p = soup.find("p", class_="sum")
    if sum_p:
        fm["subtitle"] = clean_text(sum_p.get_text())

    # ---- habitat / treasure (div.HT) ----
    ht = soup.find("div", class_="HT")
    habitat = treasure = None
    if ht:
        txt = clean_text(ht.get_text())
        # "栖息地：任意；宝藏：武备，个体"
        m = re.search(r"栖息地[：:]\s*([^；;]+?)(?:[；;]|$)", txt)
        if m:
            habitat = m.group(1).strip()
            fm["habitat"] = habitat
        m = re.search(r"宝藏[：:]\s*(.+)$", txt)
        if m:
            treasure = [t.strip() for t in re.split(r"[，,]", m.group(1)) if t.strip()]
            fm["treasure"] = treasure

    # ---- statblock ----
    sb = soup.find("div", class_="stat-block")
    if not sb:
        return {"frontmatter": fm, "body_sections": [], "raw_intro": None}

    # sub-line: "中型或小型类人，中立"
    sub_line = sb.find("div", class_="sub-line")
    if sub_line:
        txt = clean_text(sub_line.get_text())
        # parse: size + creature_type + alignment
        # examples:
        #   "中型或小型类人，中立"
        #   "中型亡灵，普遍中立邪恶"
        #   "中型或小型类人（法师），中立"
        m = re.match(
            r"(.+?)(类人|兽|亡灵|龙类|龙|构装|妖精|元素|天族|邪魔|怪兽|植物|泥怪|异怪|多类型|巨人)"
            r"(?:（(.+?)）)?[，,]\s*(.+)$",
            txt,
        )
        if m:
            size_str = m.group(1).strip()
            sizes = re.split(r"或", size_str)
            fm["size"] = sizes if len(sizes) > 1 else sizes[0]
            fm["creature_type"] = m.group(2)
            if m.group(3):
                fm["type_subtag"] = m.group(3)
            fm["alignment"] = m.group(4).strip()

    # AC / 先攻 / HP / 速度 (first table inside stat-block)
    tables = sb.find_all("table", recursive=False)
    if tables:
        first_table = tables[0]
        for td in first_table.find_all("td"):
            txt = clean_text(td.get_text())
            m = re.match(r"AC\s+(\d+)(?:\s*[（(](.+?)[）)])?", txt)
            if m:
                fm["ac"] = int(m.group(1))
                if m.group(2):
                    fm["ac_note"] = m.group(2)
                continue
            m = re.match(r"先攻\s+([+-]?\d+)\s*[（(](\d+)[）)]", txt)
            if m:
                fm["initiative_bonus"] = int(m.group(1))
                fm["initiative_value"] = int(m.group(2))
                continue
            m = re.match(r"HP\s+(\d+)\s*[（(](.+?)[）)]", txt)
            if m:
                fm["hp"] = int(m.group(1))
                fm["hp_dice"] = m.group(2).replace(" ", "")
                continue
            m = re.match(r"速度\s+(.+)$", txt)
            if m:
                fm["speed"] = parse_speed(m.group(1))
                continue

    # stat-abilities table (6 abilities + saves)
    abil_table = sb.find("table", class_="stat-abilities")
    if abil_table:
        abilities, saves = parse_abilities(abil_table)
        fm["abilities"] = abilities
        if saves:
            fm["saves"] = saves

    # third table: skills, equipment, resist, immune, senses, languages, CR
    if len(tables) >= 3:
        third = tables[2]
        for tr in third.find_all("tr"):
            txt = clean_text(tr.get_text())
            parse_misc_row(txt, fm)

    # ---- body sections (h6 headers) ----
    body_sections = []
    for h6 in sb.find_all("h6"):
        section_name = clean_text(h6.get_text())
        # Collect content until next h6
        content_parts = []
        sib = h6.find_next_sibling()
        while sib and (not isinstance(sib, Tag) or sib.name != "h6"):
            if isinstance(sib, Tag):
                content_parts.append(sib)
            sib = sib.find_next_sibling()
        body_sections.append((section_name, content_parts))

    # ---- raw intro (description + flavor tables) ----
    raw_intro = collect_intro(soup, sb)

    return {"frontmatter": fm, "body_sections": body_sections, "raw_intro": raw_intro}


def parse_speed(s: str) -> dict[str, Any]:
    """'30尺，飞行 30 尺 (盘旋)' → {walk: 30, fly: 30, hover: true}"""
    out: dict[str, Any] = {}
    s = s.replace(" ", "")
    # split by Chinese comma
    parts = re.split(r"[，,、]", s)
    type_map = {
        "飞行": "fly", "游泳": "swim", "攀爬": "climb",
        "挖掘": "burrow", "穿行": "burrow",
    }
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(\d+)尺?$", part)
        if m:
            out["walk"] = int(m.group(1))
            continue
        for zh, en in type_map.items():
            if part.startswith(zh):
                rest = part[len(zh):]
                mm = re.match(r"^(\d+)尺?", rest)
                if mm:
                    out[en] = int(mm.group(1))
                if "盘旋" in rest:
                    out["hover"] = True
                break
        # plain walk if no prefix matched and contains a number
        if "walk" not in out:
            mm = re.search(r"(\d+)", part)
            if mm and not any(part.startswith(z) for z in type_map):
                out["walk"] = int(mm.group(1))
    return out


def parse_abilities(table: Tag) -> tuple[dict[str, int], dict[str, int]]:
    """Parse stat-abilities table → ({str,dex,con,int,wis,cha}, {save_overrides})."""
    abil_map_zh = {
        "力量": "str", "敏捷": "dex", "体质": "con",
        "智力": "int", "感知": "wis", "魅力": "cha",
    }
    abilities: dict[str, int] = {}
    saves: dict[str, int] = {}

    rows = table.find_all("tr")
    # Skip header row (first <tr>). Each data row has 3 ability blocks.
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        # Each ability block = 4 cells: name, value, mod, save (+ separator td)
        # Pattern: name, value, mod, save, [sep], name, value, mod, save, [sep], name, value, mod, save
        i = 0
        while i < len(cells):
            cell_txt = clean_text(cells[i].get_text())
            if cell_txt in abil_map_zh and i + 3 < len(cells):
                key = abil_map_zh[cell_txt]
                try:
                    val = int(clean_text(cells[i + 1].get_text()))
                    mod = int(clean_text(cells[i + 2].get_text()))
                    save = int(clean_text(cells[i + 3].get_text()))
                except ValueError:
                    i += 1
                    continue
                abilities[key] = val
                # Save is recorded only if it differs from mod (= proficient)
                if save != mod:
                    saves[key] = save
                i += 4
            else:
                i += 1
    return abilities, saves


def parse_misc_row(txt: str, fm: dict[str, Any]) -> None:
    """Parse one row from the third table (skills/equipment/resist/...)."""
    pairs = [
        ("技能", parse_skills, "skills"),
        ("装备", parse_csv_list, "equipment"),
        ("抗性", parse_csv_list, "damage_resist"),
        ("免疫", parse_immune, None),  # handled specially
        ("感官", parse_senses, "senses"),
        ("语言", parse_csv_list, "languages"),
    ]
    for label, parser, target in pairs:
        m = re.match(rf"{label}\s+(.+)$", txt)
        if m:
            value = parser(m.group(1))
            if target:
                fm[target] = value
            else:  # immune handles damage vs condition itself
                if isinstance(value, dict):
                    fm.update(value)
            return
    # CR row: "CR 5 (XP1,800；PB+3)" or "CR 1/8 (XP25；PB+2)"
    m = re.match(r"CR\s+([\d/]+)\s*[（(]\s*XP\s*([\d,]+)\s*[；;]\s*PB\s*\+(\d+)", txt)
    if m:
        cr_raw = m.group(1)
        try:
            fm["cr"] = int(cr_raw)
        except ValueError:
            fm["cr"] = cr_raw
        fm["xp"] = int(m.group(2).replace(",", ""))
        fm["pb"] = int(m.group(3))


def parse_skills(s: str) -> dict[str, int]:
    """'运动+10，表演+5' → {运动: 10, 表演: 5}"""
    out: dict[str, int] = {}
    for part in re.split(r"[，,、]", s):
        part = part.strip()
        m = re.match(r"^(.+?)\s*([+-]\d+)$", part)
        if m:
            out[m.group(1).strip()] = int(m.group(2))
    return out


def parse_csv_list(s: str) -> list[str]:
    """Generic comma-separated list."""
    return [p.strip() for p in re.split(r"[，,、；;]", s) if p.strip()]


def parse_immune(s: str) -> dict[str, Any]:
    """'毒素' or '心灵；魅惑（心灵屏障 Mind Blank 期间）' → split damage vs condition."""
    out: dict[str, Any] = {}
    damage_types = {
        "强酸", "钝击", "寒冷", "火焰", "力场", "闪电", "暗蚀",
        "穿刺", "毒素", "心灵", "光耀", "挥砍", "雷鸣",
    }
    conditions = {
        "魅惑", "失明", "震慑", "恐惧", "倒地", "麻痹", "石化",
        "中毒", "限制", "无意识", "失能", "力竭", "恐慌",
    }
    # Split by ；; first, then by ，,、
    chunks = re.split(r"[；;]", s)
    dam, cond, cond_cond = [], [], []
    for chunk in chunks:
        for part in re.split(r"[，,、]", chunk):
            part = part.strip()
            if not part:
                continue
            # Conditional? e.g. "魅惑（心灵屏障 Mind Blank 期间）"
            m = re.match(r"^([一-鿿]+)[（(](.+)[）)]$", part)
            if m:
                cname = m.group(1).strip()
                when = add_zh_en_space(m.group(2).strip())
                cond_cond.append({"condition": cname, "when": when})
                continue
            if part in damage_types:
                dam.append(part)
            elif part in conditions:
                cond.append(part)
            else:
                # Unknown — assume damage type
                dam.append(part)
    if dam:
        out["damage_immune"] = dam
    if cond:
        out["condition_immune"] = cond
    if cond_cond:
        out["condition_immune_conditional"] = cond_cond
    return out


def parse_senses(s: str) -> dict[str, Any]:
    """'真实视觉 120 尺，被动察觉 17' → {truesight: 120, passive_perception: 17}"""
    out: dict[str, Any] = {}
    sense_map = {
        "真实视觉": "truesight",
        "黑暗视觉": "darkvision",
        "盲视": "blindsight",
        "震颤感知": "tremorsense",
        "被动察觉": "passive_perception",
    }
    for part in re.split(r"[，,、]", s):
        part = clean_text(part)
        for zh, en in sense_map.items():
            if part.startswith(zh):
                rest = part[len(zh):]
                m = re.search(r"(\d+)", rest)
                if m:
                    out[en] = int(m.group(1))
                break
    return out


def collect_intro(soup: BeautifulSoup, sb: Tag) -> list[Tag]:
    """Collect intro elements before stat-block: description <P>, flavor tables."""
    body = soup.body or soup
    intro = []
    for child in body.find_all(recursive=False):
        if child is sb:
            break
        if child.name in {"h1", "h2"}:
            continue  # title is in frontmatter
        if child.name == "p" and child.get("class") and "sum" in child.get("class", []):
            continue  # subtitle handled
        if child.name == "div" and child.get("class") and "HT" in child.get("class", []):
            continue  # habitat handled
        intro.append(child)
    return intro


# --------- monster_family parser ---------------------------------------------

def parse_monster_family(soup: BeautifulSoup, htm_path: Path) -> dict[str, Any]:
    source, edition = detect_source_edition(htm_path)
    fm: dict[str, Any] = {"type": "monster_family", "source": source, "edition": edition}

    h_title = soup.find(["h1", "h2"])
    if h_title:
        zh, en = split_zh_en(h_title.get_text())
        fm["name"] = zh
        if en:
            fm["en"] = en

    sum_p = soup.find("p", class_="sum")
    if sum_p:
        fm["subtitle"] = clean_text(sum_p.get_text())

    ht = soup.find("div", class_="HT")
    if ht:
        txt = clean_text(ht.get_text())
        m = re.search(r"栖息地[：:]\s*([^；;]+?)(?:[；;]|$)", txt)
        if m:
            fm["habitat"] = m.group(1).strip()
        m = re.search(r"宝藏[：:]\s*(.+)$", txt)
        if m:
            fm["treasure"] = [t.strip() for t in re.split(r"[，,]", m.group(1)) if t.strip()]

    # members: scan sibling .htm files in the same directory
    members = []
    for sibling in htm_path.parent.glob("*.htm"):
        if sibling.stem == htm_path.stem:
            continue  # skip self
        if sibling.stem.endswith("总") and sibling.stem != htm_path.stem:
            continue  # other family pages
        members.append(sibling.stem)
    if members:
        fm["members"] = members

    # intro elements (description, flavor quotes)
    intro = []
    body = soup.body or soup
    for child in body.find_all(recursive=False):
        if child.name in {"h1", "h2"}:
            continue
        if child.name == "p" and "sum" in (child.get("class") or []):
            continue
        if child.name == "div" and "HT" in (child.get("class") or []):
            continue
        intro.append(child)

    return {"frontmatter": fm, "intro": intro}


# --------- monster_2014 (WinCHM/DNDBeyond style) parser ----------------------

# Maps Chinese statblock field labels → fm key
_M2014_FIELDS = {
    "AC": ("ac", "ac_note"),
    "HP": ("hp", "hp_dice"),
    "速度": "speed",
    "豁免": "saves",
    "技能": "skills",
    "伤害抗性": "damage_resist",
    "伤害免疫": "damage_immune",
    "状态免疫": "condition_immune",
    "状态抗性": "condition_resist",
    "感官": "senses",
    "语言": "languages",
    "挑战等级": "cr_block",
}

# Headers marking 2014 statblock sub-sections.
_M2014_SECTION_LABELS = {
    "动作", "Actions", "动作 Actions",
    "反应", "Reactions", "反应 Reactions",
    "传奇动作", "Legendary Actions", "传奇动作 Legendary Actions",
    "巢穴动作", "Lair Actions",
    "区域效应", "Regional Effects",
    "附赠动作", "Bonus Actions",
}


def split_by_br(p: Tag) -> list[list]:
    """Split <p>'s direct children at every <br> into groups of nodes."""
    groups: list[list] = []
    current: list = []
    for child in p.children:
        if isinstance(child, Tag) and child.name == "br":
            if current:
                groups.append(current)
                current = []
        else:
            current.append(child)
    if current:
        groups.append(current)
    return groups


def nodes_to_text(nodes: list) -> str:
    """Flatten a list of nodes (after split_by_br) into a single string."""
    parts: list[str] = []
    for n in nodes:
        if isinstance(n, NavigableString):
            parts.append(str(n))
        else:
            parts.append(n.get_text())
    return clean_text("".join(parts))


def parse_subline_2014(text: str, fm: dict[str, Any]) -> None:
    """'中型亡灵，普遍中立邪恶' → size + creature_type + alignment."""
    text = clean_text(text)
    m = re.match(
        r"(.+?)(类人|兽|亡灵|龙类|龙|构装|妖精|元素|天族|邪魔|怪兽|"
        r"植物|泥怪|异怪|多类型|巨人)(?:[（(](.+?)[）)])?[，,]\s*(.+)$",
        text,
    )
    if m:
        size_str = m.group(1).strip()
        sizes = re.split(r"或", size_str)
        fm["size"] = sizes if len(sizes) > 1 else sizes[0]
        fm["creature_type"] = m.group(2)
        if m.group(3):
            fm["type_subtag"] = m.group(3)
        fm["alignment"] = m.group(4).strip()


def parse_2014_ac(line: str, fm: dict[str, Any]) -> None:
    """'AC：17 (天生护甲)' or 'AC ：11 (天生护甲)' → ac, ac_note"""
    m = re.search(r"AC\s*[：:]\s*(\d+)(?:\s*[（(](.+?)[）)])?", line)
    if m:
        fm["ac"] = int(m.group(1))
        if m.group(2):
            fm["ac_note"] = m.group(2).strip()


def parse_2014_hp(line: str, fm: dict[str, Any]) -> None:
    """'HP： 165 (22d8 + 66)' → hp=165, hp_dice='22d8+66'"""
    m = re.search(r"HP\s*[：:]\s*(\d+)(?:\s*[（(](.+?)[）)])?", line)
    if m:
        fm["hp"] = int(m.group(1))
        if m.group(2):
            fm["hp_dice"] = m.group(2).replace(" ", "")


def parse_2014_speed(line: str, fm: dict[str, Any]) -> None:
    """'速度： 30 尺， 飞行 30 尺 (盘旋)' → speed dict"""
    m = re.search(r"速度[：:]\s*(.+)$", line)
    if m:
        fm["speed"] = parse_speed(m.group(1))


def parse_2014_abilities(lines: list[str], fm: dict[str, Any]) -> int:
    """Parse 2 lines of abilities. Returns count of lines consumed (1 or 2).

    Format examples:
        '力量11 (+0) 敏捷18 (+4) 体质16 (+3)'
        '智力19 (+4) 感知14 (+2) 魅力12 (+1)'
    """
    consumed = 0
    abil_map = {
        "力量": "str", "敏捷": "dex", "体质": "con",
        "智力": "int", "感知": "wis", "魅力": "cha",
    }
    abilities = fm.setdefault("abilities", {})
    for line in lines:
        found_any = False
        for zh, en in abil_map.items():
            m = re.search(rf"{zh}\s*(\d+)\s*[（(][+-]?\d+[）)]", line)
            if m:
                abilities[en] = int(m.group(1))
                found_any = True
        if found_any:
            consumed += 1
        else:
            break
    return consumed


def parse_2014_saves(line: str, fm: dict[str, Any]) -> None:
    """'豁免： 智力 +9， 感知 +7' → saves dict"""
    m = re.search(r"豁免[：:]\s*(.+)$", line)
    if not m:
        return
    abil_map = {"力量": "str", "敏捷": "dex", "体质": "con",
                "智力": "int", "感知": "wis", "魅力": "cha"}
    saves: dict[str, int] = {}
    for ab_zh, ab_en in abil_map.items():
        sm = re.search(rf"{ab_zh}\s*([+-]\d+)", m.group(1))
        if sm:
            saves[ab_en] = int(sm.group(1))
    if saves:
        fm["saves"] = saves


def parse_2014_skills(line: str, fm: dict[str, Any]) -> None:
    """'技能： 奥秘 +14， 察觉+7' → skills dict"""
    m = re.search(r"技能[：:]\s*(.+)$", line)
    if not m:
        return
    out = {}
    for part in re.split(r"[，,、]", m.group(1)):
        part = part.strip()
        mm = re.match(r"^(\S+?)\s*([+-]?\d+)$", part)
        if mm:
            out[mm.group(1).strip()] = int(mm.group(2))
    if out:
        fm["skills"] = out


def parse_2014_cr_block(line: str, fm: dict[str, Any]) -> None:
    """'挑战等级： 15 (13，000 XP)  熟练加值 +5' → cr, xp, pb"""
    m = re.search(r"挑战等级[：:]\s*([\d/]+)\s*[（(]\s*([\d,，]+)\s*XP", line)
    if m:
        cr_raw = m.group(1)
        try:
            fm["cr"] = int(cr_raw)
        except ValueError:
            fm["cr"] = cr_raw
        xp_str = m.group(2).replace(",", "").replace("，", "")
        fm["xp"] = int(xp_str)
    m = re.search(r"熟练加值\s*[+]?(\d+)", line)
    if m:
        fm["pb"] = int(m.group(1))


def parse_monster_2014(soup: BeautifulSoup, htm_path: Path) -> dict[str, Any]:
    """Parse DNDBeyond/WinCHM-style 2014 monster statblock."""
    source, edition = detect_source_edition(htm_path)
    family = detect_family(htm_path)

    fm: dict[str, Any] = {"type": "monster"}

    # Title: first <p><strong><font ... size=5>name English</font></strong></p>
    name_found = False
    for p in soup.find_all("p"):
        font = p.find("font", attrs={"size": "5"})
        if font:
            zh, en = split_zh_en(font.get_text())
            if zh:
                fm["name"] = zh
                if en:
                    fm["en"] = en
                name_found = True
                break

    # Find the statblock P (first P containing all required field markers).
    # Use regex to tolerate optional whitespace around the colon.
    sb_p = None
    for p in soup.find_all("p"):
        text = p.get_text()
        if _AC_RE.search(text) and _HP_RE.search(text) and _CR_RE.search(text):
            sb_p = p
            break
    if sb_p is None:
        return {"frontmatter": fm, "body_sections": [], "raw_intro": None}

    # Backup name from statblock's first <strong> (with color #800000)
    if not name_found:
        first_strong = sb_p.find("strong")
        if first_strong:
            zh, en = split_zh_en(clean_text(first_strong.get_text()))
            if zh:
                fm["name"] = zh
                if en:
                    fm["en"] = en

    # Subline from first <em> inside sb_p
    em = sb_p.find("em")
    if em:
        parse_subline_2014(em.get_text(), fm)

    # Split sb_p contents by <br>; each group becomes a "line".
    groups = split_by_br(sb_p)
    lines_text = [nodes_to_text(g) for g in groups]
    # Drop empty leading lines
    lines_text = [ln for ln in lines_text if ln]

    # Parse statblock data lines until we hit a section marker.
    section_start_idx = None
    for i, line in enumerate(lines_text):
        # Section header: "动作Actions" / "反应Reactions" / "传奇动作Legendary Actions" etc.
        sec_hit = any(
            (line.startswith(lbl) or line == lbl) for lbl in _M2014_SECTION_LABELS
        )
        if sec_hit:
            section_start_idx = i
            break
        # Pre-section data line (use regex to tolerate optional whitespace)
        if _AC_RE.search(line):
            parse_2014_ac(line, fm)
        if _HP_RE.search(line):
            parse_2014_hp(line, fm)
        if re.search(r"速度\s*[：:]", line):
            parse_2014_speed(line, fm)
        if re.search(r"豁免\s*[：:]", line):
            parse_2014_saves(line, fm)
        if re.search(r"技能\s*[：:]", line):
            parse_2014_skills(line, fm)
        mm = re.search(r"伤害抗性\s*[：:]\s*(.+)$", line)
        if mm:
            fm["damage_resist"] = parse_csv_list(mm.group(1))
        mm = re.search(r"伤害免疫\s*[：:]\s*(.+)$", line)
        if mm:
            fm["damage_immune"] = parse_csv_list(mm.group(1))
        mm = re.search(r"(?:状态|条件)免疫\s*[：:]\s*(.+)$", line)
        if mm:
            fm["condition_immune"] = parse_csv_list(mm.group(1))
        mm = re.search(r"伤害易伤\s*[：:]\s*(.+)$", line)
        if mm:
            fm["damage_vulnerable"] = parse_csv_list(mm.group(1))
        mm = re.search(r"感官\s*[：:]\s*(.+)$", line)
        if mm:
            fm["senses"] = parse_senses(mm.group(1))
        mm = re.search(r"语言\s*[：:]\s*(.+)$", line)
        if mm:
            fm["languages"] = parse_csv_list(mm.group(1))
        if _CR_RE.search(line):
            parse_2014_cr_block(line, fm)
        # 6 abilities (numbers + paren modifier)
        if re.search(r"(力量|敏捷|体质|智力|感知|魅力)\s*\d+\s*[（(]", line):
            abil_map = {
                "力量": "str", "敏捷": "dex", "体质": "con",
                "智力": "int", "感知": "wis", "魅力": "cha",
            }
            abilities = fm.setdefault("abilities", {})
            for zh, en in abil_map.items():
                mm = re.search(rf"{zh}\s*(\d+)\s*[（(][+-]?\d+[）)]", line)
                if mm:
                    abilities[en] = int(mm.group(1))
        # Legendary resistance trait
        if "传奇抗性" in line:
            mm = re.search(r"传奇抗性[^(（]*[（(](\d+/[Dd]ay)[）)]", line)
            if mm:
                fm["legendary_resistance"] = mm.group(1)

    if family:
        # 2014 怪物 file in a subdir like "DNDBeyond/怪物纲要1/" — family is the
        # subdir but those are book names, not monster families. Skip.
        pass

    # Body sections: parse traits / actions / reactions / legendary
    body_sections = build_body_sections_2014(lines_text, section_start_idx)

    # Intro: description paragraphs + flavor tables BEFORE sb_p
    raw_intro = collect_intro_2014(soup, sb_p)

    fm.setdefault("source", source)
    fm.setdefault("edition", "2014")

    return {"frontmatter": fm, "body_sections": body_sections, "raw_intro": raw_intro}


def build_body_sections_2014(
    lines: list[str], section_start: int | None
) -> list[tuple[str, list[Tag]]]:
    """Split lines into traits/actions/reactions/legendary sections.

    Returns a list of (section_name_zh, content_lines) tuples. The content
    is plain text (already merged); we re-pack as fake <p> Tags for the
    shared renderer.
    """
    # Find trait region: between sub-line/CR and section_start
    # The traits typically come after CR line. Look for lines that start with
    # bold trait-name pattern.
    # For simplicity, slice from "first line after CR row" to section_start.
    traits: list[str] = []
    actions: list[str] = []
    reactions: list[str] = []
    bonus_actions: list[str] = []
    legendary: list[str] = []

    # Find CR line index
    cr_idx = next(
        (i for i, ln in enumerate(lines) if "挑战等级" in ln), -1
    )
    if cr_idx == -1:
        return []

    end_idx = section_start if section_start is not None else len(lines)
    # Lines between CR and end → traits (but pre-CR line may also include
    # 'legendary_resistance' which is already parsed). We treat each line as
    # a potential trait entry.
    for ln in lines[cr_idx + 1: end_idx]:
        if ln.strip():
            traits.append(ln)

    # From section_start onward, route into appropriate bucket.
    if section_start is not None:
        current_bucket = traits
        for ln in lines[section_start:]:
            stripped = ln.strip()
            if not stripped:
                continue
            # Section switch?
            if any(stripped.startswith(lbl) for lbl in ("动作", "Actions", "动作Actions", "动作 Actions")) and \
               not any(stripped.startswith(s) for s in ("动作如潮",)):
                current_bucket = actions
                # Skip the header line itself
                continue
            if stripped.startswith("反应") or stripped.startswith("Reactions") or "反应Reactions" in stripped:
                current_bucket = reactions
                continue
            if "传奇动作" in stripped and "Legendary" in stripped or stripped.startswith("传奇动作"):
                current_bucket = legendary
                continue
            if stripped.startswith("附赠动作") or "Bonus Actions" in stripped:
                current_bucket = bonus_actions
                continue
            current_bucket.append(ln)

    out: list[tuple[str, list[Tag]]] = []
    for label, items in [
        ("特性 Traits", traits),
        ("动作 Actions", actions),
        ("附赠动作 Bonus Actions", bonus_actions),
        ("反应 Reactions", reactions),
        ("传奇动作 Legendary Actions", legendary),
    ]:
        if items:
            out.append((label, items))
    return out


def collect_intro_2014(soup: BeautifulSoup, sb_p: Tag) -> list[Tag]:
    """Collect description + flavor blocks before the statblock P."""
    intro = []
    body = soup.body or soup
    for child in body.find_all(recursive=False):
        if child is sb_p:
            break
        if isinstance(child, Tag) and child.name in {"style", "script"}:
            continue
        # Skip the title P (has <font size="5">)
        if isinstance(child, Tag) and child.name == "p":
            if child.find("font", attrs={"size": "5"}):
                continue
        intro.append(child)
    return intro


def render_monster_2014(parsed: dict[str, Any], htm_path: Path) -> str:
    """Render a 2014 monster. Reuses the 2024 layout where compatible, but
    body sections are stored as text lines (not Tags), so we handle them here.
    """
    fm = parsed["frontmatter"]
    source, _ = detect_source_edition(htm_path)
    fm.setdefault("source", source)
    fm.setdefault("edition", "2014")

    # Use block-style YAML so short fm doesn't collapse to one line.
    lines = ["---", render_yaml(fm, flow=False).rstrip(), "---", ""]

    # H1 title
    name = fm.get("name", "")
    en = fm.get("en", "")
    title = f"# {name} {en}".strip()
    lines.append(title)
    lines.append("")

    # Intro
    intro = parsed.get("raw_intro") or []
    intro_chunk = []
    for el in intro:
        rendered = render_intro_element(el)
        if rendered:
            intro_chunk.append(rendered)
    if intro_chunk:
        intro_text = "\n\n".join(intro_chunk)
        intro_text = promote_flavor_table_title(intro_text)
        lines.append(intro_text)
        lines.append("")

    # Statblock summary (reuse 2024 format)
    lines.append("## 数据栏")
    lines.append("")

    size = fm.get("size")
    if isinstance(size, list):
        size_str = "或".join(size)
    else:
        size_str = size or ""
    type_str = fm.get("creature_type", "")
    subtag = fm.get("type_subtag")
    if subtag:
        type_str = f"{type_str}（{subtag}）"
    alignment = fm.get("alignment", "")
    lines.append(f"{size_str}{type_str}，{alignment}")
    lines.append("")

    # AC/HP/速度
    lines.append("| | 值 |")
    lines.append("|---|---|")
    ac_line = str(fm.get("ac", ""))
    if fm.get("ac_note"):
        ac_line = f"{fm['ac']}（{fm['ac_note']}）"
    lines.append(f"| **AC** | {ac_line} |")
    hp_line = str(fm.get("hp", ""))
    if fm.get("hp_dice"):
        hp_line = f"{fm['hp']} ({fm['hp_dice']})"
    lines.append(f"| **HP** | {hp_line} |")
    speed = fm.get("speed", {})
    speed_strs = []
    if speed.get("walk"):
        speed_strs.append(f"{speed['walk']} 尺")
    for k_zh, k_en in [("飞行", "fly"), ("游泳", "swim"), ("攀爬", "climb"), ("挖掘", "burrow")]:
        if speed.get(k_en):
            extra = "（盘旋）" if k_en == "fly" and speed.get("hover") else ""
            speed_strs.append(f"{k_zh} {speed[k_en]} 尺{extra}")
    lines.append(f"| **速度** | {'，'.join(speed_strs)} |")
    lines.append("")

    # Abilities table
    abil = fm.get("abilities", {})
    saves = fm.get("saves", {})
    if abil:
        lines.append("| 属性 | 值 | 调整 | 豁免 |")
        lines.append("|------|----|------|------|")
        for k_en, k_zh in [("str", "力量"), ("dex", "敏捷"), ("con", "体质"),
                           ("int", "智力"), ("wis", "感知"), ("cha", "魅力")]:
            v = abil.get(k_en, "")
            if v == "":
                continue
            mod = (v - 10) // 2
            save = saves.get(k_en, mod)
            sign_mod = "+" if mod >= 0 else ""
            sign_save = "+" if save >= 0 else ""
            lines.append(f"| {k_zh} | {v} | {sign_mod}{mod} | {sign_save}{save} |")
        lines.append("")

    misc_lines = []
    if fm.get("skills"):
        skl = "，".join(f"{k} +{v}" if v >= 0 else f"{k} {v}" for k, v in fm["skills"].items())
        misc_lines.append(f"- **技能**：{skl}")
    if fm.get("damage_resist"):
        misc_lines.append(f"- **抗性**：{'，'.join(fm['damage_resist'])}")
    immune_parts = []
    if fm.get("damage_immune"):
        immune_parts.extend(fm["damage_immune"])
    if fm.get("condition_immune"):
        immune_parts.extend(fm["condition_immune"])
    if immune_parts:
        misc_lines.append(f"- **免疫**：{'，'.join(immune_parts)}")
    if fm.get("senses"):
        sense_map_reverse = {
            "truesight": "真实视觉", "darkvision": "黑暗视觉",
            "blindsight": "盲视", "tremorsense": "震颤感知",
            "passive_perception": "被动察觉",
        }
        sense_strs = []
        for k_en, k_zh in sense_map_reverse.items():
            if k_en in fm["senses"]:
                v = fm["senses"][k_en]
                if k_en == "passive_perception":
                    sense_strs.append(f"{k_zh} {v}")
                else:
                    sense_strs.append(f"{k_zh} {v} 尺")
        misc_lines.append(f"- **感官**：{'，'.join(sense_strs)}")
    if fm.get("languages"):
        misc_lines.append(f"- **语言**：{'，'.join(fm['languages'])}")
    if fm.get("cr") is not None:
        cr_str = str(fm["cr"])
        xp_str = f"{fm.get('xp', 0):,}"
        pb_str = f"+{fm.get('pb', 0)}"
        misc_lines.append(f"- **CR**：{cr_str}（XP {xp_str}；PB {pb_str}）")
    if fm.get("legendary_resistance"):
        misc_lines.append(f"- **传奇抗性**：{fm['legendary_resistance']}")
    lines.extend(misc_lines)
    lines.append("")

    # Body sections (traits/actions/...). The 2014 parser stores text lines,
    # not Tags; render each line as a paragraph.
    for section_name, content_lines in parsed.get("body_sections", []):
        lines.append(f"## {add_zh_en_space(section_name)}")
        lines.append("")
        for ln in content_lines:
            ln_md = add_zh_en_space(normalize_dc(ln.strip()))
            # Bold-up the trait/action name at the start (until first 。 or .)
            mm = re.match(r"^([^。.]+?[。.])\s*(.*)$", ln_md)
            if mm:
                head = mm.group(1).rstrip()
                rest = mm.group(2)
                ln_md = f"**{head}** {rest}" if rest else f"**{head}**"
            lines.append(ln_md)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# --------- spell_collection parser -------------------------------------------

# Spell schools used in 2024 PHB
SPELL_SCHOOLS = {"塑能", "防护", "死灵", "幻术", "变化", "咒法", "惑控", "预言"}

# All recognized class names (for parsing 'X环 学派（职业列表）')
SPELL_CLASSES = {
    "吟游诗人", "牧师", "德鲁伊", "圣武士", "游侠",
    "术士", "魔契师", "法师", "战士", "游荡者", "野蛮人", "武僧",
}


def parse_spell_level_filename(stem: str) -> tuple[int, str]:
    """'0环' → (0, '戏法')  ;  '3环' → (3, '3 环')"""
    m = re.match(r"^(\d+)环$", stem)
    if not m:
        return -1, stem
    n = int(m.group(1))
    return n, "戏法" if n == 0 else f"{n} 环"


def parse_spell_meta_em(em_text: str) -> dict[str, Any]:
    """Parse '三环 死灵（牧师、法师）' → {school, classes, school_label}.

    `school_label` is the original 'X环 学派' or '学派 戏法' string for display.
    """
    out: dict[str, Any] = {}
    txt = clean_text(em_text)
    # Strip class list from parens
    m_classes = re.search(r"[（(](.+?)[）)]", txt)
    if m_classes:
        out["classes"] = parse_csv_list(m_classes.group(1))
        txt_no_classes = re.sub(r"\s*[（(].+?[）)]\s*$", "", txt).strip()
    else:
        txt_no_classes = txt
    out["school_label"] = txt_no_classes
    # Extract school name (must be one of SPELL_SCHOOLS)
    for sch in SPELL_SCHOOLS:
        if sch in txt_no_classes:
            out["school"] = sch
            break
    return out


def parse_spell_paragraph(p: Tag) -> dict[str, Any]:
    """Parse the <P> following an <H4> spell title.

    Extracts: school, classes, casting_time, range, components, duration,
    description, upcast (升环施法/戏法强化).
    """
    spell: dict[str, Any] = {}

    # First <em>: 'X环 学派（职业列表）'
    first_em = p.find("em")
    if first_em:
        spell.update(parse_spell_meta_em(first_em.get_text()))

    # Walk children: between <STRONG>label：</STRONG> and next <BR>/<STRONG>
    # the text is the field value.
    field_map = {
        "施法时间": "casting_time",
        "施法距离": "range",
        "法术成分": "components",
        "持续时间": "duration",
    }
    body_segments: list[str] = []
    current_strong_label: str | None = None
    upcast_segments: list[str] = []
    in_upcast = False
    first_em_seen = False

    def push(seg: str) -> None:
        if in_upcast:
            upcast_segments.append(seg)
        else:
            body_segments.append(seg)

    for child in p.children:
        if isinstance(child, NavigableString):
            text = str(child).replace("\n", " ")
            if not text.strip():
                continue
            if current_strong_label and current_strong_label in field_map:
                spell[field_map[current_strong_label]] = clean_text(text)
                current_strong_label = None
            else:
                push(text)
        elif isinstance(child, Tag):
            if child.name == "br":
                current_strong_label = None
                continue
            if child.name == "strong":
                stxt = clean_text(child.get_text()).rstrip("：:。.").strip()
                if stxt in field_map:
                    current_strong_label = stxt
                elif stxt in ("升环施法", "戏法强化"):
                    in_upcast = True
                    upcast_segments.append(f"**{stxt}。** ")
                    current_strong_label = None
                else:
                    push(f"**{add_zh_en_space(stxt)}**")
                    current_strong_label = None
            elif child.name == "em":
                if not first_em_seen:
                    # First em is the meta line (school/classes) — skip.
                    first_em_seen = True
                    continue
                etxt = clean_text(child.get_text())
                push(f"*{add_zh_en_space(etxt)}*")
            elif child.name == "u":
                push(child.get_text())
            else:
                push(child.get_text())

    def finalize(segments: list[str]) -> str:
        text = "".join(segments)
        text = re.sub(r"\s+", " ", text)
        text = add_zh_en_space(text)
        text = normalize_dc(text)
        return text.strip()

    if body_segments:
        spell["description"] = finalize(body_segments)
    if upcast_segments:
        spell["upcast"] = finalize(upcast_segments)

    # Also collect BLOCKQUOTE following this P (sub-options like 魔法伎俩's 6 modes)
    next_sib = p.find_next_sibling()
    if next_sib and next_sib.name == "blockquote":
        spell["sub_options"] = render_blockquote(next_sib)

    return spell


def render_blockquote(bq: Tag) -> str:
    """Render BLOCKQUOTE containing <P> with multiple <STRONG>name。</STRONG>desc<BR>...
    into a markdown unordered list.
    """
    items: list[str] = []
    for p in bq.find_all("p"):
        # Walk: <strong>name。</strong>desc<br><strong>name。</strong>desc...
        parts: list[str] = []
        current: list[str] = []

        def flush() -> None:
            if current:
                joined = "".join(current).strip()
                joined = re.sub(r"\s+", " ", joined)
                joined = add_zh_en_space(joined)
                if joined:
                    parts.append(joined)
                current.clear()

        for child in p.children:
            if isinstance(child, NavigableString):
                current.append(str(child))
            elif child.name == "br":
                flush()
            elif child.name == "strong":
                stxt = clean_text(child.get_text())
                current.append(f"**{add_zh_en_space(stxt)}**")
            elif child.name == "u":
                current.append(child.get_text())
            elif child.name == "em":
                etxt = clean_text(child.get_text())
                current.append(f"*{add_zh_en_space(etxt)}*")
            else:
                current.append(child.get_text())
        flush()
        items.extend(parts)
    return "\n".join(f"- {it}" for it in items)


def parse_spell_collection(soup: BeautifulSoup, htm_path: Path) -> dict[str, Any]:
    source, edition = detect_source_edition(htm_path)
    level, level_name = parse_spell_level_filename(htm_path.stem)

    fm: dict[str, Any] = {
        "type": "spell_collection",
        "level": level,
        "level_name": level_name,
        "source": source,
        "edition": edition,
    }

    spells_index: list[dict[str, Any]] = []
    spell_bodies: list[dict[str, Any]] = []

    for h4 in soup.find_all("h4"):
        title = clean_text(h4.get_text())
        # 'name｜English'
        m = re.match(r"^(.+?)[｜|](.+)$", title)
        if not m:
            continue
        name = m.group(1).strip()
        en = m.group(2).strip()

        # Find the next P that contains the meta + body
        p = h4.find_next_sibling()
        while p and p.name != "p":
            p = p.find_next_sibling()
        if not p:
            continue

        spell_data = parse_spell_paragraph(p)
        spell_data["name"] = name
        spell_data["en"] = en
        spell_bodies.append(spell_data)

        # Build index entry (compact)
        idx_entry: dict[str, Any] = {
            "name": name,
            "en": en,
        }
        for k in ("school", "classes", "casting_time", "range",
                  "components", "duration"):
            if k in spell_data:
                idx_entry[k] = spell_data[k]
        spells_index.append(idx_entry)

    fm["total_count"] = len(spell_bodies)
    fm["spells"] = spells_index

    return {"frontmatter": fm, "spell_bodies": spell_bodies}


def render_spell_collection(parsed: dict[str, Any], htm_path: Path) -> str:
    fm = parsed["frontmatter"]
    lines = ["---", render_yaml(fm).rstrip(), "---", ""]

    level_name = fm.get("level_name", "")
    lines.append(f"# {level_name} 法术")
    lines.append("")

    for spell in parsed["spell_bodies"]:
        name = spell.get("name", "")
        en = spell.get("en", "")
        lines.append(f"## {name} ｜ {en}")
        lines.append("")

        # Compact field list
        meta_lines: list[str] = []
        # Prefer original 'school_label' (e.g. '三环 死灵' or '塑能 戏法')
        # for natural ordering; fall back to constructed.
        school_str = spell.get("school_label") or spell.get("school", "")
        if school_str:
            meta_lines.append(f"- **学派**：{school_str}")
        if spell.get("classes"):
            meta_lines.append(f"- **职业**：{'、'.join(spell['classes'])}")
        for label, key in [
            ("施法时间", "casting_time"),
            ("施法距离", "range"),
            ("法术成分", "components"),
            ("持续时间", "duration"),
        ]:
            if spell.get(key):
                meta_lines.append(f"- **{label}**：{spell[key]}")
        lines.extend(meta_lines)
        lines.append("")

        if spell.get("description"):
            lines.append(spell["description"])
            lines.append("")
        if spell.get("sub_options"):
            lines.append(spell["sub_options"])
            lines.append("")
        if spell.get("upcast"):
            lines.append(spell["upcast"])
            lines.append("")

        lines.append("---")
        lines.append("")

    # Trim trailing separator
    while lines and lines[-1] in {"---", ""}:
        lines.pop()
    return "\n".join(lines).rstrip() + "\n"


# --------- generic document parser -------------------------------------------

def parse_document(soup: BeautifulSoup, htm_path: Path) -> dict[str, Any]:
    """Parse a generic reference document: equipment/rules/class blurbs.

    Captures top-level structure (H1-H6 + paragraphs + tables + lists +
    blockquotes) without enforcing a strict schema. The frontmatter only
    records type/name/category/source/edition.
    """
    body = soup.body or soup
    source, edition = detect_source_edition(htm_path)

    fm: dict[str, Any] = {"type": "document"}

    # Title: first H1/H2 in body, or fall back to filename
    title_el = body.find(["h1", "h2"])
    if title_el:
        zh, en = split_zh_en(title_el.get_text())
        fm["name"] = zh
        if en:
            fm["en"] = en
    else:
        fm["name"] = htm_path.stem

    # Category = parent directory name (e.g. "装备", "进行游戏")
    parent = htm_path.parent.name
    if parent not in {"", htm_path.parts[0] if htm_path.parts else ""}:
        fm["category"] = parent

    fm["source"] = source
    fm["edition"] = edition

    # Body: walk top-level elements after title
    body_parts: list[str] = []
    title_seen = False
    for el in body.find_all(recursive=False):
        if el is title_el and not title_seen:
            title_seen = True
            continue
        if isinstance(el, Tag) and el.name in {"style", "script"}:
            continue
        rendered = render_document_element(el)
        if rendered and rendered.strip():
            body_parts.append(rendered.rstrip())

    return {"frontmatter": fm, "body_parts": body_parts}


def render_document_element(el: Tag) -> str:
    """Convert a single HTML element to MD."""
    if not isinstance(el, Tag):
        text = clean_text(str(el))
        return text if text else ""

    name = el.name
    if name in {"h1", "h2"}:
        return f"# {add_zh_en_space(clean_text(el.get_text()))}"
    if name == "h3":
        return f"## {add_zh_en_space(clean_text(el.get_text()))}"
    if name == "h4":
        return f"### {add_zh_en_space(clean_text(el.get_text()))}"
    if name == "h5":
        return f"#### {add_zh_en_space(clean_text(el.get_text()))}"
    if name == "h6":
        return f"##### {add_zh_en_space(clean_text(el.get_text()))}"
    if name == "p":
        return render_paragraph(el)
    if name == "table":
        return render_flavor_table(el)
    if name in {"ul", "ol"}:
        return render_list(el, ordered=(name == "ol"))
    if name == "blockquote":
        return render_blockquote_as_md(el)
    if name == "div":
        # Recurse over children
        inner = []
        for c in el.find_all(recursive=False):
            if isinstance(c, Tag) and c.name in {"style", "script"}:
                continue
            rendered = render_document_element(c)
            if rendered and rendered.strip():
                inner.append(rendered.rstrip())
        return "\n\n".join(inner)
    if name in {"br", "hr"}:
        return ""
    if name == "img":
        # Drop images (or could keep src)
        return ""
    # Fallback: treat as paragraph-like
    return render_paragraph(el)


def render_list(el: Tag, ordered: bool = False) -> str:
    """Render <ul>/<ol> as MD list."""
    items = []
    for i, li in enumerate(el.find_all("li", recursive=False), 1):
        inner = render_inline_content(li)
        if not inner.strip():
            continue
        marker = f"{i}." if ordered else "-"
        items.append(f"{marker} {inner}")
    return "\n".join(items)


def render_inline_content(el: Tag) -> str:
    """Render the inline children of an element, ignoring nested block tags."""
    parts: list[str] = []
    for child in el.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif child.name == "br":
            parts.append("\n\n")
        elif child.name in {"strong", "b"}:
            parts.append(f"**{add_zh_en_space(clean_text(child.get_text()))}**")
        elif child.name in {"em", "i"}:
            parts.append(f"*{add_zh_en_space(clean_text(child.get_text()))}*")
        elif child.name == "u":
            parts.append(child.get_text())
        elif child.name == "a":
            parts.append(child.get_text())
        elif child.name in {"div", "p"}:
            # Inline-render the contents
            parts.append(render_inline_content(child))
        else:
            parts.append(child.get_text())
    text = "".join(parts)
    text = re.sub(r"\s+", " ", text)
    text = add_zh_en_space(text)
    text = normalize_dc(text)
    return text.strip()


def render_blockquote_as_md(bq: Tag) -> str:
    """Render <blockquote> as MD blockquote (lines prefixed with > )."""
    inner_parts = []
    for c in bq.find_all(recursive=False):
        if isinstance(c, Tag) and c.name in {"style", "script"}:
            continue
        rendered = render_document_element(c)
        if rendered and rendered.strip():
            inner_parts.append(rendered.rstrip())
    text = "\n\n".join(inner_parts)
    # Prefix each line with '> '
    lines = text.split("\n")
    return "\n".join(f"> {ln}" if ln else ">" for ln in lines)


def render_document(parsed: dict[str, Any], htm_path: Path) -> str:
    fm = parsed["frontmatter"]
    lines = ["---", render_yaml(fm, flow=False).rstrip(), "---", ""]

    name = fm.get("name", "")
    en = fm.get("en", "")
    title = f"# {name} {en}".strip()
    lines.append(title)
    lines.append("")

    body_parts = parsed.get("body_parts", [])
    for p in body_parts:
        lines.append(p)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# --------- markdown renderer -------------------------------------------------

def render_yaml(data: dict[str, Any], flow: Any = None) -> str:
    """Render frontmatter with field order preservation.

    flow=None (default): auto — short nested dicts/lists become flow style.
    flow=False: all block (multi-line). Used for flat document frontmatter
    where flow style collapses the whole dict to one ugly line.
    """
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=flow,
    )


def promote_flavor_table_title(text: str) -> str:
    """Convert '**Title**\\n\\n| col |' (bold paragraph immediately before
    a markdown table) into '## Title\\n\\n| col |'.

    Used after rendering intro section to recognize flavor-table titles
    that BS4 split apart (because <table> can't legally be inside <p>).
    """
    return re.sub(
        r"\*\*([^*\n]+)\*\*\n\n(\|[^\n]+\|)",
        r"## \1\n\n\2",
        text,
    )


def render_monster_2024(parsed: dict[str, Any], htm_path: Path) -> str:
    fm = parsed["frontmatter"]
    # Final field touch: ensure source/edition at end
    source, edition = detect_source_edition(htm_path)
    fm.setdefault("source", source)
    fm.setdefault("edition", edition)

    lines = ["---", render_yaml(fm).rstrip(), "---", ""]

    # H1 title
    name = fm.get("name", "")
    en = fm.get("en", "")
    title = f"# {name} {en}".strip()
    lines.append(title)
    lines.append("")

    # Subtitle italic
    if fm.get("subtitle"):
        lines.append(f"*{fm['subtitle']}*")
        lines.append("")

    # Habitat / treasure line
    if fm.get("habitat") or fm.get("treasure"):
        parts = []
        if fm.get("habitat"):
            parts.append(f"**栖息地**：{fm['habitat']}")
        if fm.get("treasure"):
            parts.append(f"**宝藏**：{'，'.join(fm['treasure'])}")
        lines.append("　　".join(parts))
        lines.append("")

    # Intro paragraphs + flavor tables
    intro = parsed.get("raw_intro") or []
    intro_chunk = []
    for el in intro:
        rendered = render_intro_element(el)
        if rendered:
            intro_chunk.append(rendered)
    if intro_chunk:
        intro_text = "\n\n".join(intro_chunk)
        intro_text = promote_flavor_table_title(intro_text)
        lines.append(intro_text)
        lines.append("")

    # Statblock summary
    lines.append("## 数据栏")
    lines.append("")

    # sub-line
    size = fm.get("size")
    if isinstance(size, list):
        size_str = "或".join(size)
    else:
        size_str = size or ""
    type_str = fm.get("creature_type", "")
    subtag = fm.get("type_subtag")
    if subtag:
        type_str = f"{type_str}（{subtag}）"
    alignment = fm.get("alignment", "")
    lines.append(f"{size_str}{type_str}，{alignment}")
    lines.append("")

    # AC/init/HP/speed table
    lines.append("| | 值 |")
    lines.append("|---|---|")
    ac_line = f"{fm.get('ac', '')}"
    if fm.get("ac_note"):
        ac_line = f"{fm['ac']}（{fm['ac_note']}）"
    lines.append(f"| **AC** | {ac_line} |")
    if fm.get("initiative_bonus") is not None:
        ib = fm["initiative_bonus"]
        iv = fm.get("initiative_value", "")
        sign = "+" if ib >= 0 else ""
        lines.append(f"| **先攻** | {sign}{ib} ({iv}) |")
    hp_line = str(fm.get("hp", ""))
    if fm.get("hp_dice"):
        hp_line = f"{fm['hp']} ({fm['hp_dice']})"
    lines.append(f"| **HP** | {hp_line} |")
    speed = fm.get("speed", {})
    speed_strs = []
    if speed.get("walk"):
        speed_strs.append(f"{speed['walk']} 尺")
    for k_zh, k_en in [("飞行", "fly"), ("游泳", "swim"), ("攀爬", "climb"), ("挖掘", "burrow")]:
        if speed.get(k_en):
            extra = "（盘旋）" if k_en == "fly" and speed.get("hover") else ""
            speed_strs.append(f"{k_zh} {speed[k_en]} 尺{extra}")
    lines.append(f"| **速度** | {'，'.join(speed_strs)} |")
    lines.append("")

    # 6 abilities table
    abil = fm.get("abilities", {})
    saves = fm.get("saves", {})
    lines.append("| 属性 | 值 | 调整 | 豁免 |")
    lines.append("|------|----|------|------|")
    for k_en, k_zh in [("str", "力量"), ("dex", "敏捷"), ("con", "体质"),
                       ("int", "智力"), ("wis", "感知"), ("cha", "魅力")]:
        v = abil.get(k_en, "")
        if v == "":
            continue
        mod = (v - 10) // 2
        save = saves.get(k_en, mod)
        sign_mod = "+" if mod >= 0 else ""
        sign_save = "+" if save >= 0 else ""
        lines.append(f"| {k_zh} | {v} | {sign_mod}{mod} | {sign_save}{save} |")
    lines.append("")

    # Skills / equipment / resist / immune / senses / languages / CR
    misc_lines = []
    if fm.get("skills"):
        skl = "，".join(f"{k} +{v}" if v >= 0 else f"{k} {v}" for k, v in fm["skills"].items())
        misc_lines.append(f"- **技能**：{skl}")
    if fm.get("equipment"):
        misc_lines.append(f"- **装备**：{render_equipment_list(fm['equipment'])}")
    if fm.get("damage_resist"):
        misc_lines.append(f"- **抗性**：{'，'.join(fm['damage_resist'])}")
    immune_parts = []
    if fm.get("damage_immune"):
        immune_parts.extend(fm["damage_immune"])
    if fm.get("condition_immune"):
        immune_parts.extend(fm["condition_immune"])
    for c in fm.get("condition_immune_conditional", []) or []:
        immune_parts.append(f"{c['condition']}（*{c['when']}*）")
    if immune_parts:
        misc_lines.append(f"- **免疫**：{'，'.join(immune_parts)}")
    if fm.get("senses"):
        sense_map_reverse = {
            "truesight": "真实视觉", "darkvision": "黑暗视觉",
            "blindsight": "盲视", "tremorsense": "震颤感知",
            "passive_perception": "被动察觉",
        }
        sense_strs = []
        for k_en, k_zh in sense_map_reverse.items():
            if k_en in fm["senses"]:
                v = fm["senses"][k_en]
                if k_en == "passive_perception":
                    sense_strs.append(f"{k_zh} {v}")
                else:
                    sense_strs.append(f"{k_zh} {v} 尺")
        misc_lines.append(f"- **感官**：{'，'.join(sense_strs)}")
    if fm.get("languages"):
        misc_lines.append(f"- **语言**：{'，'.join(fm['languages'])}")
    if fm.get("cr") is not None:
        cr_str = str(fm["cr"])
        xp_str = f"{fm.get('xp', 0):,}"
        pb_str = f"+{fm.get('pb', 0)}"
        misc_lines.append(f"- **CR**：{cr_str}（XP {xp_str}；PB {pb_str}）")
    lines.extend(misc_lines)
    lines.append("")

    # Body sections (特质 / 动作 / 反应 / etc.)
    for section_name, content in parsed.get("body_sections", []):
        lines.append(f"## {add_zh_en_space(section_name)}")
        lines.append("")
        rendered = render_section_content(content)
        if rendered:
            lines.append(rendered)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_intro_element(el: Tag) -> str:
    """Render a top-level intro element (paragraph or flavor table)."""
    if el.name == "p":
        # May be a description paragraph OR a flavor-table wrapper
        table = el.find("table")
        if table:
            # P > STRONG (title) + TABLE
            title_strong = el.find("strong")
            title = clean_text(title_strong.get_text()) if title_strong else ""
            md_table = render_flavor_table(table)
            out = []
            if title:
                out.append(f"## {title}")
                out.append("")
            out.append(md_table)
            return "\n".join(out)
        return render_paragraph(el)
    if el.name == "table":
        return render_flavor_table(el)
    if el.name == "p":
        return render_paragraph(el)
    return ""


def render_paragraph(p: Tag) -> str:
    """Render a description paragraph, normalizing inline tags."""
    parts = []
    for child in p.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif child.name == "br":
            parts.append("\n\n")
        elif child.name == "strong":
            txt = clean_text(child.get_text())
            parts.append(f"**{add_zh_en_space(txt)}**")
        elif child.name == "em":
            txt = clean_text(child.get_text())
            # Move trailing punctuation outside the italic
            m = re.match(r"^(.*?)\s*([:：。，,；;]+)$", txt)
            if m:
                inner = m.group(1).strip()
                punct = m.group(2).replace(":", "：")  # ASCII colon → Chinese
                parts.append(f"*{add_zh_en_space(inner)}*{punct}")
            else:
                parts.append(f"*{add_zh_en_space(txt)}*")
        elif child.name == "u":
            # 词汇高亮：保留文本，丢弃下划线
            parts.append(child.get_text())
        else:
            parts.append(child.get_text())
    text = "".join(parts)
    text = normalize_dc(text)
    text = add_zh_en_space(text)
    text = add_md_boundary_space(text)
    # Insert space between adjacent **bold** and *italic* groups
    text = re.sub(r"(\*\*[^*]+\*\*)(\*[^*])", r"\1 \2", text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n\n+", "\n\n", text)
    return text.strip()


def render_flavor_table(table: Tag) -> str:
    """Render a HTML <table> as a single MD pipe table.

    Colspan-only subheader rows (e.g. '简易近战武器 Simple Melee Weapons'
    spanning all columns in the weapons table) are rendered as a single
    bold cell occupying the first column, with remaining columns blank —
    this keeps everything in one table rather than fragmenting it.
    """
    rows = table.find_all("tr")
    if not rows:
        return ""

    header: list[str] | None = None
    data_rows: list[list[str]] = []

    for tr in rows:
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        # Colspan-only subheader
        if len(cells) == 1 and cells[0].get("colspan"):
            sub_title = add_zh_en_space(clean_text(cells[0].get_text()))
            if not sub_title:
                continue
            if header is None:
                # No header yet — record as standalone row to be padded later
                data_rows.append([f"**{sub_title}**"])
            else:
                row = [f"**{sub_title}**"] + [""] * (len(header) - 1)
                data_rows.append(row)
            continue

        is_header = bool(tr.find("th")) and header is None
        cell_texts = [
            add_zh_en_space(clean_text(c.get_text())).replace("|", "\\|")
            for c in cells
        ]
        if is_header:
            header = cell_texts
        else:
            if header is None:
                header = cell_texts
            else:
                data_rows.append(cell_texts)

    if not header:
        return ""

    md = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    for row in data_rows:
        padded = row + [""] * (len(header) - len(row))
        md.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(md)


def render_section_content(content: list[Tag]) -> str:
    """Render h6 section content (mainly <p> with <strong>name. </strong>desc<br>)."""
    parts = []
    for el in content:
        if el.name == "p":
            text = render_paragraph(el)
            parts.append(text)
        else:
            parts.append(el.get_text())
    return "\n\n".join(parts).strip()


def render_equipment_list(items: list[str]) -> str:
    """'×3' multiplier handling: 'matvz ×3' formatting."""
    return "，".join(items)


# --------- monster_family renderer -------------------------------------------

def render_monster_family(parsed: dict[str, Any], htm_path: Path) -> str:
    fm = parsed["frontmatter"]
    source, edition = detect_source_edition(htm_path)
    fm.setdefault("source", source)
    fm.setdefault("edition", edition)

    lines = ["---", render_yaml(fm).rstrip(), "---", ""]

    name = fm.get("name", "")
    en = fm.get("en", "")
    title = f"# {name} {en}".strip()
    lines.append(title)
    lines.append("")

    if fm.get("subtitle"):
        lines.append(f"*{fm['subtitle']}*")
        lines.append("")

    if fm.get("habitat") or fm.get("treasure"):
        parts = []
        if fm.get("habitat"):
            parts.append(f"**栖息地**：{fm['habitat']}")
        if fm.get("treasure"):
            parts.append(f"**宝藏**：{'，'.join(fm['treasure'])}")
        lines.append("　　".join(parts))
        lines.append("")

    for el in parsed.get("intro", []):
        rendered = render_intro_element(el)
        if rendered:
            lines.append(rendered)
            lines.append("")

    if fm.get("members"):
        lines.append("## 成员")
        lines.append("")
        for m in fm["members"]:
            lines.append(f"- [{m}]({m}.md)")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# --------- main pipeline -----------------------------------------------------

def convert_file(htm_path: Path) -> str | None:
    """Convert one .htm to MD string. Returns None if type unsupported."""
    html = htm_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    kind = detect_type(soup)

    if kind == "monster_2024":
        parsed = parse_monster_2024(soup, htm_path)
        return render_monster_2024(parsed, htm_path)
    if kind == "monster_2014_winchm":
        parsed = parse_monster_2014(soup, htm_path)
        return render_monster_2014(parsed, htm_path)
    if kind == "monster_family":
        parsed = parse_monster_family(soup, htm_path)
        return render_monster_family(parsed, htm_path)
    if kind == "spell_collection":
        parsed = parse_spell_collection(soup, htm_path)
        return render_spell_collection(parsed, htm_path)
    if kind == "document":
        parsed = parse_document(soup, htm_path)
        return render_document(parsed, htm_path)
    return None


def main():
    ap = argparse.ArgumentParser(description="HTM → MD converter (DND 5R MVP)")
    ap.add_argument("input", help="HTM file or directory")
    ap.add_argument("--dry-run", action="store_true", help="Print to stdout, don't write")
    ap.add_argument("--batch", action="store_true", help="Recurse into directory")
    ap.add_argument("--check", help="Compare output with this expected .md file")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing .md")
    args = ap.parse_args()

    inp = Path(args.input)
    if inp.is_file():
        process_one(inp, args)
    elif inp.is_dir() and args.batch:
        for htm in sorted(inp.rglob("*.htm")):
            process_one(htm, args)
    else:
        print(f"Not a file (or use --batch for dir): {inp}", file=sys.stderr)
        sys.exit(2)


def process_one(htm: Path, args) -> None:
    try:
        md = convert_file(htm)
    except Exception as e:
        print(f"[ERROR] {htm}: {e}", file=sys.stderr)
        return
    if md is None:
        print(f"[SKIP] {htm} (unsupported type)", file=sys.stderr)
        return

    if args.dry_run:
        print(f"=== {htm} ===")
        print(md)
        return

    out_path = htm.with_suffix(".md")
    if out_path.exists() and not args.overwrite:
        print(f"[EXISTS] {out_path} (use --overwrite to replace)", file=sys.stderr)
        return
    out_path.write_text(md, encoding="utf-8")
    print(f"[OK] {out_path}")

    if args.check:
        compare = Path(args.check)
        if compare.exists():
            expected = compare.read_text(encoding="utf-8")
            if expected == md:
                print(f"[CHECK PASS] {compare}")
            else:
                print(f"[CHECK DIFF] {compare}")


if __name__ == "__main__":
    main()
