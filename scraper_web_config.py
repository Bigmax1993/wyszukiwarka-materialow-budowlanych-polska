# -*- coding: utf-8 -*-
"""
Wspólna konfiguracja dla wszystkich scraperów w „Automatyczna wyszukiwarka…”.

Strony www: requests + BeautifulSoup; baner cookie — Playwright (DE: „Alle akzeptieren” itd.).
Kontakty www: regex + mailto (bez Gemini przy ekstrakcji e-maili).
Weryfikacja www + cleanup wiersza: Claude Sonnet (Anthropic API).
"""
from __future__ import annotations

# Wybór e-maila z listy znalezionej w HTML (email_targeting) — bez Gemini
ENABLE_GEMINI_CONTACT_EMAIL = False

# Bereinigung Nazwa/Adres/Telefon/Bundesland vor Excel — Claude (Gemini wyłączone)
ENABLE_GEMINI_ROW_CLEANUP = False
ENABLE_CLAUDE_PAGE_VERIFY = True
ENABLE_CLAUDE_ROW_CLEANUP = True

# Playwright: wyłącznie zamknięcie banerów cookie (bez CAPTCHA / map)
ENABLE_PLAYWRIGHT_COOKIE_CONSENT = True
