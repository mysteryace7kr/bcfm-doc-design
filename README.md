# bcfm-doc-design

부산공동어시장 재무기획팀 **인쇄문서 디자인 시스템**.
보고서를 A4 인쇄용으로 조판하는 서식 하나.

화면이 아니라 종이를 전제로 한다 — 흰 종이, 검은 잉크, 링크 외 유채색 없음.
개조식 기호(`○ ▶ ※ ⇨`)의 위계를 내어쓰기로 정렬하는 것이 뼈대다.

## 서식

| 파일 | 쓸 때 | 기본 |
|---|---|---|
| `templates/report.dc.html` | 개조식 위계 + 요약밴드 + 번호 섹션 — 보고서·검토·기안·건의서·질의서·업무진행 보고 | 1쪽 |

**서식은 하나다.** 2026-09-10 에 formal(기안)·brief(업무진행) 을 폐기했다. 세 벌을
따로 손보다 보니 하나를 고칠 때마다 나머지 둘이 어긋났다. 기안의 수신처·발신명의·
결재란처럼 서식에 없는 요소는 그 문서에서 만들어 넣는다.
지운 파일은 `notes/backup-26.9.10/` 에 있다(git 에는 올리지 않으며, 이력에도 남아 있다).

**자리표시(`[…]`)만 들어 있는 뼈대다.** 원고를 이 골격에 부어 쓴다.

## 쓰는 법

**Claude Design** — 이것이 실제 작업 경로다. 「인쇄문서」 프로젝트의
`templates/report/` 컴포넌트를 열고, 마크다운 원고를 부어 속성 패널로 조판한다.
화면에 A4 종이가 한 장씩 카드로 뜬다.

**브라우저에서 바로 보기** — `runtime/` 의 두 파일을 템플릿과 같은 폴더에 두고 열면
된다. 글꼴은 맥에 설치된 Pretendard 를 쓰므로 인터넷이 없어도 된다.

## 지면 — `section.page` 한 장이 A4 한 장

**고정 쪽 문서다.** `<section class="page">` 하나가 A4 한 장이다.

```html
<doc-page size="a4" margin="0">
<section class="page">
 <div class="body"> … 본문 … </div>
  <div class="foot"><span>문서명</span><span>1 / 2</span></div>
</section>
<section class="page"> … </section>
</doc-page>
```

- **화면에 쪽 카드가 뜬다.** 쪽 경계를 보면서 편집하고, 푸터에 쪽 번호를 적는다.
- **넘치는 내용은 잘린다.** 다음 쪽으로 흘러가지 않는다 — 대신 잘린 자리가 화면에
  바로 보이므로, 그때 `section.page` 를 하나 늘려 이어 붓는다.
- **여백은 `.page` 의 padding**(19 / 20 / 14mm)이 소유한다. `<doc-page>` 의 `margin` 은
  고정 쪽에서 무효라 `margin="0"` 으로 둔다.
- **푸터는 `.page` 안의 `.foot`.** `slot="footer"` 는 흐름 문서용이라 쓰지 않는다.

### 용지 — `size="a4"` 하나가 전부다

`doc-page.js` 가 고정 쪽 문서에서는 `@page` 에 `size: 210mm 297mm` 를 직접 쓴다
(`doc-page.js:559-565`). `<head>` 에 마지막으로 주입되므로 문서 안의 다른 `@page`
보다 우선한다. **그래서 `@page` 를 직접 쓰지 않는다** — 2026-09-10 까지 있던
`@page { size: A4; }` 는 흐름 문서 시절의 우회였고 지웠다.

**`size="a4"` 를 지우면 Letter 로 떨어진다**(A4보다 18mm 짧다).
실측(2026-09-10, 아무것도 주입하지 않고 그대로 출력): 595×842pt = 210×297mm, 1쪽.

### 재는 법

DOM 으로 쪽 경계를 알 수 있으므로 PDF 를 뽑지 않고 바로 잰다.
기준은 `STYLE.md` 「합격 기준」.

```bash
./sync/fit.sh     내문서.dc.html   # 채움을 맞추고 합격·불합격 판정
./sync/measure.sh 내문서.dc.html   # 쪽별 채움률
./sync/orphan.sh  내문서.dc.html   # 외톨이 줄 (마지막 줄에 한 단어·한 글자)
./sync/topdf.sh   내문서.dc.html   # 확인용 PDF
```

## 조판

| 항목 | 기본 | 범위 |
|---|---|---|
| 본문 | 14px | 12.5 ~ 15.5 |
| 줄간 | 1.85 | 1.70 ~ 2.00 |

여백 19 / 20 / 14mm (상 / 좌우 / 하), 자간 −0.015em, `text-align:justify`.
서체는 **Pretendard 하나** — 제목도 본문도 같은 글꼴이다.

줄바꿈은 `word-break:keep-all` + `text-wrap:pretty` + `hanging-punctuation:allow-end`
세 가지를 함께 걸어 **마지막 줄에 한 단어·한 글자가 외톨이로 남지 않게** 한다.
`sync/orphan.sh` 가 실제 렌더에서 검사한다.

## 고칠 때 지킬 것

이 세 줄은 지우면 조용히 깨진다.

- **`<doc-page>`의 `size="a4"`** — 화면 쪽 카드와 인쇄 용지를 이 한 속성이 정한다
- **`<style>` 맨 위의 `@property --body-fs` / `--body-lh`** — 속성 패널 값이 전달되지
  않는 렌더 경로에서 `--body-fs: px` 같은 무효값이 들어가는데, 이때
  `var(--body-fs, 14px)`의 폴백은 발동하지 않는다(변수가 *없는* 게 아니라 *무효*라서).
  계산 시점에 무효 처리되어 상속값인 **16px / line-height:normal** 로 튄다.
  `@property`의 `initial-value`가 이때 본래 기본값으로 되돌려 준다.
- **`doc-page{ font-family:var(--sans) }`** — `doc-page.js`의
  `:host{font-family:-apple-system…}`이 `html`로부터의 상속을 끊는다. 이 선언이
  없으면 본문이 시스템 폰트로 떨어져 **기기마다 줄바꿈이 달라진다**.

그 밖에:

- **`@page` 를 직접 쓰지 않는다** — `doc-page.js` 가 소유한다
- **쪽 방식(고정 쪽 ↔ 흐름 문서)을 바꾸는 변경은 먼저 사용자에게 묻는다** — 쪽 번호·
  화면 쪽 카드·A4 고정이 한 덩어리로 딸려온다. 2026-09-04·09-07 에 두 번 뒤집혔다
- 푸터를 `slot="footer"` 로 옮기지 않는다 — 흐름 문서와 혼용이 금지돼 있다
- 링크 외 유채색을 넣지 않는다
- `▢`는 쓰지 않는다 — 글리프가 없어 `□`로 폴백된다
- 색·크기를 인라인으로 새로 쓰지 말고 `var(--토큰)`을 쓴다

## 파일

```
templates/   report.dc.html — 이 저장소의 원본
runtime/     doc-page.js · support.js — 지면 런타임 (Claude Design 제공, 수정 금지)
styles.css   토큰 시트 — 서식의 :root 와 같은 값
STYLE.md     색·서체·간격·위계 상세 사양. Claude Design 프로젝트의 readme 도 이 파일이다
docs/
  SKILL.md          Claude Code 스킬 `doc-design` 본문
sync/
  to-skill.sh       원본 → ~/.claude/skills/doc-design/
  build-design.sh   원본 → build/design/ (Claude Design 업로드본)
  check.sh          사본이 어긋났는지 점검
  fit.sh            채움 맞추기 + 합격 판정
  measure.sh        쪽별 채움률 측정 (헤드리스 크롬)
  orphan.sh         외톨이 줄 검사 (헤드리스 크롬 + Range)
  topdf.sh          확인용 PDF (주입 없음)
  fontcache.sh      측정용 글꼴 내려받기
  README.md         동기화 절차
```

글꼴 참조는 빌드에서 치환하지 않는다. 원본이 Claude Design 기준 경로
(`../../fonts/Pretendard-*.ttf`)를 들고 있고 `local('Pretendard')` 가 앞에 있어
맥에서는 설치본이 먼저 쓰인다. 예전에 이 치환을 하던 `sync/fontswap.py` 는 원본과
업로드본이 달라지는 원인이어서 없앴다(2026-09-10).

git 에 올리지 않는 것 (`.gitignore`):

- `build/` — `sync/build-design.sh` 가 만드는 생성물
- `notes/` — 사내 작업메모·백업 사본. 원본은 옵시디언 볼트 `00_수집/` 에 있다

## 원본은 여기 하나다

스킬 폴더도 Claude Design 프로젝트도 **사본**이다. 사본을 직접 고치면 다음
동기화 때 덮어써진다. 고칠 일이 생기면 이 저장소를 고치고 `sync/` 를 돌린다.

```bash
./sync/check.sh          # 지금 뭐가 어긋나 있는지
./sync/to-skill.sh       # 스킬 폴더 갱신
./sync/build-design.sh   # Claude Design 업로드본 생성
```

절차와 주의사항은 [`sync/README.md`](sync/README.md).

## 라이선스

별도 라이선스를 두지 않았다. 저작권은 부산공동어시장 재무기획팀에 있다.
