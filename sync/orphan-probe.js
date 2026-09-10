/* 외톨이 줄 측정 프로브. orphan.sh 가 템플릿 사본에 끼워 넣는다.
 * 문단마다 실제 렌더된 줄을 세고, 마지막 줄에 남은 글자를 적는다.
 * 결과를 <pre id="__orphan"> 에 JSON 으로 적으면 --dump-dom 이 그대로 뱉는다. */
(function () {
  const SEL = '.o,.k,.t,.n,.r,.lead,.quote,td,th,h1,h2,h3';

  /* 한 요소의 텍스트를 Range 로 한 글자씩 훑어 줄로 묶는다.
   * 줄이 바뀌는 지점은 글자 사각형의 top 이 바뀌는 곳이다. */
  function lines(el) {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const rows = [];
    let node;
    while ((node = walker.nextNode())) {
      const t = node.nodeValue;
      for (let i = 0; i < t.length; i++) {
        if (t[i] === '\n') continue;
        const r = document.createRange();
        r.setStart(node, i); r.setEnd(node, i + 1);
        const box = r.getBoundingClientRect();
        if (!box.height) continue;
        const top = Math.round(box.top * 4) / 4;
        const row = rows.length && Math.abs(rows[rows.length - 1].top - top) < 2
          ? rows[rows.length - 1] : (rows.push({ top, text: '' }), rows[rows.length - 1]);
        row.text += t[i];
      }
    }
    return rows;
  }

  function run() {
    const out = [];
    document.querySelectorAll(SEL).forEach((el) => {
      const rows = lines(el);
      if (rows.length < 2) return;               // 한 줄짜리는 외톨이가 생길 수 없다
      const last = rows[rows.length - 1].text.trim();
      const words = last.split(/\s+/).filter(Boolean);
      out.push({
        cls: el.className || el.tagName.toLowerCase(),
        lines: rows.length,
        lastChars: last.replace(/\s/g, '').length,
        lastWords: words.length,
        last: last.slice(0, 30),
        head: (el.textContent || '').trim().slice(0, 22),
      });
    });
    const pre = document.createElement('pre');
    pre.id = '__orphan';
    pre.textContent = JSON.stringify(out);
    document.body.appendChild(pre);
  }

  const go = () => (document.fonts ? document.fonts.ready.then(run) : run());
  if (document.readyState === 'complete') setTimeout(go, 400);
  else window.addEventListener('load', () => setTimeout(go, 400));
})();
