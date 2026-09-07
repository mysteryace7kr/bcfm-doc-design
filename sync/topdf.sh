#!/usr/bin/env bash
# 문서를 PDF 로 뽑는다 (확인용). fit.sh 와 같은 조건에서 렌더한다.
#   ./sync/topdf.sh 내문서.dc.html [결과.pdf]
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$SRC/sync/topdf.py" "$@"
