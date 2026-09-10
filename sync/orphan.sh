#!/usr/bin/env bash
# 외톨이 줄을 잡는다 — 문단 마지막 줄에 한 단어·한 글자만 남는 곳을 찾는다.
#
#   ./sync/orphan.sh                     templates/ 의 서식 전부
#   ./sync/orphan.sh 어떤문서.dc.html     특정 파일 하나
#
# 인쇄 폭(210mm)으로 못박고 헤드리스 크롬으로 실제 렌더한 뒤, Range 로 글자마다
# 사각형을 읽어 줄을 센다. 잰 것은 화면이 아니라 인쇄에 나올 줄바꿈이다.
# 판정 — 두 줄 이상인 문단의 마지막 줄이
#   한 글자          → 불합격 (반드시 고친다)
#   한 단어 3글자 이하 → 주의
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || { echo "크롬을 못 찾았다: $CHROME" >&2; exit 1; }

targets=()
if [ $# -gt 0 ]; then
  for a in "$@"; do targets+=("$(cd "$(dirname "$a")" && pwd)/$(basename "$a")"); done
else
  for f in "$SRC"/templates/*.dc.html "$SRC"/components/*.dc.html; do
    [ -f "$f" ] && targets+=("$f")
  done
fi

WORK="$(mktemp -d)"
if [ -d "$SRC/runtime" ]; then cp "$SRC/runtime/"*.js "$WORK/";
else cp "$SRC/components/doc-page.js" "$SRC/components/support.js" "$WORK/"; fi
cp "$SRC/sync/orphan-probe.js" "$WORK/"

PORT="$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"
(cd "$WORK" && exec python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1) &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true; rm -rf "$WORK"' EXIT
for _ in $(seq 1 40); do
  curl -s -o /dev/null "http://127.0.0.1:$PORT/" && break
  perl -e 'select(undef,undef,undef,0.1)'
done

fail=0
for t in "${targets[@]}"; do
  name="$(basename "$t")"
  python3 - "$t" "$WORK/$name" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
html = open(src, encoding="utf-8").read()
tag = ('<style>doc-page > section.page{width:210mm!important;'
       'height:297mm!important;aspect-ratio:auto!important}</style>\n'
       '<script src="./orphan-probe.js"></script>\n')
html = html.replace("</body>", tag + "</body>", 1) if "</body>" in html else html + tag
open(dst, "w", encoding="utf-8").write(html)
PY
  dom=""
  for _ in 1 2 3; do
    dom="$("$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
          --window-size=1400,2400 --force-device-scale-factor=1 \
          --virtual-time-budget=15000 --dump-dom "http://127.0.0.1:$PORT/$name" 2>/dev/null)"
    case "$dom" in *'id="__orphan"'*) break ;; esac
  done
  echo "$dom" | python3 "$SRC/sync/orphan-report.py" "$name" || fail=1
done
exit $fail
