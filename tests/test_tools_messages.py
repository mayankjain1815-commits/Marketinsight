"""Regression test: tool "no data" messages must interpolate the ticker.

The tools module is imported with stub third-party dependencies so the test
runs without network access or heavy packages.
"""
import importlib.util
import sys
import types
from pathlib import Path

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
        "marketinsight_tools_under_test",
        REPO_ROOT / "MarketInsight" / "utils" / "tools.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeStock:
    def __init__(self, ticker):
        self.info = None
        self.news = None


def test_company_info_message_interpolates_ticker(tools_module, monkeypatch):
    monkeypatch.setattr(tools_module.yf, "Ticker", lambda ticker: _FakeStock(ticker))
    result = tools_module.get_company_info("AAPL")
    assert "AAPL" in result
    assert "{ticker}" not in result


def test_stock_news_message_interpolates_ticker(tools_module, monkeypatch):
    monkeypatch.setattr(tools_module.yf, "Ticker", lambda ticker: _FakeStock(ticker))
    result = tools_module.get_stock_news("MSFT")
    assert "MSFT" in result
    assert "{ticker}" not in result
