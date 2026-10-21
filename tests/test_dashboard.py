from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    return at


def test_dashboard_renders_without_exceptions(app):
    assert not app.exception, [e.value for e in app.exception]


def test_dashboard_header_metrics(app):
    got = {m.label: m.value for m in app.metric}
    assert got["Bookings"] == "119,209"
    assert got["Realized revenue"] == "EUR 25,986,912"
    assert got["Cancellation rate"] == "37.1%"
    assert got["Gross margin"] == "79.6%"


def test_sidebar_filters_recompute_the_header(app):
    app.sidebar.multiselect[1].set_value(["Direct"]).run()
    assert not app.exception, [e.value for e in app.exception]
    got = {m.label: m.value for m in app.metric}
    assert got["Bookings"] == "14,611"
    assert got["Cancellation rate"] == "17.5%"


def _keys(at):
    return [w.key for w in at.text_input]


def test_nl_sql_input_hidden_without_a_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Keep a developer's own gitignored .env from leaking into this assertion.
    monkeypatch.setattr("src.ai_insight.load_env_file", lambda path=".env": None)
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert "nl_q" not in _keys(at)


def test_nl_sql_input_shown_with_a_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-not-real")
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert "nl_q" in _keys(at)
    assert at.text_input(key="nl_q").value.startswith("Which distribution channel")
