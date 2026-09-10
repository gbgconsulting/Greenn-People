"""Calendário Brasil nacional — dias úteis sem dependência externa.

Feriados: federais fixos + móveis derivados da Páscoa gregoriana.
Estaduais/municipais ficam fora do escopo (FR-020 / research R3).
"""

from __future__ import annotations

from datetime import date, timedelta

# Carnaval e Corpus Christi entram no calendário operacional nacional
# (research R3: móveis via Páscoa; testes esperam carnaval derivado).
_CARNIVAL_MONDAY_OFFSET = -48
_CARNIVAL_TUESDAY_OFFSET = -47
_GOOD_FRIDAY_OFFSET = -2
_CORPUS_CHRISTI_OFFSET = 60

# Dia Nacional de Zumbi e da Consciência Negra — feriado federal (Lei 14.759/2023).
_CONSCIENCIA_NEGRA_FROM_YEAR = 2024


def easter_sunday(year: int) -> date:
    """Páscoa gregoriana (algoritmo anônimo / Meeus–Jones–Butcher)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def national_holidays(year: int) -> frozenset[date]:
    """Conjunto de feriados nacionais brasileiros no ano civil."""
    easter = easter_sunday(year)
    holidays: set[date] = {
        date(year, 1, 1),  # Confraternização Universal
        easter + timedelta(days=_CARNIVAL_MONDAY_OFFSET),
        easter + timedelta(days=_CARNIVAL_TUESDAY_OFFSET),
        easter + timedelta(days=_GOOD_FRIDAY_OFFSET),  # Sexta-feira Santa
        date(year, 4, 21),  # Tiradentes
        date(year, 5, 1),  # Dia do Trabalho
        easter + timedelta(days=_CORPUS_CHRISTI_OFFSET),
        date(year, 9, 7),  # Independência
        date(year, 10, 12),  # Nossa Senhora Aparecida
        date(year, 11, 2),  # Finados
        date(year, 11, 15),  # Proclamação da República
        date(year, 12, 25),  # Natal
    }
    if year >= _CONSCIENCIA_NEGRA_FROM_YEAR:
        holidays.add(date(year, 11, 20))
    return frozenset(holidays)


def is_national_holiday(d: date) -> bool:
    """True se ``d`` é feriado nacional brasileiro."""
    return d in national_holidays(d.year)


def is_business_day(d: date) -> bool:
    """Dia útil: segunda–sexta e não feriado nacional."""
    return d.weekday() < 5 and not is_national_holiday(d)


def first_business_day_of_month(year: int, month: int) -> date:
    """Primeiro dia útil do mês civil (pula fim de semana e feriado nacional)."""
    current = date(year, month, 1)
    while not is_business_day(current):
        current += timedelta(days=1)
    return current
