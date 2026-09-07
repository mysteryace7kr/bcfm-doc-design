/* 채움률 측정 프로브. measure.sh 가 템플릿 사본에 끼워 넣는다.
 * 결과를 <pre id="__measure"> 에 JSON 으로 적으면 --dump-dom 이 그대로 뱉는다. */
(function () {
  const MM = 3.779527559; // 1mm @96dpi

  function measure() {
    const dp = document.querySelector('doc-page');
    const pages = [...document.querySelectorAll('doc-page > section.page')];
    if (!dp || !pages.length) return { error: 'section.page 를 못 찾았다' };

    const cs = getComputedStyle(dp);
    const fs = parseFloat(cs.fontSize);
    const lh = parseFloat(cs.lineHeight);

    const out = pages.map((p, i) => {
      const body = p.querySelector('.body');
      if (!body) return { page: i + 1, error: '.body 없음' };
      const br = body.getBoundingClientRect();
      const kids = [...body.children];
      const last = kids[kids.length - 1];
      const used = last ? last.getBoundingClientRect().bottom - br.top : 0;
      return {
        page: i + 1,
        boxPx: +br.height.toFixed(1),
        usedPx: +used.toFixed(1),
        fillPct: +((used / br.height) * 100).toFixed(1),
        leftPx: +(br.height - used).toFixed(1),
        leftMm: +((br.height - used) / MM).toFixed(0),
        usedLines: +(used / lh).toFixed(1),
        overflow: used > br.height + 0.5,
      };
    });

    const box = out[0].boxPx;
    return {
      pageCount: pages.length,
      fontSizePx: fs,
      lineHeightPx: +lh.toFixed(2),
      bodyBoxPx: box,
      linesPerPage: +(box / lh).toFixed(1),
      target95Lines: +((box * 0.95) / lh).toFixed(1),
      pages: out,
    };
  }

  function emit() {
    const pre = document.createElement('pre');
    pre.id = '__measure';
    pre.textContent = JSON.stringify(measure());
    document.body.appendChild(pre);
  }

  /* <x-dc> 컴파일 → doc-page 업그레이드 → 슬롯 배치까지가 비동기라
   * rAF 두 번으로는 이른 경우가 있다. 지면이 실제로 잡힐 때까지 폴링한다. */
  let tries = 0;
  function poll() {
    const ready =
      document.querySelector('doc-page > section.page') &&
      document.querySelector('doc-page > section.page .body');
    if (ready) {
      const box = document
        .querySelector('doc-page > section.page')
        .getBoundingClientRect();
      if (box.height > 0) return requestAnimationFrame(emit);
    }
    if (++tries > 150) return emit(); // 약 5초 — 실패해도 이유를 남긴다
    setTimeout(poll, 33);
  }
  poll();
})();
