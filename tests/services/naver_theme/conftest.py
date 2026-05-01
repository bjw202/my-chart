"""pykrx / pkg_resources 스텁 — 이 패키지의 테스트가 pykrx를 설치 없이 실행되도록."""

from __future__ import annotations

import sys
import types


def _stub(name: str) -> None:
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)


for _mod_name in ("pykrx", "pykrx.stock", "pkg_resources"):
    _stub(_mod_name)
