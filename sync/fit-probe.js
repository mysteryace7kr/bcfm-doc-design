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

    const font = fontCheck();
    return {
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

  /* 글꼴이 실제로 앉았는지 확인한다. 대체 글꼴로 재면 같은 문장이 6% 남짓
   * 좁게 잡혀 줄바꿈이 달라진다 — 잰 값이 인쇄와 어긋나는 원인이다.
   * 같은 문장을 'Noto Sans KR' 과 없는 글꼴로 각각 재서 폭이 같으면 안 앉은 것. */
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
    const a = span("'Noto Sans KR'");
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
      try { return document.fonts.load(w + " 14px 'Noto Sans KR'", txt); }
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
