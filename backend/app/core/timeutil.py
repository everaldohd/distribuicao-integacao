"""Datas/horas no fuso de negócio (configurável por TIMEZONE).

As regras que comparam com "hoje" (antecedência de troca, expiração de ofertas)
devem usar a data local da operação, não a do container (geralmente UTC).
"""
from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings

# Fallback caso a base de fusos (tzdata) não esteja instalada na imagem.
# Horário de Brasília (sem horário de verão, extinto em 2019) = UTC−3.
_FALLBACK_TZ = timezone(timedelta(hours=-3))


def _tz() -> tzinfo:
    try:
        return ZoneInfo(settings.TIMEZONE)
    except ZoneInfoNotFoundError:
        return _FALLBACK_TZ


def now_local() -> datetime:
    """Agora, no fuso de negócio (timezone-aware)."""
    return datetime.now(_tz())


def today_local() -> date:
    """Data de hoje no fuso de negócio."""
    return now_local().date()
