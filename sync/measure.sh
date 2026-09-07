#!/usr/bin/env bash
# 쪽별 채움률을 잰다. A4 인쇄 기준이다 — 한 <section class="page"> 이 A4 한 장이고,
# 그 한 장을 이 시스템에서 "1쪽"이라고 부른다.
#
#   ./sync/measure.sh                     templates/ 의 서식 3종을 모두
#   ./sync/measure.sh 어떤문서.dc.html     특정 파일 하나
#
# 헤드리스 크롬으로 실제 렌더한 뒤 잰다. npm 의존성은 없다.
# file:// 에서는 <x-dc> 런타임이 돌지 않아 로컬 http 서버를 잠깐 띄운다.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || { echo "크롬을 못 찾았다: $CHROME" >&2; exit 1; }

targets=()
if [ $# -gt 0 ]; then
  for a in "$@"; do targets+=("$(cd "$(dirname "$a")" && pwd)/$(basename "$a")"); done
else
  for n in report formal brief; do
    if [ -f "$SRC/templates/$n.dc.html" ]; then targets+=("$SRC/templates/$n.dc.html")
    else targets+=("$SRC/components/$n.dc.html"); fi
  done
fi

WORK="$(mktemp -d)"
# 저장소는 runtime/ 에, 스킬 폴더 사본은 components/ 에 런타임을 둔다.
if [ -d "$SRC/runtime" ]; then cp "$SRC/runtime/"*.js "$WORK/";
else cp "$SRC/components/doc-page.js" "$SRC/components/support.js" "$WORK/"; fi
cp "$SRC/sync/measure-probe.js" "$WORK/"

PORT="$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"
(cd "$WORK" && exec python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1) &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true; rm -rf "$WORK"' EXIT
for _ in $(seq 1 40); do
  curl -s -o /dev/null "http://127.0.0.1:$PORT/" && break
  perl -e 'select(undef,undef,undef,0.1)'
done

for t in "${targets[@]}"; do
  name="$(basename "$t")"
  python3 - "$t" "$WORK/$name" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
html = open(src, encoding="utf-8").read()
# 화면의 .page 는 시트 폭을 따라가지만 인쇄에서는 210×297mm 로 못박힌다.
# 창 크기에 따라 줄바꿈이 달라지지 않도록 재는 동안 인쇄 크기로 고정한다.
tag = ('<style>doc-page > section.page{width:210mm!important;'
       'height:297mm!important;aspect-ratio:auto!important}</style>\n'
       '<script src="./measure-probe.js"></script>\n')
if "</body>" in html:
    html = html.replace("</body>", tag + "</body>", 1)
else:
    html += tag
open(dst, "w", encoding="utf-8").write(html)
PY
  # 웹폰트를 네트워크에서 받는 사이 렌더가 늦어 프로브가 빈손으로 끝나는
  # 경우가 있다. 결과가 없으면 다시 잰다.
  dom=""
  for attempt in 1 2 3; do
    dom="$("$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
          --window-size=1400,2400 --force-device-scale-factor=1 \
          --virtual-time-budget=15000 --dump-dom "http://127.0.0.1:$PORT/$name" 2>/dev/null)"
    case "$dom" in *'id="__measure"'*) break ;; esac
  done
  echo "$dom" | python3 "$SRC/sync/measure-report.py" "$name" || true
done
