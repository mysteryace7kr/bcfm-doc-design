#!/usr/bin/env bash
# 측정용 Noto Sans KR 을 한 번만 내려받아 sync/.fontcache/ 에 둔다.
#
# 왜 필요한가 — 헤드리스 크롬에서 Google Fonts 의 한글 웹폰트는 유니코드 구간별로
# 100개 넘게 쪼개져 있어 지연 로딩되고, document.fonts.ready 가 그보다 먼저
# 풀린다. 그러면 Apple SD Gothic Neo 로 대체돼 같은 문장이 6.4% 좁게 잡히고,
# 줄바꿈이 달라져 잰 채움률이 실제 인쇄와 어긋난다.
# 로컬 TTF 를 물리면 네트워크 없이 항상 같은 값이 나온다.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.fontcache"
mkdir -p "$DIR"
declare -a W=(400 500 700)
declare -a U=(
  "https://fonts.gstatic.com/s/notosanskr/v39/PbyxFmXiEBPT4ITbgNA5Cgms3VYcOA-vvnIzzuoyeLQ.ttf"
  "https://fonts.gstatic.com/s/notosanskr/v39/PbyxFmXiEBPT4ITbgNA5Cgms3VYcOA-vvnIzztgyeLQ.ttf"
  "https://fonts.gstatic.com/s/notosanskr/v39/PbyxFmXiEBPT4ITbgNA5Cgms3VYcOA-vvnIzzg01eLQ.ttf"
)
for i in 0 1 2; do
  f="$DIR/NotoSansKR-${W[$i]}.ttf"
  if [ -s "$f" ]; then echo "  있음: $(basename "$f")"; continue; fi
  echo "  받는 중: $(basename "$f")"
  curl -fsSL -A "Mozilla/4.0" "${U[$i]}" -o "$f"
  [ -s "$f" ] || { echo "받기 실패: ${U[$i]}" >&2; exit 1; }
done
ls -la "$DIR"
