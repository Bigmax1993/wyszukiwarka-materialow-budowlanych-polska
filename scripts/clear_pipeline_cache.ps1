# Wyczyść cały de_gu_bauunternehmen_cache.json (lokalnie).
param(
    [string]$CachePath = "Wyniki\de_gu_bauunternehmen_cache.json"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -c @"
import json
from pathlib import Path
from de_gu_bauunternehmen_scraper import reset_pipeline_cache

p = Path(r'$CachePath')
before = {}
if p.exists():
    before = json.loads(p.read_text(encoding='utf-8'))
    print('Przed:', {k: (len(v) if isinstance(v, dict) else v) for k, v in before.items()})
p.parent.mkdir(parents=True, exist_ok=True)
fresh = reset_pipeline_cache()
p.write_text(json.dumps(fresh, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Cache wyczyszczony:', p.resolve())
"@
