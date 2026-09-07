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
  for n in report formal brief; do targets+=("$SRC/templates/$n.dc.html"); done
fi

WORK="$(mktemp -d)"
cp "$SRC/runtime/"*.js "$SRC/sync/measure-probe.js" "$WORK/"

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
tag = '<script src="./measure-probe.js"></script>\n'
if "</body>" in html:
    html = html.replace("</body>", tag + "</body>", 1)
else:
    html += tag
open(dst, "w", encoding="utf-8").write(html)
PY
  dom="$("$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
        --window-size=1400,2400 --force-device-scale-factor=1 \
        --virtual-time-budget=8000 --dump-dom "http://127.0.0.1:$PORT/$name" 2>/dev/null)"
  echo "$dom" | python3 "$SRC/sync/measure-report.py" "$name" || true
done
