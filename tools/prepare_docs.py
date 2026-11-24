#!/usr/bin/env python3
"""元の Markdown をビルド用ディレクトリ(.site-src/)へコピーし、リンクを mkdocs 向けに整える。
元のファイルは書き換えない。"""
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".site-src"

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()

shutil.copy(ROOT / "LICENSE", OUT / "LICENSE")
shutil.copy(ROOT / "README.md", OUT / "index.md")
for d in sorted(ROOT.glob("Lecture*")):
    if d.is_dir():
        shutil.copytree(d, OUT / d.name)

link = re.compile(r"\]\((/[^)\s]+)\)")  # ルート始まりの絶対リンク

for md in OUT.rglob("*.md"):
    text = md.read_text(encoding="utf-8")

    def fix(m):
        target = OUT / m.group(1).lstrip("/")
        rel = os.path.relpath(target, md.parent)
        return "](" + rel.replace(os.sep, "/") + ")"

    new = link.sub(fix, text)
    if new != text:
        md.write_text(new, encoding="utf-8")
