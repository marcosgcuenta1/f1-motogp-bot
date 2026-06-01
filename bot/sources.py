"""Fuentes de datos de horarios de F1 y MotoGP.

- F1: API jolpica-f1 (sucesor de Ergast), formato compatible.
- MotoGP: API pública (no oficial) de motogp.com (api.motogp.pulselive.com).

Ambas se normalizan a una lista de objetos ``Session`` con la hora de inicio
en UTC, que luego se convierte a hora de Madrid donde haga falta.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import requests

MADRID = ZoneInfo("Europe/Madrid")
UTC = ZoneInfo("UTC")

F1_URL = "https://api.jolpi.ca/ergast/f1/current.json"
MOTOGP_EVENTS_URL = "https://api.motogp.pulselive.com/motogp/v1/events"

_TIMEOUT = 30
_HEADERS = {"User-Agent": "f1-motogp-telegram-bot/1.0 (personal use)"}


@dataclass(frozen=True)
class Session:
    """Una sesión concreta (libres, clasificación, sprint o carrera)."""

    sport: str          # "F1" | "MotoGP"
    event: str          # nombre del GP
    country: str        # país / código de país
    name: str           # nombre legible en español
    kind: str           # practice | qualifying | sprint | race
    start_utc: dt.datetime

    @property
    def start_madrid(self) -> dt.datetime:
        return self.start_utc.astimezone(MADRID)

    @property
    def uid(self) -> str:
        """Identificador estable para deduplicar avisos."""
        return f"{self.sport}|{self.event}|{self.start_utc.isoformat()}"


# --------------------------------------------------------------------------- #
# Helpers de parseo de fechas
# --------------------------------------------------------------------------- #
# Offset sin dos puntos al final, p. ej. "+0100" / "-0700".
_OFFSET_RE = re.compile(r"([+-]\d{2})(\d{2})$")


def _parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    # Python 3.9 exige el offset como +HH:MM; MotoGP lo envía como +HHMM.
    text = _OFFSET_RE.sub(r"\1:\2", text)
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_f1_dt(date_s: str | None, time_s: str | None) -> dt.datetime | None:
    if not date_s or not time_s:
        return None
    return _parse_iso(f"{date_s}T{time_s}")


# --------------------------------------------------------------------------- #
# Fórmula 1 (jolpica-f1 / Ergast)
# --------------------------------------------------------------------------- #
# (clave en el JSON, etiqueta legible, tipo de sesión)
_F1_SESSIONS = [
    ("FirstPractice", "Práctica Libre 1", "practice"),
    ("SecondPractice", "Práctica Libre 2", "practice"),
    ("ThirdPractice", "Práctica Libre 3", "practice"),
    ("SprintQualifying", "Clasificación al Sprint", "qualifying"),
    ("Sprint", "Carrera al Sprint", "sprint"),
    ("Qualifying", "Clasificación", "qualifying"),
]


def fetch_f1() -> list[Session]:
    resp = requests.get(F1_URL, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    races = resp.json()["MRData"]["RaceTable"]["Races"]

    sessions: list[Session] = []
    for race in races:
        event = race.get("raceName", "Gran Premio")
        country = race.get("Circuit", {}).get("Location", {}).get("country", "")

        for key, label, kind in _F1_SESSIONS:
            block = race.get(key)
            if not block:
                continue
            start = _parse_f1_dt(block.get("date"), block.get("time"))
            if start:
                sessions.append(Session("F1", event, country, label, kind, start))

        race_start = _parse_f1_dt(race.get("date"), race.get("time"))
        if race_start:
            sessions.append(Session("F1", event, country, "Carrera", "race", race_start))

    return sessions


# --------------------------------------------------------------------------- #
# MotoGP (api.motogp.pulselive.com)
# --------------------------------------------------------------------------- #
# Mapeo por 'shortname' de la sesión -> (etiqueta legible, tipo normalizado).
# Importante: SPR (sprint) y RAC (carrera) comparten kind="RACE" en la API, así
# que hay que distinguirlos por shortname para no disparar el aviso en el sprint.
_MGP_SESSIONS = {
    "FP1": ("Práctica Libre 1", "practice"),
    "FP2": ("Práctica Libre 2", "practice"),
    "FP3": ("Práctica Libre 3", "practice"),
    "PR": ("Práctica", "practice"),
    "Q1": ("Clasificación Q1", "qualifying"),
    "Q2": ("Clasificación Q2", "qualifying"),
    "WUP": ("Warm Up", "practice"),
    "SPR": ("Carrera al Sprint", "sprint"),
    "RAC": ("Carrera", "race"),
}

# Clase reina (MotoGP). MT2 = Moto2, MT3 = Moto3.
_MGP_CATEGORY = "MGP"
# De Moto2/Moto3 solo nos interesa la carrera (no libres ni clasificación).
_MGP_SUPPORT = {"MT2": "Moto2", "MT3": "Moto3"}


def _fetch_motogp_year(year: int) -> list[Session]:
    resp = requests.get(
        MOTOGP_EVENTS_URL,
        params={"seasonYear": year},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()
    events = payload if isinstance(payload, list) else payload.get("events", [])

    sessions: list[Session] = []
    for event in events:
        if (event.get("kind") or "").upper() == "TEST":
            continue  # ignoramos los test de pretemporada
        name = event.get("name") or event.get("sponsored_name") or "Gran Premio"
        country = event.get("country", "")
        for broadcast in event.get("broadcasts") or []:
            category = (broadcast.get("category") or {}).get("acronym")
            shortname = (broadcast.get("shortname") or "").upper()

            if category == _MGP_CATEGORY:
                mapped = _MGP_SESSIONS.get(shortname)
                if not mapped:  # descarta ruedas de prensa, shows, etc.
                    continue
                label, kind = mapped
            elif category in _MGP_SUPPORT and shortname == "RAC":
                # De Moto2/Moto3 solo la carrera. La marcamos como
                # 'support_race' para que NO dispare el aviso de 10 min.
                label, kind = f"Carrera {_MGP_SUPPORT[category]}", "support_race"
            else:
                continue

            start = _parse_iso(broadcast.get("date_start"))
            if start:
                sessions.append(Session("MotoGP", name, country, label, kind, start))
    return sessions


def fetch_motogp(years: list[int]) -> list[Session]:
    sessions: list[Session] = []
    for year in sorted(set(years)):
        try:
            sessions.extend(_fetch_motogp_year(year))
        except requests.RequestException:
            # No abortamos todo el bot si MotoGP falla un año concreto.
            continue
    return sessions


# --------------------------------------------------------------------------- #
# API combinada
# --------------------------------------------------------------------------- #
def get_all_sessions(years: list[int]) -> list[Session]:
    """Devuelve todas las sesiones de F1 + MotoGP, deduplicadas y ordenadas."""
    sessions: list[Session] = []

    try:
        sessions.extend(fetch_f1())
    except requests.RequestException:
        pass

    sessions.extend(fetch_motogp(years))

    # Deduplicar por uid (varios canales de TV comparten misma sesión/hora).
    unique: dict[str, Session] = {s.uid: s for s in sessions}
    return sorted(unique.values(), key=lambda s: s.start_utc)
