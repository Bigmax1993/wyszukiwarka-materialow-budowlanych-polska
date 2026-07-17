# -*- coding: utf-8 -*-
"""Claude: naturalne maile przypominające PL (akapity, ludzki ton)."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from claude_client import claude_generate_text
from pl_claude_prompts import build_reminder_email_prompt_pl
from scraper_env import ENV_USE_CLAUDE_REPLY_INTELLIGENCE, get_anthropic_api_key, get_env_value


def _claude_reminders_enabled() -> bool:
    raw = get_env_value(ENV_USE_CLAUDE_REPLY_INTELLIGENCE, "1").strip().lower()
    return raw not in ("0", "false", "no", "off", "nie")


def _strip_signature_from_intro(text: str) -> str:
    """Usuń podpis, jeśli model dodał go mimo instrukcji."""
    lines = (text or "").splitlines()
    out: list[str] = []
    for line in lines:
        low = line.strip().lower()
        if low.startswith(("z poważaniem", "z powazaniem", "pozdrawiam", "pozdrawiam serdecznie")):
            break
        if "swinczakdata" in low or re.search(r"\b516\s*513\s*965\b", line):
            break
        out.append(line)
    return "\n".join(out).strip()


def _normalize_paragraphs(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Jedna linia → podziel na zdania do dwóch akapitów, jeśli brak akapitów
    if "\n\n" not in text and len(text) > 180:
        parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=2)
        if len(parts) >= 2:
            text = f"{parts[0]} {parts[1]}".strip()
            if len(parts) > 2:
                text = f"{text}\n\n{' '.join(parts[2:]).strip()}"
    return text


def _parse_reminder_intro_json(text: str) -> str:
    match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
    raw = match.group(0) if match else (text or "")
    parsed: dict[str, Any] = json.loads(raw)
    intro = str(parsed.get("intro") or parsed.get("body") or "").strip()
    if not intro:
        raise ValueError("Claude zwróciło pusty intro")
    return intro


def claude_generate_reminder_intro_pl(
    contact: dict,
    logger: logging.Logger | None,
    cache: dict | None,
    *,
    reminder_number: int = 1,
    cache_key: str = "",
) -> str | None:
    """
    Generuje naturalną treść przypomnienia (2–3 akapity).
    Zwraca sam intro (bez podpisu i cytatu) lub None przy braku API / błędzie.
    """
    if not _claude_reminders_enabled():
        return None
    api_key = get_anthropic_api_key()
    if not api_key:
        return None

    company = (
        contact.get("company_name_clean")
        or contact.get("company_name")
        or contact.get("nazwa")
        or "Państwo"
    ).strip()
    sent_raw = str(contact.get("email_sent_at") or "")
    sent_date = sent_raw[:10] if sent_raw else ""
    orig_subj = str(
        contact.get("email_subject_sent") or contact.get("email_subject") or ""
    ).strip()
    orig_body = str(
        contact.get("email_body_sent") or contact.get("email_body") or ""
    ).strip()

    key = (
        cache_key
        or contact.get("email_target")
        or company
        or "reminder"
    ).strip()
    cache_bucket = (cache or {}).setdefault("claude_reminder_email", {})
    bucket_key = f"{key}|r{reminder_number}|{sent_date}"
    if bucket_key in cache_bucket:
        cached = cache_bucket[bucket_key]
        if isinstance(cached, dict):
            intro = str(cached.get("intro") or "").strip()
            if intro:
                return intro

    prompt = build_reminder_email_prompt_pl(
        company_name=company,
        original_subject=orig_subj,
        sent_date=sent_date,
        original_body_excerpt=orig_body,
        reminder_number=reminder_number,
    )
    log = logger or logging.getLogger("pl_claude_reminder_email")
    try:
        text, model = claude_generate_text(
            prompt,
            log,
            api_key,
            cache=cache,
            model_tier="verify",
            bypass_daily_limit=True,
        )
        log.info(
            "Claude reminder PL, model=%s, firma=%s, r=%s",
            model,
            company[:60],
            reminder_number,
        )
        intro = _normalize_paragraphs(
            _strip_signature_from_intro(_parse_reminder_intro_json(text))
        )
        if not intro:
            raise ValueError("puste intro po normalizacji")
        cache_bucket[bucket_key] = {"intro": intro, "model": model}
        return intro
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        log.warning("Claude reminder PL parse error: %s", exc)
        return None
    except Exception as exc:
        log.warning("Claude reminder PL: %s", exc)
        return None
