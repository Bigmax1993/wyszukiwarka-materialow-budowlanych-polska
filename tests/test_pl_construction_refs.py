# -*- coding: utf-8 -*-
from __future__ import annotations

from pl_regional_construction_refs import (
    address_present_in_body,
    extract_city_from_address_pl,
    inject_construction_project_context,
    pick_construction_project,
)


def test_pick_project_for_malopolskie_has_real_address():
    project = pick_construction_project("malopolskie", seed="supplier-a")
    assert project.address_pl.startswith("Kraków") or "Kraków" in project.address_pl or "Tarnów" in project.address_pl
    assert "ul." in project.address_pl


def test_address_present_detects_full_address():
    project = pick_construction_project("mazowieckie", seed="x")
    body = f"Budujemy obiekt pod adresem {project.address_pl}."
    assert address_present_in_body(body, project.address_pl)


def test_inject_adds_verified_address_when_missing():
    project = pick_construction_project("pomorskie", seed="supplier-b")
    body = "Szanowni Państwo,\n\nProśba o cennik.\n\nZ poważaniem,\nTest"
    out = inject_construction_project_context(body, project)
    assert address_present_in_body(out, project.address_pl)
    assert project.name_pl in out


def test_extract_city_from_address():
    assert extract_city_from_address_pl("Warszawa, ul. Marszałkowska 1") == "Warszawa"
    assert extract_city_from_address_pl("Kraków, ul. Floriańska 2") == "Kraków"


def test_pick_project_prefers_supplier_city_in_wojewodztwo():
    project = pick_construction_project(
        "dolnoslaskie",
        seed="demo",
        prefer_city="Głogów",
    )
    assert "Głogów" in project.address_pl


def test_pick_project_for_warszawa_supplier_uses_warszawa_address():
    project = pick_construction_project(
        "mazowieckie",
        seed="demo",
        prefer_city="Warszawa",
    )
    assert "Warszawa" in project.address_pl


def test_glogow_refs_are_real_public_projects():
    names = {
        pick_construction_project("dolnoslaskie", seed=s, prefer_city="Głogów").name_pl
        for s in ("a", "b", "c", "d", "e", "f")
    }
    assert names & {"Park Głowackiego", "Nowy Piastów", "Osiedle SIM Żurawia"}
