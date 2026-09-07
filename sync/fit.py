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
import math
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

    def probe(self, html, fs=None, lh=None, splits=None):
        name = "__fit__.dc.html"
        # 네트워크 웹폰트는 지연 로딩돼 대체 글꼴로 재는 사고가 난다. 끊고
        # 로컬 TTF 를 물린다 — 같은 서체이므로 자폭이 같고, 오프라인에서도
        # 항상 같은 값이 나온다.
        html = re.sub(r'<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>', "", html)
        tag = self.PRINT_GEOM + self.local_fonts()
        if splits:
            tag += ("<script>window.__FIT_SPLITS=" + json.dumps(splits, ensure_ascii=False)
                    + ";</script>\n")
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



# ── 블록 쪼개기 ─────────────────────────────────────────────────────────
def _norm(t):
    """글자 비교용 — 공백 차이는 무시한다."""
    return re.sub(r"\s+", "", t or "")


def strip_tags(h):
    return re.sub(r"<[^>]+>", " ", h or "")


def body_text(html):
    """표 머리행을 뺀 본문 글자. 표를 나누면 머리행만 한 번 더 생기므로,
    문서 전체를 대조할 때는 머리행을 양쪽에서 빼고 본다. 머리행 자체는
    쪼갤 때마다 text_kept() 가 따로 확인한다."""
    return _norm(strip_tags(re.sub(r"<thead\b.*?</thead>", "", html, flags=re.S | re.I)))


def text_kept(orig_html, r):
    """나눈 두 조각을 합치면 원래 블록과 글자가 똑같아야 한다.

    표만 예외다 — 이어지는 쪽에도 머리행을 다시 얹으므로 그 글자가 한 번 더
    나온다. 뒷조각이 정확히 머리행으로 시작하는지 확인하고 그만큼만 걷어낸
    다음 대조한다. 걷어낼 자리가 어긋나면 대조에 실패하므로 그냥 통과되지 않는다.
    """
    a, b = _norm(strip_tags(r["a"])), _norm(strip_tags(r["b"]))
    head = _norm(r.get("headText") or "")
    if r.get("kind") == "table" and head:
        if not b.startswith(head):
            return False
        b = b[len(head):]
    return a + b == _norm(strip_tags(orig_html))


def refit(pr, doc, blocks_html, fs, lh, avail, rounds=6, quiet=False):
    """쪽 경계에 걸린 블록을 나눠 남는 자리를 채운다.

    한 쪽 아래에 3~4줄짜리 문단 하나가 안 들어가서 20mm 넘게 비는 일이 잦다.
    문단·표·인용을 쪽 경계에서 나누면 그 자리가 채워진다. 자를 자리는 브라우저가
    실제 줄상자를 재서 정하고(fit-probe.js), 여기서는 부탁과 검산만 한다.

    글자는 한 자도 늘거나 줄지 않는다 — 나눈 두 조각을 합쳐 원래 블록과 대조하고,
    어긋나면 그 쪼개기를 버린다. 표만은 이어지는 쪽에 머리행을 다시 얹으므로
    그만큼을 감안한다.
    """
    line = fs * lh
    MIN_GAP = line * 2.2          # 두 줄은 들어가야 나눌 값어치가 있다
    made = bad = 0
    refused = set()               # 브라우저가 못 자른다고 한 블록 (내용으로 기억)
    pair_of = {}                  # (앞조각, 뒷조각) → 나누기 전 원래 블록
    pending = None

    for _ in range(rounds):
        meas = pr.probe(doc.render([blocks_html]), fs, lh, pending)
        flat = [k for pg in meas["pages"] for k in pg["kids"]]
        if len(flat) != len(blocks_html):
            raise SystemExit(f"블록 수가 안 맞는다 — 잰 것 {len(flat)}, 읽은 것 {len(blocks_html)}")

        # 지난 회차에 부탁한 결과를 받는다. 번호는 지금 목록 기준이므로,
        # 목록을 건드리기 전에 먼저 내용으로 바꿔 기억해 둔다.
        results = meas.get("splits") or []
        for r in results:
            if not r.get("ok") and 0 <= r["index"] < len(blocks_html):
                refused.add(blocks_html[r["index"]])

        applied = False
        for r in sorted([x for x in results if x.get("ok")], key=lambda x: -x["index"]):
            i = r["index"]
            if not (0 <= i < len(blocks_html)):
                continue
            if not text_kept(blocks_html[i], r):
                refused.add(blocks_html[i])       # 다시 묻지 않는다
                bad += 1
                continue
            lead = re.match(r"\s*", blocks_html[i]).group(0)
            a_html, b_html = lead + r["a"], lead + r["b"]
            pair_of[(a_html, b_html)] = blocks_html[i]
            blocks_html[i:i + 1] = [a_html, b_html]
            made += 1
            applied = True
        if applied:
            pending = None
            continue                              # 반영했으니 다시 재고 다시 본다

        for k, raw in zip(flat, blocks_html):
            k["html"] = raw
            k["break"] = 'data-break="page"' in raw or "data-break='page'" in raw
        packed = pack(flat, avail)

        # 쪽 아래가 비었는데 다음 블록이 그보다 크면 나눠 달라고 부탁한다
        req = []
        idx = 0
        for pg in packed:
            idx += len(pg)
            if idx >= len(flat):
                break
            used, prev = 0.0, 0.0
            for j, b in enumerate(pg):
                used += (b["mt"] if j == 0 else max(prev, b["mt"])) + b["h"]
                prev = b["mb"]
            # 안 들어간 것이 제목이면 제목을 자를 게 아니다. 제목은 뒤 블록과
            # 붙어 다니므로, 그 덩어리에서 실제로 자를 수 있는 첫 블록을 찾는다.
            j, consumed, mb = idx, 0.0, prev
            while j < len(flat) and keep_with_next(flat[j]):
                consumed += max(mb, flat[j]["mt"]) + flat[j]["h"]
                mb = flat[j]["mb"]
                j += 1
            if j >= len(flat):
                continue
            tgt = flat[j]
            gap = avail - used - consumed - max(mb, tgt["mt"]) - SAFETY
            if (gap >= MIN_GAP and tgt["h"] > gap and not tgt["break"]
                    and blocks_html[j] not in refused):
                req.append({"index": j, "maxPx": round(gap, 1)})
        if not req:
            break
        pending = req

    # 나눠 놓고 보니 두 조각이 같은 쪽에 앉은 것은 되돌린다. 쪽 경계를 못 바꿨으니
    # 나눌 이유가 없고, 한 문단이 둘로 쪼개진 채 남으면 나중에 손보기만 나빠진다.
    for _ in range(3):
        meas = pr.probe(doc.render([blocks_html]), fs, lh)
        flat = [k for pg in meas["pages"] for k in pg["kids"]]
        for k, raw in zip(flat, blocks_html):
            k["html"] = raw
            k["break"] = 'data-break="page"' in raw or "data-break='page'" in raw
        page_of, i = {}, 0
        for pno, pg in enumerate(pack(flat, avail)):
            for _b in pg:
                page_of[i] = pno
                i += 1
        undone = False
        for i in range(len(blocks_html) - 2, -1, -1):
            key = (blocks_html[i], blocks_html[i + 1])
            if key in pair_of and page_of.get(i) == page_of.get(i + 1):
                refused.add(pair_of[key])          # 다시 나누러 오지 않는다
                blocks_html[i:i + 2] = [pair_of[key]]
                made -= 1
                undone = True
        if not undone:
            break

    if made and not quiet:
        note = f"  ⋯ 쪽 경계에 걸린 블록 {made}개를 나눠 남는 자리를 채웠다"
        if bad:
            note += f" (검산에서 {bad}개는 버렸다)"
        print(note)
    return blocks_html, made


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


def score(pages, fs, lh):
    """좋은 조판의 차례 — 쪽수가 적을수록, 그다음 글자가 클수록, 그다음 덜 헐거울수록.

    본문크기를 채움률보다 앞에 둔다. 인쇄해서 사람이 읽는 문서라 2%p 더 채우자고
    본문을 12.5px 로 줄이는 것은 남는 장사가 아니다.

    줄 피치(크기×줄간)가 아니라 **크기 자체**로 견준다. 12.5px/1.95 와
    13.5px/1.80 은 피치가 같지만 읽기는 전혀 다르다 — 글자가 큰 쪽이 낫다.
    """
    # 마지막 쪽은 남는 내용만큼만 차는 꼬리라 판정에서 뺀다. 넣으면 꼬리가
    # 헐겁다는 이유로 본문을 쓸데없이 줄이는 쪽을 고르게 된다.
    fills = [p["fill"] for p in pages]
    body = fills[:-1] or fills
    return (len(pages), -fs, -lh, -min(body))


def measure_pack(pr, doc, fs, lh, base, blocks=None):
    """주어진 조판값으로 재고 나눈 결과를 돌려준다."""
    bl = doc.blocks if blocks is None else blocks
    src = doc.src if blocks is None else doc.render([bl])
    meas = pr.probe(src, None if base else fs, None if base else lh)
    flat = [k for p in meas["pages"] for k in p["kids"]]
    if len(flat) != len(bl):
        raise SystemExit(f"블록 수가 안 맞는다 — 잰 것 {len(flat)}, 읽은 것 {len(bl)}")
    avail = min(p["availPx"] for p in meas["pages"])
    for k, raw in zip(flat, bl):
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


def sweep(pr, doc, cur_pages, cur, blocks, avail, no_split):
    """속성 패널 범위 안에서 더 나은 본문크기·줄간을 찾는다.

    한 쪽 줄이는 것이 첫째 목표다. 높이는 본문크기·줄간에 대체로 비례하므로
    필요한 축소비를 어림한 뒤, **그 안에 드는 것 중 가장 큰 글자부터** 재본다.
    전 조합(49가지)을 다 재면 느려서 여섯 개만 본다.
    """
    sizes, spacings = grid_for(doc)
    dfs, dlh = cur
    total = sum(p["fill"] for p in cur_pages)      # 내용 전체가 몇 쪽어치인가
    want = max(1, int(total)) if total > int(total) else max(1, int(total))
    need = want / total if total else 1.0

    base = dfs * dlh
    cands = []
    for fs in sizes:
        for lh in spacings:
            if (fs, lh) == (dfs, dlh):
                continue
            est = (fs * lh) / base
            if est > need * 1.04:                  # 지금보다 쪽이 늘 만한 것은 뺀다
                continue
            # 이 조판이면 내용이 몇 쪽어치가 되는지 어림. 먼저 쪽수로 묶고,
            # 같은 쪽수 안에서 큰 글자부터 본다. 큰 글자만 훑으면 쪽이 줄어드는
            # 조합을 영영 못 만나고, 작은 것만 훑으면 쓸데없이 작아진다.
            pred = math.ceil(total * est - 1e-9)
            cands.append((pred, -fs, -lh, fs, lh))
    cands.sort()

    best = (score(cur_pages, dfs, dlh), dfs, dlh, cur_pages, blocks)
    for n, (_pred, _a, _b, fs, lh) in enumerate(cands):
        if n >= 8:
            break
        # 조판값이 바뀌면 줄바꿈이 달라져 자를 자리도 달라진다. 지금 조판에서 만든
        # 쪼개기를 물려받으면 안 되므로, 후보마다 나누지 않은 원본에서 다시 시작한다.
        bl = list(doc.blocks)
        if not no_split:
            bl, _n = refit(pr, doc, bl, fs, lh, avail, rounds=4, quiet=True)
        pages = measure_pack(pr, doc, fs, lh, base=False, blocks=bl)
        if any(p["fill"] > 1.0 for p in pages):
            continue
        sc = score(pages, fs, lh)
        if sc < best[0]:
            best = (sc, fs, lh, pages, bl)
    return best[1], best[2], best[3], best[4]


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
    no_split = "--no-split" in sys.argv
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
        avail = min(p["availPx"] for p in before["pages"])

        # 1) 쪽 경계에 걸린 블록을 나눈다. 쪽 아래에 3~4줄짜리 문단 하나가
        #    안 들어가서 20mm 넘게 비는 것이 가장 흔한 낭비다.
        blocks = list(doc.blocks)
        if not no_split:
            blocks, _n = refit(pr, doc, blocks, fs, lh, avail)
        pages = measure_pack(pr, doc, fs, lh, base=no_split and True or False,
                             blocks=None if no_split else blocks)

        # 2) 그래도 마지막 쪽이 헐겁거나 어디든 넘치면 조판값까지 맞춰 본다
        need_sweep = (not no_sweep and len(pages) > 1
                      and (pages[-1]["fill"] < 0.80
                           or any(p["fill"] > 1.0 for p in pages)))
        if need_sweep:
            print("\n  ⋯ 마지막 쪽이 헐거워 본문크기·줄간을 함께 맞춰 보는 중")
            fs, lh, pages, blocks = sweep(pr, doc, pages, (dfs, dlh),
                                          blocks, avail, no_split)

        out = doc.render([p["html"] for p in pages])
        if (fs, lh) != (dfs, dlh):
            # 문서 전체를 손봐야 한다. @property 는 머리말에 있지만 x-dc 의
            # 속성 기본값(data-props · renderVals 의 ?? 14)은 </doc-page> 뒤에
            # 있고, 그쪽이 {{ bodyFs }} 를 되돌려 놓아 조판이 어긋난다.
            out, missed = apply_typography(out, fs, lh)
            if missed:
                print("  ! 조판값을 못 새긴 곳: " + ", ".join(missed))

        # 글자가 새지 않았는지 문서 전체로 한 번 더 검산한다
        if body_text("".join(doc.blocks)) != \
           body_text("".join(b for pg in pages for b in pg["html"])):
            raise SystemExit("본문 글자가 달라졌다 — 쪼개기가 잘못됐다. 파일은 건드리지 않았다.")

        after = pr.probe(out)
        note = f"  ·  본문 {fs:g}px / 줄간 {lh:g}"
        table(f"{os.path.basename(path)}  → 재배치", after["pages"], note)

        if before["pageCount"] != after["pageCount"]:
            print(f"\n  쪽수 {before['pageCount']} → {after['pageCount']}")
        if any(p["usedPx"] > p["availPx"] + EPS for p in after["pages"]):
            print("\n  ★ 아직 넘치는 쪽이 있다. 한 블록이 한 쪽보다 크다는 뜻이다.")

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
