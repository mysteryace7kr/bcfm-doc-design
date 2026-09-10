// Run: NODE_PATH=<playwright packages> node tests/layout.cjs [output-directory]
// Exercises template CSS + the unmodified doc-page runtime, with offline fonts.
// Component bindings are resolved at their defaults for this layout fixture.
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const repo = path.resolve(__dirname, '..');
const out = path.resolve(process.argv[2] || path.join(repo, 'build/layout-test'));
fs.mkdirSync(out, {recursive:true});
const sentence = '부산공동어시장 재무기획팀은 검토 결과와 후속 조치사항을 관계 부서에 전달하고 추진 일정을 확인합니다.';
const body = `<h1>A4 조판 검증</h1><p class="o">○ 동일 원고·동일 글꼴로 수정 전후를 비교합니다.</p>
<h2 id="heading" style="width:230px">검토결과보고서와추진계획 안내</h2>
<p id="plain" style="width:180px">${sentence}</p>
<table id="url-table"><thead><tr><th>구분</th><th>확인자료</th></tr></thead><tbody><tr><th>주소</th><td>https://example.com/${'abcdefghijk'.repeat(12)}</td></tr></tbody></table>
<h2>1. 인용문 분할</h2><p class="o">○ 아래 인용문은 다음 쪽으로 이어질 수 있습니다.</p>
<div class="quote">${Array.from({length:24},(_,i)=>`<p class="o">인용${String(i+1).padStart(2,'0')} ${sentence}</p>`).join('')}</div>
<h2>2. 표 머리행 반복</h2><table><thead><tr><th>표번호</th><th>확인사항</th></tr></thead><tbody>${Array.from({length:28},(_,i)=>`<tr><th>항목${String(i+1).padStart(2,'0')}</th><td>${sentence}</td></tr>`).join('')}</tbody></table>
<h2>3. 마지막 조치</h2><p class="o">○ 원문 끝까지 보존합니다. 문서종료표식</p>
<div slot="footer" class="foot"><span>조판 검증</span><span>부산공동어시장</span></div>`;

(async()=>{
  const browser = await chromium.launch({executablePath:process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1100,height:1400}});
    const source = process.env.BASELINE
      ? execFileSync('git',['show','HEAD:templates/report.dc.html'],{cwd:repo,encoding:'utf8'})
      : fs.readFileSync(path.join(repo,'templates/report.dc.html'),'utf8');
    const css = source.match(/<style>([\s\S]*?)<\/style>/)[1];
    const fonts = [400,500,700].map(w=>`@font-face{font-family:'Noto Sans KR';font-weight:${w};src:url(data:font/ttf;base64,${fs.readFileSync(path.join(repo,`sync/.fontcache/NotoSansKR-${w}.ttf`)).toString('base64')})}`).join('');
    await page.setContent(`<html lang="ko"><head><style>${css}${fonts}</style></head><body><doc-page size="a4" margin="20mm">${body}</doc-page></body></html>`);
    await page.addScriptTag({path:path.join(repo,'runtime/doc-page.js')});
    await page.evaluate(async()=>{await document.fonts.ready; await Promise.all([400,500,700].map(w=>document.fonts.load(`${w} 14px "Noto Sans KR"`,'검토결과')));});
    const metrics = await page.evaluate(()=>{
      const dp=document.querySelector('doc-page'), plain=document.querySelector('#plain');
      const heading=document.querySelector('#heading');
      const word=heading.firstChild, r=document.createRange();r.setStart(word,0);r.setEnd(word,word.textContent.indexOf(" "));
      return {bodyWidth:dp.shadowRoot.querySelector('.body').getBoundingClientRect().width,
        tableWidth:document.querySelector('#url-table').getBoundingClientRect().width,
        headingWordLines:new Set([...r.getClientRects()].map(x=>Math.round(x.y))).size,
        plainWordBreak:getComputedStyle(plain).wordBreak,
        quoteBreak:getComputedStyle(document.querySelector('.quote')).breakInside,
        pageRule:document.getElementById('doc-page-print').textContent,
        text:dp.innerText};
    });
    await page.screenshot({path:path.join(out,'screen.png'),fullPage:true});
    // Isolate pagination from the URL's shrink-to-fit failure.
    await page.locator('#url-table').evaluate(el=>el.remove());
    await page.locator('#plain').evaluate(el=>el.style.width='');
    const expectedText = await page.locator('doc-page').innerText();
    await page.emulateMedia({media:'print'});
    metrics.printWidows = await page.locator('#plain').evaluate(el=>getComputedStyle(el).widows);
    await page.pdf({path:path.join(out,'layout.pdf'),format:'A4',printBackground:true,preferCSSPageSize:true});
    const pdfText=execFileSync('pdftotext',['-layout',path.join(out,'layout.pdf'),'-'],{encoding:'utf8'});
    const pages=pdfText.split('\f').filter(x=>x.trim());
    const failures=[];
    if(metrics.printWidows!=='2') failures.push('일반 문단의 인쇄 widows가 런타임에 덮임');
    const normalize = text=>text.replace(/\s/g,'').replaceAll('조판검증부산공동어시장','').replaceAll('표번호확인사항','');
    if(normalize(pdfText)!==normalize(expectedText)) failures.push('PDF 본문 글자·순서가 원본 DOM과 다름');
    if(metrics.tableWidth>645) failures.push(`긴 주소가 A4 본문을 확장함: ${metrics.tableWidth.toFixed(1)}px`);
    if(metrics.headingWordLines>1) failures.push('한글 제목의 한 단어가 중간에서 나뉨');
    if(metrics.plainWordBreak!=='keep-all') failures.push('일반 문단에 한글 단어 보호가 없음');
    if(!pages[0].includes('인용01')) failures.push('긴 인용 상자가 통째로 이동해 첫 쪽을 비움');
    if(!pdfText.includes('문서종료표식')) failures.push('마지막 본문 누락');
    for(let i=1;i<=28;i++) if(!pdfText.includes(`항목${String(i).padStart(2,'0')}`)) failures.push(`표 행 ${i} 누락`);
    for (const printed of pages) {
      if(/항목\d/.test(printed) && !printed.includes('표번호')) failures.push('표 머리행 반복 누락');
      if((printed.match(/인용\d\d/g)||[]).length===1) failures.push('인용 상자의 한 줄 문단만 쪽 경계에 고립됨');
    }
    // Browser export defaults to Letter; authored A4 must still win.
    await page.pdf({path:path.join(out,'paper-contract.pdf'),format:'Letter',preferCSSPageSize:true});
    const info=execFileSync('pdfinfo',[path.join(out,'paper-contract.pdf')],{encoding:'utf8'});
    const size=info.match(/Page size:\s+([\d.]+) x ([\d.]+)/);
    metrics.paperPoints=size && size.slice(1).map(Number);
    if(!size || Math.abs(+size[1]-595.28)>1 || Math.abs(+size[2]-841.89)>1) failures.push('기본 Letter 출력에서 A4 계약이 적용되지 않음');
    fs.writeFileSync(path.join(out,'metrics.json'),JSON.stringify({...metrics,pages:pages.length,failures},null,2));
    console.log(JSON.stringify({browser:browser.version(),...metrics,text:undefined,pageRule:undefined,pages:pages.length,failures},null,2));
    if(failures.length) process.exitCode=1;
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
