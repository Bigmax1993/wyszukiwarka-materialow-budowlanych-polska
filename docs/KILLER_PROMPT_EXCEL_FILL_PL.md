# Killer prompt — uzupełnianie wiersza Excel (PL materiały)

Używany przez `pl_claude_prompts.build_row_cleanup_prompt` przed zapisem `pl_materialy_kontakte.xlsx`.

## Kolumny docelowe (sztywno)

| Kolumna | Zawartość |
|---------|-----------|
| Nazwa firmy | Oficjalna nazwa + forma prawna |
| Adres | ul. …, XX-XXX Miasto |
| Województwo | dokładnie jedno z 16 |
| Telefon | jeden numer +48… |
| E-mail | jeden adres firmowy |
| Strona www | https://domena.pl (root) |
| URL | = Strona www |
| Kategorie materiałów | cement, piasek, … (małe litery) |
| WWW sprawdzone / Mała firma / GU | tak \| nie |
| Znacznik GU | krótki marker lub puste |
| Status | status pipeline (sent / …) — nie kategorie |

## Prompt (skrót zasad)

1. Tylko hurtownie / składy / dystrybutorzy / producenci materiałów budowlanych PL.
2. Portale (Facebook, Lento, OLX, Allegro…) → puste pola nazwa/www/url.
3. URL w polu nazwy → przenieś do website/url; nazwę wyprowadź tylko z pewnego kontekstu.
4. Województwo nie może być w Adres.
5. „tak”/„nie”/statusy nie mogą być w Kategorie.
6. Niepewność → pusty string, nigdy halucynacja.

Pełny tekst: funkcja `build_row_cleanup_prompt` w `pl_claude_prompts.py`.
