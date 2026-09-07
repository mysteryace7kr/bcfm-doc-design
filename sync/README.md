# 동기화 절차

**원본은 이 저장소 하나다.** 스킬 폴더도 Claude Design 프로젝트도 사본이다.
사본을 직접 고치면 다음 동기화 때 덮어써진다.

```
                    이 저장소 (원본)
                    templates/ · runtime/ · STYLE.md · styles.css · docs/
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
   to-skill.sh      build-design.sh      git push
        │                 │                  │
        ▼                 ▼                  ▼
  ~/.claude/skills   build/design/       GitHub
    /doc-design       (업로드용)      bcfm-doc-design
                          │
                          │ Claude Code 에서 DesignSync 로 업로드
                          ▼
                  Claude Design 「인쇄문서」
```

## 고치고 나서

```bash
./sync/check.sh          # 지금 뭐가 어긋나 있는지
./sync/to-skill.sh       # 스킬 폴더 갱신
./sync/build-design.sh   # Claude Design 업로드본 생성
git add -A && git commit && git push
```

## 채움률 — 재기와 고치기

```bash
./sync/fontcache.sh                  # 처음 한 번. 측정용 Noto TTF 3개
./sync/fit.sh     내문서.dc.html      # 쪽을 다시 나눠 채운다 (원본은 .bak)
./sync/fit.sh --dry 내문서.dc.html    # 고치지 않고 결과만
./sync/measure.sh 내문서.dc.html      # 재기만 한다
./sync/topdf.sh   내문서.dc.html      # 확인용 PDF
```

헤드리스 크롬으로 실제 렌더한 뒤 잰다. npm 의존성은 없다.

**`measure.sh` 는 재기만 하고 `fit.sh` 는 고친다.** `fit.sh` 가 하는 일은
`.body` 안 블록을 전부 꺼내 한 줄로 세운 뒤, 한 쪽이 허용하는 높이까지 눌러
담고 넘칠 때만 다음 쪽으로 넘기는 것이다. 제목 뒤에서 끊기지 않게 제목은
뒤 블록과 한 덩어리로 본다. 마지막 쪽이 헐거우면 속성 패널 범위 안에서
본문크기·줄간 조합을 여덟 개까지 재보고 더 나은 것을 고른다.

원고를 부을 때 쪽을 나누지 않는 것이 전제다 — `<section class="page">` 하나에
다 붓고 `fit.sh` 를 돌린다.

### 밟은 함정 셋

1. **`.page` 는 화면에서 시트 폭을 따라가고 인쇄에서는 210×297mm 로 못박힌다.**
   창 폭에 따라 줄바꿈이 달라져 잰 값과 PDF 가 어긋난다. 두 도구 모두 재는
   동안 `width:210mm!important` 로 고정한다.
2. **한글 웹폰트는 유니코드 구간별로 100개 넘게 쪼개져 지연 로딩된다.**
   `document.fonts.ready` 가 그보다 먼저 풀려 대체 글꼴로 재게 되고, 같은
   문장이 6.4% 좁게 잡힌다. `fontcache.sh` 가 받아 둔 로컬 TTF 를 물리고,
   프로브가 실제로 앉았는지 폭을 비교해 확인한다.
3. **본문크기·줄간은 네 군데에 적혀 있다.** `@property` 의 `initial-value` 둘은
   로컬 렌더·PDF 를, 문서 끝 x-dc 의 `data-props` 기본값과 `renderVals` 의
   `?? 14` 는 Claude Design 안의 `{{ bodyFs }}` 를 정한다. 앞의 둘만 고치면
   Claude Design 이 옛 값으로 되돌려 쪽 나눔이 통째로 어긋난다.

`.page` 는 `width:100%` + `aspect-ratio` 라 **시트 폭에 따라 지면 크기가 변한다.**
창이 좁으면 지면이 축소돼 채움률이 실제보다 높게 나온다 — `measure.sh` 가
`--window-size=1400,2400` 을 주는 이유다. 직접 브라우저로 잴 때도 창을 충분히 넓혀야 한다.

`file://` 로는 `<x-dc>` 런타임이 돌지 않아 로컬 http 서버를 잠깐 띄웠다 끈다.

**채움률은 자동으로 맞춰지지 않는다.** 지면은 고정된 A4 상자이고 `.body{flex:1}` 이
푸터를 바닥으로 밀 뿐이다. 원고 분량으로 맞추는 수밖에 없다. 기준값은 `STYLE.md`
「한 쪽에 들어가는 분량」에 있다.

## Claude Design 업로드

`build/design/` 을 만든 뒤 Claude Code 에게 이렇게 시킨다.

> build/design 을 Claude Design 「인쇄문서」 프로젝트에 올려줘

DesignSync 는 `list_files` → `finalize_plan` → `write_files` 순서로 돈다.
`finalize_plan` 에 올릴 경로를 명시하므로, 아래 4개는 계획에 넣지 않는다 —
**Claude Design 이 소유하는 파일이라 덮어쓰면 안 된다.**

| 건드리지 않는 것 | 왜 |
|---|---|
| `fonts/` (TTF 8개) | 맥북에 원본이 없다. 지우면 복구할 방법이 없다 |
| `templates/*/ds-base.js` | Claude Design 런타임이 자동으로 넣는다 |
| `_ds_manifest.json` · `_ds_bundle.js` | 앱이 자체 점검으로 생성한다 |
| `.thumbnail` · `thumbnail.html` | 앱이 만든 미리보기 |

올릴 것은 `readme.md` · `styles.css` · `templates/{report,formal,brief}/*` 뿐이고,
그중에서도 **실제로 바뀐 것만 올린다.** 올리기 전에 `get_file` 로 원격본을 읽어
`build/design/` 과 대조한다 — 누군가 Claude Design 편집기에서 손댔을 수 있고,
그걸 모르고 덮어쓰면 그 수정이 조용히 사라진다.

## 폰트 참조는 두 파일에서 바뀐다

`.dc.html` 만 치환하면 안 된다. `styles.css` 도 폰트 참조가 다르고, 경로도 다르다.

| 파일 | 저장소본 | Claude Design본 |
|---|---|---|
| `templates/*.dc.html` | `<link>` 3줄 | `@font-face` … `../../fonts/…` |
| `styles.css` | `@import url(…)` | `@font-face` … `fonts/…` |

`.dc.html` 은 `templates/<이름>/` 안에, `styles.css` 는 프로젝트 루트에 놓이므로
`fonts/` 로 올라가는 깊이가 다르다. `fontswap.py` 가 확장자를 보고 갈라 처리한다.

## 왜 변형이 두 종류인가

폰트 참조만 다르다.

| | 폰트 | 이유 |
|---|---|---|
| 원본 · 스킬 · GitHub | Google Fonts `<link>` | 폰트 파일 없이 어디서나 열린다 |
| Claude Design | 로컬 TTF `@font-face` | 웹폰트 로딩 실패 시 줄바꿈이 달라지는 사고를 원천 차단 |

`sync/fontswap.py` 가 이 치환을 한다. 기대한 `<link>` 줄을 못 찾으면
**조용히 넘어가지 않고 죽는다** — 치환만 실패해서 Claude Design 쪽 폰트가
슬그머니 웹폰트로 돌아가는 것이 막으려는 사고다.
