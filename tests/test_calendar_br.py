"""T015 [US1]: calendário Brasil nacional — 1º dia útil, feriado, fim de semana.

Contrato / research R3: ``apps/core/calendar_br.py`` sem lib externa;
feriados federais fixos + móveis via Páscoa; estaduais/municipais fora.
"""

from __future__ import annotations

from datetime import date, timedelta

from apps.core.calendar_br import (
    easter_sunday,
    first_business_day_of_month,
    is_business_day,
    is_national_holiday,
    national_holidays,
)


def test_easter_sunday_known_years():
    """Páscoa gregoriana alinhada a anos de referência conhecidos."""
    assert easter_sunday(2024) == date(2024, 3, 31)
    assert easter_sunday(2025) == date(2025, 4, 20)
    assert easter_sunday(2026) == date(2026, 4, 5)


def test_national_holidays_include_fixed_and_movable_2026():
    holidays = national_holidays(2026)
    easter = easter_sunday(2026)

    assert date(2026, 1, 1) in holidays
    assert date(2026, 4, 21) in holidays  # Tiradentes
    assert date(2026, 5, 1) in holidays
    assert date(2026, 9, 7) in holidays
    assert date(2026, 10, 12) in holidays
    assert date(2026, 11, 2) in holidays
    assert date(2026, 11, 15) in holidays
    assert date(2026, 11, 20) in holidays  # Consciência Negra (federal ≥2024)
    assert date(2026, 12, 25) in holidays

    assert easter + timedelta(days=-48) in holidays  # Carnaval segunda
    assert easter + timedelta(days=-47) in holidays  # Carnaval terça
    assert easter + timedelta(days=-2) in holidays  # Sexta Santa
    assert easter + timedelta(days=60) in holidays  # Corpus Christi


def test_consciencia_negra_only_from_2024():
    assert date(2023, 11, 20) not in national_holidays(2023)
    assert date(2024, 11, 20) in national_holidays(2024)


def test_is_business_day_false_on_weekend():
    """Sábado e domingo nunca são dia útil."""
    saturday = date(2026, 7, 4)
    sunday = date(2026, 7, 5)
    assert saturday.weekday() == 5
    assert sunday.weekday() == 6
    assert is_business_day(saturday) is False
    assert is_business_day(sunday) is False


def test_is_business_day_false_on_national_holiday():
    """Feriado nacional em dia de semana → não útil."""
    independencia = date(2026, 9, 7)  # segunda
    assert independencia.weekday() == 0
    assert is_national_holiday(independencia) is True
    assert is_business_day(independencia) is False


def test_is_business_day_true_on_ordinary_weekday():
    ordinary = date(2026, 7, 2)  # quinta
    assert ordinary.weekday() == 3
    assert is_national_holiday(ordinary) is False
    assert is_business_day(ordinary) is True


def test_first_business_day_when_month_starts_on_weekday():
    """1º civil útil → ele próprio (jul/2026 = quarta)."""
    assert date(2026, 7, 1).weekday() == 2
    assert first_business_day_of_month(2026, 7) == date(2026, 7, 1)


def test_first_business_day_skips_weekend():
    """ago/2026 começa sábado → 1º útil = segunda 03/08."""
    assert date(2026, 8, 1).weekday() == 5
    assert first_business_day_of_month(2026, 8) == date(2026, 8, 3)


def test_first_business_day_skips_national_holiday():
    """jan/2026: 01/01 (quinta, feriado) → 1º útil = 02/01."""
    assert date(2026, 1, 1).weekday() == 3
    assert is_national_holiday(date(2026, 1, 1)) is True
    assert first_business_day_of_month(2026, 1) == date(2026, 1, 2)


def test_first_business_day_skips_holiday_on_weekday_may():
    """mai/2026: 01/05 (sexta, Dia do Trabalho) → 1º útil = 04/05 (segunda)."""
    assert date(2026, 5, 1).weekday() == 4
    assert is_national_holiday(date(2026, 5, 1)) is True
    assert first_business_day_of_month(2026, 5) == date(2026, 5, 4)
