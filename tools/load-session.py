#!/usr/bin/env python3
"""读档：从 all-saves.json 重建【当前 thread】的 session.json。

单一事实源——宿主「继续」按钮（Tauri 直接 spawn 本脚本）和 AI 打字 /load
（SKILL.md G7/S2 调本脚本）共用这一份读档逻辑，避免「Rust 实现」与「SKILL.md 手写步骤」
两处漂移。输出形状须与宿主 Rust `dnd_load_session` 完全一致，两条路径才能互换。

做的事：
  读 all-saves.json 里某战役某存档的 mode / dmStyle / module / chapter / inGameTime / location
  → 按 session-v2 契约全量重写 <data-base>/threads/<threadId>/session.json。
  不含 players[]——队伍 HUD 由 panel 从 canonical characters/*.json 派生。

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


def _find_campaign(all_saves: dict, name: str) -> dict:
    camps = all_saves.get("campaigns")
    if not isinstance(camps, list):
        _die("all-saves.json 缺 campaigns 数组")
    for c in camps:
        if isinstance(c, dict) and c.get("name") == name:
            return c
    _die(f"all-saves 未找到战役: {name}")


def _pick_save(campaign: dict, save_name: str) -> dict:
    """save_name 为空 → 取最新（最后一个）；否则按名查找。无 saves 则返回空 dict。"""
    saves = campaign.get("saves")
    if not isinstance(saves, list) or not saves:
        return {}
    if not save_name:
        last = saves[-1]
        return last if isinstance(last, dict) else {}
    for s in saves:
        if isinstance(s, dict) and s.get("name") == save_name:
            return s
    _die(f"战役「{campaign.get('name', '')}」未找到存档: {save_name}")


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
        description="从 all-saves.json 重建当前 thread 的 session.json"
    )
    ap.add_argument(
        "--data-base", required=True,
        help="技能业务数据根，即 <workspace>/.fathom-panels/<skill>",
    )
    ap.add_argument(
        "--thread", default=None,
        help="thread_id；省略则读 <workspace>/.fathom-context.json 的 threadId",
    )
    ap.add_argument("campaign", help="战役名（all-saves 里 campaigns[].name）")
    ap.add_argument("save", nargs="?", default="", help="存档名；省略=最新存档")
    args = ap.parse_args(argv)
    _force_utf8_streams()

    # resolve()：相对路径按 CWD 展开（AI 路径 CWD=workspace），并让 parent.parent 取到真实 workspace
    data_base = Path(args.data_base).resolve()
    all_saves_path = data_base / "all-saves.json"
    if not all_saves_path.is_file():
        _die(f"读 all-saves.json 失败：{all_saves_path} 不存在")
    try:
        all_saves = json.loads(all_saves_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _die(f"解析 all-saves.json 失败: {e}")

    thread_id = _resolve_thread_id(data_base, args.thread)
    campaign = _find_campaign(all_saves, args.campaign)
    save_entry = _pick_save(campaign, args.save.strip())
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
