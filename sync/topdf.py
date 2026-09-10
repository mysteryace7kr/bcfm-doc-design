#!/usr/bin/env python3
"""문서를 PDF 로 뽑는다. 잰 값과 실제 인쇄물을 대조하기 위한 확인용이다.

    ./sync/topdf.sh 내문서.dc.html            옆에 같은 이름 .pdf 를 만든다
    ./sync/topdf.sh 내문서.dc.html 결과.pdf

맥에 설치된 Pretendard 를 물려 렌더하며, 용지는 아무것도 주입하지 않는다 —
고정 쪽(section.page)에서는 doc-page.js 가 @page 에 용지를 직접 쓰므로, 도구가
끼워 넣으면 서식의 결함을 가려 준다. 서식만으로 A4 가 나오는지 함께 보는 셈이다.
고정 시간 대기 방식이라 파일 생성 성공이 폰트·내용 렌더 완료를 뜻하지는 않는다.
쪽수·채움률은 fit.sh·measure.sh 의 DOM 측정이 기준이고, 이 PDF 는 그 값과
실제 인쇄물을 대조하는 확인용이다. 어긋나면 둘 중 하나가 틀린 것이니 그대로 두지 말 것.
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
        # 용지는 주입하지 않는다. 고정 쪽(section.page)에서는 doc-page.js 가
        # @page 에 size: 210mm 297mm 를 직접 쓰므로(doc-page.js:559-565),
        # 주입하면 도구가 서식을 대신 고쳐 주는 셈이 되어 서식의 결함을 숨긴다.
        # 글꼴만 로컬로 물린다 — 측정과 같은 조건을 만들기 위해서다.
        tag = pr.local_fonts()
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
