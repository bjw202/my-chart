

# ─────────────────────────────────────────────────────────────────────────────
# SPEC-AI-REPORT-007 M3 — 네이버 최신 뉴스 사전 수집 연결 (REQ-AIR7-001~004·008·012·015)
# ─────────────────────────────────────────────────────────────────────────────

_NAVER_FIX = Path(__file__).parent / "fixtures" / "naver"
_ENV_NAVER = "AI_REPORT_GOOSE_NAVER_PREFETCH"


class FakeNaver:
    """네이버 수집기 대역: 순서·인자를 기록하고, gate가 열릴 때까지 기다린다."""

    def __init__(self, order: list | None = None, *, wait: bool = False, raise_exc=None):
        self.order = order if order is not None else []
        self.calls: list[tuple[str, Path, bool]] = []
        self.entered = asyncio.Event()
        self.gate = asyncio.Event()
        if not wait:
            self.gate.set()
        self.raise_exc = raise_exc

    async def __call__(self, code, out_dir, *, code_validated=False):
        self.order.append("naver")
        self.calls.append((code, Path(out_dir), code_validated))
        self.entered.set()
        if self.raise_exc is not None:
            raise self.raise_exc
        await self.gate.wait()
        return {"outcome": "complete"}


def _fake_dart(order: list):
    async def dart(code, out_dir):
        order.append("dart")
        return {"outcome": "complete"}

    return dart


def _naver_recorder(body: bytes | None = None, *, status: int = 200, respond=None):
    """실제 네이버 수집기 + 모든 요청을 기록하는 MockTransport."""
    httpx = __import__("httpx")
    requests: list = []

    async def handle(request):
        requests.append(str(request.url))
        if respond is not None:
            resp = respond(request)
            if asyncio.iscoroutine(resp):
                resp = await resp
            return resp
        return httpx.Response(status, content=body or b"")

    return httpx.MockTransport(handle), requests


def _real_naver(mods, transport):
    return mods.gjs.goose_naver_prefetch.NaverPrefetcher(transport=transport)


def _naver_index(tmp_path: Path, job) -> dict:
    path = tmp_path / "runs" / job.job_id / "naver" / "index.json"
    return __import__("json").loads(path.read_text(encoding="utf-8"))


def _progress_stages(job) -> list:
    return [e.data.get("stage") for e in job.events if e.type == "progress"]


async def _run_job(svc):
    out = await asyncio.wait_for(svc.start("020150", "롯데에너지머티리얼즈"), 2)
    assert out.kind == "started"
    await asyncio.wait_for(_finish(out.job), 5)
    return out.job


# ── AC-AIR7-001 — 실행 순서 ─────────────────────────────────────────────────


async def test_air7_001_order_with_dart_and_naver(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    order: list = []
    naver = FakeNaver(order)
    svc = _service(mods, tmp_path, OrderRunner(mods.gr, order), integrity=_order_integrity(mods.gh, order),
                   prefetcher=_fake_dart(order), naver_prefetcher=naver)
    job = await _run_job(svc)
    assert order == ["integrity", "dart", "naver", "integrity", "runner"]
    assert [c[:2] for c in naver.calls] == [("020150", tmp_path / "runs" / job.job_id / "naver")]
    assert (job.status, job.error_kind) == ("done", None)


async def test_air7_001_order_with_naver_only(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    order: list = []
    svc = _service(mods, tmp_path, OrderRunner(mods.gr, order), integrity=_order_integrity(mods.gh, order),
                   naver_prefetcher=FakeNaver(order))
    job = await _run_job(svc)
    assert order == ["integrity", "naver", "integrity", "runner"]
    assert job.status == "done"


async def test_air7_001_order_without_prefetchers(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    order: list = []
    svc = _service(mods, tmp_path, OrderRunner(mods.gr, order), integrity=_order_integrity(mods.gh, order))
    job = await _run_job(svc)
    assert order == ["integrity", "runner"]
    assert not (tmp_path / "runs" / job.job_id / "naver").exists()


async def test_air7_001_second_integrity_failure_with_naver_only(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    order: list = []
    runner = OrderRunner(mods.gr, order)
    svc = _service(mods, tmp_path, runner, integrity=_order_integrity(mods.gh, order, fail_on=2),
                   naver_prefetcher=FakeNaver(order))
    job = await _run_job(svc)
    assert (job.status, job.error_kind) == ("error", "integrity")
    assert runner.calls == []


def test_air7_013_defaults_have_no_naver_and_production_injects_it(mods):
    default = mods.gjs.GooseJobService()
    assert default._naver_prefetcher is None and default._code_check is None
    prod = mods.gjs.get_service()
    assert isinstance(prod._naver_prefetcher, mods.gjs.goose_naver_prefetch.NaverPrefetcher)
    assert callable(prod._code_check)


# ── AC-AIR7-002 — 수집 중 취소 ──────────────────────────────────────────────


async def test_air7_002_cancel_and_shutdown_during_fake_naver_prefetch(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)

    async def scenario():
        for how in ("cancel", "shutdown"):
            naver = FakeNaver(wait=True)  # gate가 열리지 않는다 = 영원히 대기
            runner = FakeRunner(mods.gr)
            runner.release.set()
            svc = _service(mods, tmp_path / how, runner, naver_prefetcher=naver)
            job = (await svc.start("020150", "롯데에너지머티리얼즈")).job
            await naver.entered.wait()
            if how == "cancel":
                await svc.cancel(job.job_id)
            else:
                await svc.shutdown()
            assert (job.status, job.error_kind) == ("cancelled", None), how
            assert job.events[-1].type == "cancelled", how
            assert runner.calls == [], how
            assert svc.active() is None

    await asyncio.wait_for(scenario(), 5)


async def test_air7_002_cancel_and_shutdown_during_real_naver_request(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)

    async def scenario():
        for how in ("cancel", "shutdown"):
            entered, never = asyncio.Event(), asyncio.Event()

            async def hang(request):  # 비동기 처리기 — 스레드를 쓰지 않는다
                entered.set()
                await never.wait()
                return __import__("httpx").Response(200, content=b"[]")

            transport, _ = _naver_recorder(respond=hang)
            runner = FakeRunner(mods.gr)
            runner.release.set()
            svc = _service(mods, tmp_path / how, runner, naver_prefetcher=_real_naver(mods, transport))
            job = (await svc.start("020150", "롯데에너지머티리얼즈")).job
            await entered.wait()
            if how == "cancel":
                await svc.cancel(job.job_id)
            else:
                await svc.shutdown()
            assert (job.status, job.error_kind) == ("cancelled", None), how
            assert job.events[-1].type == "cancelled", how
            assert runner.calls == [], how

    await asyncio.wait_for(scenario(), 5)


# ── AC-AIR7-003 — 끄기 스위치 ───────────────────────────────────────────────


async def test_air7_003_switch_off_skips_naver_prefetcher_and_writes_disabled_index(mods, tmp_path, monkeypatch):
    transport, requests = _naver_recorder((_NAVER_FIX / "recorded" / "020150_p1.json").read_bytes())
    real = _real_naver(mods, transport)
    calls = {"n": 0}

    async def spy(code, out_dir, *, code_validated=False):  # 작업 서비스가 수집기를 부른 횟수
        calls["n"] += 1
        return await real(code, out_dir, code_validated=code_validated)

    monkeypatch.setenv(_ENV_NAVER, "0")
    runner = FakeRunner(mods.gr)
    runner.release.set()
    job = await _run_job(_service(mods, tmp_path / "off", runner, naver_prefetcher=spy))
    index = _naver_index(tmp_path / "off", job)
    assert requests == []
    assert calls["n"] == 0
    assert index["outcome"] == "disabled" and index["articles"] == []
    assert len(runner.calls) == 1 and job.status == "done"

    # 대조: 변수 미설정이면 수집기 호출 1, 요청 1
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    runner2 = FakeRunner(mods.gr)
    runner2.release.set()
    job2 = await _run_job(_service(mods, tmp_path / "on", runner2, naver_prefetcher=spy))
    assert calls["n"] == 1
    assert len(requests) == 1
    assert _naver_index(tmp_path / "on", job2)["outcome"] == "complete"


# ── AC-AIR7-004 — 진행 이벤트 없음 ──────────────────────────────────────────


async def test_air7_004_naver_prefetch_adds_no_progress_event(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    stages = {}
    for variant in ("with_naver", "without_naver"):
        kw = {"naver_prefetcher": FakeNaver()} if variant == "with_naver" else {}
        runner = FakeRunner(mods.gr, events=("goose_start",))
        runner.release.set()
        job = await _run_job(_service(mods, tmp_path / variant, runner, prefetcher=FakePrefetcher(), **kw))
        stages[variant] = _progress_stages(job)
    assert stages["with_naver"] == stages["without_naver"] == ["dart_prefetch", "goose_start"]
    assert not [s for s in stages["with_naver"] if "naver" in str(s)]


# ── AC-AIR7-008 — 실패해도 goose는 진행 ─────────────────────────────────────


def _naver_failure(case):
    httpx = __import__("httpx")
    syn = _NAVER_FIX / "synthetic"

    def connect_error(request):
        raise httpx.ConnectError("refused", request=request)

    return {
        "connect_error": dict(respond=connect_error),
        "http_410": dict(body=b"gone", status=410),
        "http_500": dict(body=b"down", status=500),
        "not_json": dict(body=(syn / "not_json.txt").read_bytes()),
        "missing_items_path": dict(body=(syn / "missing_items_path.json").read_bytes()),
        "top_level_object": dict(body=(syn / "top_level_object.json").read_bytes()),
    }[case]


@pytest.mark.parametrize(
    "case", ["connect_error", "http_410", "http_500", "not_json", "missing_items_path", "top_level_object"]
)
async def test_air7_008_naver_failures_still_run_goose(mods, tmp_path, monkeypatch, case):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    transport, requests = _naver_recorder(**_naver_failure(case))
    runner = FakeRunner(mods.gr)
    runner.release.set()
    job = await _run_job(_service(mods, tmp_path, runner, naver_prefetcher=_real_naver(mods, transport)))
    assert len(requests) == 1
    assert len(runner.calls) == 1
    assert (job.status, job.error_kind) == ("done", None)
    index = _naver_index(tmp_path, job)
    assert index["outcome"] == "failed" and index["search"]["error"]


async def test_air7_008_naver_prefetcher_exception_does_not_stop_goose(mods, tmp_path, monkeypatch, caplog):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    runner = FakeRunner(mods.gr)
    runner.release.set()
    svc = _service(mods, tmp_path, runner, naver_prefetcher=FakeNaver(raise_exc=RuntimeError("naver boom")))
    with caplog.at_level("ERROR"):
        job = await _run_job(svc)
    assert len(runner.calls) == 1
    assert (job.status, job.error_kind) == ("done", None)
    recs = [r for r in caplog.records if r.levelname == "ERROR" and job.job_id in r.getMessage()]
    assert recs and isinstance(recs[0].exc_info[1], RuntimeError)


# ── AC-AIR7-015 — 종목코드 확인 기록 ────────────────────────────────────────


def _raise_check(code):
    raise RuntimeError("registry unavailable")


@pytest.mark.parametrize(
    "variant,check,expected",
    [("a_true", lambda c: True, True), ("b_false", lambda c: False, False),
     ("c_absent", None, False), ("d_raises", _raise_check, False)],
)
async def test_air7_015_code_validated_passed_to_index(mods, tmp_path, monkeypatch, variant, check, expected):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    transport, requests = _naver_recorder((_NAVER_FIX / "recorded" / "999999_p1.json").read_bytes())
    real = _real_naver(mods, transport)
    calls = {"n": 0}

    async def spy(code, out_dir, *, code_validated=False):
        calls["n"] += 1
        return await real(code, out_dir, code_validated=code_validated)

    kw = {"code_check": check} if check is not None else {}
    runner = FakeRunner(mods.gr)
    runner.release.set()
    job = await _run_job(_service(mods, tmp_path, runner, naver_prefetcher=spy, **kw))
    index = _naver_index(tmp_path, job)
    assert calls["n"] == 1 and len(requests) == 1
    assert index["outcome"] == "no_results" and index["search"]["item_count"] == 0
    assert index["code_validated"] is expected
    assert len(runner.calls) == 1 and job.status == "done"


async def test_air7_015_disabled_index_records_code_validated(mods, tmp_path, monkeypatch):
    monkeypatch.setenv(_ENV_NAVER, "0")
    transport, requests = _naver_recorder((_NAVER_FIX / "recorded" / "999999_p1.json").read_bytes())
    runner = FakeRunner(mods.gr)
    runner.release.set()
    job = await _run_job(_service(mods, tmp_path, runner, naver_prefetcher=_real_naver(mods, transport),
                                  code_check=lambda c: True))
    index = _naver_index(tmp_path, job)
    assert index["outcome"] == "disabled"
    assert index["code_validated"] is True
    assert requests == []


async def test_air7_015_production_code_check_uses_server_stock_list(mods, monkeypatch):
    # test_ai_report_service.py가 sys.modules에 my_chart.registry 스텁을 영구히 심는다(같은 세션에서 먼저
    # 돌면 이 검사가 스텁을 보게 된다). 이 테스트 동안만 지워 실제 서버 종목 목록을 읽게 한다(종료 때 복원)
    monkeypatch.delitem(sys.modules, "my_chart.registry", raising=False)
    monkeypatch.delitem(sys.modules, "backend.services.ai_report_service", raising=False)
    check = mods.gjs.get_service()._code_check
    assert await asyncio.wait_for(asyncio.to_thread(check, "020150"), 30) is True
    assert await asyncio.wait_for(asyncio.to_thread(check, "999999"), 30) is False
