# bcfm-doc-design

부산공동어시장 재무기획팀 **인쇄문서 디자인 시스템**.
보고서·기안(공문)·업무진행 보고를 A4 인쇄용으로 조판하는 서식 3종.

화면이 아니라 종이를 전제로 한다 — 흰 종이, 검은 잉크, 링크 외 유채색 없음.
개조식 기호(`○ ▶ ※ ⇨`)의 위계를 내어쓰기로 정렬하는 것이 뼈대다.

## 서식

| 파일 | 쓸 때 | 기본 |
|---|---|---|
| `templates/report.dc.html` | 여러 장, 개조식 위계 + 요약밴드 + 번호 섹션 — 보고서·검토 | 2쪽 |
| `templates/formal.dc.html` | 수신처·발신명의가 필요한 문서 — 기안(공문)·건의서·질의서. 결재란 포함 | 1쪽 |
| `templates/brief.dc.html` | 1~2장, 타임라인·항목 나열 — 업무진행사항·요약보고 | 1쪽 |

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

`<section class="page">` **하나가 A4 한 장**이다.

```html
<doc-page size="a4" margin="0">
  <section class="page">
    <div class="body"> … 내용 … </div>
    <div class="foot"><span>문서명</span><span>1 / 2</span></div>
  </section>
  <section class="page"> … 2쪽 … </section>
</doc-page>
```

이 구조라서:

- **편집 화면에 페이지가 한 장씩 카드로 보인다.** 화면에서 본 그대로 인쇄된다.
- **A4가 못박힌다** — `doc-page.js`가 `@page { size: 210mm 297mm }`를 주입한다.
  내보내기 대화상자에서 무엇을 고르든 쪽수와 구성이 변하지 않는다.
- **페이지 번호를 쓸 수 있다.** 푸터에 직접 적는다.

### 장을 늘리려면

`<section class="page">` 블록을 통째로 복사해 붙이고 푸터의 `n / N`만 고친다.
**장수 제한은 없다.**

### 넘치면 잘린다 — 대신 화면에 보인다

한 페이지에 내용이 넘치면 다음 장으로 흘러가지 않고 **잘린다**(`overflow:hidden`).
내용을 줄이라는 뜻이 아니라 **페이지를 하나 더 만들라는 뜻**이다.
잘린 것은 편집 화면 카드에 그대로 보인다 — 카드가 곧 인쇄될 종이다.

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

- **`<doc-page>`의 `size="a4"`** — 화면 카드 크기와 인쇄 용지를 동시에 정한다
- **`<style>` 맨 위의 `@property --body-fs` / `--body-lh`** — 속성 패널 값이 전달되지
  않는 렌더 경로에서 `--body-fs: px` 같은 무효값이 들어가는데, 이때
  `var(--body-fs, 14px)`의 폴백은 발동하지 않는다(변수가 *없는* 게 아니라 *무효*라서).
  계산 시점에 무효 처리되어 상속값인 **16px / line-height:normal** 로 튄다.
  `@property`의 `initial-value`가 이때 본래 기본값으로 되돌려 준다.
- **`doc-page{ font-family:var(--sans) }`** — `doc-page.js`의
  `:host{font-family:-apple-system…}`이 `html`로부터의 상속을 끊는다. 이 선언이
  없으면 본문이 시스템 폰트로 떨어져 **기기마다 줄바꿈이 달라진다**.

그 밖에:

- `@page` 규칙을 직접 쓰지 않는다 — `doc-page.js`가 소유한다
- 푸터를 `slot="footer"`로 옮기지 않는다 — `section.page`와 혼용이 금지돼 있고,
  옮기면 페이지 번호를 쓸 수 없다
- 링크 외 유채색을 넣지 않는다
- `▢`는 쓰지 않는다 — 글리프가 없어 `□`로 폴백된다
- 색·크기를 인라인으로 새로 쓰지 말고 `var(--토큰)`을 쓴다

## 파일

```
templates/   서식 3종 (.dc.html) — 등록·사용 대상
runtime/     doc-page.js · support.js — 지면 분할 런타임 (로컬 미리보기용)
styles.css   토큰 시트 — 각 서식의 :root 와 같은 값
STYLE.md     색·서체·간격·위계 상세 사양
```

`runtime/`의 두 파일은 Claude Design이 제공하는 런타임이며 이 저장소에서
수정하지 않는다.

## 라이선스

별도 라이선스를 두지 않았다. 저작권은 부산공동어시장 재무기획팀에 있다.
