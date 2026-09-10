#!/usr/bin/env python3
"""흐름 문서를 A4 로 뽑아 쪽별 본문 잉크 도달률을 참고 지표로 출력한다.

    ./sync/checkpdf.sh 내문서.dc.html

흐름 문서는 브라우저 인쇄 엔진이 쪽을 나누므로 DOM 을 봐서는 쪽 경계를 알 수
없다. 실제로 PDF 를 뽑아 잉크가 닿은 마지막 줄까지를 재는 수밖에 없다.

기본 margin=20mm인 흐름 서식 전용이다. 원문 보존·글자 크기·줄 고립·잘림의
종합 품질검사가 아니다. 다른 여백 또는 큰 푸터에는 별도 측정이 필요하다.
"""
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fit import MIN_FILL  # noqa: E402

MM = 25.4


def page_fills(pdf, dpi=50):
    """A4의 y=20..277mm 본문 영역. 기본 푸터는 이미 이 영역 밖에 있다."""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-gray", "-r", str(dpi), pdf, os.path.join(d, "p")],
                       check=True)
        out = []
        files = sorted(Path(d).glob("p-*.pgm"),
                       key=lambda p: int(p.stem.rsplit("-", 1)[1]))
        for file in files:
            raw = file.read_bytes()
            header = re.match(rb"P5\s+(\d+)\s+(\d+)\s+255\s", raw)
            if not header:
                raise ValueError("지원하지 않는 PGM 출력")
            w, h = map(int, header.groups())
            data = raw[header.end():]
            if len(data) != w * h:
                raise ValueError("불완전한 PGM 출력")
            px_mm = h / 297.0
            top, bot = round(20 * px_mm), round(277 * px_mm)
            side = round(20 * w / 210.0)
            last = top
            for y in range(bot - 1, top - 1, -1):
                row = data[y*w+side:(y+1)*w-side]
                if sum(v < 230 for v in row) > 2:
                    last = y + 1
                    break
            avail = bot - top
            used = last - top
            out.append((used / avail * 100, (avail - used) / px_mm))
        if not out:
            raise ValueError("PDF 페이지를 읽지 못했다")
        return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(args) != 1:
        raise SystemExit(__doc__)
    src = os.path.abspath(args[0])
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with tempfile.TemporaryDirectory() as d:
        pdf = os.path.join(d, "check.pdf")
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
        print(f"\n  검토 필요 — {', '.join(map(str, loose))}쪽이 "
              f"{MIN_FILL*100:.0f}% 미만")
        print("    제목·표 행·유지 블록의 이동을 먼저 확인한다. 채움률만으로 글자를 줄이지 않는다.")
    else:
        print("\n  채움률 참고 검사 완료")
    print("  이 값은 종합 합격 판정이 아니다. PDF의 잘림·줄 고립·원문 보존을 별도로 확인한다.")
    if any(p == 0 for p, _ in fills):
        raise SystemExit("본문 잉크가 없는 쪽이 있다 — 빈 출력 또는 의도된 빈 쪽인지 확인한다.")


if __name__ == "__main__":
    main()
