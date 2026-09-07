#!/usr/bin/env python3
"""Google Fonts <link> 3줄 → 로컬 TTF @font-face 1줄 치환.

기대한 줄을 못 찾으면 조용히 넘어가지 않고 죽는다. 원본이 바뀌었는데
치환만 실패해서 Claude Design 쪽 폰트가 슬그머니 웹폰트로 돌아가는 것이
이 스크립트가 막으려는 사고다.
"""
import sys

LINKS = [
    '<link rel="preconnect" href="https://fonts.googleapis.com">',
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">',
    '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:'
    'wght@400;500;700&display=swap" rel="stylesheet">',
]
FONT_FACE = (
    "  @font-face{font-family:'Noto Sans KR';"
    "src:url('../../fonts/NotoSansKR-VariableFont_wght.ttf') "
    "format('truetype-variations');"
    "font-weight:100 900;font-style:normal;font-display:swap}"
)

src, dst = sys.argv[1], sys.argv[2]
lines = open(src, encoding="utf-8").read().split("\n")

for want in LINKS:
    if want not in lines:
        sys.exit(f"{src}: 기대한 Google Fonts 줄을 못 찾았다 — {want}")
if "<style>" not in lines:
    sys.exit(f"{src}: <style> 줄을 못 찾았다")

out = []
for line in lines:
    if line in LINKS:
        continue
    out.append(line)
    if line == "<style>":
        out.append(FONT_FACE)

open(dst, "w", encoding="utf-8").write("\n".join(out))
