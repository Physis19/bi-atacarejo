"""Os números são recalculados em Python puro, sem reaproveitar o SQL do pipeline."""

import csv
import hashlib
from collections import defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import duckdb
import pytest
from openpyxl import load_workbook

from gerador.gerar import gerar
from pipeline.executar import executar
from pipeline.planilha import gerar_planilha


@pytest.fixture(scope="session")
def origem(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("raw")
    gerar(pasta)
    return pasta


@pytest.fixture(scope="session")
def banco(origem, tmp_path_factory):
    caminho = tmp_path_factory.mktemp("banco") / "teste.duckdb"
    executar(origem, caminho)
    return caminho


@pytest.fixture
def con(banco):
    with duckdb.connect(str(banco), read_only=True) as conexao:
        yield conexao


def ler(origem, nome):
    with (origem / "erp" / f"{nome}.csv").open(encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def para_data(texto):
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto.strip(), formato).date()
        except ValueError:
            pass
    return None


def decimal(texto):
    try:
        return Decimal(texto.replace(",", "."))
    except InvalidOperation:
        return None


def centavos(valor):
    return valor.quantize(Decimal("0.01"), ROUND_HALF_UP)


def test_receita_e_lucro_batem_com_os_arquivos_de_origem(origem, con):
    produtos = {p["id_produto"] for p in ler(origem, "produtos")}
    vistos, vendas = set(), {}
    esperado = defaultdict(lambda: [Decimal(0), Decimal(0)])

    for linha in ler(origem, "vendas"):
        if linha["id_item"] in vistos:
            continue
        vistos.add(linha["id_item"])
        data, custo = para_data(linha["data"]), decimal(linha["custo_unitario"])
        qtd = int(linha["quantidade"])
        if (linha["status"].strip().upper() != "FATURADA" or data is None or custo is None
                or qtd <= 0 or linha["id_produto"] not in produtos):
            continue
        preco = decimal(linha["preco_unitario"])
        desconto = decimal(linha["desconto_pct"]) or Decimal(0)
        receita = qtd * preco - centavos(qtd * preco * desconto)
        esperado[data.year, data.month][0] += receita
        esperado[data.year, data.month][1] += receita - qtd * custo
        vendas[linha["id_item"]] = (qtd, preco, desconto, custo)

    vistos.clear()
    for linha in ler(origem, "devolucoes"):
        if linha["id_devolucao"] in vistos:
            continue
        vistos.add(linha["id_devolucao"])
        venda, qtd = vendas.get(linha["id_item"]), int(linha["quantidade"])
        if not venda or qtd > venda[0]:
            continue
        data, (_, preco, desconto, custo) = para_data(linha["data"]), venda
        valor = centavos(qtd * preco * (1 - desconto))
        recuperado = 0 if linha["motivo"] in ("avaria", "validade") else qtd * custo
        esperado[data.year, data.month][0] -= valor
        esperado[data.year, data.month][1] -= valor - recuperado

    obtido = con.execute("""
        SELECT ano, mes, sum(receita_liquida), sum(lucro_bruto)
        FROM marts.movimento GROUP BY ALL
    """).fetchall()
    assert {(a, m): [r, l] for a, m, r, l in obtido} == dict(esperado)


def test_verificacoes_de_qualidade_zeradas(con):
    assert con.execute("SELECT * FROM qualidade.verificacoes WHERE falhas <> 0").fetchall() == []


def test_toda_linha_tem_destino(origem, con):
    resumo = {f: (l, v, e) for f, l, v, e in con.execute("FROM qualidade.resumo").fetchall()}
    for fonte, arquivo in (("Vendas", "vendas"), ("Devoluções", "devolucoes")):
        lidas, validas, excluidas = resumo[fonte]
        assert lidas == len(ler(origem, arquivo)) == validas + excluidas


def test_bronze_preserva_o_texto_da_origem(origem, con):
    colunas = list(ler(origem, "vendas")[0])
    bronze = con.execute(f"SELECT {','.join(colunas)} FROM bronze.vendas ORDER BY _linha").fetchall()
    fonte = [tuple(linha[c] or None for c in colunas) for linha in ler(origem, "vendas")]
    assert bronze == fonte


def test_gerador_e_reproduzivel(origem, tmp_path):
    gerar(tmp_path)
    for arquivo in sorted((origem / "erp").glob("*.csv")):
        outro = tmp_path / "erp" / arquivo.name
        assert hashlib.sha256(arquivo.read_bytes()).digest() == hashlib.sha256(outro.read_bytes()).digest()

    def celulas(pasta):
        wb = load_workbook(pasta / "financeiro" / "orcamento_2026.xlsx")
        return [list(ws.values) for ws in wb.worksheets]

    assert celulas(origem) == celulas(tmp_path)


def test_planilha_bate_com_o_sql(banco, con, tmp_path):
    arquivo = tmp_path / "painel.xlsx"
    if not gerar_planilha(banco, arquivo):
        pytest.skip("precisa do LibreOffice para calcular as fórmulas")
    wb = load_workbook(arquivo, data_only=True)
    receita, lucro = con.execute("""
        SELECT sum(receita_liquida), sum(lucro_bruto)
        FROM marts.movimento WHERE ano = 2026 AND mes <= 10
    """).fetchone()
    assert wb["Painel"]["E10"].value == pytest.approx(float(receita), abs=0.01)
    assert wb["Painel"]["E12"].value == pytest.approx(float(lucro), abs=0.01)
    erros = [(ws.title, c.coordinate) for ws in wb for linha in ws.iter_rows() for c in linha
             if isinstance(c.value, str) and c.value.startswith(("#", "Err:"))]
    assert erros == []
