#!/usr/bin/env bash
# 원본(이 저장소) → Claude Code 스킬 폴더로 밀어넣는다.
# 반대 방향은 없다. 스킬 폴더를 직접 고치지 말 것.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="$HOME/.claude/skills/doc-design"

[ -d "$DST" ] || { echo "스킬 폴더가 없다: $DST" >&2; exit 1; }
mkdir -p "$DST/components"

cp "$SRC/docs/SKILL.md"          "$DST/SKILL.md"
cp "$SRC/STYLE.md"               "$DST/STYLE.md"
cp "$SRC/templates/"*.dc.html    "$DST/components/"
cp "$SRC/runtime/"*.js           "$DST/components/"

echo "스킬 폴더 갱신 완료 → $DST"
