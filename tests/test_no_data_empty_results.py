"""Regression test: empty yfinance results must return the "no data" message.

yfinance reports "nothing found" with empty containers (``[]`` for news,
``{}`` for info, and empty ``DataFrame``/``Series`` objects for tabular
data), never with ``None``.  Converting an empty frame with ``.to_dict()``
still yields a truthy dict when the frame has columns, so checking the
converted value against ``None`` can never detect the empty result.  The
tools therefore reported success with an empty payload instead of the
documented ``"No ... available for <ticker>"`` message.
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
        "marketinsight_tools_empty_results_under_test",
        REPO_ROOT / "MarketInsight" / "utils" / "tools.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Frame:
    """Minimal stand-in for a pandas DataFrame / Series."""

    def __init__(self, data, empty):
        self._data = data
        self.empty = empty

    def to_dict(self):
        return self._data


EMPTY_FRAME = _Frame({"Open": {}}, empty=True)
EMPTY_SERIES = _Frame({}, empty=True)


class _EmptyStock:
    info = {}
    news = []
    dividends = EMPTY_SERIES
    splits = EMPTY_SERIES
    balance_sheet = EMPTY_FRAME
    financials = EMPTY_FRAME
    cashflow = EMPTY_FRAME
    institutional_holders = EMPTY_FRAME
    major_holders = EMPTY_FRAME
    mutualfund_holders = EMPTY_FRAME
    insider_transactions = EMPTY_FRAME
    recommendations = EMPTY_FRAME
    recommendations_summary = EMPTY_FRAME

    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, start=None, end=None):
        return EMPTY_FRAME


CASES = [
    ("get_historical_data", ("AAPL", "2024-01-01", "2024-01-31"), "No historical data available for AAPL"),
    ("get_stock_news", ("AAPL",), "No news available for AAPL"),
    ("get_balance_sheet", ("AAPL",), "No balance sheet available for AAPL"),
    ("get_income_statement", ("AAPL",), "No income statement available for AAPL"),
    ("get_cash_flow", ("AAPL",), "No cash flow available for AAPL"),
    ("get_company_info", ("AAPL",), "No company info available for AAPL"),
    ("get_dividends", ("AAPL",), "No dividends available for AAPL"),
    ("get_splits", ("AAPL",), "No stock splits available for AAPL"),
    ("get_institutional_holders", ("AAPL",), "No institutional holders available for AAPL"),
    ("get_major_shareholders", ("AAPL",), "No major share holders available for AAPL"),
    ("get_mutual_fund_holders", ("AAPL",), "No mutual fund holders available for AAPL"),
    ("get_insider_transactions", ("AAPL",), "No insider transactions available for AAPL"),
    ("get_analyst_recommendations", ("AAPL",), "No analyst recommendations available for AAPL"),
    ("get_analyst_recommendations_summary", ("AAPL",), "No analyst recommendations summary available for AAPL"),
]


@pytest.mark.parametrize("tool_name,args,expected", CASES)
def test_empty_result_returns_no_data_message(tools_module, monkeypatch, tool_name, args, expected):
    monkeypatch.setattr(tools_module.yf, "Ticker", _EmptyStock)

    result = getattr(tools_module, tool_name)(*args)

    assert result == expected


class _PopulatedStock:
    info = {"symbol": "AAPL"}
    news = [{"title": "Apple ships something"}]
    dividends = _Frame({"2024-01-01": 0.24}, empty=False)
    splits = _Frame({"2024-01-01": 4.0}, empty=False)
    balance_sheet = _Frame({"2024": {"Total Assets": 1}}, empty=False)
    financials = _Frame({"2024": {"Total Revenue": 1}}, empty=False)
    cashflow = _Frame({"2024": {"Operating Cash Flow": 1}}, empty=False)
    institutional_holders = _Frame({"Holder": {"Shares": 1}}, empty=False)
    major_holders = _Frame({"0": {"Value": "10%"}}, empty=False)
    mutualfund_holders = _Frame({"Holder": {"Shares": 1}}, empty=False)
    insider_transactions = _Frame({"Insider": {"Shares": 1}}, empty=False)
    recommendations = _Frame({"period": {"strongBuy": 1}}, empty=False)
    recommendations_summary = _Frame({"period": {"strongBuy": 1}}, empty=False)

    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, start=None, end=None):
        return _Frame({"Open": {"2024-01-02": 1.0}}, empty=False)


@pytest.mark.parametrize("tool_name,args", [(name, args) for name, args, _ in CASES])
def test_non_empty_result_is_still_returned(tools_module, monkeypatch, tool_name, args):
    monkeypatch.setattr(tools_module.yf, "Ticker", _PopulatedStock)

    result = getattr(tools_module, tool_name)(*args)

    assert not isinstance(result, str) or not result.startswith("No ")
    assert result
