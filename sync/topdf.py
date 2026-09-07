#!/usr/bin/env python3
"""문서를 PDF 로 뽑는다. 잰 값과 실제 인쇄물을 대조하기 위한 확인용이다.

    ./sync/topdf.sh 내문서.dc.html            옆에 같은 이름 .pdf 를 만든다
    ./sync/topdf.sh 내문서.dc.html 결과.pdf

fit.sh 와 같은 조건(로컬 Noto TTF · 210×297mm)에서 렌더하므로, 나온 PDF 의
쪽수와 잘림 여부가 fit.sh 가 보고한 것과 일치해야 한다. 어긋나면 둘 중 하나가
틀린 것이니 그대로 두지 말 것.
"""
import os
import re
import subprocess
import sys

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
        html = open(src, encoding="utf-8").read()
        html = re.sub(r'<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>', "", html)
        # 흐름 문서는 용지를 못 박지 않는다 — 인쇄 대화상자의 용지를 따른다.
        # 헤드리스 크롬은 기본이 Letter(A4보다 18mm 짧다)라 그대로 뽑으면
        # 쪽수가 실제와 달라진다. 확인용 PDF 는 A4 로 고정해 뽑는다.
        tag = "<style>@page{size:A4}</style>\n" + pr.local_fonts()
        html = html.replace("</body>", tag + "</body>", 1) if "</body>" in html else html + tag
        name = "__pdf__.dc.html"
        with open(os.path.join(pr.work, name), "w", encoding="utf-8") as f:
            f.write(html)
        r = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=25000", "--no-pdf-header-footer",
             f"--print-to-pdf={out}", f"http://127.0.0.1:{pr.port}/{name}"],
            capture_output=True, text=True)
        if not os.path.exists(out):
            raise SystemExit("PDF 를 못 만들었다:\n" + r.stderr[-800:])
        print(f"  {out}")
    finally:
        pr.close()


if __name__ == "__main__":
    main()
