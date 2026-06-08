# -*- coding: utf-8 -*-
"""
Wspólna konfiguracja dla wszystkich scraperów w „Automatyczna wyszukiwarka…”.

Strony www: requests + BeautifulSoup; baner cookie — Playwright (DE: „Alle akzeptieren” itd.).
Kontakty www: parse → Gemini → regex. Przed Excelem: Gemini row cleanup.
"""
from __future__ import annotations

# Wybór e-maila z listy znalezionej w HTML (email_targeting) — bez Gemini
ENABLE_GEMINI_CONTACT_EMAIL = False

# Bereinigung Nazwa/Adres/Telefon/Bundesland vor Excel — einziger Gemini-Aufruf
ENABLE_GEMINI_ROW_CLEANUP = True

# Playwright: wyłącznie zamknięcie banerów cookie (bez CAPTCHA / map)
ENABLE_PLAYWRIGHT_COOKIE_CONSENT = True
