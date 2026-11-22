"""Roda Bronze -> Silver -> Gold -> Marts e para se a qualidade falhar."""

from pathlib import Path

import duckdb

from pipeline import bronze

SQL = Path(__file__).resolve().parent.parent / "sql"


def executar(origem: Path, banco: Path):
    banco.parent.mkdir(parents=True, exist_ok=True)
    banco.unlink(missing_ok=True)
    with duckdb.connect(str(banco)) as con:
        bronze.carregar(con, origem)
        for script in sorted(SQL.glob("*.sql")):
            con.execute(script.read_text(encoding="utf-8"))
        falhas = con.execute("SELECT * FROM qualidade.verificacoes WHERE falhas <> 0").fetchall()
    if falhas:
        raise RuntimeError(f"Verificações de qualidade falharam: {falhas}")
