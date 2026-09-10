# bcfm-doc-design

부산공동어시장 재무기획팀 **인쇄문서 디자인 시스템**.
보고서·기안(공문)·업무진행 보고를 A4 인쇄용으로 조판하는 서식 3종.

화면이 아니라 종이를 전제로 한다 — 흰 종이, 검은 잉크, 링크 외 유채색 없음.
개조식 기호(`○ ▶ ※ ⇨`)의 위계를 내어쓰기로 정렬하는 것이 뼈대다.

## 서식

| 파일 | 쓸 때 | 기본 |
|---|---|---|
| `templates/report.dc.html` | 여러 쪽, 개조식 위계 + 요약밴드 + 번호 섹션 — 보고서·검토 | 1쪽 |
| `templates/formal.dc.html` | 수신처·발신명의가 필요한 문서 — 기안(공문)·건의서·질의서. 결재란 포함 | 1쪽 |
| `templates/brief.dc.html` | 1~2쪽, 타임라인·항목 나열 — 업무진행사항·요약보고 | 1쪽 |

애매하면 `report`.

**세 서식 모두 자리표시(`[…]`)만 들어 있는 뼈대다.** 원고를 이 골격에 부어 쓴다.

## 쓰는 법

**브라우저에서 바로 보기** — `templates/report.dc.html`을 열면 된다.
폰트를 Google Fonts에서 불러오므로 인터넷만 되면 따로 준비할 게 없다.
(`runtime/`의 두 파일은 같은 폴더에 있어야 하므로, 로컬 미리보기 시에는
템플릿을 `runtime/` 옆에 두거나 경로를 맞춰야 한다.)

**Claude Design에 등록** — `templates/`의 `.dc.html` 3개를 올린다.
`runtime/`은 로컬 미리보기용이라 등록에는 필요 없다.

## 지면 — 이 시스템의 핵심

**흐름 문서다.** `<doc-page>` 안에 원고를 그냥 이어서 부으면, 인쇄·PDF 내보내기
때 브라우저 인쇄 엔진이 쪽을 나눈다. 사람도 도구도 쪽을 계산하지 않는다.

```html
<doc-page size="a4" margin="20mm">
  … 원고를 그대로 이어서 …
  <div slot="footer" class="foot"><span>문서명</span><span>기관명</span></div>
</doc-page>
```

- **`<section class="page">` 를 만들지 않는다.** 그건 고정 쪽 방식이고, 이 서식은
  흐름 문서다. 둘은 섞어 쓸 수 없다.
- **푸터는 `slot="footer"`.** 매 쪽 아래에 반복해서 찍힌다.
- **넘쳐도 잘리지 않는다.** 다음 쪽으로 흘러간다.

### 용지는 서식이 A4 로 못 박는다

`<style>` 맨 위의 `@page { size: A4; }` 한 줄이 한다. `doc-page.js` 는 흐름 문서일 때
`size` 디스크립터를 비워 두므로(설계상 의도) 경쟁자가 없어 이 줄이 먹고, `margin` 은
`doc-page.js` 것이 적용된다 — `@page` 캐스케이드가 디스크립터 단위라 공존한다.

**지우면 크롬 기본값 Letter 로 떨어진다.** A4보다 18mm 짧아 쪽이 엉뚱한 데서
나뉜다. 실측(2026-09-10): 지운 상태의 report 뼈대가 Letter 2쪽, 넣으면 A4 1쪽.

### 대신 포기한 것

| | 왜 |
|---|---|
| **쪽 번호** | 흐름 문서에서는 만들 수 없다. `@page` 여백상자 카운터를 크롬이 지원하지 않는다. 푸터는 `문서명 / 기관명` 으로 쓴다 |
| **화면 = 쪽 카드** | 편집 화면은 한 장의 긴 시트다. 쪽 경계는 PDF 로 뽑아야 보인다 |

### 채움률은 뽑아서 잰다

흐름 문서는 DOM 으로 쪽 경계를 알 수 없다. `sync/checkpdf.sh 문서.dc.html` 이
A4 로 뽑아 쪽별 채움률과 합격·불합격을 찍는다. 기준은 `STYLE.md` 「합격 기준」.

## 조판

| 서식 | 본문 | 줄간 |
|---|---|---|
| report · brief | 14px (12.5~15.5) | 1.85 (1.70~2.00) |
| formal | 13.5px (12.0~15.0) | 1.75 (1.60~1.90) |

여백 19 / 20 / 14mm (상 / 좌우 / 하), 자간 −0.015em,
`text-align:justify` + `word-break:keep-all`.
서체는 **Noto Sans KR 하나** — 제목도 고딕이다.

## 고칠 때 지킬 것

이 세 줄은 지우면 조용히 깨진다.

- **`<doc-page>`의 `size="a4"`** — 흐름 문서에서는 화면 시트 폭을 정한다 (인쇄 용지는 위 `@page`)
- **`<style>` 맨 위의 `@property --body-fs` / `--body-lh`** — 속성 패널 값이 전달되지
  않는 렌더 경로에서 `--body-fs: px` 같은 무효값이 들어가는데, 이때
  `var(--body-fs, 14px)`의 폴백은 발동하지 않는다(변수가 *없는* 게 아니라 *무효*라서).
  계산 시점에 무효 처리되어 상속값인 **16px / line-height:normal** 로 튄다.
  `@property`의 `initial-value`가 이때 본래 기본값으로 되돌려 준다.
- **`doc-page{ font-family:var(--sans) }`** — `doc-page.js`의
  `:host{font-family:-apple-system…}`이 `html`로부터의 상속을 끊는다. 이 선언이
  없으면 본문이 시스템 폰트로 떨어져 **기기마다 줄바꿈이 달라진다**.

그 밖에:

- **`@page { size: A4; }` 한 줄만 직접 쓴다** — 나머지 `@page` 는 `doc-page.js` 가 소유한다
- 푸터를 `section.page` 안으로 옮기지 않는다 — 흐름 문서와 혼용이 금지돼 있다
- 링크 외 유채색을 넣지 않는다
- `▢`는 쓰지 않는다 — 글리프가 없어 `□`로 폴백된다
- 색·크기를 인라인으로 새로 쓰지 말고 `var(--토큰)`을 쓴다

## 파일

```
templates/   서식 3종 (.dc.html) — 이 저장소의 원본
runtime/     doc-page.js · support.js — 지면 분할 런타임 (로컬 미리보기용)
styles.css   토큰 시트 — 각 서식의 :root 와 같은 값
STYLE.md     색·서체·간격·위계 상세 사양
docs/
  SKILL.md          Claude Code 스킬 `doc-design` 본문
  design-readme.md  Claude Design 프로젝트에 올라가는 readme
sync/
  to-skill.sh       원본 → ~/.claude/skills/doc-design/
  build-design.sh   원본 → build/design/ (Claude Design 업로드본)
  fontswap.py       폰트 참조 치환 (build-design.sh 가 부른다)
  check.sh          사본이 어긋났는지 점검
  measure.sh        쪽별 채움률 측정 (헤드리스 크롬)
  measure-probe.js  measure.sh 가 끼워 넣는 측정 프로브
  measure-report.py 측정 결과를 표로 찍는다
  README.md         동기화 절차
```

`runtime/`의 두 파일은 Claude Design이 제공하는 런타임이며 이 저장소에서
수정하지 않는다.

git 에 올리지 않는 것 (`.gitignore`):

- `build/` — `sync/build-design.sh` 가 만드는 생성물
- `notes/` — 사내 작업메모 사본. 원본은 옵시디언 볼트 `00_수집/` 에 있다

## 원본은 여기 하나다

스킬 폴더도 Claude Design 프로젝트도 **사본**이다. 사본을 직접 고치면 다음
동기화 때 덮어써진다. 고칠 일이 생기면 이 저장소를 고치고 `sync/` 를 돌린다.

```bash
./sync/check.sh          # 지금 뭐가 어긋나 있는지
./sync/to-skill.sh       # 스킬 폴더 갱신
./sync/build-design.sh   # Claude Design 업로드본 생성
./sync/measure.sh        # 쪽별 채움률 측정
```

절차와 주의사항은 [`sync/README.md`](sync/README.md).

## 라이선스

별도 라이선스를 두지 않았다. 저작권은 부산공동어시장 재무기획팀에 있다.
