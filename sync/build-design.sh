#!/usr/bin/env bash
# 원본 → Claude Design 업로드용 변형을 build/design/ 에 만든다.
#
# 원본과 다른 점은 딱 둘이다.
#   1) 폰트 — .dc.html 은 <link> 3줄을 빼고 @font-face 를 넣고,
#            styles.css 는 @import 를 @font-face 로 바꾼다
#   2) 배치 — templates/<이름>/ 안에 런타임을 각각 복제한다
#
# fonts/ · ds-base.js · _ds_manifest.json · _ds_bundle.js 는 Claude Design 이
# 소유한다. 여기서 만들지 않고, 업로드할 때도 건드리지 않는다.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$SRC/build/design"

rm -rf "$OUT"
mkdir -p "$OUT/templates"
cp "$SRC/docs/design-readme.md" "$OUT/readme.md"
# styles.css 도 폰트 참조가 다르다 — 루트에 놓이므로 경로는 fonts/ 다.
python3 "$SRC/sync/fontswap.py" "$SRC/styles.css" "$OUT/styles.css"

for name in report formal brief; do
  mkdir -p "$OUT/templates/$name"
  cp "$SRC/runtime/"*.js "$OUT/templates/$name/"
  python3 "$SRC/sync/fontswap.py" \
    "$SRC/templates/$name.dc.html" \
    "$OUT/templates/$name/$name.dc.html"
done

echo "빌드 완료 → $OUT"
find "$OUT" -type f | sed "s|$OUT|  build/design|"
