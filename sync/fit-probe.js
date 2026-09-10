/* 재배치용 측정 프로브. fit.py 가 사본에 끼워 넣는다.
 * measure-probe.js 는 쪽 단위 채움률만 재지만, 이쪽은 .body 안 블록 하나하나의
 * 높이와 위아래 마진을 재서 fit.py 가 쪽을 다시 나눌 수 있게 한다.
 * 결과를 <pre id="__fit"> 에 JSON 으로 적으면 --dump-dom 이 그대로 뱉는다. */
(function () {
  function measure() {
    const dp = document.querySelector('doc-page');
    const pages = [...document.querySelectorAll('doc-page > section.page')];
    if (!dp || !pages.length) return { error: 'section.page 를 못 찾았다' };

    const dcs = getComputedStyle(dp);
    const curFs = parseFloat(dcs.fontSize);
    const curLh = parseFloat(dcs.lineHeight) / curFs;

    const out = pages.map((p, i) => {
      const body = p.querySelector('.body');
      const foot = p.querySelector('.foot');
      if (!body) return { page: i + 1, error: '.body 없음' };

      const pr = p.getBoundingClientRect();
      const pcs = getComputedStyle(p);
      const contentTop = pr.top + parseFloat(pcs.paddingTop);
      const contentBottom = pr.bottom - parseFloat(pcs.paddingBottom);
      const footH = foot ? foot.getBoundingClientRect().height : 0;
      /* .body 가 실제로 쓸 수 있는 세로 공간. .foot 은 margin 이 없다. */
      const avail = contentBottom - contentTop - footH;

      const kids = [...body.children].map((el, j) => {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        return {
          i: j,
          tag: el.tagName,
          cls: el.className || '',
          h: +r.height.toFixed(2),                    // border-box 높이 (마진 제외)
          mt: +parseFloat(cs.marginTop).toFixed(2),
          mb: +parseFloat(cs.marginBottom).toFixed(2),
        };
      });

      const last = body.children[body.children.length - 1];
      const used = last ? last.getBoundingClientRect().bottom - contentTop : 0;

      return {
        page: i + 1,
        widthPx: +pr.width.toFixed(2),
        availPx: +avail.toFixed(2),
        usedPx: +used.toFixed(2),
        fillPct: +((used / avail) * 100).toFixed(1),
        kids,
      };
    });

    /* 쪼개기 요청은 쪽 구분 없이 이어 센 번호로 온다 — fit.py 쪽 목록과 같은 순서다. */
    const allKids = [];
    for (const p of pages) {
      const body = p.querySelector('.body');
      if (body) allKids.push(...body.children);
    }
    const font = fontCheck();
    return {
      splits: splitAll(allKids, parseFloat(dcs.lineHeight)),
      ok: true,
      pageCount: pages.length,
      bodyFs: +curFs.toFixed(2),
      bodyLh: +curLh.toFixed(3),
      fontOk: font.ok,
      fontSample: font.sample,
      fontFallback: font.fallback,
      pages: out,
    };
  }

  function emit() {
    const pre = document.createElement('pre');
    pre.id = '__fit';
    pre.textContent = JSON.stringify(measure());
    document.body.appendChild(pre);
  }


  /* ── 블록 쪼개기 ────────────────────────────────────────────────────
   * fit.py 가 window.__FIT_SPLITS 에 {index, maxPx} 를 넣어 두면, 그 블록을
   * maxPx 높이에서 둘로 나눈 HTML 을 돌려준다. 줄 위치는 브라우저만 아는
   * 것이라 여기서 나눈다 — Range 로 실제 줄상자를 재서 자를 자리를 찾는다.
   * 글자는 한 자도 더하거나 빼지 않는다(fit.py 가 대조해 확인한다). */

  function textNodes(el) {
    const out = [];
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) out.push(n);
    return out;
  }

  function posAt(nodes, off) {
    for (const n of nodes) {
      if (off <= n.length) return [n, off];
      off -= n.length;
    }
    const last = nodes[nodes.length - 1];
    return [last, last.length];
  }

  /* 요소 처음부터 off 번째 글자까지 그렸을 때의 아래쪽 좌표 */
  function bottomAt(el, nodes, off) {
    const r = document.createRange();
    r.setStart(el, 0);
    const [n, o] = posAt(nodes, off);
    r.setEnd(n, o);
    const box = r.getBoundingClientRect();
    return box.height ? box.bottom : el.getBoundingClientRect().top;
  }

  function cloneWith(el, frag, which) {
    const c = el.cloneNode(false);
    c.appendChild(frag);
    /* 내어쓰기(○·▶·※·가.)는 첫 줄에만 걸리는 것이라, 이어지는 쪽에서는
     * 기호 자리만큼 텅 비어 보인다. 뒷조각은 내어쓰기를 없앤다. */
    if (which === 'b') c.style.textIndent = '0';
    /* 인용 상자가 둘로 갈리면 테두리가 네 줄이 되어 다른 인용처럼 보인다.
     * 맞닿는 쪽 테두리를 없애 한 상자가 이어지는 것으로 읽히게 한다. */
    if (el.classList && el.classList.contains('quote')) {
      if (which === 'a') c.style.borderBottom = '0';
      else c.style.borderTop = '0';
    }
    return c;
  }

  function splitText(el, maxPx, lh) {
    const nodes = textNodes(el);
    if (!nodes.length) return fail('글자 없음');
    const total = nodes.reduce((a, n) => a + n.length, 0);
    if (total < 40) return fail('너무 짧다(' + total + '자)');

    const top = el.getBoundingClientRect().top;
    const limit = top + maxPx;
    if (bottomAt(el, nodes, total) <= limit) return fail('통째로 들어간다');

    /* limit 안에 들어가는 가장 큰 글자수를 이분탐색 */
    let lo = 0, hi = total;
    while (lo < hi) {
      const mid = Math.ceil((lo + hi) / 2);
      if (bottomAt(el, nodes, mid) <= limit) lo = mid; else hi = mid - 1;
    }
    if (lo <= 0) return fail('첫 줄도 안 들어간다');

    /* 낱말 가운데를 자르지 않도록 바로 앞 공백까지 물러난다 */
    const all = nodes.map(n => n.data).join('');
    let cut = lo;
    while (cut > 0 && !/\s/.test(all[cut - 1])) cut--;
    while (cut > 0 && /\s/.test(all[cut - 1])) cut--;
    if (cut <= 0) return fail('낱말 경계가 없다');

    /* 앞뒤 각각 두 줄은 남긴다 (STYLE.md 의 orphans/widows 2와 같은 취지) */
    const hA = bottomAt(el, nodes, cut) - top;
    const hAll = bottomAt(el, nodes, total) - top;
    if (hA < lh * 1.8 || hAll - hA < lh * 1.8)
      return fail('앞 ' + (hA / lh).toFixed(1) + '줄 / 뒤 ' + ((hAll - hA) / lh).toFixed(1)
                  + '줄 — 두 줄씩은 남아야 한다');

    const [n1, o1] = posAt(nodes, cut);
    const ra = document.createRange();
    ra.setStart(el, 0); ra.setEnd(n1, o1);
    const rb = document.createRange();
    rb.setStart(n1, o1); rb.setEnd(el, el.childNodes.length);

    const a = cloneWith(el, ra.cloneContents(), 'a');
    const b = cloneWith(el, rb.cloneContents(), 'b');
    return [a.outerHTML, b.outerHTML];
  }

  /* 못 자른 까닭을 남긴다 — 조용히 실패하면 왜 여백이 남는지 알 수 없다. */
  let FAILWHY = null;
  function fail(why) { FAILWHY = why; return null; }

  function splitTable(el, maxPx) {
    const head = el.querySelector('thead');
    const body = el.querySelector('tbody');
    if (!body) return null;
    const rows = [...body.rows];
    if (rows.length < 2) return null;

    const top = el.getBoundingClientRect().top;
    const limit = top + maxPx;
    let k = 0;
    for (let i = 0; i < rows.length; i++) {
      if (rows[i].getBoundingClientRect().bottom <= limit) k = i + 1; else break;
    }
    if (k < 1 || k >= rows.length) return null;

    const a = el.cloneNode(true);
    const b = el.cloneNode(true);
    const ab = a.querySelector('tbody'), bb = b.querySelector('tbody');
    for (let i = rows.length - 1; i >= k; i--) ab.deleteRow(i);
    for (let i = k - 1; i >= 0; i--) bb.deleteRow(i);
    /* 이어지는 쪽에도 머리행을 다시 얹는다 — 무슨 칸인지 모르게 되면 안 된다 */
    if (head && !b.querySelector('thead')) b.insertBefore(head.cloneNode(true), bb);
    return [a.outerHTML, b.outerHTML];
  }

  /* 쪼개지 않는 것 — 제목·요약밴드·짧은 마무리 줄 */
  const NO_SPLIT_TAGS = ['H1', 'H2', 'H3', 'H4'];
  const NO_SPLIT_CLS = ['kicker', 'rule86', 'band', 'r', 'n'];

  function splitAll(kids, lh) {
    const req = window.__FIT_SPLITS || [];
    const out = [];
    for (const r of req) {
      const el = kids[r.index];
      if (!el) { out.push({ index: r.index, ok: false, why: '블록 없음' }); continue; }
      const cls = (el.className || '').split(/\s+/);
      if (NO_SPLIT_TAGS.includes(el.tagName) || NO_SPLIT_CLS.some(c => cls.includes(c))) {
        out.push({ index: r.index, ok: false, why: '쪼개지 않는 종류' });
        continue;
      }
      let res = null, err = null;
      FAILWHY = null;
      try {
        res = el.tagName === 'TABLE' ? splitTable(el, r.maxPx) : splitText(el, r.maxPx, lh);
      } catch (e) { err = String(e && e.message || e); }
      if (!res) {
        out.push({ index: r.index, ok: false, why: err || FAILWHY || '자를 자리 없음' });
        continue;
      }
      /* 표는 이어지는 쪽에도 머리행을 다시 얹으므로 글자가 그만큼 늘어난다.
       * fit.py 가 검산할 때 빼고 볼 수 있도록 그 글자를 함께 보낸다. */
      const head = el.tagName === 'TABLE' ? el.querySelector('thead') : null;
      out.push({
        index: r.index, ok: true, a: res[0], b: res[1],
        kind: el.tagName === 'TABLE' ? 'table' : 'text',
        headText: head ? head.textContent : '',
      });
    }
    return out;
  }

  /* 글꼴이 실제로 앉았는지 확인한다. 대체 글꼴로 재면 같은 문장이 6% 남짓
   * 좁게 잡혀 줄바꿈이 달라진다 — 잰 값이 인쇄와 어긋나는 원인이다.
   * 같은 문장을 'Pretendard' 와 없는 글꼴로 각각 재서 폭이 같으면 안 앉은 것. */
  const SAMPLE = '부산공동어시장 재무기획팀 인쇄문서 디자인 시스템';

  function span(family) {
    const el = document.createElement('span');
    el.textContent = SAMPLE;
    el.style.cssText = "position:absolute;left:-9999px;top:0;white-space:nowrap;" +
                       "letter-spacing:-0.015em;font-size:14px;font-family:" + family;
    document.body.appendChild(el);
    return el;
  }

  function fontCheck() {
    const a = span("'Pretendard'");
    const b = span("'__no_such_font__'");
    const wa = a.getBoundingClientRect().width;
    const wb = b.getBoundingClientRect().width;
    a.remove();
    b.remove();
    return { sample: +wa.toFixed(2), fallback: +wb.toFixed(2), ok: Math.abs(wa - wb) > 0.5 };
  }

  /* document.fonts.ready 는 지연 로딩되는 굵기보다 먼저 풀린다.
   * 쓰는 굵기를 하나씩 명시적으로 불러 놓고 기다린다. */
  function fontsSettled() {
    if (!document.fonts) return Promise.resolve();
    const txt = '부산공동어시장 재무기획팀 가나다라 0123';
    const jobs = [400, 500, 700].map(function (w) {
      try { return document.fonts.load(w + " 14px 'Pretendard'", txt); }
      catch (e) { return Promise.resolve(); }
    });
    /* 어느 한 약속이라도 안 풀리면 영영 안 재게 되므로 시간을 걸어 둔다. */
    const cap = new Promise(function (r) { setTimeout(r, 6000); });
    const all = Promise.all(jobs).then(function () { return document.fonts.ready; },
                                       function () { return document.fonts.ready; });
    return Promise.race([all, cap]);
  }

  /* <x-dc> 컴파일 → doc-page 업그레이드 → 슬롯 배치까지가 비동기다.
   * 지면이 실제로 잡히고 글꼴이 앉을 때까지 기다린다. */
  let tries = 0;
  function poll() {
    const pg = document.querySelector('doc-page > section.page');
    if (pg && pg.querySelector('.body') && pg.getBoundingClientRect().height > 0) {
      return fontsSettled().then(emit, emit);
    }
    if (++tries > 150) return emit(); // 약 5초 — 실패해도 이유를 남긴다
    setTimeout(poll, 33);
  }
  poll();
})();
