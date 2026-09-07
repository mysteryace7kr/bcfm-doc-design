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

## 채움률 측정

```bash
./sync/measure.sh                    # 서식 3종 전부
./sync/measure.sh 내문서.dc.html      # 특정 파일
```

헤드리스 크롬으로 실제 렌더한 뒤 쪽별 채움률을 잰다. npm 의존성은 없다.

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

올릴 것은 `readme.md` · `styles.css` · `templates/{report,formal,brief}/*` 뿐이다.

## 왜 변형이 두 종류인가

폰트 참조만 다르다.

| | 폰트 | 이유 |
|---|---|---|
| 원본 · 스킬 · GitHub | Google Fonts `<link>` | 폰트 파일 없이 어디서나 열린다 |
| Claude Design | 로컬 TTF `@font-face` | 웹폰트 로딩 실패 시 줄바꿈이 달라지는 사고를 원천 차단 |

`sync/fontswap.py` 가 이 치환을 한다. 기대한 `<link>` 줄을 못 찾으면
**조용히 넘어가지 않고 죽는다** — 치환만 실패해서 Claude Design 쪽 폰트가
슬그머니 웹폰트로 돌아가는 것이 막으려는 사고다.
