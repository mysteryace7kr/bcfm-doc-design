#!/usr/bin/env bash
# 쪽을 다시 나눠 채운다. measure.sh 가 재기만 한다면 이쪽은 고친다.
#
#   ./sync/fit.sh 내문서.dc.html          제자리에서 고친다 (.bak 를 남긴다)
#   ./sync/fit.sh --dry 내문서.dc.html    고치지 않고 결과만 본다
#
# 제목에서 쪽을 나누지 않는다. 한 쪽을 꽉 채우고 넘칠 때만 다음 쪽으로 넘긴다.
# 반드시 새 쪽에서 시작해야 하는 블록에만 data-break="page" 를 붙인다.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$SRC/sync/fit.py" "$@"
