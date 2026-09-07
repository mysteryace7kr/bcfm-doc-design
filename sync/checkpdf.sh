#!/usr/bin/env bash
# 흐름 문서를 A4 로 뽑아 쪽별 채움률을 재고 합격·불합격을 찍는다.
#   ./sync/checkpdf.sh 내문서.dc.html
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$SRC/sync/checkpdf.py" "$@"
