"""Weryfikacja izolacji repo — brak plikow drugiej kampanii."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "pattern",
    [
        "ua_*.py",
        "tests/test_ua_*.py",
        ".github/workflows/ua_*.yml",
        ".github/workflows/sync-google-drive-ua.yml",
        "run_config/ua_*.json",
        "schedule/ua",
        "legacy",
    ],
)
def test_no_ua_campaign_artifacts(pattern: str) -> None:
    matches = list(ROOT.glob(pattern))
    assert not matches, f"Znaleziono artefakty UA/legacy w repo PL: {matches}"
