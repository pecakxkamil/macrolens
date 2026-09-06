from datetime import date

from app.analytics import compute_all as compute_all_module


def test_compute_all_processes_every_configured_series(monkeypatch, capsys):
    calls = []

    monkeypatch.setattr(
        compute_all_module,
        "_load_series_config",
        lambda: {"PAYEMS": {}, "UNRATE": {}, "ICSA": {}},
    )
    monkeypatch.setattr(
        compute_all_module,
        "compute_features",
        lambda series_id, as_of_date=None: calls.append((series_id, as_of_date)),
    )

    summary = compute_all_module.compute_all()

    assert calls == [("PAYEMS", None), ("UNRATE", None), ("ICSA", None)]
    assert summary == {
        "successful_series": ["PAYEMS", "UNRATE", "ICSA"],
        "failed_series": [],
    }

    output = capsys.readouterr().out
    assert "Batch feature computation completed." in output
    assert "Successful: 3" in output
    assert "Failed: 0" in output
    assert "Failed series:" not in output


def test_compute_all_continues_after_failure(monkeypatch, capsys):
    def fake_compute_features(series_id, as_of_date=None):
        if series_id == "UNRATE":
            raise RuntimeError("sample failure")

    monkeypatch.setattr(
        compute_all_module,
        "_load_series_config",
        lambda: {"PAYEMS": {}, "UNRATE": {}, "ICSA": {}},
    )
    monkeypatch.setattr(
        compute_all_module,
        "compute_features",
        fake_compute_features,
    )

    summary = compute_all_module.compute_all()

    assert summary == {
        "successful_series": ["PAYEMS", "ICSA"],
        "failed_series": [("UNRATE", "sample failure")],
    }

    output = capsys.readouterr().out
    assert "Successful: 2" in output
    assert "Failed: 1" in output
    assert "- PAYEMS" in output
    assert "- ICSA" in output
    assert "- UNRATE: sample failure" in output


def test_compute_all_passes_shared_as_of_date(monkeypatch):
    calls = []
    as_of_date = date(2026, 9, 4)

    monkeypatch.setattr(
        compute_all_module,
        "_load_series_config",
        lambda: {"PAYEMS": {}, "UNRATE": {}},
    )
    monkeypatch.setattr(
        compute_all_module,
        "compute_features",
        lambda series_id, as_of_date=None: calls.append((series_id, as_of_date)),
    )

    compute_all_module.compute_all(as_of_date)

    assert calls == [("PAYEMS", as_of_date), ("UNRATE", as_of_date)]
