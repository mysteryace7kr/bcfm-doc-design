#!/usr/bin/env python3
"""measure.sh 가 넘긴 DOM 에서 프로브 결과를 꺼내 사람이 읽는 표로 찍는다."""
import html as htmlmod
import json
import re
import sys

name = sys.argv[1] if len(sys.argv) > 1 else "?"
dom = sys.stdin.read()

m = re.search(r'<pre id="__measure">(.*?)</pre>', dom, re.S)
if not m:
    print(f"\n■ {name}\n  측정 실패 — 프로브가 결과를 안 남겼다 "
          f"(doc-page 가 정의되지 않았거나 렌더 전에 끊겼다)")
    sys.exit(1)

d = json.loads(htmlmod.unescape(m.group(1)))
if "error" in d:
    print(f"\n■ {name}\n  {d['error']}")
    sys.exit(1)

print(f"\n■ {name}  —  A4 {d['pageCount']}쪽")
print(f"  본문 {d['fontSizePx']:g}px / 줄높이 {d['lineHeightPx']:g}px"
      f"  ·  한 쪽 용량 {d['linesPerPage']:g}줄"
      f"  ·  95% 목표 {d['target95Lines']:g}줄")
print(f"  {'쪽':<4}{'채움률':>8}{'쓴 줄':>8}{'남은 여백':>11}   판정")
for p in d["pages"]:
    if p.get("overflow"):
        verdict = "★ 넘침 — 잘린다. 쪽을 나눠라"
    elif p["fillPct"] >= 92:
        verdict = "적정"
    elif p["fillPct"] >= 80:
        verdict = "조금 빈다"
    else:
        short = d["target95Lines"] - p["usedLines"]
        verdict = f"비었다 — {short:.1f}줄 부족"
    print(f"  {p['page']:<4}{p['fillPct']:>7.1f}%{p['usedLines']:>8.1f}"
          f"{p['leftMm']:>9}mm   {verdict}")
