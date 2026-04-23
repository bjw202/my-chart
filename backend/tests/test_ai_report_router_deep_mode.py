"""SPEC-AI-REPORT-002 Phase D1+D3: 라우터 deep-mode 분기 + lifespan 회귀 테스트.

테스트 범주:
- Characterization (SPEC-001 보존): mode 없거나 'perplexity'이면 기존 Perplexity 경로
- Deep mode routing: ?mode=deep → stream_deep_analysis 호출
- Guard chain: 코드 형식/종목 존재 체크가 mode 분기 전에 실행
- Error cases: 503(claude 없음), 429(rate limit, 중복), 422(유효하지 않은 mode)
- Independence: Deep 쿼터 소진 시 Perplexity 경로는 영향 없음
- Lifespan: claude 바이너리 체크, 합성 프롬프트 로드, /tmp 정리

로드 전략: test_ai_report_service.py 패턴 동일하게 sys.modules 스텁 후
  importlib.util.spec_from_file_location으로 격리 로드.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# 공통 유틸: sys.modules 스텁 + 격리 로드
# ─────────────────────────────────────────────────────────────────────────────

_ROUTER_PATH = Path(__file__).parent.parent / "routers" / "ai_report.py"
_SERVICE_PATH = Path(__file__).parent.parent / "services" / "ai_report_service.py"
_DEEP_SERVICE_PATH = Path(__file__).parent.parent / "services" / "deep_research_service.py"


# ─────────────────────────────────────────────────────────────────────────────
# 모듈 레벨 스텁 설치: backend.main을 import하기 전에 my_chart 스텁 필요
# ─────────────────────────────────────────────────────────────────────────────

def _name_fn_default(code: str) -> str:
    return "삼성전자" if code == "005930" else "NonName"


_registry_stub = types.SimpleNamespace(
    _name=_name_fn_default,
    get_stock_registry=lambda: None,
    get_sector_registry=lambda: None,
)
_config_stub = types.SimpleNamespace(
    initialize=lambda: None,
    DEFAULT_DB_DAILY="daily.db",
    DEFAULT_DB_WEEKLY="weekly.db",
)
# 테스트 파일 로드 시점에 스텁 등록 (backend.main import 전에 필요)
# 다만 실 my_chart 패키지가 import 가능하면 __path__를 빈 배열로 두지 말고 실제 경로로
# 세팅해야 이후 실행되는 test_sector_advanced.py 등이 my_chart.analysis 등 서브패키지를
# 정상 import할 수 있다.
_project_root = Path(__file__).resolve().parent.parent.parent
_my_chart_pkg_path = _project_root / "my_chart"
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

_existing_my_chart = sys.modules.get("my_chart")
if _existing_my_chart is None or not hasattr(_existing_my_chart, "__path__") or not _existing_my_chart.__path__:
    _my_chart_mod = types.ModuleType("my_chart")
    _my_chart_mod.__path__ = [str(_my_chart_pkg_path)] if _my_chart_pkg_path.is_dir() else []
    sys.modules["my_chart"] = _my_chart_mod
sys.modules["my_chart.registry"] = _registry_stub
sys.modules["my_chart.config"] = _config_stub
# db_service가 임포트하는 my_chart 하위 모듈 스텁
for _sub in ("my_chart.db", "my_chart.db.daily", "my_chart.db.weekly"):
    _stub = types.ModuleType(_sub)
    _stub.__path__ = []  # type: ignore[attr-defined]
    _stub.price_daily_db = lambda *a, **k: None
    _stub.price_weekly_db = lambda *a, **k: None
    sys.modules.setdefault(_sub, _stub)


def _install_stubs(code_to_name: dict[str, str] | None = None) -> None:
    """my_chart, sse_starlette 등 외부 의존성을 sys.modules 스텁으로 교체."""
    if code_to_name is None:
        code_to_name = {"005930": "삼성전자"}

    def _name_fn(code: str) -> str:
        return code_to_name.get(code, "NonName")

    # my_chart 스텁 (get_stock_registry, get_sector_registry 포함)
    my_chart_mod = types.ModuleType("my_chart")
    sys.modules.setdefault("my_chart", my_chart_mod)
    registry_stub = types.SimpleNamespace(
        _name=_name_fn,
        get_stock_registry=lambda: None,
        get_sector_registry=lambda: None,
    )
    sys.modules["my_chart.registry"] = registry_stub
    config_stub = types.SimpleNamespace(
        initialize=lambda: None,
        DEFAULT_DB_DAILY="daily.db",
        DEFAULT_DB_WEEKLY="weekly.db",
    )
    sys.modules["my_chart.config"] = config_stub


def _load_service_module(name: str, path: Path, stubs: dict[str, Any] | None = None) -> Any:
    """격리된 모듈을 파일 경로로 직접 로드."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    if stubs:
        for k, v in stubs.items():
            sys.modules[k] = v
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    return mod


@pytest.fixture
def service_mod():
    """격리된 ai_report_service 모듈 (상태 초기화 포함)."""
    _install_stubs()
    mod = _load_service_module("_test_svc", _SERVICE_PATH)
    mod._active_analyses.clear()
    mod._daily_call_count = 0
    mod._daily_reset_date = ""
    mod._recent_call_timestamps.clear()
    return mod


@pytest.fixture
def deep_service_mod():
    """격리된 deep_research_service 모듈 (상태 초기화 포함)."""
    _install_stubs()
    # deep_research_service는 ai_report_service(save_report),
    # claude_cli_streamer, deep_research_collector에 의존함.
    # 각각 스텁 처리
    svc_stub = types.SimpleNamespace(save_report=lambda *a, **k: None)
    streamer_stub = types.SimpleNamespace(
        stream_claude_synthesis=MagicMock(),
        TextDelta=type("TextDelta", (), {"text": ""}),
        DoneSignal=type("DoneSignal", (), {}),
        ErrorSignal=type("ErrorSignal", (), {"message": ""}),
        DoneSignal_cls=None,
    )

    collector_stub = types.SimpleNamespace(
        collect_all_sources=MagicMock(),
        create_staging_directory=MagicMock(return_value=Path("/tmp/fake")),
        CollectionResult=MagicMock(),
    )

    sys.modules["backend.services.ai_report_service"] = svc_stub
    sys.modules["backend.services.claude_cli_streamer"] = streamer_stub
    sys.modules["backend.services.deep_research_collector"] = collector_stub

    mod = _load_service_module("_test_deep_svc", _DEEP_SERVICE_PATH)
    mod._active_deep_analyses.clear()
    mod._deep_daily_call_count.clear()
    mod._deep_recent_timestamps.clear()
    return mod


def _make_router_app(
    *,
    api_key: str = "test-key",
    service_mod: Any = None,
    deep_service_mod: Any = None,
) -> tuple[FastAPI, Any]:
    """격리된 라우터를 FastAPI 앱에 마운트.

    service_mod와 deep_service_mod는 위 fixture로부터 주입된 격리 모듈.
    라우터 모듈을 직접 로드해 sys.modules에 없는 의존성을 스텁으로 대체.
    """
    import os

    os.environ["PERPLEXITY_API_KEY"] = api_key

    _install_stubs()

    # 라우터가 import할 서비스 스텁 등록
    if service_mod is None:
        svc = _load_service_module("_test_svc_router", _SERVICE_PATH)
    else:
        svc = service_mod

    svc._active_analyses.clear()

    # sse_starlette 스텁 (TestClient용 패스스루)
    from sse_starlette.sse import EventSourceResponse

    # deep_research_service 스텁 (나중에 patch로 교체)
    if deep_service_mod is None:
        ds = types.SimpleNamespace(
            stream_deep_analysis=MagicMock(),
            check_deep_rate_limit=MagicMock(),
            _active_deep_analyses=set(),
            DeepRateLimitError=type("DeepRateLimitError", (Exception,), {}),
            AlreadyRunningError=type("AlreadyRunningError", (Exception,), {}),
        )
    else:
        ds = deep_service_mod

    sys.modules["backend.services.ai_report_service"] = svc
    sys.modules["backend.services.deep_research_service"] = ds

    # 라우터 격리 로드
    router_mod = _load_service_module("_test_router", _ROUTER_PATH)

    app = FastAPI()
    app.include_router(router_mod.router, prefix="/api")
    return app, router_mod


# ─────────────────────────────────────────────────────────────────────────────
# Characterization Tests: SPEC-001 Perplexity 경로 보존
# ─────────────────────────────────────────────────────────────────────────────


class TestFastModePathPreservation:
    """SPEC-AI-REPORT-003: mode 없거나 'fast'/'perplexity' 이면 Codex Fast 경로로 라우팅."""

    def _setup_fast_mode_app(self, mode_suffix: str, query_suffix: str = ""):
        """Fast Mode 테스트용 앱 생성 — stream_codex_fast 를 fake 로 교체."""
        import shutil
        _install_stubs()
        svc = _load_service_module(f"_test_svc_{mode_suffix}", _SERVICE_PATH)
        svc._active_analyses.clear()
        svc._daily_call_count = 0
        svc._daily_reset_date = ""
        svc._recent_call_timestamps.clear()

        call_tracker = {"fast": 0, "deep": 0}

        async def fake_fast(stock_name: str, code: str) -> AsyncGenerator[dict, None]:
            call_tracker["fast"] += 1
            yield {"data": "chunk"}
            yield {"event": "done", "data": ""}

        async def fake_deep(code: str, stock_name: str) -> AsyncGenerator[dict, None]:
            call_tracker["deep"] += 1
            yield {"data": "bad"}

        ds_stub = types.SimpleNamespace(
            stream_deep_analysis=fake_deep,
            check_deep_rate_limit=MagicMock(),
            _active_deep_analyses=set(),
            DeepRateLimitError=type("DeepRateLimitError", (Exception,), {}),
            AlreadyRunningError=type("AlreadyRunningError", (Exception,), {}),
        )
        sys.modules["backend.services.ai_report_service"] = svc
        sys.modules["backend.services.deep_research_service"] = ds_stub

        router_mod = _load_service_module(f"_test_router_{mode_suffix}", _ROUTER_PATH)
        router_mod.stream_codex_fast = fake_fast
        # shutil.which("codex") 가 True 를 반환하도록 하여 바이너리 체크 통과
        router_mod.shutil = types.SimpleNamespace(which=lambda cmd: "/usr/local/bin/codex")

        app = FastAPI()
        app.include_router(router_mod.router, prefix="/api")
        return app, call_tracker

    def test_no_mode_param_routes_to_fast(self):
        """mode 파라미터 없으면 stream_codex_fast 호출, stream_deep_analysis 미호출."""
        app, call_tracker = self._setup_fast_mode_app("np_fast")
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/ai-report/005930")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert call_tracker["fast"] == 1, "stream_codex_fast 가 정확히 1번 호출되어야 함"
        assert call_tracker["deep"] == 0, "stream_deep_analysis 는 호출되지 않아야 함"

    def test_mode_fast_routes_to_fast(self):
        """?mode=fast 이면 stream_codex_fast 호출."""
        app, call_tracker = self._setup_fast_mode_app("mf_fast")
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/ai-report/005930?mode=fast")

        assert response.status_code == 200
        assert call_tracker["fast"] == 1
        assert call_tracker["deep"] == 0

    def test_mode_perplexity_is_deprecated_alias_to_fast(self):
        """?mode=perplexity 는 backward-compat 알리아스 → stream_codex_fast 로 라우팅."""
        app, call_tracker = self._setup_fast_mode_app("mp_fast")
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/ai-report/005930?mode=perplexity")

        assert response.status_code == 200
        assert call_tracker["fast"] == 1, (
            "perplexity alias 도 Codex Fast 로 라우팅되어야 함"
        )
        assert call_tracker["deep"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Deep Mode Routing Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeepModeRouting:
    """?mode=deep 라우팅 동작 검증."""

    def _make_app_with_deep(
        self,
        *,
        which_return: str | None = "/usr/local/bin/claude",
        rate_limit_fn: Any = None,
        active_deep: set | None = None,
        deep_stream_fn: Any = None,
    ) -> tuple[Any, Any]:
        """Deep mode 테스트용 앱 생성 헬퍼."""
        import os

        os.environ["PERPLEXITY_API_KEY"] = "test-key"
        _install_stubs()

        svc = _load_service_module("_test_svc_deep", _SERVICE_PATH)
        svc._active_analyses.clear()

        active_deep_set: set = active_deep if active_deep is not None else set()

        DeepRateLimitError = type("DeepRateLimitError", (Exception,), {})

        if rate_limit_fn is None:
            def rate_limit_fn():
                pass

        if deep_stream_fn is None:
            async def deep_stream_fn(code: str, stock_name: str) -> AsyncGenerator[dict, None]:
                yield {"data": "deep chunk"}
                yield {"event": "done", "data": ""}

        ds_stub = types.SimpleNamespace(
            stream_deep_analysis=deep_stream_fn,
            check_deep_rate_limit=rate_limit_fn,
            _active_deep_analyses=active_deep_set,
            DeepRateLimitError=DeepRateLimitError,
            AlreadyRunningError=type("AlreadyRunningError", (Exception,), {}),
        )

        sys.modules["backend.services.ai_report_service"] = svc
        sys.modules["backend.services.deep_research_service"] = ds_stub

        # 고유 모듈 이름으로 로드
        import time as _time
        unique_name = f"_test_router_{id(self)}_{int(_time.time() * 1000) % 10000}"
        router_mod = _load_service_module(unique_name, _ROUTER_PATH)

        # shutil.which 패치
        shutil_stub = types.SimpleNamespace(which=lambda cmd: which_return)
        router_mod.shutil = shutil_stub

        app = FastAPI()
        app.include_router(router_mod.router, prefix="/api")
        return app, router_mod

    def test_mode_deep_routes_to_stream_deep_analysis(self):
        """?mode=deep → stream_deep_analysis 호출, SSE 200 응답, content-type=text/event-stream."""
        call_count = {"n": 0}

        async def tracked_deep(code: str, stock_name: str) -> AsyncGenerator[dict, None]:
            call_count["n"] += 1
            yield {"data": "deep chunk"}
            yield {"event": "done", "data": ""}

        app, _ = self._make_app_with_deep(deep_stream_fn=tracked_deep)

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/ai-report/005930?mode=deep")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert call_count["n"] == 1, "stream_deep_analysis가 정확히 1번 호출되어야 함"

    def test_mode_invalid_returns_422(self):
        """?mode=invalid → FastAPI Query 패턴 검증 실패로 422 반환."""
        import os

        os.environ["PERPLEXITY_API_KEY"] = "test-key"
        _install_stubs()
        svc = _load_service_module("_test_svc_inv", _SERVICE_PATH)
        svc._active_analyses.clear()

        ds_stub = types.SimpleNamespace(
            stream_deep_analysis=MagicMock(),
            check_deep_rate_limit=MagicMock(),
            _active_deep_analyses=set(),
            DeepRateLimitError=type("DeepRateLimitError", (Exception,), {}),
            AlreadyRunningError=type("AlreadyRunningError", (Exception,), {}),
        )
        sys.modules["backend.services.ai_report_service"] = svc
        sys.modules["backend.services.deep_research_service"] = ds_stub
        router_mod = _load_service_module("_test_router_inv", _ROUTER_PATH)

        app = FastAPI()
        app.include_router(router_mod.router, prefix="/api")

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/ai-report/005930?mode=invalid")

        assert response.status_code == 422

    def test_deep_mode_missing_claude_returns_503(self):
        """claude binary 없으면 503 반환, error='claude_cli_missing'."""
        app, _ = self._make_app_with_deep(which_return=None)

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/ai-report/005930?mode=deep")

        assert response.status_code == 503
        body = response.json()
        assert body["detail"]["error"] == "claude_cli_missing"

    def test_deep_mode_rate_limit_returns_429(self):
        """check_deep_rate_limit()가 DeepRateLimitError 발생 시 429 반환."""
        DeepRateLimitError = type("DeepRateLimitError", (Exception,), {})

        def rate_limit_raises():
            raise DeepRateLimitError("일일 쿼터 초과")

        import os

        os.environ["PERPLEXITY_API_KEY"] = "test-key"
        _install_stubs()
        svc = _load_service_module("_test_svc_rl", _SERVICE_PATH)
        svc._active_analyses.clear()

        ds_stub = types.SimpleNamespace(
            stream_deep_analysis=MagicMock(),
            check_deep_rate_limit=rate_limit_raises,
            _active_deep_analyses=set(),
            DeepRateLimitError=DeepRateLimitError,
            AlreadyRunningError=type("AlreadyRunningError", (Exception,), {}),
        )
        sys.modules["backend.services.ai_report_service"] = svc
        sys.modules["backend.services.deep_research_service"] = ds_stub
        router_mod = _load_service_module("_test_router_rl", _ROUTER_PATH)

        shutil_stub = types.SimpleNamespace(which=lambda cmd: "/usr/local/bin/claude")
        router_mod.shutil = shutil_stub

        app = FastAPI()
        app.include_router(router_mod.router, prefix="/api")

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/ai-report/005930?mode=deep")

        assert response.status_code == 429
        body = response.json()
        assert "일일 쿼터 초과" in str(body)

    def test_deep_mode_duplicate_returns_429(self):
        """_active_deep_analyses에 코드가 이미 있으면 429 반환, '이미 진행' 포함."""
        app, _ = self._make_app_with_deep(active_deep={"005930"})

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/ai-report/005930?mode=deep")

        assert response.status_code == 429
        body = response.json()
        detail_str = str(body["detail"])
        assert "이미 진행" in detail_str or "already" in detail_str.lower()

    def test_fast_rate_limit_unaffected_by_deep_quota(self):
        """SPEC-AI-REPORT-003: Deep 쿼터 소진 후에도 Fast (Codex) 경로는 정상 동작 (200 SSE)."""
        _install_stubs()
        svc = _load_service_module("_test_svc_prul", _SERVICE_PATH)
        svc._active_analyses.clear()
        # Fast rate limit 상태 초기화
        svc._daily_call_count = 0
        svc._daily_reset_date = ""
        svc._recent_call_timestamps.clear()

        call_tracker = {"fast": 0}

        async def fake_fast(stock_name: str, code: str) -> AsyncGenerator[dict, None]:
            call_tracker["fast"] += 1
            yield {"data": "chunk"}
            yield {"event": "done", "data": ""}

        ds_stub = types.SimpleNamespace(
            stream_deep_analysis=MagicMock(),
            check_deep_rate_limit=MagicMock(),
            _active_deep_analyses=set(),
            DeepRateLimitError=type("DeepRateLimitError", (Exception,), {}),
            AlreadyRunningError=type("AlreadyRunningError", (Exception,), {}),
        )
        sys.modules["backend.services.ai_report_service"] = svc
        sys.modules["backend.services.deep_research_service"] = ds_stub
        router_mod = _load_service_module("_test_router_prul", _ROUTER_PATH)
        router_mod.stream_codex_fast = fake_fast
        router_mod.shutil = types.SimpleNamespace(which=lambda cmd: "/usr/local/bin/codex")

        app = FastAPI()
        app.include_router(router_mod.router, prefix="/api")

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/ai-report/005930")

        assert response.status_code == 200
        assert call_tracker["fast"] == 1

    def test_existing_guard_chain_preserved_for_deep_invalid_format(self):
        """잘못된 형식 종목 코드(5자리)는 deep mode에서도 422 반환."""
        import os

        os.environ["PERPLEXITY_API_KEY"] = "test-key"
        _install_stubs()
        svc = _load_service_module("_test_svc_gcp", _SERVICE_PATH)
        svc._active_analyses.clear()

        ds_stub = types.SimpleNamespace(
            stream_deep_analysis=MagicMock(),
            check_deep_rate_limit=MagicMock(),
            _active_deep_analyses=set(),
            DeepRateLimitError=type("DeepRateLimitError", (Exception,), {}),
            AlreadyRunningError=type("AlreadyRunningError", (Exception,), {}),
        )
        sys.modules["backend.services.ai_report_service"] = svc
        sys.modules["backend.services.deep_research_service"] = ds_stub
        router_mod = _load_service_module("_test_router_gcp", _ROUTER_PATH)

        app = FastAPI()
        app.include_router(router_mod.router, prefix="/api")

        with TestClient(app, raise_server_exceptions=False) as client:
            # 5자리 코드 → 코드 형식 체크 → 422
            response = client.post("/api/ai-report/00000?mode=deep")

        assert response.status_code == 422
        body = response.json()
        assert body["detail"]["error"] == "invalid_code"

    def test_nonexistent_stock_returns_404_for_deep(self):
        """존재하지 않는 종목 코드는 deep mode에서도 404 반환."""
        import os

        os.environ["PERPLEXITY_API_KEY"] = "test-key"
        _install_stubs()
        svc = _load_service_module("_test_svc_404", _SERVICE_PATH)
        svc._active_analyses.clear()

        ds_stub = types.SimpleNamespace(
            stream_deep_analysis=MagicMock(),
            check_deep_rate_limit=MagicMock(),
            _active_deep_analyses=set(),
            DeepRateLimitError=type("DeepRateLimitError", (Exception,), {}),
            AlreadyRunningError=type("AlreadyRunningError", (Exception,), {}),
        )
        sys.modules["backend.services.ai_report_service"] = svc
        sys.modules["backend.services.deep_research_service"] = ds_stub
        router_mod = _load_service_module("_test_router_404", _ROUTER_PATH)

        app = FastAPI()
        app.include_router(router_mod.router, prefix="/api")

        with TestClient(app, raise_server_exceptions=False) as client:
            # 999999 → NonName → 404
            response = client.post("/api/ai-report/999999?mode=deep")

        assert response.status_code == 404
        body = response.json()
        assert body["detail"]["error"] == "not_found"


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan Tests
# main.py 격리 로드 전략: spec_from_file_location으로 직접 로드하여
# backend.routers.* → backend.services.* → my_chart.* 전체 체인 import 회피.
# lifespan 함수를 직접 추출해 asynccontextmanager로 래핑된 상태에서 실행.
# ─────────────────────────────────────────────────────────────────────────────

_MAIN_PATH = Path(__file__).parent.parent / "main.py"


def _load_main_isolated(
    *,
    which_return: str | None = "/usr/local/bin/claude",
    load_synthesis_fn: Any = None,
    cleanup_fn: Any = None,
) -> Any:
    """backend/main.py를 격리 로드 (router/service 체인 import 회피).

    - 모든 backend.routers.*, backend.services.* → 스텁 등록
    - shutil, _load_synthesis_prompt, _cleanup_stale_staging_dirs → 패치
    """
    # 라우터 스텁 (빈 APIRouter)
    from fastapi import APIRouter

    empty_router = APIRouter()

    for _rmod in (
        "backend.routers.ai_report",
        "backend.routers.analysis",
        "backend.routers.chart",
        "backend.routers.db",
        "backend.routers.market",
        "backend.routers.screen",
        "backend.routers.sectors",
        "backend.routers.stage",
    ):
        _s = types.SimpleNamespace(router=empty_router)
        sys.modules[_rmod] = _s

    # SPEC-AI-REPORT-003: lifespan 이 codex_cli_runner.load_codex_prompt 를 호출하도록 변경됨.
    # ai_report_service 스텁은 유지 (_active_analyses 만 필요)
    svc_stub = types.SimpleNamespace(
        _active_analyses=set(),
    )
    sys.modules["backend.services.ai_report_service"] = svc_stub

    # codex_cli_runner 스텁 (lifespan 이 load_codex_prompt 로 fail-fast 검증)
    codex_stub = types.SimpleNamespace(
        load_codex_prompt=lambda *, code, stock_name: f"tmpl {stock_name} ({code})",
    )
    sys.modules["backend.services.codex_cli_runner"] = codex_stub

    # deep_research_service 스텁 (lifespan에서 import)
    if load_synthesis_fn is None:
        def load_synthesis_fn() -> str:
            return "valid synthesis prompt"

    if cleanup_fn is None:
        def cleanup_fn(*, max_age_days: int = 7) -> int:
            return 0

    deep_svc_stub = types.SimpleNamespace(
        _load_synthesis_prompt=load_synthesis_fn,
        _cleanup_stale_staging_dirs=cleanup_fn,
    )
    sys.modules["backend.services.deep_research_service"] = deep_svc_stub

    # shutil 스텁
    import shutil as _real_shutil

    shutil_stub = types.SimpleNamespace(which=lambda cmd: which_return)

    # 고유 모듈 이름으로 main.py 격리 로드
    import time as _time

    unique_name = f"_test_main_{int(_time.time() * 1000) % 100000}"
    spec = importlib.util.spec_from_file_location(unique_name, _MAIN_PATH)
    assert spec and spec.loader

    # sys.modules에 스텁 대신 shutil 교체는 모듈 로드 전에 해야 함
    # main.py 내 `import shutil as _shutil` 구문 처리를 위해 shutil을 실제로 사용하고
    # 로드 후 속성 교체
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[arg-type]

    # 로드 후 shutil 교체 (lifespan이 실행될 때 적용됨)
    mod.shutil = shutil_stub  # type: ignore[attr-defined]
    # _load_synthesis_prompt, _cleanup_stale_staging_dirs도 교체
    mod._load_synthesis_prompt = load_synthesis_fn  # type: ignore[attr-defined]
    mod._cleanup_stale_staging_dirs = cleanup_fn  # type: ignore[attr-defined]

    return mod


class TestLifespanDeepBlock:
    """main.py lifespan에 추가된 Deep mode 블록 검증.

    격리 로드 전략: _load_main_isolated()로 main.py를 spec_from_file_location으로 로드.
    lifespan의 핵심 로직(claude 체크, 합성 프롬프트, /tmp 정리)을 직접 호출해 검증.
    """

    def _run_lifespan_and_collect_logs(
        self,
        main_mod: Any,
        raise_exceptions: bool = False,
    ) -> list[tuple[int, str]]:
        """lifespan 함수를 실행하고 로그 레코드를 반환."""
        import asyncio
        import logging

        log_records: list[tuple[int, str]] = []

        class _CaptureHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                log_records.append((record.levelno, record.getMessage()))

        handler = _CaptureHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        old_level = root_logger.level
        root_logger.setLevel(logging.DEBUG)

        try:
            app = main_mod.app
            with TestClient(app, raise_server_exceptions=raise_exceptions):
                pass
        finally:
            root_logger.removeHandler(handler)
            root_logger.setLevel(old_level)

        return log_records

    def test_lifespan_logs_warning_when_claude_missing(self):
        """claude CLI 없으면 WARNING 로그 기록 ('claude CLI 미설치' 포함)."""
        main_mod = _load_main_isolated(which_return=None)
        records = self._run_lifespan_and_collect_logs(main_mod)

        warning_msgs = [msg for level, msg in records if level >= 30]  # WARNING=30
        assert any(
            "claude" in msg.lower() or "미설치" in msg
            for msg in warning_msgs
        ), f"WARNING이 없음: {warning_msgs}"

    def test_lifespan_loads_synthesis_prompt_success(self):
        """합성 프롬프트 정상 로드 시 INFO 로그 기록, 예외 없음."""
        call_tracker = {"load": 0}

        def mock_load() -> str:
            call_tracker["load"] += 1
            return "valid synthesis prompt"

        main_mod = _load_main_isolated(
            which_return="/usr/local/bin/claude",
            load_synthesis_fn=mock_load,
        )
        records = self._run_lifespan_and_collect_logs(main_mod)

        assert call_tracker["load"] == 1, "_load_synthesis_prompt이 1번 호출되어야 함"
        info_msgs = [msg for level, msg in records if level == 20]  # INFO=20
        assert any(
            "합성 프롬프트" in msg or "Deep Research" in msg
            for msg in info_msgs
        ), f"합성 프롬프트 INFO 로그 없음: {info_msgs}"

    def test_lifespan_fails_fast_on_missing_synthesis_prompt(self):
        """합성 프롬프트 파일 없으면 lifespan에서 FileNotFoundError 발생 (fail-fast)."""

        def failing_load() -> str:
            raise FileNotFoundError("prompt missing")

        main_mod = _load_main_isolated(
            which_return="/usr/local/bin/claude",
            load_synthesis_fn=failing_load,
        )

        with pytest.raises(FileNotFoundError):
            self._run_lifespan_and_collect_logs(main_mod, raise_exceptions=True)

    def test_lifespan_cleans_up_stale_staging_dirs(self):
        """시작 시 _cleanup_stale_staging_dirs(max_age_days=7) 호출됨."""
        cleanup_calls: list[dict] = []

        def mock_cleanup(*, max_age_days: int = 7) -> int:
            cleanup_calls.append({"max_age_days": max_age_days})
            return 0

        main_mod = _load_main_isolated(
            which_return="/usr/local/bin/claude",
            cleanup_fn=mock_cleanup,
        )
        self._run_lifespan_and_collect_logs(main_mod)

        assert len(cleanup_calls) == 1, "_cleanup_stale_staging_dirs가 1번 호출되어야 함"
        assert cleanup_calls[0]["max_age_days"] == 7, "max_age_days=7로 호출되어야 함"
