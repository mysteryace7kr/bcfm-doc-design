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
