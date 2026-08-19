"""Exceções do domínio de avaliações."""


class CalculationError(Exception):
    """Erro em cálculo de nota (ex.: soma de pesos igual a zero)."""
