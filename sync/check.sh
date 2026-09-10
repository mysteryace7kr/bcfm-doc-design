#!/usr/bin/env bash
# 사본이 원본에서 벗어났는지 점검한다. 고치지는 않는다.
set -uo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$HOME/.claude/skills/doc-design"
rc=0

echo "── 스킬 폴더 ($SKILL)"
if [ ! -d "$SKILL" ]; then
  echo "   없음"; rc=1
else
  # 서식 목록을 박아 두지 않는다 — 폐기한 서식을 계속 찾던 사고가 있었다.
  for src in "$SRC"/templates/*.dc.html; do
    f="$(basename "$src")"
    diff -q "$src" "$SKILL/components/$f" >/dev/null 2>&1 \
      || { echo "   어긋남: $f"; rc=1; }
  done
  # 원본에 없는데 사본에 남아 있는 서식 — to-skill.sh 가 지우지 못한 것
  for cp in "$SKILL"/components/*.dc.html; do
    f="$(basename "$cp")"
    [ -f "$SRC/templates/$f" ] || { echo "   사본에만 있음(폐기 누락): $f"; rc=1; }
  done
  for f in doc-page.js support.js; do
    diff -q "$SRC/runtime/$f" "$SKILL/components/$f" >/dev/null 2>&1 \
      || { echo "   어긋남: $f"; rc=1; }
  done
  diff -q "$SRC/docs/SKILL.md" "$SKILL/SKILL.md" >/dev/null 2>&1 || { echo "   어긋남: SKILL.md"; rc=1; }
  diff -q "$SRC/STYLE.md"     "$SKILL/STYLE.md" >/dev/null 2>&1 || { echo "   어긋남: STYLE.md"; rc=1; }
  diff -q "$SRC/sync/README.md" "$SKILL/sync/README.md" >/dev/null 2>&1 || { echo "   어긋남: sync/README.md"; rc=1; }
  [ $rc -eq 0 ] && echo "   일치"
fi

echo "── git"
if [ -n "$(git -C "$SRC" status --porcelain)" ]; then
  echo "   커밋 안 된 변경 있음"
  git -C "$SRC" status --short | sed 's/^/   /'
  rc=1
else
  echo "   깨끗함"
fi

echo "── Claude Design (원격)"
echo "   bash 로는 못 본다. Claude Code 에서 DesignSync 로 확인한다:"
echo "   list_files / get_file → build/design/ 과 대조"

exit $rc
