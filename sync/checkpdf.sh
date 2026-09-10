#!/usr/bin/env bash
# 흐름 문서를 A4 로 뽑아 기본 여백의 본문 잉크 도달률을 참고값으로 출력한다.
#   ./sync/checkpdf.sh 내문서.dc.html
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$SRC/sync/checkpdf.py" "$@"
