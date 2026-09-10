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

## 현재 흐름 서식의 PDF 확인

```bash
./sync/fontcache.sh
./sync/topdf.sh 내문서.dc.html 결과.pdf
./sync/checkpdf.sh 내문서.dc.html
```

`topdf.sh`는 macOS Chrome의 헤드리스 출력이다. Noto TTF는 로컬 캐시를 쓰지만
React는 CDN에서 불러온다. 고정 대기 시간 후 출력하므로 결과 파일을 반드시 열어
글꼴·내용·쪽 경계를 확인한다. 상대 경로 이미지 등은 임시 작업 디렉터리로 자동
복사되지 않는다. 첨부 자산이 있는 문서는 누락 여부를 따로 확인한다.

`checkpdf.sh`는 기본 A4·20mm 흐름 서식의 본문 잉크 도달률만 잰다.
92% 미만은 검토 신호이며 종합 불합격이 아니다. 원문 보존·고립 줄·잘림은 별도 확인한다.
브라우저와 PDF를 비교할 때 글꼴 파일·용지·배율·본문 크기·줄간을 동일하게 맞춘다.

### 이전 고정 쪽 문서 전용 도구

`fit.sh`·`measure.sh`는 `section.page > .body` 구조에만 적용된다.
현재 세 템플릿에 사용하지 않는다. 흐름 서식에 맞추려고 `section.page`를 새로
감싸면 잘림을 일으키는 이전 모델로 되돌아간다.

`fit.sh`는 기존 고정 쪽 문서의 블록 재배치와 조판값 후보 탐색을 한다.
글자 보존 검사는 있으나 HTML을 쪼개는 별도 알고리즘이므로 실제 PDF 검증이 필요하다.
이 도구를 흐름 문서의 '마지막 한 줄 자동 보정기'로 안내하지 않는다.

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
