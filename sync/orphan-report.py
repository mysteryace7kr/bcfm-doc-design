#!/usr/bin/env python3
"""orphan-probe.js 가 DOM 에 적은 JSON 을 읽어 외톨이 줄을 보고한다."""
import html
import json
import re
import sys

name = sys.argv[1]
dom = sys.stdin.read()
m = re.search(r'<pre id="__orphan">(.*?)</pre>', dom, re.S)
if not m:
    print(f"■ {name}  —  측정 실패 (프로브가 결과를 못 남겼다)")
    raise SystemExit(1)
rows = json.loads(html.unescape(m.group(1)))

bad = [r for r in rows if r["lastChars"] <= 1]
warn = [r for r in rows if r["lastChars"] > 1 and r["lastWords"] == 1 and r["lastChars"] <= 3]
print(f"■ {name}  —  두 줄 이상 문단 {len(rows)}개")
for r in bad:
    print(f"  불합격  .{r['cls']:<6} {r['lines']}줄  마지막 줄 「{r['last']}」  ← {r['head']}…")
for r in warn:
    print(f"  주의    .{r['cls']:<6} {r['lines']}줄  마지막 줄 「{r['last']}」  ← {r['head']}…")
if not bad and not warn:
    print("  합격 — 마지막 줄에 한 글자·한 단어만 남는 문단이 없다")
raise SystemExit(1 if bad else 0)
