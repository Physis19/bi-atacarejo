"""Atualiza tudo: python run.py (use --regerar para recriar os dados simulados)."""

import argparse
from pathlib import Path

from gerador.gerar import gerar
from pipeline.executar import executar
from pipeline.planilha import gerar_planilha

RAIZ = Path(__file__).resolve().parent
ORIGEM = RAIZ / "data" / "raw"
BANCO = RAIZ / "data" / "warehouse.duckdb"
PLANILHA = RAIZ / "entregas" / "painel_gerencial.xlsx"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regerar", action="store_true", help="recria os dados sintéticos")
    args = parser.parse_args()

    if args.regerar or not (ORIGEM / "financeiro" / "orcamento_2026.xlsx").exists():
        print("[1/3] Simulando extrações do ERP e orçamento")
        gerar(ORIGEM)
    else:
        print("[1/3] Usando as fontes de data/raw")

    print("[2/3] Bronze, Silver, Gold, marts e qualidade")
    executar(ORIGEM, BANCO)

    print("[3/3] Planilha gerencial")
    if not gerar_planilha(BANCO, PLANILHA):
        print("      LibreOffice não encontrado: abra no Excel para calcular as fórmulas.")
    print(f"Pronto: {PLANILHA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
