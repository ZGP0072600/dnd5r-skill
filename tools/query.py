#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
query.py — 法术快查（只读）。

【查询期脚本·硬约束】只用 stdlib（json/argparse/sys/pathlib）——任何带 Python 的
Agent 都能直接 `python query.py ...` 调用，零 pip 安装。永远不要往这里加第三方依赖，
否则破坏可移植性（YAML 等脏活留在 build_index.py 构建期）。

索引 index/spells.json 由 build_index.py 生成；本脚本只读不写、自定位（相对 __file__）。

用法：
  python query.py spell 火球术                    # 查单条，默认展示最高优先来源 + 其他版本
  python query.py spell Fireball                  # 中英任意
  python query.py spell 火球术 --all              # 列出全部印次
  python query.py spell --class 牧师 --level 2     # 按职业+环阶枚举
  python query.py spell --class 法师 --level 0 --school 塑能
  python query.py spell 火球术 --json             # 机器可读输出
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")   # Windows cp936 下输出中文不崩
except Exception:
    pass

INDEX_DIR = Path(__file__).parent / "index"


def _load(fname, key):
    f = INDEX_DIR / fname
    if not f.exists():
        sys.exit(f"[索引缺失] {f}\n请先运行: python {Path(__file__).with_name('build_index.py')}")
    return json.loads(f.read_text(encoding="utf-8")).get(key, [])


def load_spells():
    return _load("spells.json", "spells")


def load_monsters():
    return _load("monsters.json", "monsters")


def lvl_str(lv):
    if lv == 0:
        return "戏法"
    if lv is None:
        return "?环"
    return f"{lv}环"


def identity(r):
    """法术身份（跨书去重键）：优先英文名，回退中文名。
    归一空格/撇号，吸收跨版译名漂移（如 Enlarge / Reduce ↔ Enlarge/Reduce）。"""
    en = (r.get("en") or "").lower()
    en = re.sub(r"\s+", "", en).replace("'", "").replace("’", "")
    return en or r.get("name") or ""


def parse_level(s):
    s = s.strip()
    if s in ("戏法", "cantrip", "0环"):
        return 0
    try:
        return int(s.rstrip("环"))
    except ValueError:
        return None


def cr_to_num(cr):
    if cr is None:
        return None
    s = str(cr).strip()
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


# 常用 fan 译名 → 资料库正名（资料库译名与社区习惯不一致时；可按需扩展）
ALIASES = {
    "哥布林": "地精",      # Goblin（MM2025 译作"地精"）
    "鹰身女妖": "鸟妖",    # Harpy
    "豺狼人": "鬣狗人",    # Gnoll
}


def apply_alias(q):
    for fan, canon in ALIASES.items():
        if fan in q:
            return q.replace(fan, canon), fan, canon
    return q, None, None


# ---------- 搜索 ----------
def score(r, q):
    name = r.get("name") or ""
    en = (r.get("en") or "").lower()
    ql = q.lower()
    if name == q or en == ql:
        return 100
    if name.startswith(q) or en.startswith(ql):
        return 80
    if q in name or ql in en:
        return 60
    return 0


def search(spells, q):
    """返回 [(best_score, [该 identity 的全部印次记录])]，按相关度+优先级排序。"""
    groups = {}   # ident -> {"score": int, "recs": [...]}
    for r in spells:
        sc = score(r, q)
        if sc == 0:
            continue
        g = groups.setdefault(identity(r), {"score": 0, "recs": []})
        g["score"] = max(g["score"], sc)
        g["recs"].append(r)
    ordered = sorted(groups.values(),
                     key=lambda g: (-g["score"], min(x["priority"] for x in g["recs"])))
    return ordered


# ---------- 输出 ----------
def fmt_detail(recs):
    """一个法术（含多印次）→ 详情文本。recs 已是同一 identity 的所有记录。"""
    recs = sorted(recs, key=lambda r: r["priority"])
    b = recs[0]
    out = []
    head = f"{b['name']} ｜ {b['en']}".strip(" ｜")
    out.append(f"{head}   [{lvl_str(b['level'])} · {b.get('school') or '—'}]")
    if b.get("classes"):
        out.append("职业: " + " / ".join(b["classes"]))
    line2 = []
    if b.get("casting_time"):
        line2.append(f"施法: {b['casting_time']}")
    if b.get("range"):
        line2.append(f"距离: {b['range']}")
    if b.get("duration"):
        line2.append(f"持续: {b['duration']}")
    if line2:
        out.append("    ".join(line2))
    if b.get("components"):
        out.append(f"成分: {b['components']}")
    flags = []
    if b.get("concentration"):
        flags.append("专注")
    if b.get("ritual"):
        flags.append("仪式")
    if flags:
        out.append("特性: " + "、".join(flags))
    ln = f":{b['line']}" if b.get("line") else ""
    out.append(f"📖 {b['source']}（{b.get('edition') or '?'}）  →  {b['path']}{ln}")
    if len(recs) > 1:
        extra = []
        for r in recs[1:]:
            ln2 = f":{r['line']}" if r.get("line") else ""
            extra.append(f"   · {r['source']}（{r.get('edition') or '?'}） → {r['path']}{ln2}")
        out.append("其他版本:")
        out.extend(extra)
    return "\n".join(out)


def fmt_row(r):
    cls = "/".join(r.get("classes") or []) or "—"
    ln = f":{r['line']}" if r.get("line") else ""
    return (f" {lvl_str(r['level']):<4} {r['name']} {r.get('en') or ''}".rstrip()
            + f"  · {r.get('school') or '—'} · {cls}  → {r['path']}{ln}")


def do_spell(args):
    spells = load_spells()

    # 过滤器（枚举模式）
    has_filter = any([args.cls, args.level, args.school, args.source])
    if not args.name and not has_filter:
        sys.exit("用法: query.py spell <法术名>  或  query.py spell --class 牧师 --level 2")

    pool = spells
    if args.cls:
        pool = [r for r in pool if any(args.cls == c or args.cls in c for c in (r.get("classes") or []))]
    if args.level:
        lv = parse_level(args.level)
        pool = [r for r in pool if r.get("level") == lv]
    if args.school:
        pool = [r for r in pool if args.school in (r.get("school") or "")]
    if args.source:
        pool = [r for r in pool if args.source in (r.get("source") or "")]

    # 有法术名 → 搜索 + 详情
    if args.name:
        groups = search(pool, args.name)
        if not groups:
            print(f"未找到「{args.name}」。docs/extracted 法术索引中无此条目（可换英文名再试，或确认拼写）。")
            return
        if args.json:
            ranked = [r for g in groups
                      for r in sorted(g["recs"], key=lambda x: x["priority"])]
            print(json.dumps(ranked, ensure_ascii=False, indent=2))
            return
        top = groups[0]
        # 命中唯一、或最相关组是精确/前缀匹配 → 直接给详情
        if len(groups) == 1 or top["score"] >= 80:
            if args.all:
                print(fmt_detail(top["recs"]))
            else:
                print(fmt_detail(top["recs"]))
            # 还有其它弱相关候选时附一行提示
            if len(groups) > 1:
                others = "、".join(g["recs"][0]["name"] for g in groups[1:6])
                print(f"\n（另有相关: {others}{' …' if len(groups) > 6 else ''}）")
        else:
            print(f"「{args.name}」匹配到 {len(groups)} 个法术，请明确：")
            for g in groups[:20]:
                r = sorted(g["recs"], key=lambda x: x["priority"])[0]
                print(fmt_row(r))
        return

    # 纯枚举模式
    pool, hidden = official_only(pool, args.all or bool(args.source))
    if args.json:
        records = pool if args.all else _collapse(pool)
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return
    records = pool if args.all else _collapse(pool)
    records.sort(key=lambda r: ((r["level"] if r["level"] is not None else 99), r["name"]))
    desc = []
    if args.cls:
        desc.append(f"职业={args.cls}")
    if args.level:
        desc.append(f"环阶={args.level}")
    if args.school:
        desc.append(f"学派={args.school}")
    if args.source:
        desc.append(f"来源={args.source}")
    extra = f"；已隐藏第三方/UA/模组 {hidden} 条（--all 全含）" if hidden else "；--all 看全部印次"
    tail = "" if args.all else f"（每法术取最高优先来源{extra}）"
    print(f"筛选 {' '.join(desc)} → {len(records)} 条{tail}")
    for r in records[:args.limit]:
        print(fmt_row(r))
    if len(records) > args.limit:
        print(f"… 还有 {len(records) - args.limit} 条（--limit 调整上限）")


def _collapse(pool):
    """同一法术多印次 → 取最高优先来源那条。"""
    best = {}
    for r in pool:
        k = identity(r)
        if k not in best or r["priority"] < best[k]["priority"]:
            best[k] = r
    return list(best.values())


def official_only(pool, include_all):
    """枚举默认排除第三方/UA/模组（priority>=5）防淹没；include_all 时保留全部。返回 (kept, hidden)。"""
    if include_all:
        return pool, 0
    kept = [r for r in pool if r.get("priority", 9) < 5]
    return kept, len(pool) - len(kept)


# ---------- 怪物 ----------
SPEED_K = {"walk": "走", "fly": "飞", "swim": "游", "climb": "攀", "burrow": "掘", "hover": "悬"}
SENSE_K = {"darkvision": "黑视", "blindsight": "盲视", "tremorsense": "震颤感",
           "truesight": "真视", "passive_perception": "被察"}
ABILITY_K = {"str": "力", "dex": "敏", "con": "体", "int": "智", "wis": "感", "cha": "魅"}


def _s(v):
    """安全转字符串：list→斜杠拼接，None→空（怪物 size/alignment 偶为列表）。"""
    if isinstance(v, list):
        return "/".join(str(x) for x in v)
    return str(v) if v else ""


def _mod(v):
    try:
        return (int(v) - 10) // 2
    except (TypeError, ValueError):
        return None


def _fmt_dict(d, keymap):
    if not isinstance(d, dict):
        return str(d) if d else ""
    return " ".join(f"{keymap.get(k, k)}{v}" for k, v in d.items())


def _fmt_abilities(ab):
    if not isinstance(ab, dict):
        return ""
    out = []
    for k in ("str", "dex", "con", "int", "wis", "cha"):
        if k in ab:
            m = _mod(ab[k])
            out.append(f"{ABILITY_K[k]}{ab[k]}({m:+d})" if m is not None else f"{ABILITY_K[k]}{ab[k]}")
    return " ".join(out)


def cr_label(r):
    s = f"CR {r['cr']}" if r.get("cr") else "CR ?"
    return s + (f" · {r['xp']}XP" if r.get("xp") else "")


def fmt_monster_detail(recs):
    recs = sorted(recs, key=lambda r: r["priority"])
    b = recs[0]
    if b.get("kind") == "family":
        out = [f"{b['name']} ｜ {b['en']}（怪物族）" + (f"   {b['subtitle']}" if b.get("subtitle") else "")]
        if b.get("members"):
            out.append("成员: " + " / ".join(b["members"]))
        if b.get("habitat"):
            out.append(f"栖息地: {b['habitat']}")
        ln = f":{b['line']}" if b.get("line") else ""
        out.append(f"📖 {b['source']} → {b['path']}{ln}")
        return "\n".join(out)
    out = []
    head = f"{b['name']} ｜ {b['en']}".strip(" ｜")
    sub = " · ".join(x for x in [_s(b.get("size")) + _s(b.get("creature_type")),
                                 _s(b.get("alignment"))] if x.strip())
    out.append(f"{head}   [{cr_label(b)}]" + (f"   {sub}" if sub else ""))
    dfn = []
    if b.get("ac") is not None:
        dfn.append(f"AC {b['ac']}")
    if b.get("hp") is not None:
        dfn.append(f"HP {b['hp']}" + (f" ({b['hp_dice']})" if b.get("hp_dice") else ""))
    if b.get("speed"):
        dfn.append("速度 " + _fmt_dict(b["speed"], SPEED_K))
    if dfn:
        out.append(" | ".join(dfn))
    if b.get("abilities"):
        out.append("属性 " + _fmt_abilities(b["abilities"]))
    dl = []
    for key, lab in [("damage_vuln", "易伤"), ("damage_resist", "抗性"),
                     ("damage_immune", "免疫"), ("condition_immune", "状态免疫")]:
        if b.get(key):
            dl.append(f"{lab} " + "/".join(b[key]))
    if dl:
        out.append(" | ".join(dl))
    ex = []
    if b.get("senses"):
        ex.append("感官 " + _fmt_dict(b["senses"], SENSE_K))
    if b.get("languages"):
        ex.append("语言 " + "/".join(b["languages"]))
    if ex:
        out.append(" | ".join(ex))
    ln = f":{b['line']}" if b.get("line") else ""
    out.append(f"📖 {b['source']}（{b.get('edition') or '?'}） → {b['path']}{ln}")
    if len(recs) > 1:
        out.append("其他版本: " + "; ".join(
            f"{r['source']}({r.get('edition') or '?'})→{r['path']}" + (f":{r['line']}" if r.get("line") else "")
            for r in recs[1:]))
    return "\n".join(out)


def fmt_monster_row(r):
    if r.get("kind") == "family":
        return f" [族] {r['name']} {r.get('en') or ''}  成员:{len(r.get('members') or [])}  → {r['path']}"
    tags = []
    if r.get("creature_type"):
        tags.append(_s(r.get("size")) + _s(r.get("creature_type")))
    if r.get("ac") is not None:
        tags.append(f"AC{r['ac']}")
    if r.get("hp") is not None:
        tags.append(f"HP{r['hp']}")
    ln = f":{r['line']}" if r.get("line") else ""
    name = f"{r['name']} {r.get('en') or ''}".strip()
    return f" {cr_label(r):<14} {name}  {' '.join(tags)}  → {r['path']}{ln}"


def cr_filter(recs, expr):
    expr = expr.strip()
    for sym, fn in [(">=", lambda a, b: a >= b), ("<=", lambda a, b: a <= b),
                    (">", lambda a, b: a > b), ("<", lambda a, b: a < b)]:
        if expr.startswith(sym):
            t = cr_to_num(expr[len(sym):])
            return [r for r in recs if r.get("cr_num") is not None and t is not None and fn(r["cr_num"], t)]
    if re.match(r"^[\d/.]+-[\d/.]+$", expr):
        lo, hi = expr.split("-")
        lo, hi = cr_to_num(lo), cr_to_num(hi)
        return [r for r in recs if r.get("cr_num") is not None and lo is not None and hi is not None
                and lo <= r["cr_num"] <= hi]
    t = cr_to_num(expr)
    return [r for r in recs if r.get("cr_num") == t]


def do_monster(args):
    monsters = load_monsters()
    if args.name:
        newq, fan, canon = apply_alias(args.name)
        if fan:
            print(f"（别名归一：{fan} → {canon}）")
            args.name = newq
    has_filter = any([args.cr, args.type, args.source, args.size])
    if not args.name and not has_filter:
        sys.exit("用法: query.py monster <怪物名>  或  query.py monster --cr '>=5' --type 类人")
    pool = monsters
    if args.cr:
        pool = cr_filter(pool, args.cr)
    if args.type:
        pool = [r for r in pool if args.type in (r.get("creature_type") or "")]
    if args.size:
        pool = [r for r in pool if args.size in (r.get("size") or "")]
    if args.source:
        pool = [r for r in pool if args.source in (r.get("source") or "")]

    if args.name:
        groups = search(pool, args.name)
        if not groups:
            print(f"未找到「{args.name}」。docs/extracted 怪物索引中无此条目（可换英文名再试）。")
            return
        if args.json:
            print(json.dumps([r for g in groups for r in sorted(g["recs"], key=lambda x: x["priority"])],
                             ensure_ascii=False, indent=2))
            return
        top = groups[0]
        if len(groups) == 1 or top["score"] >= 80:
            print(fmt_monster_detail(top["recs"]))
            if len(groups) > 1:
                others = "、".join(g["recs"][0]["name"] for g in groups[1:6])
                print(f"\n（另有相关: {others}{' …' if len(groups) > 6 else ''}）")
        else:
            print(f"「{args.name}」匹配到 {len(groups)} 个，请明确：")
            for g in groups[:25]:
                print(fmt_monster_row(sorted(g["recs"], key=lambda x: x["priority"])[0]))
        return

    if not args.family:
        pool = [r for r in pool if r.get("kind") != "family"]
    pool, hidden = official_only(pool, args.all or bool(args.source))
    records = pool if args.all else _collapse(pool)
    records.sort(key=lambda r: (r.get("cr_num") if r.get("cr_num") is not None else -1, r.get("name") or ""))
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return
    desc = []
    if args.cr:
        desc.append(f"CR{args.cr}")
    if args.type:
        desc.append(f"类型={args.type}")
    if args.size:
        desc.append(f"体型={args.size}")
    if args.source:
        desc.append(f"来源={args.source}")
    extra = f"；已隐藏第三方/UA/模组 {hidden} 条（--all 全含）" if hidden else "；--all 看全部"
    print(f"筛选 {' '.join(desc)} → {len(records)} 条" + ("" if args.all else f"（折叠多版本{extra}）"))
    for r in records[:args.limit]:
        print(fmt_monster_row(r))
    if len(records) > args.limit:
        print(f"… 还有 {len(records) - args.limit} 条（--limit 调整）")


# ---------- 职业 / 子职业 ----------
def load_classes():
    return _load("classes.json", "entries")


def fmt_subclass_detail(recs):
    recs = sorted(recs, key=lambda r: r["priority"])
    b = recs[0]
    out = [f"{b['name']} ｜ {b['en']}".strip(" ｜") + f"   [{b.get('class') or '?'} 子职]"]
    if b.get("flavor"):
        out.append(b["flavor"])
    ln = f":{b['line']}" if b.get("line") else ""
    out.append(f"📖 {b['source']}（{b.get('edition') or '?'}） → {b['path']}{ln}（特性全文读此处）")
    if len(recs) > 1:
        out.append("其他版本: " + "; ".join(
            f"{r['source']}→{r['path']}" + (f":{r['line']}" if r.get("line") else "") for r in recs[1:]))
    return "\n".join(out)


def fmt_subclass_row(e):
    ln = f":{e['line']}" if e.get("line") else ""
    fl = f"  — {e['flavor']}" if e.get("flavor") else ""
    name = f"{e['name']} {e.get('en') or ''}".strip()
    return f"  {name}{fl}  → {e['path']}{ln}"


def do_subclass(args):
    pool = [e for e in load_classes() if e["kind"] == "subclass"]
    if args.cls:
        pool = [e for e in pool if args.cls in (e.get("class") or "")]
    if args.source:
        pool = [e for e in pool if args.source in (e.get("source") or "")]

    if args.name:
        groups = search(pool, args.name)
        if not groups:
            print(f"未找到子职「{args.name}」。")
            return
        if args.json:
            print(json.dumps([r for g in groups for r in sorted(g["recs"], key=lambda x: x["priority"])],
                             ensure_ascii=False, indent=2))
            return
        top = groups[0]
        if len(groups) == 1 or top["score"] >= 80:
            print(fmt_subclass_detail(top["recs"]))
            if len(groups) > 1:
                print(f"\n（另有相关: {'、'.join(g['recs'][0]['name'] for g in groups[1:6])}）")
        else:
            print(f"「{args.name}」匹配到 {len(groups)} 个子职：")
            for g in groups[:25]:
                print(fmt_subclass_row(sorted(g["recs"], key=lambda x: x["priority"])[0]))
        return

    if args.json:
        print(json.dumps(pool, ensure_ascii=False, indent=2))
        return
    by_src = {}
    for e in pool:
        by_src.setdefault(e["source"], []).append(e)
    title = "子职枚举" + (f"：{args.cls}" if args.cls else "（全部）")
    print(f"{title} → {len(pool)} 条（含 PHB24 + 塔莎/珊娜萨 + 奇械师/铳士/血猎手 + 5 部第三方书子职；PHB14/剑湾/谦卑林待接入）")
    for src in sorted(by_src, key=lambda s: min(x["priority"] for x in by_src[s])):
        print(f"\n【{src}】")
        for e in sorted(by_src[src], key=lambda x: (x.get("class") or "", x["name"])):
            print(fmt_subclass_row(e))


def do_class(args):
    classes = [e for e in load_classes() if e["kind"] == "class"]
    if args.name:
        groups = search(classes, args.name)
        if not groups:
            print(f"未找到职业「{args.name}」。")
            return
        if args.json:
            print(json.dumps(sorted(groups[0]["recs"], key=lambda x: x["priority"]), ensure_ascii=False, indent=2))
            return
        c = sorted(groups[0]["recs"], key=lambda x: x["priority"])[0]
        out = [f"{c['name']} ｜ {c['en']}".strip(" ｜") + (f"   命中骰 {c['hit_die']}" if c.get("hit_die") else "")]
        if c.get("subclasses"):
            out.append(f"子职业（{len(c['subclasses'])}）: " + " / ".join(c["subclasses"]))
        ln = f":{c['line']}" if c.get("line") else ""
        out.append(f"📖 {c['source']} → {c['path']}{ln}")
        out.append(f"（子职详情: query.py subclass --class {c['name']}）")
        print("\n".join(out))
        return
    if args.json:
        print(json.dumps(classes, ensure_ascii=False, indent=2))
        return
    n_phb = sum(1 for c in classes if c["priority"] == 0)
    print(f"职业（共 {len(classes)}：{n_phb} PHB24 + {len(classes) - n_phb} 跨书/第三方）：")
    for c in sorted(classes, key=lambda x: x["priority"]):
        hd = f" HD{c['hit_die']}" if c.get("hit_die") else ""
        ln = f":{c['line']}" if c.get("line") else ""
        src = "" if c["priority"] == 0 else f" [{c['source']}]"
        print(f"  {c['name']} {c.get('en') or ''}{hd}{src}  子职{len(c.get('subclasses') or [])}个  → {c['path']}{ln}")


# ---------- 种族 / 专长 / 装备 ----------
def load_races():
    return _load("races.json", "races")


def load_feats():
    return _load("feats.json", "feats")


def load_equipment():
    return _load("equipment.json", "equipment")


def load_magic():
    return _load("magic.json", "magic")


def do_race(args):
    races = load_races()
    if not args.name:
        if args.json:
            print(json.dumps(races, ensure_ascii=False, indent=2))
            return
        print(f"种族（共 {len(races)}：PHB24 + 剑湾 + 费资本龙裔）：")
        for r in sorted(races, key=lambda x: x["name"]):
            ln = f":{r['line']}" if r.get("line") else ""
            print(f"  {r['name']} {r.get('en') or ''}  → {r['path']}{ln}")
        return
    groups = search(races, args.name)
    if not groups:
        print(f"未找到种族「{args.name}」。")
        return
    if args.json:
        print(json.dumps(sorted(groups[0]["recs"], key=lambda x: x["priority"]), ensure_ascii=False, indent=2))
        return
    r = sorted(groups[0]["recs"], key=lambda x: x["priority"])[0]
    out = [f"{r['name']} ｜ {r['en']}".strip(" ｜")]
    if r.get("flavor"):
        out.append(r["flavor"])
    ln = f":{r['line']}" if r.get("line") else ""
    out.append(f"📖 {r['source']} → {r['path']}{ln}（特性全文读此处）")
    print("\n".join(out))


def do_feat(args):
    pool = load_feats()
    if args.cat:
        pool = [f for f in pool if args.cat in (f.get("category") or "")]
    if args.name:
        groups = search(pool, args.name)
        if not groups:
            print(f"未找到专长「{args.name}」。（专长为启发式解析，可能漏；可 grep 玩家手册2024/专长/ 核对）")
            return
        if args.json:
            print(json.dumps([r for g in groups for r in g["recs"]], ensure_ascii=False, indent=2))
            return
        top = groups[0]
        if len(groups) == 1 or top["score"] >= 80:
            b = sorted(top["recs"], key=lambda x: x["priority"])[0]
            ln = f":{b['line']}" if b.get("line") else ""
            print(f"{b['name']} ｜ {b['en']}".strip(" ｜") + f"   [{b.get('category')}专长]")
            print(f"📖 {b['source']} → {b['path']}{ln}（专长全文读此处）")
        else:
            print(f"「{args.name}」匹配 {len(groups)} 个：")
            for g in groups[:25]:
                b = sorted(g["recs"], key=lambda x: x["priority"])[0]
                print(f"  {b['name']} {b.get('en') or ''} [{b.get('category')}]")
        return
    if args.json:
        print(json.dumps(pool, ensure_ascii=False, indent=2))
        return
    print(f"专长{('：' + args.cat) if args.cat else '（全部）'} → {len(pool)} 条"
          f"（best-effort 解析，枚举请按 path:line 核对原文）")
    for f in sorted(pool, key=lambda x: (x.get("category") or "", x["name"])):
        ln = f":{f['line']}" if f.get("line") else ""
        print(f"  [{f.get('category')}] {f['name']} {f.get('en') or ''}  → {f['path']}{ln}")


def fmt_equip_detail(recs):
    b = sorted(recs, key=lambda r: r["priority"])[0]
    out = [f"{b['name']} ｜ {b['en']}".strip(" ｜") + f"   [{b.get('category') or b['kind']}]"]
    if b["kind"] == "weapon":
        cols = [("伤害", "damage"), ("词条", "properties"), ("精通", "mastery"),
                ("重量", "weight"), ("价格", "cost")]
    else:
        cols = [("AC", "ac"), ("力量", "strength"), ("隐匿", "stealth"),
                ("重量", "weight"), ("价格", "cost")]
    row = [f"{lab} {b[k]}" for lab, k in cols if b.get(k)]
    if row:
        out.append(" | ".join(row))
    ln = f":{b['line']}" if b.get("line") else ""
    out.append(f"📖 {b['source']} → {b['path']}{ln}")
    return "\n".join(out)


def do_equip(args):
    pool = load_equipment()
    if args.kind:
        pool = [r for r in pool if r["kind"] == args.kind]
    if args.category:
        pool = [r for r in pool if args.category in (r.get("category") or "")]
    if args.name:
        groups = search(pool, args.name)
        if not groups:
            print(f"未找到装备「{args.name}」。（当前仅武器+护甲；工具/法器/魔法物品待接入）")
            return
        if args.json:
            print(json.dumps([r for g in groups for r in g["recs"]], ensure_ascii=False, indent=2))
            return
        top = groups[0]
        if len(groups) == 1 or top["score"] >= 80:
            print(fmt_equip_detail(top["recs"]))
        else:
            print(f"「{args.name}」匹配 {len(groups)} 个：")
            for g in groups[:25]:
                b = sorted(g["recs"], key=lambda x: x["priority"])[0]
                print(f"  {b['name']} {b.get('en') or ''} [{b.get('category') or b['kind']}]")
        return
    if args.json:
        print(json.dumps(pool, ensure_ascii=False, indent=2))
        return
    print(f"装备 → {len(pool)} 条" + (f"（{args.kind}）" if args.kind else "（武器 + 护甲）"))
    for r in sorted(pool, key=lambda x: x["name"]):
        ln = f":{r['line']}" if r.get("line") else ""
        extra = r.get("damage") or r.get("ac") or ""
        print(f"  {r['name']} {r.get('en') or ''}  [{r.get('category') or r['kind']}] {extra}  → {r['path']}{ln}")


def fmt_magic_detail(recs):
    b = sorted(recs, key=lambda r: r["priority"])[0]
    att = " · 需同调" if b.get("attunement") else ""
    out = [f"{b['name']} ｜ {b['en']}".strip(" ｜") + f"   [{b['item_type']} · {b['rarity']}{att}]"]
    if b.get("meta"):
        out.append(b["meta"])
    ln = f":{b['line']}" if b.get("line") else ""
    out.append(f"📖 {b['source']} → {b['path']}{ln}（完整词条读此处）")
    return "\n".join(out)


def do_magic(args):
    pool = load_magic()
    if args.type:
        pool = [r for r in pool if args.type in (r.get("item_type") or "")]
    if args.rarity:
        pool = [r for r in pool if args.rarity in (r.get("rarity") or "")]
    if args.attune:
        pool = [r for r in pool if r.get("attunement")]
    if args.name:
        groups = search(pool, args.name)
        if not groups:
            print(f"未找到魔法物品「{args.name}」。")
            return
        if args.json:
            print(json.dumps([r for g in groups for r in g["recs"]], ensure_ascii=False, indent=2))
            return
        top = groups[0]
        if len(groups) == 1 or top["score"] >= 80:
            print(fmt_magic_detail(top["recs"]))
            if len(groups) > 1:
                print(f"\n（另有相关: {'、'.join(g['recs'][0]['name'] for g in groups[1:6])}）")
        else:
            print(f"「{args.name}」匹配 {len(groups)} 个：")
            for g in groups[:25]:
                b = g["recs"][0]
                print(f"  {b['name']} {b.get('en') or ''} [{b['item_type']}·{b['rarity']}]")
        return
    if args.json:
        print(json.dumps(pool, ensure_ascii=False, indent=2))
        return
    desc = []
    if args.type:
        desc.append(f"类型={args.type}")
    if args.rarity:
        desc.append(f"稀有度={args.rarity}")
    if args.attune:
        desc.append("需同调")
    print(f"魔法物品 {' '.join(desc)} → {len(pool)} 件")
    for r in sorted(pool, key=lambda x: (x["item_type"], x["name"]))[:args.limit]:
        att = " ⊙同调" if r.get("attunement") else ""
        ln = f":{r['line']}" if r.get("line") else ""
        print(f"  {r['name']} {r.get('en') or ''}  [{r['item_type']}·{r['rarity']}{att}]  → {r['path']}{ln}")
    if len(pool) > args.limit:
        print(f"… 还有 {len(pool) - args.limit} 件（--limit 调整）")


def main():
    ap = argparse.ArgumentParser(description="D&D 5r 快查（法术/怪物/职业/种族/专长/装备/魔法物品）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("spell", help="查法术")
    sp.add_argument("name", nargs="?", help="法术名（中/英，可部分）")
    sp.add_argument("-c", "--class", dest="cls", help="按职业筛选")
    sp.add_argument("-l", "--level", help="按环阶筛选（0/戏法 ~ 9）")
    sp.add_argument("-s", "--school", help="按学派筛选")
    sp.add_argument("--source", help="按来源书筛选")
    sp.add_argument("--all", action="store_true", help="展示全部印次（默认折叠到最高优先来源）")
    sp.add_argument("--json", action="store_true", help="机器可读输出")
    sp.add_argument("--limit", type=int, default=60, help="枚举上限（默认 60）")
    sp.set_defaults(func=do_spell)

    mp = sub.add_parser("monster", help="查怪物")
    mp.add_argument("name", nargs="?", help="怪物名（中/英，可部分）")
    mp.add_argument("--cr", help="挑战等级：'>=5' / '<=1' / '5' / '1/4' / '1-5'")
    mp.add_argument("-t", "--type", help="生物类型（亡灵/类人/龙/…）")
    mp.add_argument("--size", help="体型（微型/小型/中型/大型/巨型/超巨型）")
    mp.add_argument("--source", help="按来源书筛选")
    mp.add_argument("--family", action="store_true", help="枚举时包含怪物族首页")
    mp.add_argument("--all", action="store_true", help="展示全部版本（默认折叠）")
    mp.add_argument("--json", action="store_true", help="机器可读输出")
    mp.add_argument("--limit", type=int, default=60, help="枚举上限（默认 60）")
    mp.set_defaults(func=do_monster)

    scp = sub.add_parser("subclass", help="查子职业")
    scp.add_argument("name", nargs="?", help="子职名（中/英，可部分）")
    scp.add_argument("-c", "--class", dest="cls", help="按所属职业枚举（如 战士）")
    scp.add_argument("--source", help="按来源书筛选")
    scp.add_argument("--json", action="store_true", help="机器可读输出")
    scp.set_defaults(func=do_subclass)

    cp = sub.add_parser("class", help="查职业（无参=列全部）")
    cp.add_argument("name", nargs="?", help="职业名（中/英，可部分）")
    cp.add_argument("--json", action="store_true", help="机器可读输出")
    cp.set_defaults(func=do_class)

    rp = sub.add_parser("race", help="查种族（无参=列全部）")
    rp.add_argument("name", nargs="?", help="种族名（中/英，可部分）")
    rp.add_argument("--json", action="store_true")
    rp.set_defaults(func=do_race)

    fp = sub.add_parser("feat", help="查专长（best-effort）")
    fp.add_argument("name", nargs="?", help="专长名（中/英，可部分）")
    fp.add_argument("--cat", help="按分类枚举（起源/通用/战斗风格/传奇恩惠）")
    fp.add_argument("--json", action="store_true")
    fp.set_defaults(func=do_feat)

    ep = sub.add_parser("equip", help="查装备（武器/护甲）")
    ep.add_argument("name", nargs="?", help="装备名（中/英，可部分）")
    ep.add_argument("--kind", choices=["weapon", "armor"], help="只看武器/护甲")
    ep.add_argument("--category", help="按分类（简易近战/重甲/...）")
    ep.add_argument("--json", action="store_true")
    ep.set_defaults(func=do_equip)

    gp = sub.add_parser("magic", help="查魔法物品")
    gp.add_argument("name", nargs="?", help="物品名（中/英，可部分）")
    gp.add_argument("-t", "--type", help="类型（武器/护甲/戒指/药水/卷轴/法杖/魔杖/权杖/奇物）")
    gp.add_argument("-r", "--rarity", help="稀有度（普通/非普通/珍稀/极珍稀/传说/神器）")
    gp.add_argument("--attune", action="store_true", help="只看需同调的")
    gp.add_argument("--json", action="store_true")
    gp.add_argument("--limit", type=int, default=60)
    gp.set_defaults(func=do_magic)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
