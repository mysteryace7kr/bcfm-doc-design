#!/usr/bin/env python3
"""저장소본(Google Fonts) → Claude Design본(로컬 TTF) 폰트 참조 치환.

파일 종류에 따라 치환 방식이 다르다.

  .dc.html  <link> 3줄을 빼고 <style> 맨 위에 @font-face 를 넣는다.
            templates/<이름>/ 안에 놓이므로 경로가 ../../fonts/ 다.
  .css      @import 한 줄을 @font-face 로 바꾼다.
            프로젝트 루트에 놓이므로 경로가 fonts/ 다.

기대한 줄을 못 찾으면 조용히 넘어가지 않고 죽는다. 치환만 실패해서
Claude Design 쪽 폰트가 슬그머니 웹폰트로 돌아가는 것이 막으려는 사고다.
"""
import sys

LINKS = [
    '<link rel="preconnect" href="https://fonts.googleapis.com">',
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">',
    '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:'
    'wght@400;500;700&display=swap" rel="stylesheet">',
]
IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Noto+Sans+KR:wght@400;500;700&display=swap');"
)


def face(prefix, indent=""):
    return (
        f"{indent}@font-face{{font-family:'Noto Sans KR';"
        f"src:url('{prefix}fonts/NotoSansKR-VariableFont_wght.ttf') "
        "format('truetype-variations');"
        "font-weight:100 900;font-style:normal;font-display:swap}"
    )


def swap_template(src, lines):
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
            out.append(face("../../", "  "))
    return out


def swap_css(src, lines):
    if IMPORT not in lines:
        sys.exit(f"{src}: 기대한 @import 줄을 못 찾았다 — {IMPORT}")
    return [face("") if line == IMPORT else line for line in lines]


src, dst = sys.argv[1], sys.argv[2]
lines = open(src, encoding="utf-8").read().split("\n")
swap = swap_css if src.endswith(".css") else swap_template
open(dst, "w", encoding="utf-8").write("\n".join(swap(src, lines)))
