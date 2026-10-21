"""SPEC-AI-REPORT-007 M1 녹화 스크립트 (테스트에서 실행하지 않음, 실제 네트워크 사용).

네이버 증권 모바일 뉴스 JSON을 종목코드별로 1회씩 받아 응답 본문을 바이트 그대로 저장하고,
요청별 메타(주소·상태·content-type·받은 시각·바이트)를 request_log.json에 남긴다.
요청 헤더는 User-Agent만 보낸다. 쿠키·인증 정보는 없다. 리디렉트는 따라가지 않는다.

실행: /Users/byunjungwon/Dev/my_chart/.venv/bin/python -I backend/tests/fixtures/naver/capture_naver.py <출력 폴더> <종목코드> [<종목코드> ...]
"""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
URL = "https://m.stock.naver.com/api/news/stock/{code}?pageSize=10&page=1"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # 리디렉트 비추적
        return None


def main(out_dir, codes):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(_NoRedirect)
    log_path = out / "request_log.json"
    # 기존 기록은 보존하고 이번 실행분을 뒤에 붙인다
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    for i, code in enumerate(codes):
        if i:
            time.sleep(1.1)
        url = URL.format(code=code)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        retrieved_at = datetime.now(KST).isoformat(timespec="milliseconds")
        try:
            with opener.open(req, timeout=10) as resp:
                status, ctype, body = resp.status, resp.headers.get("content-type"), resp.read()
        except urllib.error.HTTPError as e:
            status, ctype, body = e.code, e.headers.get("content-type"), e.read()
        name = f"{code}_p1.json"
        (out / name).write_bytes(body)
        log.append({"file": name, "method": "GET", "url": url, "request_headers": {"User-Agent": UA},
                    "status": status, "content_type": ctype, "retrieved_at": retrieved_at,
                    "bytes": len(body)})
        print(status, ctype, len(body), url)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n",
                                          encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
