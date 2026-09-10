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
./sync/fit.sh     내문서.dc.html      # 쪽을 다시 나눠 채운다 (원본은 .bak)
./sync/fit.sh --dry 내문서.dc.html    # 고치지 않고 결과만
./sync/measure.sh 내문서.dc.html      # 재기만 한다
./sync/orphan.sh  내문서.dc.html      # 외톨이 줄 (마지막 줄에 한 단어·한 글자)
./sync/topdf.sh   내문서.dc.html      # 확인용 PDF (아무것도 주입하지 않는다)
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

1. **`.page` 는 화면에서 시트 폭을 따라가고 인쇄에서는 210×297mm 로 못박힌다.**
   창 폭에 따라 줄바꿈이 달라져 잰 값과 PDF 가 어긋난다. 두 도구 모두 재는
   동안 `width:210mm!important` 로 고정한다.
2. **한글 웹폰트는 유니코드 구간별로 100개 넘게 쪼개져 지연 로딩된다.**
   `document.fonts.ready` 가 그보다 먼저 풀려 대체 글꼴로 재게 되고, 같은
   문장이 6.4% 좁게 잡힌다. 그래서 재는 동안은 맥에 설치된 Pretendard TTF
   (`~/Library/Fonts`) 를 물리고, 프로브가 실제로 앉았는지 폭을 비교해 확인한다.
   내려받는 글꼴 캐시(`fontcache.sh`)는 2026-09-10 에 없앴다 — Pretendard 는
   Google Fonts 에 없고, 설치본이 있으면 받을 이유가 없다.
3. **본문크기·줄간은 네 군데에 적혀 있다.** `@property` 의 `initial-value` 둘은
   로컬 렌더·PDF 를, 문서 끝 x-dc 의 `data-props` 기본값과 `renderVals` 의
   `?? 14` 는 Claude Design 안의 `{{ bodyFs }}` 를 정한다. 앞의 둘만 고치면
   Claude Design 이 옛 값으로 되돌려 쪽 나눔이 통째로 어긋난다.
4. **막힌 것이 제목이면 제목을 자를 게 아니다.** 제목은 뒤 블록과 붙어 다니므로,
   여백을 만든 범인은 그 뒤의 표나 문단이다. 제목을 건너뛰고 그쪽을 나눠야 한다.
   이걸 놓쳐서 한 쪽이 48% 로 남은 채 「입증방법」 표가 통째로 넘어갔다.
5. **조판값이 바뀌면 자를 자리도 바뀐다.** 조판 후보를 재볼 때 앞 후보에서 만든
   쪼개기를 물려받으면 안 된다. 후보마다 나누지 않은 원본에서 다시 시작한다.
   (이걸 놓쳤을 때 7쪽 94.3%, 고친 뒤 7쪽 97.6%.)
6. **조판 판정은 줄 피치가 아니라 글자 크기로 한다.** 12.5px/1.95 와 13.5px/1.80 은
   피치가 같지만 읽기는 전혀 다르다. 피치로 견주다가 구청 제출 문서에 12.5px 를
   고른 적이 있다.

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

올릴 것은 `readme.md` · `styles.css` · `templates/report/*` 와 **이 시스템이 올리는
유일한 자산인** `fonts/Pretendard-{Regular,Medium,Bold}.ttf` 뿐이고,
그중에서도 **실제로 바뀐 것만 올린다.** 올리기 전에 `get_file` 로 원격본을 읽어
`build/design/` 과 대조한다 — 누군가 Claude Design 편집기에서 손댔을 수 있고,
그걸 모르고 덮어쓰면 그 수정이 조용히 사라진다.

## 폰트 참조는 치환하지 않는다

저장소본과 Claude Design본이 **같은 줄**을 쓴다.

```css
@font-face{font-family:'Pretendard';font-weight:400;font-style:normal;font-display:swap;
  src:local('Pretendard'),url('../../fonts/Pretendard-Regular.ttf') format('truetype')}
```

`local('Pretendard')` 가 먼저라 맥에서는 설치본이 쓰이고(네트워크도 다운로드도
없다), 설치본이 없는 환경에서만 프로젝트 `fonts/` 의 TTF 로 떨어진다. 경로는
Claude Design 배치 기준이다 — `.dc.html` 은 `templates/report/` 안, `styles.css` 는
루트에 놓이므로 각각 `../../fonts/` 와 `fonts/` 다.

예전에는 `sync/fontswap.py` 가 저장소본(Google Fonts `<link>`) → Claude Design본
(로컬 TTF `@font-face`) 치환을 했다. **2026-09-10 에 없앴다** — 원본과 업로드본이
서로 다른 파일이 되어, 한쪽만 고쳐 놓고 고쳤다고 착각하는 사고의 원인이었다.
Pretendard 는 Google Fonts 에 없어 `<link>` 경로가 아예 없기도 하다.
