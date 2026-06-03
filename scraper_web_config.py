# -*- coding: utf-8 -*-
"""
Wspólna konfiguracja dla wszystkich scraperów w „Automatyczna wyszukiwarka…”.

Strony www: requests + BeautifulSoup; baner cookie — Playwright (DE: „Alle akzeptieren” itd.).
Gemini nie wybiera e-maili ze stron ani nie „czyści” rekordów z HTML.
"""
from __future__ import annotations

# Wybór e-maila z listy znalezionej w HTML (email_targeting) — bez Gemini
ENABLE_GEMINI_CONTACT_EMAIL = False

# Bereinigung wiersza / województwo przez Gemini — wyłączone (tylko BS4 + reguły)
ENABLE_GEMINI_ROW_CLEANUP = False

# Playwright: wyłącznie zamknięcie banerów cookie (bez CAPTCHA / map)
ENABLE_PLAYWRIGHT_COOKIE_CONSENT = True
