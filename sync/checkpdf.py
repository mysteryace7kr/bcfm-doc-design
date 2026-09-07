#!/usr/bin/env python3
"""흐름 문서를 A4 로 뽑아 쪽별 채움률을 재고 합격·불합격을 찍는다.

    ./sync/checkpdf.sh 내문서.dc.html

흐름 문서는 브라우저 인쇄 엔진이 쪽을 나누므로 DOM 을 봐서는 쪽 경계를 알 수
없다. 실제로 PDF 를 뽑아 잉크가 닿은 마지막 줄까지를 재는 수밖에 없다.

합격 기준은 STYLE.md 「합격 기준」과 같다.
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fit import MIN_BODY_PX, MIN_FILL  # noqa: E402

MM = 25.4


def page_fills(pdf, dpi=50):
    """쪽마다 (채움률, 남은 여백 mm). 위아래 여백과 푸터를 뺀 본문 영역 기준."""
    d = tempfile.mkdtemp()
    subprocess.run(["pdftoppm", "-gray", "-r", str(dpi), pdf, os.path.join(d, "p")],
                   check=True)
    out = []
    for f in sorted(x for x in os.listdir(d) if x.endswith(".pgm")):
        raw = open(os.path.join(d, f), "rb").read()
        parts = raw.split(b"\n", 3)
        w, h = map(int, parts[1].split())
        data = parts[3]
        px_mm = h / 297.0                       # A4 세로 297mm
        top, bot = int(20 * px_mm), int(277 * px_mm)
        side = int(15 * px_mm)
        rows = []
        for y in range(top, bot):
            r = data[y * w:(y + 1) * w]
            rows.append((y, sum(1 for v in r[side:w - side] if v < 230)))
        # 아래에서 올라오며 푸터를 한 번 건너뛰고 본문 바닥을 찾는다
        seen_foot, foot_y, last = False, bot, top
        for y, dark in reversed(rows):
            if dark > 2:
                if not seen_foot:
                    seen_foot, foot_y = True, y
                    continue
                if y > foot_y - int(6 * px_mm):
                    continue
                last = y
                break
        avail = (277 - 20 - 6) * px_mm
        used = last - top
        out.append((used / avail * 100, (avail - used) / px_mm))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(args) != 1:
        raise SystemExit(__doc__)
    src = os.path.abspath(args[0])
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf = os.path.join(tempfile.mkdtemp(), "check.pdf")
    subprocess.run([os.path.join(repo, "sync", "topdf.sh"), src, pdf],
                   check=True, capture_output=True)

    fills = page_fills(pdf)
    print(f"\n■ {os.path.basename(src)} — A4 {len(fills)}쪽")
    print(f"  {'쪽':<4}{'채움률':>8}{'남은 여백':>11}")
    for i, (pct, left) in enumerate(fills, 1):
        print(f"  {i:<4}{pct:>7.1f}%{left:>9.0f}mm")
    print(f"  평균 {sum(p for p, _ in fills) / len(fills):.1f}%")

    loose = [i for i, (p, _) in enumerate(fills[:-1], 1) if p < MIN_FILL * 100]
    if loose:
        print(f"\n  ✗ 불합격 — {', '.join(map(str, loose))}쪽이 "
              f"{MIN_FILL*100:.0f}% 미만")
        print("    속성 패널의 본문크기·줄간을 한 눈금 낮춰 다시 본다.")
        print(f"    본문 {MIN_BODY_PX:g}px 아래로 내려가야 한다면 원고가 긴 것이다.")
    else:
        print(f"\n  ✓ 합격 — 마지막 쪽을 뺀 모든 쪽 {MIN_FILL*100:.0f}% 이상")


if __name__ == "__main__":
    main()
