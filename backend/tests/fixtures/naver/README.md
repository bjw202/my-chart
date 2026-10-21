# 네이버 뉴스 픽스처 (SPEC-AI-REPORT-007 M1·M2)

goose 네이버 사전 수집 모듈(M2 `backend/services/goose_naver_prefetch.py`) 테스트용 녹화·합성 JSON이다. 테스트는 이 파일을 `httpx.MockTransport`로 돌려줄 뿐 네이버에 접속하지 않는다.

## 녹화 픽스처 (`recorded/`)

- 받은 때: 2026-10-21 17:59:55.533 ~ 18:00:44.936 (KST, +09:00). 요청별 주소·상태·content-type·받은 시각·바이트는 `recorded/request_log.json`.
- 명령: `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I backend/tests/fixtures/naver/capture_naver.py backend/tests/fixtures/naver/recorded <종목코드…>` (urllib, 리디렉트 추적 끔, 브라우저형 User-Agent만 전송, 쿠키·인증 없음, 요청 간격 1.1초 이상). 020150·000040을 한 번에, 999999를 따로 실행했다.
- 요청 수: `m.stock.naver.com` 3회(전부 200). 그 밖에 기사 주소 확인용 `n.news.naver.com` GET 1회(저장하지 않음, `progress.md §E.2` R4).
- 응답 본문은 바이트 그대로 저장했다. 합성 픽스처는 `020150_p1.json`에서 만든다.

| 파일 | 요청 | 바이트 | 내용 |
|---|---|---|---|
| `020150_p1.json` | `GET https://m.stock.naver.com/api/news/stock/020150?pageSize=10&page=1` | 8,094 | 롯데에너지머티리얼즈, 그룹 10개 × 기사 1건 |
| `000040_p1.json` | `GET https://m.stock.naver.com/api/news/stock/000040?pageSize=10&page=1` | 8,192 | 기사가 적을 것으로 보고 골랐으나 그룹 10개 × 기사 1건 |
| `999999_p1.json` | `GET https://m.stock.naver.com/api/news/stock/999999?pageSize=10&page=1` | 2 | 존재하지 않는 종목코드. 본문 `[]` — 실제로 관측한 0건 응답 모양 |

## 응답 모양 (관측)

```
[                                   ← 최상위 배열 = 그룹 목록 (pageSize=10 → 10개)
  {"total": 4,                      ← 그룹의 관련 기사 묶음 크기. 기사 수가 아니다
   "items": [                       ← 관측한 그룹은 모두 기사 1건
     {"id", "officeId", "articleId", "officeName", "datetime", "type", "title",
      "photoType", "imageOriginLink"(일부 없음), "titleFull", "mobileNewsUrl", "body"}
   ]},
  ...
]
```

- 기사 목록 경로: 그룹들의 `items`를 펼친 목록 `[*].items[*]`.
- `officeId`·`articleId`는 앞자리 0이 있는 숫자 문자열(`"015"`, `"0005344879"`). `datetime`은 `YYYYMMDDHHMM` 문자열.
- `body`는 129~154자에서 잘린 요약 조각이고 `... `로 끝난다. HTML 태그는 없고 `&quot;` 같은 HTML 엔티티가 들어 있다.
- `mobileNewsUrl`은 `https://n.news.naver.com/mnews/article/<officeId>/<articleId>`와 20건 모두 같다.

## 합성 픽스처 (`synthetic/`)

`build_synthetic.py`가 `recorded/020150_p1.json`을 읽어 필드 값만 바꿔 쓴다(네트워크 없음, 다시 실행해도 같은 바이트). 키 이름과 그룹 구조는 녹화본 그대로다. 실행: `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I backend/tests/fixtures/naver/build_synthetic.py`

| 파일 | 원본 그룹 | 바꾼 것 | 쓰는 AC |
|---|---|---|---|
| `zero_articles.json` | 없음 | 빈 배열 `[]` (`999999_p1.json`과 같은 모양) | AC-AIR7-008 (0건), AC-014 |
| `empty_body.json` | 0 | `body` → `""` | AC-AIR7-006 |
| `bad_article_id.json` | 0 | `articleId` → `"../x"` | AC-AIR7-006 |
| `bad_datetime.json` | 0 | `datetime` → `"2026102113"`(10자리) | AC-AIR7-006 |
| `markup_body.json` | 0 | `body` 앞에 `<b>강조</b> ` 추가 | AC-AIR7-006 |
| `parse_cases.json` | 0·1·2·3 | 차례로 빈 `body` / `articleId "../x"` / `datetime "2026102113"` / `datetime "202610211352"` + `body` 앞 `<b>강조</b> ` | AC-AIR7-006 (2) |
| `mixed_status.json` | 0·1·2 | 0 그대로(`ok`), 1 빈 `body`(`metadata_only`), 2 `articleId "../x"`(`error`) | AC-AIR7-014 (`partial`) |
| `all_metadata_only.json` | 전체 10 | 모든 `body` → `""` | AC-AIR7-014 (`failed`) |
| `missing_items_path.json` | 전체 10 | 그룹에서 `items` 키 삭제 | AC-AIR7-008 (경로 없음) |
| `not_json.txt` | — | 녹화본 바이트 앞 50바이트(ASCII 구간에서 잘린 JSON → `JSONDecodeError`) | AC-AIR7-008 (JSON 아님) |

M2에서 더한 합성 픽스처(plan.md §3 M2, 감사 부채 D-B). 만드는 방법은 위와 같고, 두 번 실행해 `shasum` 목록이 같은지 확인했다(`progress.md §E.2` M2).

| 파일 | 원본 그룹 | 바꾼 것 | 쓰는 AC |
|---|---|---|---|
| `top_level_object.json` | 0 | 그룹 객체 하나를 최상위에 둠(배열 아님) | AC-AIR7-008 (최상위 객체 → `failed`, 오류 문구 `top-level JSON value is not an array`) |
| `mixed_malformed_groups.json` | 0·1·2·3 | 응답 순서: 그룹 1 정상 / 그룹 2 `items` 없음 / 그룹 3 `items`가 문자열 / 그룹 4 객체가 아님(문자열) / 그룹 5 정상 기사 1건 + 객체가 아닌 기사(정수 `42`) 1건 | AC-AIR7-006 (4), AC-014 (e) |
| `two_items_group.json` | 0·1·2 | 그룹 0에 그룹 1의 기사를 붙여 기사 2건, 그 뒤 그룹 2(그룹 2개·기사 3건) | AC-AIR7-006 (3) |
| `entity_body.json` | 0 | `body` → `a&#39;b&#x27;c &amp; &lt;b&gt;리터럴&lt;/b&gt; <i>태그</i>` | AC-AIR7-006 7 (태그 제거 → 엔티티 해제 순서) |
| `all_empty_items.json` | 전체 10 | 모든 그룹의 `items` → `[]` | AC-AIR7-008 (REQ-AIR7-009 두 번째 절 → `no_results`) |

## 테스트가 픽스처에서 읽어야 할 값 (lessons #10 — 손으로 옮겨 적지 않기)

- 기사 수: 펼친 목록 길이 `len([it for g in data for it in g["items"]])`. 그룹의 `total`을 쓰지 않는다.
- 제목·본문 기대값: 각 기사의 `title`, `body`(엔티티 해제·태그 제거 후 평문과 비교).
- 식별자·주소: `officeId`, `articleId`, `officeName`, `datetime`. 기대 `article_url`은 `officeId`·`articleId`로 만든다(응답의 `mobileNewsUrl`과 같다는 것은 관측 사실이며 테스트 기대값으로 쓰려면 응답에서 읽는다).
- `published_at` 기대값: 합성 픽스처의 리터럴 `202610211352` → `2026-10-21T13:52:00+09:00`만 형식 규칙으로 허용된다(acceptance §A).
- 원본 보존: `response.json` 바이트는 `MockTransport`에 넘긴 픽스처 파일 바이트와 비교한다.
