"""SPEC-AI-REPORT-007 M1 합성 픽스처 생성 스크립트 (네트워크 없음, 테스트에서 실행하지 않음).

녹화 픽스처 recorded/020150_p1.json을 읽어 필드 값만 바꿔 synthetic/에 쓴다.
키 이름과 그룹 구조(최상위 배열 → 그룹 {total, items} → 기사)는 녹화본 그대로 둔다.
다시 실행하면 같은 바이트가 나온다.
실행: /Users/byunjungwon/Dev/my_chart/.venv/bin/python -I backend/tests/fixtures/naver/build_synthetic.py
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REC = HERE / "recorded" / "020150_p1.json"
SYN = HERE / "synthetic"
SYN.mkdir(exist_ok=True)

BASE = json.loads(REC.read_bytes().decode("utf-8"))


def groups(*idx):
    """녹화본의 지정 그룹을 깊은 복사로 돌려준다."""
    return [copy.deepcopy(BASE[i]) for i in idx]


def item(g):
    return g["items"][0]


def write_json(name, data):
    # 녹화본과 같은 압축 형태(공백 없음, 한글 그대로)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (SYN / name).write_bytes(text.encode("utf-8"))


# 기사 0건 — 녹화본 999999_p1.json의 실제 빈 응답과 같은 모양
write_json("zero_articles.json", [])

# 단일 사례 파일: 녹화본 첫 그룹 1개만 두고 한 필드를 바꾼다
g = groups(0)
item(g[0])["body"] = ""
write_json("empty_body.json", g)

g = groups(0)
item(g[0])["articleId"] = "../x"
write_json("bad_article_id.json", g)

g = groups(0)
item(g[0])["datetime"] = "2026102113"  # 10자리
write_json("bad_datetime.json", g)

g = groups(0)
item(g[0])["body"] = "<b>강조</b> " + item(g[0])["body"]
write_json("markup_body.json", g)

# AC-AIR7-006 (2) 묶음: 빈 body, ../x, 10자리 datetime, 정상(+<b>강조</b>) 순서
g = groups(0, 1, 2, 3)
item(g[0])["body"] = ""
item(g[1])["articleId"] = "../x"
item(g[2])["datetime"] = "2026102113"
item(g[3])["datetime"] = "202610211352"
item(g[3])["body"] = "<b>강조</b> " + item(g[3])["body"]
write_json("parse_cases.json", g)

# AC-AIR7-014 혼합: ok(그대로), metadata_only(빈 body), error(../x)
g = groups(0, 1, 2)
item(g[1])["body"] = ""
item(g[2])["articleId"] = "../x"
write_json("mixed_status.json", g)

# AC-AIR7-014 전부 metadata_only: 녹화본 10그룹 모두 body 비움
g = copy.deepcopy(BASE)
for grp in g:
    for it in grp["items"]:
        it["body"] = ""
write_json("all_metadata_only.json", g)

# AC-AIR7-008 기사 목록 경로 없음: 그룹에서 items 키 제거
g = copy.deepcopy(BASE)
for grp in g:
    del grp["items"]
# 파일 이름에 "_key."를 넣지 않는다 — .gitignore의 비밀 파일 규칙 `*_key.*`에 걸린다
write_json("missing_items_path.json", g)

# AC-AIR7-008 JSON이 아닌 본문: 녹화본 바이트 앞 50바이트(ASCII 구간에서 잘린 JSON).
# 한글 바이트 중간에서 자르면 JSON 오류가 아니라 UTF-8 디코딩 오류가 나므로 ASCII 구간에서 자른다.
(SYN / "not_json.txt").write_bytes(REC.read_bytes()[:50])
