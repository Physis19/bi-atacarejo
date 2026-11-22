"""Bronze: copia cada fonte como texto, sem corrigir nada."""

from pathlib import Path

import duckdb
from openpyxl import load_workbook

FONTES_CSV = ("vendas", "devolucoes", "clientes", "produtos", "vendedores")


def carregar(con: duckdb.DuckDBPyConnection, origem: Path):
    con.execute("CREATE SCHEMA bronze")
    for fonte in FONTES_CSV:
        caminho = str(origem / "erp" / f"{fonte}.csv").replace("'", "''")
        con.execute(f"""
            CREATE TABLE bronze.{fonte} AS
            SELECT row_number() OVER () + 1 AS _linha, '{fonte}.csv' AS _arquivo, *
            FROM read_csv('{caminho}', delim = ';', header = true,
                          all_varchar = true, parallel = false)
        """)

    # O orçamento chega em formato largo (um mês por coluna): vira uma linha por célula.
    pasta = load_workbook(origem / "financeiro" / "orcamento_2026.xlsx", read_only=True)
    celulas = []
    for aba in pasta.worksheets:
        cabecalho, *linhas = list(aba.values)
        for numero, linha in enumerate(linhas, start=2):
            for mes, valor in zip(cabecalho[1:], linha[1:]):
                celulas.append((numero, aba.title, str(linha[0]), str(mes), str(valor)))
    pasta.close()
    con.execute("""
        CREATE TABLE bronze.orcamento
        (_linha INTEGER, aba VARCHAR, categoria VARCHAR, mes VARCHAR, valor VARCHAR)
    """)
    con.executemany("INSERT INTO bronze.orcamento VALUES (?, ?, ?, ?, ?)", celulas)
