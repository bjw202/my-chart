"""SPEC-AI-REPORT-005 M1 합성 픽스처 생성 스크립트 (네트워크 없음, 테스트에서 실행하지 않음).

녹화 픽스처(recorded/)를 문자열 단위로 손봐 synthetic/에 쓴다. 다시 실행하면 같은 바이트가 나온다.
실행: /Users/byunjungwon/Dev/my_chart/.venv/bin/python -I backend/tests/fixtures/dart/build_synthetic.py
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REC = HERE / "recorded"
SYN = HERE / "synthetic"
SYN.mkdir(exist_ok=True)


def read(name):
    # newline="" — 원본의 CRLF를 그대로 보존한다
    with open(REC / name, encoding="utf-8", newline="") as f:
        return f.read()


def write(name, text):
    with open(SYN / name, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def list_rows(html):
    """tbody 안의 <tr>…</tr> 행 구간(시작, 끝)을 돌려준다."""
    body_start = html.index('<tbody id="tbody">')
    body_end = html.index("</tbody>", body_start)
    spans = [(m.start(), m.end())
             for m in re.finditer(r"<tr>.*?</tr>", html[body_start:body_end], re.S)]
    return [(body_start + s, body_start + e) for s, e in spans]


def row_of(html, rcp):
    for s, e in list_rows(html):
        if f"rcpNo={rcp}" in html[s:e]:
            return s, e
    raise KeyError(rcp)


lst = read("list_020150_recent.html")

# 1) 회사 고유번호가 2개 섞인 목록 (AC-AIR5-005 (2)): 5번째 행(20250814003923)만 다른 고유번호
s, e = row_of(lst, "20250814003923")
row = lst[s:e]
assert row.count("openCorpInfoNew('00113997'") == 1
write("list_020150_mixed_corp.html",
      lst[:s] + row.replace("openCorpInfoNew('00113997'", "openCorpInfoNew('00999999'") + lst[e:])

# 2) 같은 기간 원본 + 늦게 접수된 정정본 (AC-AIR5-006 (2)): 반기보고서 (2025.06) 정정 행 추가
#    정정 행 표기는 recorded/list_299030_recent.html의 실제 [기재정정] 마크업을 따른다
CORR = "20250902000123"
corr = (row.replace("20250814003923", CORR)
        .replace("<td>2025.08.14</td>", "<td>2025.09.02</td>"))
corr, n = re.subn(
    r'(title="반기보고서 공시뷰어 새창">\s*)반기보고서',
    r'\1<span title="본 보고서명으로 이미 제출된 보고서의 기재내용이 변경되어 제출된 것임" '
    r'class="txtCB">[기재정정]</span>반기보고서', corr)
assert n == 1 and corr.count(CORR) >= 2, "정정 행 치환 실패"
write("list_020150_correction.html", lst[:s] + corr + "\r\n\t\t\t\t" + lst[s:])

# 3) 행 0개 목록 (AC-AIR5-005 (3)): tbody 비움. 실제 DART의 "결과 없음" 마크업은 관측하지 않았다
rows = list_rows(lst)
write("list_empty.html", lst[:rows[0][0]] + lst[rows[-1][1]:])

# --- 목차 (반기보고서 20260814000373 본문) ---
toc = read("main_20260814000373.html")
starts = [m.start() for m in re.finditer(r"var node2 = \{\};", toc)]


def block(title):
    """`title`을 가진 node2 블록(자식 포함, 다음 node2 선언 직전까지)의 구간."""
    for i, st in enumerate(starts):
        nxt = starts[i + 1] if i + 1 < len(starts) else None
        seg = toc[st:nxt]
        if f"node2['text'] = \"{title}\";" in seg:
            assert nxt is not None
            return st, nxt
    raise KeyError(title)


fs_s, fs_e = block("2. 연결재무제표")
nt_s, nt_e = block("3. 연결재무제표 주석")
assert fs_e == nt_s, "연결재무제표와 주석 블록이 인접하지 않음"
fs_blk, nt_blk = toc[fs_s:fs_e], toc[nt_s:nt_e]

# 4) 연결 노드를 지운 목차 (AC-AIR5-007 (2)): 연결재무제표·연결재무제표 주석 블록(하위 노드 포함) 삭제
write("main_20260814000373_no_consolidated.html", toc[:fs_s] + toc[nt_e:])

# 5) 주석을 재무제표보다 앞에 둔 목차 (AC-AIR5-007 (4))
write("main_20260814000373_reordered.html", toc[:fs_s] + nt_blk + fs_blk + toc[nt_e:])

# 6) 값이 오염된 목차 노드 (AC-AIR5-012 (2)): 연결재무제표 노드의 dcmNo·offset·dtd 오염
head_end = fs_blk.index("node2['tocNo']")
head, tail = fs_blk[:head_end], fs_blk[head_end:]
bad = (head.replace("node2['dcmNo'] = \"11527102\";", "node2['dcmNo'] = \"../1\";")
       .replace("node2['offset'] = \"259834\";", "node2['offset'] = \"1&x=y\";")
       .replace("node2['dtd'] = \"dart4.xsd\";", "node2['dtd'] = \"a/b\";"))
assert bad.count("../1") == 1 and bad.count("1&x=y") == 1 and bad.count("a/b") == 1
write("main_20260814000373_polluted.html", toc[:fs_s] + bad + tail + toc[fs_e:])

print(sorted(p.name for p in SYN.iterdir()))
