# -*- coding: utf-8 -*-
"""Claude Sonnet: weryfikacja kontekstu strony www (GU / Filialbau / sieci handlowe)."""
from __future__ import annotations

from typing import Callable

from claude_client import claude_generate_text
from scraper_env import get_anthropic_api_key
from gemini_page_verify import (
    apply_gemini_page_verdict,
    build_gemini_page_verify_prompt,
    hard_reject_page_context,
    parse_gemini_page_verify_response,
)
from retail_store_builder_filter import is_generalunternehmer


def claude_verify_company_page(
    company_name: str,
    website: str,
    page_text: str,
    logger,
    cache: dict | None,
    *,
    cache_key: str = "",
    serper_blob: str = "",
    require_generalunternehmer: bool = True,
    on_step: Callable[[str], None] | None = None,
) -> dict | None:
    """Czyta stronę (tekst) i zwraca werdykt JSON; None przy braku API lub błędzie."""
    api_key = get_anthropic_api_key()
    if not api_key:
        return None

    verify_cache = (cache or {}).setdefault("claude_page_verify", {})
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
            "claude": {},
        }
        if cache_key:
            verify_cache[cache_key] = out
        return out

    prompt = build_gemini_page_verify_prompt(company_name, website, page_text)
    try:
        text, model = claude_generate_text(
            prompt, logger, api_key, cache=cache, on_step=on_step
        )
        logger.info("Claude page verify, model=%s", model)
        parsed = parse_gemini_page_verify_response(text)
    except Exception as exc:
        logger.warning("Claude page verify: %s", exc)
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
        "verification_reason": reason.replace("gemini", "claude", 1) if reason.startswith("gemini") else f"claude:{reason}",
        "retail_chains": chains,
        "is_gu": gu_ok,
        "gu_marker": gu_marker,
        "claude": parsed,
    }
    if cache_key:
        verify_cache[cache_key] = out
    return out
