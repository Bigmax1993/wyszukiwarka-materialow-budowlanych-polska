# -*- coding: utf-8 -*-
from __future__ import annotations

from pl_regional_sender_context import (
    build_regional_sender_instructions_pl,
    resolve_discovery_wojewodztwo,
    wojewodztwo_primary_city_pl,
)


def test_resolve_discovery_prefers_discovery_bundesland():
    key = resolve_discovery_wojewodztwo(
        {"discovery_bundesland": "malopolskie", "bundesland": "slaskie"}
    )
    assert key == "malopolskie"


def test_primary_city_mazowieckie():
    assert wojewodztwo_primary_city_pl("mazowieckie") == "Warszawa"


def test_regional_sender_mentions_construction_block():
    text = build_regional_sender_instructions_pl(
        "dolnoslaskie",
        sender_name="Maksym Swinczak",
        sender_phone="516513965",
        construction_project_block="OBIEKT BUDOWY\n• Adres: Wrocław, ul. Test 1",
    )
    assert "REGION DISCOVERY" in text
    assert "Wrocław" in text or "dolnoslaskie" in text
    assert "OBIEKT BUDOWY" in text
    assert "516513965" in text
    assert "Maksym Swinczak" in text
    assert "średni" in text.lower()


def test_regional_sender_requires_real_company():
    text = build_regional_sender_instructions_pl(
        "dolnoslaskie",
        sender_name="Maksym Swinczak",
        sender_phone="516513965",
    )
    assert "REALNĄ" in text or "istniejącą" in text.lower() or "ISTNIEJĄCĄ" in text
    assert "NIE wymyślaj" in text or "fikcyjnych" in text.lower()
