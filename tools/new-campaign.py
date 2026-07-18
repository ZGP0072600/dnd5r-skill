#!/usr/bin/env python3
"""开桌：为一个【新战役】建好最小骨架（campaign.json）并点亮当前 thread 的面板（session.json）。

与 load-session.py 对称的「单一真源」骨架脚本：
  - load-session.py：已存在的战役 → 投影 session.json（读档 / 宿主「继续」按钮）。
  - new-campaign.py：无中生有一个新战役 → 建 campaign.json + 复用 load-session 写 session.json（开桌 / 开沙盒）。

只做【确定性骨架】——注册战役 + 点亮面板。叙事层（world-state / progress / 车卡 /
NPC 秘密 / 沙盒五问）留给 AI 的 G1 / I1 工作流，脚本不碰。

做的事：
  1. 写 <data-base>/campaigns/<name>/campaign.json = {name, mode, module, dmStyle, lastPlayed}
     （已存在则不覆盖、只刷 lastPlayed —— 幂等，等同「继续」）。
  2. 复用 load-session.py 把当前 thread 的 session.json 写好（mode=G/I → 面板立即亮）。
     无 thread 上下文（非 Fathom 环境）则跳过第 2 步，campaign.json 仍建好，下次读档即点亮。

⚠️ 不建 workspace 根的叙事 .md（README/world-state/progress/players…）——那是 AI 的创作层。

用法：
    python tools/new-campaign.py --data-base .fathom-panels/dnd5r --mode G --module "风骸岛之龙" --name "风骸岛之龙-小明组" [--dm-style 标准]
    python tools/new-campaign.py --data-base .fathom-panels/dnd5r --mode I --name "博德之门-日常" [--dm-style 粉红恋爱向]
    python tools/new-campaign.py ... --thread thr_xxx      # 宿主路径：显式传 thread
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load_sibling(mod_name: str, filename: str):
    """importlib 加载同目录带连字符的脚本（load-session.py 无法直接 import）。"""
    spec = importlib.util.spec_from_file_location(mod_name, _HERE / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 复用 load-session.py 的会话投影逻辑（session 形状单一真源，避免与宿主 Rust / 手写步骤漂移）
_ls = _load_sibling("ls_shared", "load-session.py")


def _force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(
        description="为新战役建 campaign.json 骨架并点亮当前 thread 的面板 session.json"
    )
    ap.add_argument("--data-base", required=True, help="技能业务数据根，即 <workspace>/.fathom-panels/<skill>")
    ap.add_argument("--mode", required=True, choices=["G", "I"], help="G=模组带团 / I=沙盒")
    ap.add_argument("--name", required=True, help="战役名（= 战役目录名 / campaign.json 的 name）")
    ap.add_argument("--module", default="", help="模组名（mode=G 应填；mode=I 留空）")
    ap.add_argument("--dm-style", dest="dm_style", default="标准", help="DM 风格预设名，默认 标准")
    ap.add_argument("--thread", default=None, help="thread_id；省略则读 <workspace>/.fathom-context.json 的 threadId")
    args = ap.parse_args(argv)
    _force_utf8()

    if args.mode == "G" and not args.module.strip():
        print("警告：mode=G（带团）但未指定 --module，campaign.json.module 将为空。", file=sys.stderr)

    data_base = Path(args.data_base).resolve()
    name = args.name.strip()
    if not name or "/" in name or "\\" in name or ".." in name:
        print(f"非法战役名: {name!r}", file=sys.stderr)
        return 1

    camp_dir = data_base / "campaigns" / name
    camp_json = camp_dir / "campaign.json"
    today = datetime.now().strftime("%Y-%m-%d")

    # 1) campaign.json —— 幂等：已存在则只刷 lastPlayed（不覆盖，等同「继续」）
    if camp_json.is_file():
        meta = _ls._read_json(camp_json)
        if not isinstance(meta, dict):
            meta = {}
        meta["lastPlayed"] = today
        action = "已存在（未覆盖，仅刷新 lastPlayed）"
    else:
        meta = {
            "name": name,
            "mode": args.mode,
            "module": args.module.strip(),
            "dmStyle": args.dm_style.strip(),
            "lastPlayed": today,
        }
        action = "已新建"
    camp_dir.mkdir(parents=True, exist_ok=True)
    camp_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"campaign.json {action}: {camp_json}  (mode={meta.get('mode')} module={meta.get('module') or '—'})")

    # 2) session.json —— 复用 load-session.py 点亮面板；无 thread 上下文则优雅跳过
    ls_argv = ["--data-base", str(data_base)]
    if args.thread:
        ls_argv += ["--thread", args.thread]
    ls_argv += [name]
    try:
        rc = _ls.main(ls_argv)
    except SystemExit as e:  # load-session 的 _die() 会抛 SystemExit（如无 .fathom-context.json）
        rc = e.code if isinstance(e.code, int) else 1
    if rc == 0:
        print(f"✅ 面板已点亮（mode={meta.get('mode')}，campaign={name}）")
    else:
        print("ℹ️ 无 thread 上下文（非 Fathom 环境）：campaign.json 已建好，进 Fathom / 下次读档即可点亮面板。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
