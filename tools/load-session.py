#!/usr/bin/env python3
"""读档：从 campaigns/<战役>/campaign.json + saves/*.json 重建【当前 thread】的 session.json。

单一事实源——宿主「继续」按钮（Tauri 直接 spawn 本脚本）和 AI 打字 /load
（SKILL.md G7/S2 调本脚本）共用这一份读档逻辑，避免「Rust 实现」与「SKILL.md 手写步骤」
两处漂移。输出形状须与宿主 Rust `dnd_load_session` 完全一致，两条路径才能互换。

做的事：
  从 campaigns/<战役>/campaign.json 取 mode / dmStyle / module，
  从 campaigns/<战役>/saves/<存档>.json 取 chapter / inGameTime / location
  → 按 session-v2 契约全量重写 <data-base>/threads/<threadId>/session.json。
  不含 players[]——队伍 HUD 由 panel 从 canonical characters/*.json 派生。
  注：不再读 all-saves.json（已弃用）。存档改为「一存档一文件」、由目录派生，
      AI 不再维护任何全局索引——面板的 campaignFiles(collection) 自动枚举。

threadId 来源（优先级）：
  1. --thread 显式传入（宿主按钮路径用：currentThreadId 最权威，且草稿态 .fathom-context 可能滞后）
  2. <workspace>/.fathom-context.json 的 "threadId"（AI 路径用；workspace = data-base 的上两级）

用法：
    python tools/load-session.py --data-base .fathom-panels/dnd5r "<战役名>" "<存档名>"
    python tools/load-session.py --data-base .fathom-panels/dnd5r "<战役名>"            # 存档名省略=最新
    python tools/load-session.py --data-base <abs> --thread thr_xxx "<战役>" "<存档>"    # 宿主路径
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _force_utf8_streams() -> None:
    """stdout/stderr 强制 UTF-8——否则 Windows 控制台默认 GBK，
    打印含生僻字的战役名会抛 UnicodeEncodeError；而文件已先写好，
    这一抛会让脚本在成功之后反以非零码退出，宿主误判为失败。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def _now_iso() -> str:
    """与宿主 Rust chrono_now_iso 对齐：UTC、秒级、YYYY-MM-DDTHH:MM:SSZ。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _str_or(d: dict, key: str, default: str) -> str:
    """对齐 Rust `get(key).and_then(as_str).unwrap_or(default)`：
    键存在且是字符串就用它（哪怕空串），否则取默认。"""
    v = d.get(key)
    return v if isinstance(v, str) else default


def _die(msg: str) -> "Any":
    """打到 stderr 并以非零码退出（宿主 spawn 时按退出码判失败）。"""
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def _norm_campaign(s: str) -> str:
    """与 panel.html 的 normCampaign 对齐：消除「目录(连字符)/索引/会话(括号)」三处命名漂移做模糊匹配。"""
    return re.sub(r"[（）()\-—\s·]", "", str(s if s is not None else ""))


def _read_json(path: Path) -> "Any":
    """读 + 解析 JSON；不存在 / 坏档 → None（调用方按需兜底）。"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _resolve_thread_id(data_base: Path, explicit: str | None) -> str:
    if explicit and explicit.strip():
        tid = explicit.strip()
    else:
        # data-base 形如 <workspace>/.fathom-panels/<skill>，故 workspace = 上两级
        ctx_path = data_base.parent.parent / ".fathom-context.json"
        if not ctx_path.is_file():
            _die(f"找不到 .fathom-context.json（期望在 {ctx_path}）；可用 --thread 显式指定")
        try:
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            _die(f"读 .fathom-context.json 失败: {e}")
        tid = str(ctx.get("threadId", "")).strip()
    # threadId 要拼进路径，防目录穿越（与 Rust 同款校验）
    if not tid or "/" in tid or "\\" in tid or ".." in tid:
        _die(f"非法 thread_id: {tid!r}")
    return tid


def _load_campaign(data_base: Path, name: str) -> "tuple[dict, Path]":
    """定位战役目录并读 campaign.json，返回 (campaign_meta, campaign_dir)。
    先按目录名精确匹配，再扫所有 campaign.json 按 name 字段 / 归一名兜底（容忍命名漂移）。"""
    camps_root = data_base / "campaigns"
    if not camps_root.is_dir():
        _die(f"找不到 campaigns 目录: {camps_root}")
    # 1) 目录名精确匹配
    exact = camps_root / name / "campaign.json"
    meta = _read_json(exact)
    if isinstance(meta, dict):
        return meta, exact.parent
    # 2) 扫所有 campaign.json：先 name 字段精确，再归一名（name 字段 / 目录名）兜底
    target = _norm_campaign(name)
    fallback: "tuple[dict, Path] | None" = None
    for d in sorted(camps_root.iterdir()):
        if not d.is_dir():
            continue
        meta = _read_json(d / "campaign.json")
        if not isinstance(meta, dict):
            continue
        if meta.get("name") == name:
            return meta, d
        if fallback is None and (
            _norm_campaign(meta.get("name", "")) == target or _norm_campaign(d.name) == target
        ):
            fallback = (meta, d)
    if fallback is not None:
        return fallback
    _die(f"未找到战役（缺 campaign.json）: {name}")


def _pick_save(camp_dir: Path, save_name: str) -> dict:
    """从 <camp_dir>/saves/*.json 选存档：空名→createdAt 最大（次取文件名，迁移用 NNNN_ 前缀=新旧序）；
    否则按 name 字段匹配。无 saves 则返回空 dict（idle/无存档照常起 session）。"""
    saves_dir = camp_dir / "saves"
    items: "list[tuple[str, str, dict]]" = []
    if saves_dir.is_dir():
        for p in sorted(saves_dir.glob("*.json")):
            obj = _read_json(p)
            if isinstance(obj, dict):
                items.append((_str_or(obj, "createdAt", ""), p.name, obj))
    if not items:
        return {}
    if not save_name:
        return max(items, key=lambda t: (t[0], t[1]))[2]
    for _created, _fname, obj in items:
        if obj.get("name") == save_name:
            return obj
    _die(f"战役目录「{camp_dir.name}」未找到存档: {save_name}")


def build_session(campaign: dict, save_entry: dict) -> dict:
    """构造 session-v2——字段与顺序须与宿主 Rust dnd_load_session 完全一致。"""
    mode = _str_or(campaign, "mode", "G")
    dm_style = _str_or(campaign, "dmStyle", "")
    module_name = _str_or(campaign, "module", "")

    chapter = _str_or(save_entry, "chapter", "")
    in_game_time = _str_or(save_entry, "inGameTime", "") or chapter
    location = _str_or(save_entry, "location", "")

    module_val = {"name": module_name, "currentChapter": chapter} if mode == "G" else None
    sandbox_val: dict | None = {} if mode == "I" else None

    return {
        "_schema": "session-v2",
        "mode": mode,
        "campaign": {
            "name": _str_or(campaign, "name", ""),
            "dmStyle": dm_style,
            "inGameTime": in_game_time,
            "location": location,
        },
        "module": module_val,
        "combat": None,
        "sandbox": sandbox_val,
        "lastUpdate": _now_iso(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="从 campaigns/<战役>/campaign.json + saves/ 重建当前 thread 的 session.json"
    )
    ap.add_argument(
        "--data-base", required=True,
        help="技能业务数据根，即 <workspace>/.fathom-panels/<skill>",
    )
    ap.add_argument(
        "--thread", default=None,
        help="thread_id；省略则读 <workspace>/.fathom-context.json 的 threadId",
    )
    ap.add_argument("campaign", help="战役名（= campaign.json 的 name / 战役目录名）")
    ap.add_argument("save", nargs="?", default="", help="存档名；省略=最新存档")
    args = ap.parse_args(argv)
    _force_utf8_streams()

    # resolve()：相对路径按 CWD 展开（AI 路径 CWD=workspace），并让 parent.parent 取到真实 workspace
    data_base = Path(args.data_base).resolve()

    thread_id = _resolve_thread_id(data_base, args.thread)
    campaign, camp_dir = _load_campaign(data_base, args.campaign)
    save_entry = _pick_save(camp_dir, args.save.strip())
    session = build_session(campaign, save_entry)

    target = data_base / "threads" / thread_id / "session.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    # 不加末尾换行，贴近 Rust to_string_pretty 输出；ensure_ascii=False 保留中文可读
    target.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"session.json written: {target} "
        f"(mode={session['mode']} campaign={args.campaign})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
