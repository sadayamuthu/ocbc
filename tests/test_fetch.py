"""Tests for ocbc.fetch."""

import argparse
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from ocbc.fetch import OCBC_CATALOG_URL, main


def _make_args(out: str) -> argparse.Namespace:
    return argparse.Namespace(out=out)


def _fake_response(data: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    return mock_resp


def test_fetch_writes_catalog_to_file():
    fake_data = {"count": 3, "controls": [{"id": 1}, {"id": 2}, {"id": 3}]}
    mock_resp = _fake_response(fake_data)

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = str(Path(tmpdir) / "catalog.json")
        args = _make_args(out_path)

        with patch("ocbc.fetch.requests.get", return_value=mock_resp) as mock_get:
            main(args)

        mock_get.assert_called_once_with(OCBC_CATALOG_URL, timeout=30)
        mock_resp.raise_for_status.assert_called_once()

        with open(out_path, encoding="utf-8") as f:
            written = json.load(f)

    assert written == fake_data


def test_fetch_prints_count_and_path(capsys):
    fake_data = {"count": 42, "controls": []}
    mock_resp = _fake_response(fake_data)

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = str(Path(tmpdir) / "catalog.json")
        args = _make_args(out_path)

        with patch("ocbc.fetch.requests.get", return_value=mock_resp):
            main(args)

    captured = capsys.readouterr()
    assert "42" in captured.out
    assert out_path in captured.out


def test_fetch_prints_question_mark_when_count_missing(capsys):
    fake_data = {"controls": []}  # no 'count' key
    mock_resp = _fake_response(fake_data)

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = str(Path(tmpdir) / "catalog.json")
        args = _make_args(out_path)

        with patch("ocbc.fetch.requests.get", return_value=mock_resp):
            main(args)

    captured = capsys.readouterr()
    assert "?" in captured.out


def test_fetch_prints_fetching_url(capsys):
    fake_data = {"count": 0, "controls": []}
    mock_resp = _fake_response(fake_data)

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = str(Path(tmpdir) / "catalog.json")
        args = _make_args(out_path)

        with patch("ocbc.fetch.requests.get", return_value=mock_resp):
            main(args)

    captured = capsys.readouterr()
    assert OCBC_CATALOG_URL in captured.out
