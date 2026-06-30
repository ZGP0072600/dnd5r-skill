#!/usr/bin/env python3
"""一次性迁移：把手维护的 all-saves.json 拆成「一战役一 campaign.json + 一存档一文件」。

背景：存档面板原来读 .fathom-panels/dnd5r/all-saves.json（AI 手维护的全局索引）。
改版后面板从 campaigns/<战役>/campaign.json + saves/*.json 目录派生，AI 不再维护索引。
本脚本把现有 all-saves.json 的内容铺成目录文件；跑通验证后可加 --delete-index 删掉旧索引。

注意：这只迁移【面板索引】。完整存档快照目录（workspace 根的
campaigns/<战役>/saves/<名>/）是另一套、由 /save 创建，本脚本不碰。

用法：
    python tools/migrate-saves.py --data-base <workspace>/.fathom-panels/dnd5r [--dry-run] [--delete-index]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _norm(s: str) -> str:
    """与 panel.html normCampaign / load-session.py _norm_campaign 对齐。"""
    return re.sub(r"[（）()\-—\s·]", "", str(s if s is not None else ""))


def _safe(name: str) -> str:
    """存档名 → 文件名安全片段（去掉路径非法字符）。"""
    s = re.sub(r'[\\/:*?"<>|]+', "_", str(name if name is not None else "")).strip()
    return s or "存档"


def _find_campaign_dir(camps_root: Path, name: str) -> Path:
    """把 campaign.json/saves 落进【已有的】战役目录（按归一名匹配 characters/ 那套目录），
    避免因命名漂移（连字符/括号/下划线）新建一个和实体目录错位的空目录。找不到则用原名。"""
    exact = camps_root / name
    if exact.is_dir():
        return exact
    target = _norm(name)
    if camps_root.is_dir():
        for d in sorted(camps_root.iterdir()):
            if d.is_dir() and _norm(d.name) == target:
                return d
    return exact  # 不存在 → 用原名（后续 mkdir 会建）


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="all-saves.json → campaign.json + saves/*.json")
    ap.add_argument("--data-base", required=True, help="<workspace>/.fathom-panels/dnd5r")
    ap.add_argument("--dry-run", action="store_true", help="只打印不写文件")
    ap.add_argument(
        "--delete-index", action="store_true",
        help="迁移成功后删除 all-saves.json（建议先不删、验证 OK 再删）",
    )
    args = ap.parse_args(argv)
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass

    db = Path(args.data_base).resolve()
    idx = db / "all-saves.json"
    if not idx.is_file():
        print(f"无 all-saves.json，无需迁移：{idx}")
        return 0
    try:
        data = json.loads(idx.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"解析 all-saves.json 失败: {e}", file=sys.stderr)
        return 1

    camps = data.get("campaigns") if isinstance(data, dict) else None
    if not isinstance(camps, list):
        print("all-saves.json 没有 campaigns 数组，无可迁移", file=sys.stderr)
        return 1

    camps_root = db / "campaigns"
    n_camp = n_save = 0
    for c in camps:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        name = c["name"]
        cdir = _find_campaign_dir(camps_root, name)
        meta = {
            "name": name,
            "mode": c.get("mode", "G"),
            "module": c.get("module", ""),
            "dmStyle": c.get("dmStyle", ""),
            "lastPlayed": c.get("lastPlayed", ""),
        }
        saves = c.get("saves") or []
        print(f"战役 {name!r}  ->  {cdir}  (campaign.json + {len(saves)} 存档)")
        if not args.dry_run:
            cdir.mkdir(parents=True, exist_ok=True)
            (cdir / "campaign.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            sdir = cdir / "saves"
            sdir.mkdir(exist_ok=True)
            for i, s in enumerate(saves, 1):
                if not isinstance(s, dict):
                    continue
                fname = f"{i:04d}_{_safe(s.get('name'))}.json"
                (sdir / fname).write_text(
                    json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        n_camp += 1
        n_save += len(saves)

    tail = "（dry-run，未写文件）" if args.dry_run else ""
    print(f"\n完成：{n_camp} 战役 / {n_save} 存档{tail}")
    if args.delete_index and not args.dry_run:
        idx.unlink()
        print(f"已删除旧索引 {idx}")
    elif not args.dry_run:
        print(f"旧索引保留：{idx}（验证 OK 后可加 --delete-index 删，或手删）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
