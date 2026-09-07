#!/usr/bin/env bash
# 원본(이 저장소) → Claude Code 스킬 폴더로 밀어넣는다.
# 반대 방향은 없다. 스킬 폴더를 직접 고치지 말 것.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="$HOME/.claude/skills/doc-design"

[ -d "$DST" ] || { echo "스킬 폴더가 없다: $DST" >&2; exit 1; }
mkdir -p "$DST/components"

mkdir -p "$DST/sync"

cp "$SRC/docs/SKILL.md"          "$DST/SKILL.md"
cp "$SRC/STYLE.md"               "$DST/STYLE.md"
cp "$SRC/templates/"*.dc.html    "$DST/components/"
cp "$SRC/runtime/"*.js           "$DST/components/"
# 채움률 도구도 함께. 스킬 폴더만 있어도 fit.sh 가 돌아야 한다 —
# 런타임은 components/ 에서 찾고, 글꼴 캐시는 스킬 폴더 안에 따로 받는다.
cp "$SRC/sync/fit.py" "$SRC/sync/fit.sh" "$SRC/sync/fit-probe.js" \
   "$SRC/sync/measure.sh" "$SRC/sync/measure-probe.js" "$SRC/sync/measure-report.py" \
   "$SRC/sync/topdf.py" "$SRC/sync/topdf.sh" "$SRC/sync/fontcache.sh" \
   "$SRC/sync/checkpdf.py" "$SRC/sync/checkpdf.sh" "$DST/sync/"
chmod +x "$DST/sync/"*.sh

echo "스킬 폴더 갱신 완료 → $DST"
