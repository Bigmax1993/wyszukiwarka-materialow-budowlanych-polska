# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

import pytest

from pl_claude_prompts import build_personalized_inquiry_email_prompt_pl
from pl_materialy_inquiry_email_pl import DEFAULT_INQUIRY_PHONE_PL, DEFAULT_INQUIRY_SENDER_NAME_PL


def test_prompt_polish_personalization():
    p = build_personalized_inquiry_email_prompt_pl(
        company_name="Hurtownia Budmarket Kraków",
        website="https://budmarket.krakow.pl",
        wojewodztwo="malopolskie",
        materials="cegła, bloczek",
        page_snippet="Sprzedaż cegły i bloczków hurtowo w Krakowie",
        discovery_wojewodztwo="malopolskie",
    )
    assert "Hurtownia Budmarket Kraków" in p
    assert "polsk" in p.lower()
    assert "cegła" in p or "bloczek" in p
    assert "OBIEKT BUDOWY" in p
    assert "REGION DISCOVERY" in p


def test_prompt_no_mfg_branding(monkeypatch):
    monkeypatch.setenv("MAIL_SENDER_NAME", "Testowy Menedzer")
    monkeypatch.setenv("INQUIRY_COMPANY_NAME", " ")
    monkeypatch.setenv("INQUIRY_PHONE", "516513965")
    monkeypatch.setenv("INQUIRY_WEBSITE", " ")
    p = build_personalized_inquiry_email_prompt_pl(company_name="Test Sp. z o.o.")
    lowered = p.lower()
    assert "mfg" not in lowered
    assert "fliesen" not in lowered
    assert "moderner" not in lowered


def test_prompt_includes_pl_phone_and_sender(monkeypatch):
    from pl_materialy_inquiry_email_pl import inquiry_phone, inquiry_sender_name

    monkeypatch.setenv("MAIL_SENDER_NAME", "Maksym Swinczak Tel.+4915223655399")
    monkeypatch.setenv("INQUIRY_PHONE", "+49 1522 3655 399")
    monkeypatch.setenv("INQUIRY_COMPANY_NAME", " ")
    monkeypatch.setenv("INQUIRY_WEBSITE", " ")
    p = build_personalized_inquiry_email_prompt_pl(
        company_name="Test Sp. z o.o.",
        discovery_wojewodztwo="mazowieckie",
    )
    assert DEFAULT_INQUIRY_PHONE_PL in p
    assert inquiry_sender_name() in p
    assert DEFAULT_INQUIRY_SENDER_NAME_PL in p
    assert inquiry_phone() == DEFAULT_INQUIRY_PHONE_PL
    assert "1522" not in p


def test_prompt_forbids_attachments():
    p = build_personalized_inquiry_email_prompt_pl(company_name="Test")
    assert "załącznik" in p.lower() or "plik" in p.lower()


def test_prompt_requires_json_output():
    p = build_personalized_inquiry_email_prompt_pl(company_name="Test")
    assert '"subject"' in p
    assert '"body"' in p


def test_prompt_requires_paragraph_layout():
    p = build_personalized_inquiry_email_prompt_pl(company_name="Test")
    assert "FORMAT LISTU" in p
    assert "\\n\\n" in p
    assert "Z poważaniem," in p


def test_cached_inquiry_without_construction_address_is_ignored():
    from pl_claude_inquiry_email import _cached_inquiry_is_usable

    assert not _cached_inquiry_is_usable(
        {"subject": "Test", "body": "Treść bez adresu budowy."}
    )


def test_cached_inquiry_with_verified_address_is_reused():
    from pl_claude_inquiry_email import _cached_inquiry_is_usable
    from pl_regional_construction_refs import pick_construction_project

    project = pick_construction_project("malopolskie", seed="demo")
    body = f"Budujemy obiekt pod adresem {project.address_pl}."
    assert _cached_inquiry_is_usable(
        {
            "subject": "Test",
            "body": body,
            "construction_address": project.address_pl,
        }
    )


def test_require_claude_raises_without_api_key(monkeypatch):
    from pl_claude_inquiry_email import claude_generate_inquiry_email_pl

    monkeypatch.setattr(
        "pl_claude_inquiry_email.get_anthropic_api_key",
        lambda: "",
    )
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        claude_generate_inquiry_email_pl(
            "Test",
            logging.getLogger("test"),
            {},
            require=True,
        )
