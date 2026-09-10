#!/usr/bin/env python3
"""문서를 PDF 로 뽑는다. 잰 값과 실제 인쇄물을 대조하기 위한 확인용이다.

    ./sync/topdf.sh 내문서.dc.html            옆에 같은 이름 .pdf 를 만든다
    ./sync/topdf.sh 내문서.dc.html 결과.pdf

로컬 Noto TTF와 A4를 사용하는 확인용 출력이다. 흐름 문서의 쪽 경계는 PDF에서
확인한다. 이전 고정 쪽 전용 fit.sh의 DOM 측정과 자동으로 같다고 가정하지 않는다.
고정 시간 대기 방식이므로 파일 생성 성공만으로 폰트·내용 렌더 완료를 보장하지 않는다.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fit import CHROME, Prober  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not 1 <= len(args) <= 2:
        raise SystemExit(__doc__)
    src = os.path.abspath(args[0])
    out = os.path.abspath(args[1]) if len(args) == 2 else re.sub(r"\.dc\.html$|\.html$", "", src) + ".pdf"
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    pr = Prober(repo)
    try:
        html = Path(src).read_text(encoding="utf-8")
        html = re.sub(r'<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>', "", html)
        # 새 BCFM 템플릿은 A4를 선언한다. 구버전 문서도 동일 조건으로 확인하도록
        # 출력 도구에서 A4를 지정한다. 여백은 런타임이 소유한다.
        tag = "<style>@page{size:A4}</style>\n" + pr.local_fonts()
        html = html.replace("</body>", tag + "</body>", 1) if "</body>" in html else html + tag
        name = "__pdf__.dc.html"
        with open(os.path.join(pr.work, name), "w", encoding="utf-8") as f:
            f.write(html)
        # 기존 PDF를 성공의 증거로 오인하지 않는다. 실패하면 원래 파일을 보존한다.
        with tempfile.TemporaryDirectory(prefix="pdf-", dir=os.path.dirname(out)) as d:
            candidate = Path(d) / "render.pdf"
            try:
                r = subprocess.run(
                    [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                     "--virtual-time-budget=25000", "--no-pdf-header-footer",
                     f"--print-to-pdf={candidate}", f"http://127.0.0.1:{pr.port}/{name}"],
                    capture_output=True, text=True, timeout=90)
            except (subprocess.TimeoutExpired, OSError) as exc:
                raise SystemExit(f"PDF 렌더 실행 실패: {exc}") from exc
            if r.returncode or not candidate.is_file() or not candidate.read_bytes().startswith(b"%PDF-"):
                raise SystemExit("PDF 를 못 만들었다:\n" + r.stderr[-800:])
            os.replace(candidate, out)
        print(f"  {out}")
    finally:
        pr.close()


if __name__ == "__main__":
    main()
