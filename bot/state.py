"""Estado persistente para no repetir avisos (deduplicación).

Se guarda como un JSON sencillo {uid: fecha_inicio_iso}. El workflow de
GitHub Actions hace commit del fichero solo cuando cambia (es decir, solo
cuando se ha enviado un aviso nuevo), así que apenas genera ruido en el repo.
"""
from __future__ import annotations

import datetime as dt
import json
import os

_PRUNE_DAYS = 3


def load(path: str) -> dict[str, str]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def prune(data: dict[str, str], now_utc: dt.datetime) -> dict[str, str]:
    """Elimina avisos cuya sesión empezó hace más de _PRUNE_DAYS días."""
    cutoff = now_utc - dt.timedelta(days=_PRUNE_DAYS)
    kept: dict[str, str] = {}
    for uid, iso in data.items():
        try:
            when = dt.datetime.fromisoformat(iso)
        except ValueError:
            continue
        if when >= cutoff:
            kept[uid] = iso
    return kept


def save(path: str, data: dict[str, str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
