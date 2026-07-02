import sys

import pytest

from src.core.config import Settings, load_settings


def test_load_settings_success(monkeypatch):
    # Already configured in conftest.py
    settings = load_settings()
    assert isinstance(settings, Settings)


def test_load_settings_validation_error_exits(monkeypatch, capsys):
    # Remove required DATABASE_URL
    monkeypatch.delenv("DATABASE_URL", raising=False)

    exit_called = False
    exit_code = None

    def mock_exit(code):
        nonlocal exit_called, exit_code
        exit_called = True
        exit_code = code
        # Raise SystemExit so the execution stops, but we catch it
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", mock_exit)

    with pytest.raises(SystemExit):
        load_settings()

    assert exit_called
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "FATAL: Missing required configuration." in captured.out
    assert "DATABASE_URL" in captured.out
    assert "Hint:" in captured.out
