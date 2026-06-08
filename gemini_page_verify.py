# -*- coding: utf-8 -*-
"""
Gemini: klasyfikacja strony www względem szablonowego słownika kampanii GU.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from campaign_keyword_profile import (
    GEMINI_REJECT_PRIMARY_ROLES,
    gu_required_keywords_sample,
    negative_keywords_sample,
    retail_chain_keywords_sample,
    retail_context_keywords_sample,
)
from retail_store_builder_filter import (
    REQUIRED_RETAIL_CHAIN_KEYWORDS,
    detect_required_retail_chains,
    has_required_retail_chain_mention,
    is_excluded_non_gu_role,
    is_generalunternehmer,
    is_media_publisher_contact,
    is_retail_store_operator_contact,
)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

_REJECT_ROLES_NORMALIZED = {r.lower() for r in GEMINI_REJECT_PRIMARY_ROLES}


def _match_keywords_in_text(text: str, keywords: tuple[str, ...] | list[str]) -> list[str]:
    low = (text or "").lower()
    found: list[str] = []
    for kw in keywords:
        k = (kw or "").strip().lower()
        if k and k in low and kw.strip() not in found:
            found.append(kw.strip())
    return found


def hard_reject_page_context(
    *,
    url: str = "",
    name: str = "",
    page_text: str = "",
) -> tuple[bool, str]:
    """Twarde NO-GO przed/po Gemini — operator, media, role nie-GU."""
    blob = " ".join([name, url, page_text]).lower()
    if is_retail_store_operator_contact(url=url, text=blob):
        return True, "einzelhandel_betrieb_kein_bau"
    if is_media_publisher_contact(url=url, name=name, text=blob):
        return True, "medienportal"
    if is_excluded_non_gu_role(blob):
        return True, "excluded_non_gu_role"
    return False, ""


def build_gemini_page_verify_prompt(
    company_name: str,
    website: str,
    page_text: str,
    *,
    max_chars: int = 8000,
) -> str:
    snippet = (page_text or "")[:max_chars]
    return (
        "Du bist strenger Prüfer für B2B-Outreach an Generalunternehmer (GU) "
        "im Filialbau / Supermarktbau in Deutschland.\n\n"
        "Bewerte den Website-Auszug anhand dieser Kampagnen-Schlüsselwörter:\n\n"
        f"[WYMAGANE GU]\n{', '.join(gu_required_keywords_sample())}\n\n"
        f"[KONTEKST RETAIL / FILIALBAU]\n{', '.join(retail_context_keywords_sample())}\n\n"
        f"[SIECI HANDLOWE — Projekte]\n{', '.join(retail_chain_keywords_sample())}\n\n"
        f"[ODRZUĆ jeśli dominiert]\n{', '.join(negative_keywords_sample())}\n\n"
        f"Firma: {company_name}\nWebseite: {website}\n\n"
        "Antwort NUR als JSON (kein Markdown):\n"
        "{\n"
        '  "matched_gu_keywords": ["generalunternehmer"],\n'
        '  "matched_retail_keywords": ["filialbau"],\n'
        '  "matched_chains": ["rewe"],\n'
        '  "matched_negative_keywords": [],\n'
        '  "is_gu": true,\n'
        '  "has_retail_context": true,\n'
        '  "primary_role": "Generalunternehmer",\n'
        '  "reason": "kurz DE max 2 Sätze"\n'
        "}\n\n"
        f"Auszug:\n{snippet or '(leer)'}"
    )


def parse_gemini_page_verify_response(text: str) -> dict:
    raw = (text or "").strip()
    match = _JSON_BLOCK_RE.search(raw)
    payload = match.group(0) if match else raw
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Gemini page verify: not a JSON object")

    def _list(key: str) -> list[str]:
        val = data.get(key) or []
        if not isinstance(val, list):
            return []
        return [str(x).strip() for x in val if str(x).strip()]

    return {
        "matched_gu_keywords": _list("matched_gu_keywords"),
        "matched_retail_keywords": _list("matched_retail_keywords"),
        "matched_chains": [c.lower() for c in _list("matched_chains")],
        "matched_negative_keywords": _list("matched_negative_keywords"),
        "is_gu": bool(data.get("is_gu")),
        "has_retail_context": bool(data.get("has_retail_context")),
        "primary_role": str(data.get("primary_role") or "").strip(),
        "reason": str(data.get("reason") or "").strip(),
    }


def apply_gemini_page_verdict(
    gemini: dict,
    *,
    page_text: str,
    serper_blob: str = "",
    require_generalunternehmer: bool = True,
) -> tuple[bool, str, list[str]]:
    """
    Werdykt z JSON Gemini + guardrails na tekście strony.
    Zwraca (verified, reason, retail_chains).
    """
    blob = " ".join([page_text or "", serper_blob or ""]).lower()
    hard, hard_reason = hard_reject_page_context(page_text=blob)
    if hard:
        return False, hard_reason, []

    neg = gemini.get("matched_negative_keywords") or []
    if neg:
        return False, f"gemini_negative:{neg[0]}", gemini.get("matched_chains") or []

    role = (gemini.get("primary_role") or "").strip()
    if role and role.lower() in _REJECT_ROLES_NORMALIZED:
        return False, f"gemini_role:{role}", gemini.get("matched_chains") or []

    if not gemini.get("is_gu"):
        return False, "gemini_kein_gu", gemini.get("matched_chains") or []

    if require_generalunternehmer:
        gu_text, _ = is_generalunternehmer(blob)
        gu_json = bool(gemini.get("matched_gu_keywords"))
        if not gu_text and not gu_json:
            return False, "kein_generalunternehmer", gemini.get("matched_chains") or []

    if not gemini.get("has_retail_context"):
        return False, "gemini_kein_retail", gemini.get("matched_chains") or []

    required_set = set(REQUIRED_RETAIL_CHAIN_KEYWORDS)
    gemini_chains = [
        c.lower()
        for c in (gemini.get("matched_chains") or [])
        if c and c.lower() in required_set
    ]
    blob_chains = detect_required_retail_chains(blob)
    chains = list(dict.fromkeys(gemini_chains + blob_chains))
    if not chains and not has_required_retail_chain_mention(blob):
        return False, "keine_handelskette", []

    reason = (gemini.get("reason") or "gemini_gu_retail").strip()
    return True, f"gemini:{reason[:120]}", chains


def gemini_verify_company_page(
    company_name: str,
    website: str,
    page_text: str,
    logger,
    cache: dict | None,
    *,
    gemini_generate_text: Callable,
    api_key: str,
    cache_key: str = "",
    serper_blob: str = "",
    require_generalunternehmer: bool = True,
) -> dict | None:
    """Wywołanie Gemini; None gdy brak API lub błąd."""
    if not api_key:
        return None

    verify_cache = (cache or {}).setdefault("gemini_page_verify", {})
    if cache_key and cache_key in verify_cache:
        return dict(verify_cache[cache_key])

    hard, hard_reason = hard_reject_page_context(
        url=website, name=company_name, page_text=page_text
    )
    if hard:
        out = {
            "verified": False,
            "verification_reason": hard_reason,
            "retail_chains": [],
            "gemini": {},
        }
        if cache_key:
            verify_cache[cache_key] = out
        return out

    prompt = build_gemini_page_verify_prompt(company_name, website, page_text)
    try:
        text, model = gemini_generate_text(prompt, logger, api_key, cache=cache)
        logger.info("Gemini page verify, model=%s", model)
        parsed = parse_gemini_page_verify_response(text)
    except Exception as exc:
        logger.warning("Gemini page verify: %s", exc)
        return None

    verified, reason, chains = apply_gemini_page_verdict(
        parsed,
        page_text=page_text,
        serper_blob=serper_blob,
        require_generalunternehmer=require_generalunternehmer,
    )
    gu_ok, gu_marker = is_generalunternehmer(
        " ".join([page_text, serper_blob, " ".join(parsed.get("matched_gu_keywords") or [])])
    )
    out = {
        "verified": verified,
        "verification_reason": reason,
        "retail_chains": chains,
        "is_gu": gu_ok,
        "gu_marker": gu_marker,
        "gemini": parsed,
    }
    if cache_key:
        verify_cache[cache_key] = out
    return out
