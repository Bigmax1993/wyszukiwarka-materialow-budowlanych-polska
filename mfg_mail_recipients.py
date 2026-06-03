# -*- coding: utf-8 -*-
"""Stałe odbiorcy kopii dla kampanii MFG (DE GU / Ost)."""
from __future__ import annotations

MFG_OFFICE_CC_EMAIL = "office@mfg-fliesen.de"


def merge_mfg_campaign_cc(to_email: str, extra_env_cc: str = "") -> list[str]:
    """
    Widoczna kopia (Cc) — zawsze office@mfg-fliesen.de + MAIL_CC z .env.
    """
    try:
        from mail_transport import merge_mail_cc_recipients

        cc = merge_mail_cc_recipients(to_email, extra_env_cc)
    except Exception:
        cc = []
    to_norm = (to_email or "").strip().lower()
    seen = {a.strip().lower() for a in cc if a}
    if (
        MFG_OFFICE_CC_EMAIL.lower() not in seen
        and MFG_OFFICE_CC_EMAIL.lower() != to_norm
    ):
        cc.append(MFG_OFFICE_CC_EMAIL)
    return cc
