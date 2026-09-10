#!/usr/bin/env bash
# 원본 → Claude Design 업로드용 배치를 build/design/ 에 만든다.
#
# 원본과 다른 점은 하나뿐이다 — 배치. templates/report/ 안에 런타임을 함께 둔다.
# 폰트 참조는 치환하지 않는다. 원본이 이미 Claude Design 기준 경로를 들고 있고
# (@font-face 의 ../../fonts/), local('Pretendard') 가 앞에 있어 맥에서는 설치본이
# 먼저 쓰인다. 예전에는 fontswap.py 가 이 치환을 했는데, 원본과 업로드본이
# 달라지는 원인이었으므로 없앴다.
#
# fonts/ · ds-base.js · _ds_manifest.json · _ds_bundle.js 는 Claude Design 이
# 소유한다. 여기서 만들지 않는다 — 단, Pretendard TTF 3개는 이 시스템이 올린다.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$SRC/build/design"

rm -rf "$OUT"
mkdir -p "$OUT/templates/report"
# Claude Design 프로젝트의 readme 는 STYLE.md 그 자체다. 예전에는
# docs/design-readme.md 라는 사본을 따로 뒀는데 STYLE.md 와 바이트 단위로
# 같았다 — 중복이라 없앴다(2026-09-10).
cp "$SRC/STYLE.md" "$OUT/readme.md"
cp "$SRC/styles.css"            "$OUT/styles.css"
cp "$SRC/runtime/"*.js          "$OUT/templates/report/"
cp "$SRC/templates/report.dc.html" "$OUT/templates/report/report.dc.html"

# Pretendard TTF 3개 — Claude Design 의 fonts/ 에 이 시스템이 올리는 유일한 자산이다.
# 맥 설치본(~/Library/Fonts)에서 가져온다. Pretendard 는 Google Fonts 에 없어서
# 웹폰트로 물릴 수 없고, 서버에서 렌더하는 내보내기 경로에는 설치본이 없기 때문이다.
# fonts/ 의 Noto TTF 8개는 앱 소유다 — 빌드에 넣지 않고 업로드 계획에도 넣지 않는다.
mkdir -p "$OUT/fonts"
for w in Regular Medium Bold; do
  f="$HOME/Library/Fonts/Pretendard-$w.ttf"
  [ -f "$f" ] || { echo "Pretendard-$w.ttf 가 없다: $f" >&2; exit 1; }
  cp "$f" "$OUT/fonts/"
done

echo "빌드 완료 → $OUT"
find "$OUT" -type f | sed "s|$OUT|  build/design|"
