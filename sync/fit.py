#!/usr/bin/env python3
"""쪽을 다시 나눠 채운다.

measure.sh 는 재기만 한다. 이쪽은 실제로 고친다 — .body 안의 블록을 전부 꺼내
한 줄로 세운 뒤, A4 한 쪽이 허용하는 높이까지 눌러 담고 넘칠 때만 다음 쪽으로
넘긴다. 제목에서 쪽을 나누지 않는다. 쪽을 일부러 비우지 않는다.

    ./sync/fit.sh 내문서.dc.html          제자리에서 고친다 (.bak 를 남긴다)
    ./sync/fit.sh --dry 내문서.dc.html    고치지 않고 결과만 보여준다

블록 하나를 반드시 새 쪽에서 시작해야 할 때만 그 블록에 data-break="page" 를
붙인다. 그 밖에는 전부 자동이다.
"""
import html as htmlmod
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
EPS = 0.5          # 반올림 오차 여유(px)
SAFETY = 2.0       # 지면 바닥에 남겨 두는 여유(px). 소수점에서 잘리는 것을 막는다
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "source", "track", "wbr"}
# 뒤 블록과 떼어 놓지 않는다 — 쪽 맨 아래에 제목만 남는 꼴을 막는다
KEEP_WITH_NEXT_TAGS = {"H1", "H2", "H3", "H4"}
KEEP_WITH_NEXT_CLS = ("kicker", "rule86")


# ── HTML 훑기 ────────────────────────────────────────────────────────────
def skip_tag(s, i):
    """i 가 '<' 를 가리킬 때 그 태그(또는 주석)가 끝난 바로 다음 위치를 준다."""
    if s.startswith("<!--", i):
        k = s.find("-->", i)
        return len(s) if k < 0 else k + 3
    j, q = i + 1, None
    while j < len(s):
        c = s[j]
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c == ">":
            return j + 1
        j += 1
    return len(s)


def match_element(s, i, limit):
    """i 가 여는 태그의 '<' 일 때 (이름, 여는태그끝, 안쪽끝, 요소끝)."""
    m = re.match(r"<([a-zA-Z][-a-zA-Z0-9]*)", s[i:])
    if not m:
        raise ValueError("태그가 아니다")
    name = m.group(1).lower()
    open_end = skip_tag(s, i)
    if name in VOID or s[open_end - 2:open_end] == "/>":
        return name, open_end, open_end, open_end

    depth, j = 1, open_end
    while j < limit:
        k = s.find("<", j)
        if k < 0 or k >= limit:
            break
        if s.startswith("<!--", k):
            j = skip_tag(s, k)
            continue
        m2 = re.match(r"</?([a-zA-Z][-a-zA-Z0-9]*)", s[k:])
        if not m2:
            j = k + 1
            continue
        nm = m2.group(1).lower()
        nxt = skip_tag(s, k)
        if nm == name:
            if s[k + 1] == "/":
                depth -= 1
                if depth == 0:
                    return name, open_end, k, nxt
            elif nm not in VOID and s[nxt - 2:nxt] != "/>":
                depth += 1
        j = nxt
    raise ValueError(f"닫는 태그를 못 찾았다: <{name}>")


def top_children(s, lo, hi):
    """[lo,hi) 안의 최상위 요소들. 앞에 붙은 공백·주석은 그 요소에 딸려 간다."""
    out, i, pending = [], lo, lo
    while i < hi:
        k = s.find("<", i)
        if k < 0 or k >= hi:
            break
        if s.startswith("<!--", k) or not re.match(r"<[a-zA-Z]", s[k:k + 2]):
            i = skip_tag(s, k) if s.startswith("<!--", k) else k + 1
            continue
        name, oe, ie, ee = match_element(s, k, hi)
        out.append({"name": name, "html": s[pending:ee], "open": s[k:oe],
                    "inner": s[oe:ie], "inner_start": oe, "inner_end": ie})
        i = pending = ee
    return out, s[pending:hi]


def has_class(open_tag, cls):
    m = re.search(r'class\s*=\s*["\']([^"\']*)["\']', open_tag)
    return bool(m) and cls in m.group(1).split()


# ── 문서 갈라 놓기 ───────────────────────────────────────────────────────
class Doc:
    def __init__(self, path):
        self.path = path
        self.src = open(path, encoding="utf-8").read()
        s = self.src

        i = s.find("<doc-page")
        if i < 0:
            raise SystemExit("<doc-page> 가 없다 — 이 시스템의 문서가 아니다")
        _, dp_open_end, dp_inner_end, dp_end = match_element(s, i, len(s))
        self.head = s[:dp_open_end]
        self.tail = s[dp_inner_end:]

        secs, self.after_secs = top_children(s, dp_open_end, dp_inner_end)
        secs = [x for x in secs if x["name"] == "section" and has_class(x["open"], "page")]
        if not secs:
            raise SystemExit("<section class=\"page\"> 를 못 찾았다")

        self.sec_open = secs[0]["open"]
        self.blocks = []          # 쪽 구분 없이 한 줄로 세운 본문 블록
        self.body_open = None
        self.foot_html = None
        self.sec_indent = re.match(r"\s*", secs[0]["html"]).group(0)

        for sec in secs:
            kids, _ = top_children(s, sec["inner_start"], sec["inner_end"])
            for k in kids:
                if has_class(k["open"], "body"):
                    if self.body_open is None:
                        self.body_open = k["open"]
                        self.body_indent = re.match(r"\s*", k["html"]).group(0)
                    inner, _ = top_children(s, k["inner_start"], k["inner_end"])
                    self.blocks.extend(b["html"] for b in inner)
                elif has_class(k["open"], "foot") and self.foot_html is None:
                    self.foot_html = k["html"]
        if self.body_open is None:
            raise SystemExit('<div class="body"> 를 못 찾았다')
        if self.foot_html is None:
            self.foot_html = '\n  <div class="foot"><span></span><span>1 / 1</span></div>'

    def render(self, pages):
        """쪽별 블록 목록을 받아 문서 전체를 다시 쓴다."""
        n = len(pages)
        parts = []
        for idx, blocks in enumerate(pages, 1):
            foot = re.sub(r"(<span[^>]*>)\s*\d+\s*/\s*\d+\s*(</span>)",
                          lambda m: f"{m.group(1)}{idx} / {n}{m.group(2)}",
                          self.foot_html)
            parts.append(self.sec_indent + self.sec_open
                         + self.body_indent + self.body_open
                         + "".join(blocks)
                         + "\n " + " " * len(self.body_indent.strip("\n")) + "</div>"
                         + foot
                         + "\n</section>")
        return self.head + "\n" + "".join(parts) + self.after_secs + self.tail


# ── 헤드리스 크롬으로 재기 ───────────────────────────────────────────────
class Prober:
    def __init__(self, repo):
        self.repo = repo
        self.work = tempfile.mkdtemp(prefix="fit-")
        # 저장소는 runtime/ 에, 스킬 폴더 사본은 components/ 에 런타임을 둔다.
        for f in ("doc-page.js", "support.js"):
            for d in ("runtime", "components"):
                src = os.path.join(repo, d, f)
                if os.path.exists(src):
                    shutil.copy(src, self.work)
                    break
            else:
                raise SystemExit(f"런타임을 못 찾았다: {f}")
        shutil.copy(os.path.join(repo, "sync", "fit-probe.js"), self.work)

        cache = os.path.join(repo, "sync", ".fontcache")
        self.fonts = []
        for w in (400, 500, 700):
            src = os.path.join(cache, f"NotoSansKR-{w}.ttf")
            if os.path.exists(src):
                shutil.copy(src, self.work)
                self.fonts.append(w)
        if len(self.fonts) != 3:
            raise SystemExit("측정용 글꼴이 없다. 먼저 "
                             + os.path.join(repo, "sync", "fontcache.sh") + " 를 돌려라.")

        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.srv = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(self.port), "--bind", "127.0.0.1"],
            cwd=self.work, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def close(self):
        self.srv.terminate()
        shutil.rmtree(self.work, ignore_errors=True)

    # 화면의 .page 는 width:100% + aspect-ratio 라 시트 폭을 따라간다. 인쇄에서는
    # doc-page.js 가 210×297mm 로 못박으므로, 창 크기에 따라 줄바꿈이 달라져
    # 잰 값과 실제 PDF 가 어긋난다. 측정 동안만 인쇄 크기로 고정한다.
    # ::slotted 기본 규칙은 일부러 약하게 잡혀 있어 문서 쪽 규칙이 이긴다.
    PRINT_GEOM = ('<style>doc-page > section.page{width:210mm!important;'
                  'height:297mm!important;aspect-ratio:auto!important}</style>\n')

    def local_fonts(self):
        return "<style>" + "".join(
            f"@font-face{{font-family:'Noto Sans KR';font-style:normal;"
            f"font-weight:{w};src:url(./NotoSansKR-{w}.ttf) format('truetype');"
            f"font-display:block}}" for w in self.fonts) + "</style>\n"

    def probe(self, html, fs=None, lh=None):
        name = "__fit__.dc.html"
        # 네트워크 웹폰트는 지연 로딩돼 대체 글꼴로 재는 사고가 난다. 끊고
        # 로컬 TTF 를 물린다 — 같은 서체이므로 자폭이 같고, 오프라인에서도
        # 항상 같은 값이 나온다.
        html = re.sub(r'<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>', "", html)
        tag = self.PRINT_GEOM + self.local_fonts()
        if fs is not None:
            # doc-page 의 인라인 style 은 {{ }} 라 로컬에서 무효값이 된다.
            # !important 로 눌러 조판값을 그때그때 바꿔 가며 잰다.
            tag += (f'<style>doc-page{{--body-fs:{fs}px!important;'
                    f'--body-lh:{lh}!important}}</style>\n')
        tag += '<script src="./fit-probe.js"></script>\n'
        html = html.replace("</body>", tag + "</body>", 1) if "</body>" in html else html + tag
        with open(os.path.join(self.work, name), "w", encoding="utf-8") as f:
            f.write(html)
        for _ in range(3):
            dom = subprocess.run(
                [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                 "--window-size=1400,2400", "--force-device-scale-factor=1",
                 "--virtual-time-budget=15000", "--dump-dom",
                 f"http://127.0.0.1:{self.port}/{name}"],
                capture_output=True, text=True).stdout
            m = re.search(r'<pre id="__fit">(.*?)</pre>', dom, re.S)
            if m:
                d = json.loads(htmlmod.unescape(m.group(1)))
                if d.get("ok"):
                    if not d.get("fontOk"):
                        continue          # 글꼴이 안 앉았다 — 대체 글꼴로 재면
                                          # 줄바꿈이 달라져 값이 못 쓰게 된다
                    return d
        raise SystemExit("측정 실패 — 크롬이 지면을 못 그렸다")


# ── 쪽 나누기 ────────────────────────────────────────────────────────────
def keep_with_next(b):
    return b["tag"] in KEEP_WITH_NEXT_TAGS or any(c in b["cls"] for c in KEEP_WITH_NEXT_CLS)


def pack(blocks, avail):
    """한 쪽이 허용하는 높이까지 눌러 담는다. 넘칠 때만 다음 쪽으로 넘긴다."""
    pages, cur, used, prev_mb = [], [], 0.0, 0.0
    n, i = len(blocks), 0
    while i < n:
        b = blocks[i]
        if b["break"] and cur:
            pages.append(cur)
            cur, used, prev_mb = [], 0.0, 0.0
            continue

        # 제목이면 뒤따르는 내용까지 한 덩어리로 보고 자리를 잰다
        need = (b["mt"] if not cur else max(prev_mb, b["mt"])) + b["h"]
        j = i
        while j + 1 < n and keep_with_next(blocks[j]) and not blocks[j + 1]["break"]:
            nb = blocks[j + 1]
            need += max(blocks[j]["mb"], nb["mt"]) + nb["h"]
            j += 1

        if cur and used + need > avail - SAFETY:
            pages.append(cur)
            cur, used, prev_mb = [], 0.0, 0.0
            continue

        used += (b["mt"] if not cur else max(prev_mb, b["mt"])) + b["h"]
        cur.append(b)
        prev_mb = b["mb"]
        i += 1
    if cur:
        pages.append(cur)
    return pages


def verdict(pct, over):
    if over:
        return "★ 넘침"
    if pct >= 92:
        return "적정"
    if pct >= 80:
        return "조금 빈다"
    return "비었다"


def table(title, meas_pages, note=""):
    print(f"\n■ {title} — A4 {len(meas_pages)}쪽{note}")
    print(f"  {'쪽':<4}{'채움률':>8}{'남은 여백':>11}   판정")
    for p in meas_pages:
        over = p["usedPx"] > p["availPx"] + EPS
        left = max(0.0, p["availPx"] - p["usedPx"]) / 3.779527559
        print(f"  {p['page']:<4}{p['fillPct']:>7.1f}%{left:>9.0f}mm   "
              f"{verdict(p['fillPct'], over)}")
    avg = sum(p["fillPct"] for p in meas_pages) / len(meas_pages)
    print(f"  평균 {avg:.1f}%")


# ── 조판값(본문크기·줄간) 탐색 ───────────────────────────────────────────
def _range(html, key, fallback):
    """속성 패널 정의(data-props)에서 min·max·step 을 그대로 읽는다.

    서식마다 허용 범위가 다르고(formal 은 12.0~15.0px), 앞으로 바뀔 수도 있다.
    코드에 베껴 두면 어긋나므로 문서에서 읽는다."""
    m = re.search(key + r"&quot;:\s*\{[^}]*?&quot;min&quot;:\s*([\d.]+)[^}]*?"
                  r"&quot;max&quot;:\s*([\d.]+)[^}]*?&quot;step&quot;:\s*([\d.]+)", html)
    if not m:
        return fallback
    lo, hi, step = (float(x) for x in m.groups())
    if step <= 0 or hi < lo:
        return fallback
    out, v = [], lo
    while v <= hi + 1e-9 and len(out) < 40:
        out.append(round(v, 3))
        v += step
    return out


def grid_for(doc):
    sizes = _range(doc.src, "&quot;bodySize&quot;", [12.5, 13.0, 13.5, 14.0, 14.5, 15.0, 15.5])
    spacings = _range(doc.src, "&quot;lineSpacing&quot;", [1.70, 1.75, 1.80, 1.85, 1.90, 1.95, 2.00])
    return sizes, spacings


def score(pages, blocks_avail):
    """쪽수가 적을수록, 그다음 가장 헐거운 쪽이 덜 헐거울수록 좋다."""
    fills = [p["fill"] for p in pages]
    return (len(pages), -min(fills))


def measure_pack(pr, doc, fs, lh, base):
    """주어진 조판값으로 재고 나눈 결과를 돌려준다."""
    meas = pr.probe(doc.src, None if base else fs, None if base else lh)
    flat = [k for p in meas["pages"] for k in p["kids"]]
    if len(flat) != len(doc.blocks):
        raise SystemExit(f"블록 수가 안 맞는다 — 잰 것 {len(flat)}, 읽은 것 {len(doc.blocks)}")
    avail = min(p["availPx"] for p in meas["pages"])
    for k, raw in zip(flat, doc.blocks):
        k["html"] = raw
        k["break"] = 'data-break="page"' in raw or "data-break='page'" in raw
    packed = pack(flat, avail)
    pages = []
    for i, pg in enumerate(packed, 1):
        used = 0.0
        prev_mb = 0.0
        for j, b in enumerate(pg):
            used += (b["mt"] if j == 0 else max(prev_mb, b["mt"])) + b["h"]
            prev_mb = b["mb"]
        pages.append({"page": i, "availPx": avail, "usedPx": used,
                      "fillPct": round(used / avail * 100, 1),
                      "fill": used / avail,
                      "html": [b["html"] for b in pg]})
    return pages


def sweep(pr, doc, cur_pages, cur):
    """마지막 쪽이 헐겁거나 넘칠 때, 속성 패널 범위 안에서 더 나은 값을 찾는다.

    높이는 본문크기·줄간에 대체로 비례하므로, 필요한 축소비에 가까운 조합부터
    본다. 전 조합(49가지)을 다 재면 느려서 여덟 개만 본다."""
    sizes, spacings = grid_for(doc)
    dfs, dlh = cur
    total = sum(p["fill"] for p in cur_pages)          # 내용 전체가 몇 쪽어치인가
    want = max(1, int(total))                          # 한 쪽 줄여 볼 수 있나
    need = want / total if total else 1.0

    cands = []
    for fs in sizes:
        for lh in spacings:
            if fs == dfs and lh == dlh:
                continue
            est = (fs * lh) / (dfs * dlh)
            cands.append((abs(est - need), abs(fs - dfs) + abs(lh - dlh) * 10, fs, lh))
    cands.sort()

    best = (score(cur_pages, None), dfs, dlh, cur_pages)
    tried = 0
    for _, _, fs, lh in cands:
        if tried >= 8:
            break
        tried += 1
        pages = measure_pack(pr, doc, fs, lh, base=False)
        if any(p["fill"] > 1.0 + EPS / 1000 for p in pages):
            continue
        sc = score(pages, None)
        if sc < best[0]:
            best = (sc, fs, lh, pages)
    return best[1], best[2], best[3]


def apply_typography(html, fs, lh):
    """고른 조판값을 문서에 새긴다 — 로컬 렌더·PDF 와 Claude Design 슬라이더 양쪽.

    네 군데를 함께 고쳐야 한다. @property 의 initial-value 두 개는 속성 패널
    바인딩이 안 붙는 경로(로컬 브라우저·PDF 내보내기)를 맡고, 문서 끝 x-dc
    블록의 data-props 기본값과 renderVals 의 `?? 14` 는 Claude Design 안에서
    {{ bodyFs }} 를 무엇으로 채울지를 정한다. 머리말만 고치면 Claude Design 이
    옛 값으로 되돌려 놓아 쪽 나눔이 어긋난다."""
    out, missed = html, []
    for pat, rep, label in (
        (r"(@property --body-fs \{[^}]*initial-value:)\s*[\d.]+px", rf"\g<1>{fs}px", "@property --body-fs"),
        (r"(@property --body-lh \{[^}]*initial-value:)\s*[\d.]+", rf"\g<1>{lh}", "@property --body-lh"),
        (r"(var\(--body-fs,)\s*[\d.]+px", rf"\g<1>{fs}px", "var(--body-fs) 폴백"),
        (r"(var\(--body-lh,)\s*[\d.]+", rf"\g<1>{lh}", "var(--body-lh) 폴백"),
        (r"(&quot;bodySize&quot;:[^}]*&quot;default&quot;:)\s*[\d.]+", rf"\g<1> {fs}", "속성 패널 bodySize"),
        (r"(&quot;lineSpacing&quot;:[^}]*&quot;default&quot;:)\s*[\d.]+", rf"\g<1> {lh}", "속성 패널 lineSpacing"),
        (r"(this\.props\.bodySize \?\?)\s*[\d.]+", rf"\g<1> {fs}", "renderVals bodySize"),
        (r"(this\.props\.lineSpacing \?\?)\s*[\d.]+", rf"\g<1> {lh}", "renderVals lineSpacing"),
    ):
        new, n = re.subn(pat, rep, out)
        if n == 0:
            missed.append(label)
        out = new
    return out, missed


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry = "--dry" in sys.argv
    no_sweep = "--no-sweep" in sys.argv
    if len(args) != 1:
        raise SystemExit(__doc__)
    path = os.path.abspath(args[0])
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    doc = Doc(path)
    pr = Prober(repo)
    try:
        before = pr.probe(doc.src)
        table(f"{os.path.basename(path)}  ← 지금", before["pages"])

        # 지금 문서에 실제로 박혀 있는 조판값. 눈금의 기본값이 아니라
        # 렌더에서 읽는다 — 한 번 fit 한 문서는 값이 이미 바뀌어 있다.
        dfs, dlh = before["bodyFs"], round(before["bodyLh"], 2)
        fs, lh = dfs, dlh
        pages = measure_pack(pr, doc, fs, lh, base=True)

        # 마지막 쪽이 헐겁거나 어디든 넘치면 조판값을 같이 맞춰 본다
        need_sweep = (not no_sweep and len(pages) > 1
                      and (pages[-1]["fill"] < 0.80
                           or any(p["fill"] > 1.0 for p in pages)))
        if need_sweep:
            print("\n  ⋯ 마지막 쪽이 헐거워 본문크기·줄간을 함께 맞춰 보는 중")
            fs, lh, pages = sweep(pr, doc, pages, (dfs, dlh))

        out = doc.render([p["html"] for p in pages])
        if (fs, lh) != (dfs, dlh):
            # 문서 전체를 손봐야 한다. @property 는 머리말에 있지만 x-dc 의
            # 속성 기본값(data-props · renderVals 의 ?? 14)은 </doc-page> 뒤에
            # 있고, 그쪽이 {{ bodyFs }} 를 되돌려 놓아 조판이 어긋난다.
            out, missed = apply_typography(out, fs, lh)
            if missed:
                print("  ! 조판값을 못 새긴 곳: " + ", ".join(missed))

        after = pr.probe(out)
        note = f"  ·  본문 {fs:g}px / 줄간 {lh:g}"
        table(f"{os.path.basename(path)}  → 재배치", after["pages"], note)

        if before["pageCount"] != after["pageCount"]:
            print(f"\n  쪽수 {before['pageCount']} → {after['pageCount']}")
        if any(p["usedPx"] > p["availPx"] + EPS for p in after["pages"]):
            print("\n  ★ 아직 넘치는 쪽이 있다. 한 블록이 한 쪽보다 크다는 뜻이니 "
                  "표를 쪼개라.")

        if dry:
            print("\n  --dry 라 파일은 그대로 두었다.")
            return
        shutil.copy(path, path + ".bak")
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"\n  고쳤다: {path}\n  원본: {path}.bak")
    finally:
        pr.close()


if __name__ == "__main__":
    main()
