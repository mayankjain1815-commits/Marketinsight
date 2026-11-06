"""Regression test: get_ticker must URL-encode the company name.

Yahoo's search endpoint treats an unescaped "&" in the query string as a
parameter separator.  Building the URL by hand therefore turns
``get_ticker("AT&T")`` into a search for ``q=AT``, whose first hit is the
unrelated "AT" ETF rather than AT&T (symbol "T").
"""
import importlib.util
import sys
import types
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _install_stubs():
    if "yfinance" not in sys.modules:
        yf = types.ModuleType("yfinance")
        yf.Ticker = object  # replaced by tests
        sys.modules["yfinance"] = yf

    if "requests" not in sys.modules:
        req = types.ModuleType("requests")
        req.get = lambda *a, **k: None
        sys.modules["requests"] = req

    if "langchain" not in sys.modules:
        langchain = types.ModuleType("langchain")
        langchain_tools = types.ModuleType("langchain.tools")

        def tool(name=None, description=None):
            def deco(fn):
                return fn
            return deco

        langchain_tools.tool = tool
        langchain.tools = langchain_tools
        sys.modules["langchain"] = langchain
        sys.modules["langchain.tools"] = langchain_tools


@pytest.fixture()
def tools_module(monkeypatch):
    _install_stubs()
    monkeypatch.syspath_prepend(str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location(
        "marketinsight_tools_ticker_under_test",
        REPO_ROOT / "MarketInsight" / "utils" / "tools.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _server_query(url, params):
    """Return the value Yahoo would see for the ``q`` parameter."""
    if params is not None:
        return params.get("q")
    return parse_qs(urlparse(url).query).get("q", [None])[0]


class _FakeResponse:
    status_code = 200

    def __init__(self, symbol):
        self._symbol = symbol

    def json(self):
        return {"quotes": [{"symbol": self._symbol}]}


def test_get_ticker_sends_full_company_name(tools_module, monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        query = _server_query(url, kwargs.get("params"))
        captured["query"] = query
        # Yahoo resolves the truncated query "AT" to the "AT" ETF, while the
        # full query "AT&T" resolves to AT&T's ticker, "T".
        return _FakeResponse("T" if query == "AT&T" else "AT")

    monkeypatch.setattr(tools_module.requests, "get", fake_get)

    result = tools_module.get_ticker("AT&T")

    assert captured["query"] == "AT&T"
    assert result == "T"
