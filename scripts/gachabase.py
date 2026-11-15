#!/usr/bin/env python
"""Gachabase 读取工具：列表取 ID 与名字，详情取页面文本。

用法:
    python scripts/gachabase.py gi char                 # 原神角色列表（beta）
    python scripts/gachabase.py gi char release         # 正式分支
    python scripts/gachabase.py gi weapon               # 武器
    python scripts/gachabase.py gi artifact             # 圣遗物
    python scripts/gachabase.py zzz char                # 绝区零代理人
    python scripts/gachabase.py zzz weapon              # 音擎
    python scripts/gachabase.py zzz disc                # 驱动盘
    python scripts/gachabase.py gi char danica          # 单角色页文本
    python scripts/gachabase.py zzz weapon 13022        # 单音擎页文本
    python scripts/gachabase.py gi char danica en       # 指定语言，默认 zh-cn
"""
import html as htmllib
import re
import sys
import urllib.request

HOST = {"gi": "https://gi.gachabase.net", "zzz": "https://zzz.gachabase.net"}
SECTION = {
    "gi": {"char": "characters", "weapon": "weapons", "artifact": "artifacts"},
    "zzz": {"char": "agents", "weapon": "w-engines", "disc": "drive-discs"},
}
BRANCHES = ("beta", "release", "creator")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "ignore")


def payload(doc):
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", doc, re.S)
    return max(scripts, key=len)


def records(doc):
    """列表页数据只在页尾内嵌 payload 里，页面不渲染条目。

    以 slug:"xxx" 锚定每条记录：ID 可能在前一条记录头（绝区零、圣遗物），
    也可能在 slug 之后的 character_id / href 上（原神角色）。
    """
    p = payload(doc)
    out, seen, skipped = [], set(), 0
    for m in re.finditer(r'slug:"([^"]+)"', p):
        slug = m.group(1)
        if slug in seen:
            continue
        seen.add(slug)
        after = p[m.end():m.end() + 2000]
        nxt = after.find('slug:"')  # 不许跨到下一条记录
        after = after[:nxt] if nxt != -1 else after
        nm = re.search(r'name:[{]key:"[^"]*",text:"([^"]*)"', after)
        if not nm:  # name 为 null 或引用变量的占位条目，原神旅行者与废案武器都属于这类
            skipped += 1
            continue
        hit = (re.search(r"character_id:(\d+)", after)
               or re.search(r'href:"/[a-z-]+/(\d+)/', after))
        if hit:
            item_id = hit.group(1)
        else:
            ids = re.findall(r"(?<![a-z_])id:(\d+)", p[max(0, m.start() - 220):m.start()])
            item_id = ids[-1] if ids else ""
        out.append((slug, nm.group(1), item_id))
    if skipped:
        print(f"跳过 {skipped} 条无内嵌名称的占位记录", file=sys.stderr)
    return out


def text(doc):
    """详情页已服务端渲染，去标签即可读。"""
    doc = re.sub(r"<script[^>]*>.*?</script>", "", doc, flags=re.S)
    doc = re.sub(r"<style[^>]*>.*?</style>", "", doc, flags=re.S)
    lines = htmllib.unescape(re.sub(r"<[^>]+>", "\n", doc)).split("\n")
    return [l.strip() for l in lines if l.strip()]


def main(argv):
    game = argv[0] if argv else "gi"
    kind = argv[1] if len(argv) > 1 else "char"
    arg = argv[2] if len(argv) > 2 else "beta"
    lang = argv[3] if len(argv) > 3 else "zh-cn"
    base = f"{HOST[game]}/{SECTION[game][kind]}"

    if arg in BRANCHES:
        for slug, name, item_id in records(fetch(f"{base}/{arg}?lang={lang}")):
            print(f"{item_id}\t{slug}\t{name}")
        return

    # 详情页 URL 需要数字 ID，先用列表页解析 slug。
    hit = [r for r in records(fetch(f"{base}/beta?lang={lang}")) if arg in r]
    if not hit:
        sys.exit(f"没有找到 {arg}")
    item_id, slug = hit[0][2], hit[0][0]
    lines = text(fetch(f"{base}/{item_id}/{slug}/beta?lang={lang}"))
    head = next((n for n, l in enumerate(lines) if re.match(r"^v\d+\.\d+", l)), 0)
    print("\n".join(lines[head:]))


if __name__ == "__main__":
    main(sys.argv[1:])
