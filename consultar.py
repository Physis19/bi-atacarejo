"""Roda uma consulta: python consultar.py consultas/02_curva_abc.sql"""

import sys
from pathlib import Path

import duckdb

if len(sys.argv) != 2:
    sys.exit(__doc__)

banco = Path(__file__).resolve().parent / "data" / "warehouse.duckdb"
with duckdb.connect(str(banco), read_only=True) as con:
    con.sql(Path(sys.argv[1]).read_text(encoding="utf-8")).show(max_rows=200)
