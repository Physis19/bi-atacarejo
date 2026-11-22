"""
Parâmetros do cenário de negócio simulado.

ATENÇÃO, SPOILER: este arquivo contém o gabarito da análise.
Leia só depois de investigar os dados pela planilha e pelo SQL.
"""

from datetime import date


def desconto_extra(dia: date, vendedor: str) -> float:
    if vendedor in ("V04", "V09") and dia >= date(2026, 3, 1):
        return 0.075
    return 0.0


def fator_custo(dia: date, categoria: str) -> float:
    if categoria == "Bebidas" and dia >= date(2026, 4, 1):
        return 1.10
    return 1.0


def fator_preco(dia: date, categoria: str) -> float:
    if categoria == "Bebidas" and dia >= date(2026, 4, 1):
        return 1.015
    return 1.0


def devolucao_extra(dia: date, categoria: str, cidade: str) -> tuple[float, str | None]:
    if (
        categoria == "Frios e laticínios"
        and cidade in ("Arapiraca", "Palmeira dos Índios")
        and dia >= date(2026, 6, 15)
    ):
        return 0.22, "validade"
    return 0.0, None
