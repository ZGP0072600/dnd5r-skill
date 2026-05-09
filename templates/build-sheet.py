#!/usr/bin/env python3
"""
车卡输出脚本：把角色 JSON 嵌进模板，产出独立的单文件 HTML。

用法：
    # 文件输入
    python build-sheet.py <character.json> <output.html>

    # stdin 输入（推荐 —— AI 工作流不落盘）
    python build-sheet.py - <output.html> <<'EOF'
    {...JSON...}
    EOF

行为：
- 读取同目录下的 character-sheet.html 作模板
- 把 JSON 注入到 <script id="character-data" type="application/json"> 块
- 自动 normalize：cur 数字字段 → used 布尔数组（兼容旧 schema 写法）
- 若 meta.charId 缺失，按 "<name>-<unix-time>" 自动生成
- 改 <title> 为 "<角色名> - DnD 5r"
- 写到 output.html（UTF-8）
"""
import json
import re
import sys
import time
from pathlib import Path


def normalize(c: dict) -> dict:
    """把 cur 数字字段转成 used 布尔数组（pip 独立 toggle 所需）。
    旧 schema (cur:N, max:M) → 新 schema (max:M, used:[bool*M])
    旧 deathSaves (success:N, fail:N) → 新 (success:[bool*3], fail:[bool*3])
    已经是新 schema 的不动。
    """
    # 法术位
    sc = c.get('spellcasting') or {}
    slots = sc.get('slots') or {}
    for lv, s in slots.items():
        if isinstance(s.get('used'), list):
            continue
        mx = int(s.get('max', 0))
        cur = int(s.get('cur', mx))
        used_count = max(0, mx - cur)
        s['used'] = [False] * mx
        # 把已用的标在右边（视觉上仍是"满在左、空在右"，但用户后续可独立 toggle）
        for i in range(used_count):
            if mx - 1 - i >= 0:
                s['used'][mx - 1 - i] = True
        s.pop('cur', None)

    # 职业资源
    for r in c.get('classResources') or []:
        if isinstance(r.get('used'), list):
            continue
        mx = int(r.get('max', 0))
        cur = int(r.get('cur', mx))
        used_count = max(0, mx - cur)
        r['used'] = [False] * mx
        for i in range(used_count):
            if mx - 1 - i >= 0:
                r['used'][mx - 1 - i] = True
        r.pop('cur', None)

    # 死亡豁免
    combat = c.get('combat') or {}
    ds = combat.get('deathSaves')
    if isinstance(ds, dict):
        for k in ('success', 'fail'):
            v = ds.get(k)
            if isinstance(v, list):
                continue
            n = int(v or 0)
            ds[k] = [i < n for i in range(3)]

    return c


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    script_dir = Path(__file__).resolve().parent
    template_path = script_dir / 'character-sheet.html'
    out_path = Path(sys.argv[2])

    if not template_path.exists():
        print(f'错误：模板不存在 {template_path}', file=sys.stderr)
        return 1

    # 读 JSON：'-' 表示 stdin
    if sys.argv[1] == '-':
        # 强制 UTF-8 读取（绕开 Windows cp936 默认）
        char_text = sys.stdin.buffer.read().decode('utf-8')
    else:
        char_path = Path(sys.argv[1])
        if not char_path.exists():
            print(f'错误：角色 JSON 不存在 {char_path}', file=sys.stderr)
            return 1
        char_text = char_path.read_text(encoding='utf-8')

    char = json.loads(char_text)
    char = normalize(char)

    # 补 charId
    char.setdefault('meta', {})
    name = char['meta'].get('name', 'character')
    if not char['meta'].get('charId'):
        suffix = str(int(time.time()))[-8:]
        char['meta']['charId'] = f'{name}-{suffix}'

    new_data = json.dumps(char, ensure_ascii=False, indent=2)

    html = template_path.read_text(encoding='utf-8')
    pattern = re.compile(
        r'(<script id="character-data" type="application/json">)(.*?)(</script>)',
        re.DOTALL,
    )
    if not pattern.search(html):
        print('错误：模板中找不到 <script id="character-data"> 锚点', file=sys.stderr)
        return 1
    html = pattern.sub(
        lambda m: m.group(1) + '\n' + new_data + '\n' + m.group(3),
        html,
        count=1,
    )
    html = re.sub(
        r'<title>.*?</title>',
        f'<title>{name} - DnD 5r</title>',
        html,
        count=1,
    )

    out_path.write_text(html, encoding='utf-8')
    size_kb = out_path.stat().st_size / 1024
    print(f'已生成: {out_path} ({size_kb:.1f} KB, charId={char["meta"]["charId"]})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
