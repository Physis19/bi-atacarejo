"""
Monta o Excel gerencial.

O Python só cola as bases (abas Base_*) e escreve fórmulas. Todo KPI das abas
de análise é calculado pelo Excel, para poder clicar na célula e ver a conta.
"""

import shutil
import subprocess
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import duckdb
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.datavalidation import DataValidation

from pipeline import estilo as e

ANO = 2026
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MES = "Painel!$B$4"  # célula que controla a planilha inteira

BASES = {
    "Base_Comercial": "SELECT * FROM marts.comercial_mensal ORDER BY ALL",
    "Base_Orcamento": """SELECT ano, mes, categoria, receita_orcada, lucro_orcado
                         FROM gold.fato_orcamento ORDER BY ALL""",
    "Base_Vendedor": "SELECT * FROM marts.vendedor_mensal ORDER BY ALL",
    "Base_Estatistica": "SELECT * FROM marts.vendedor_estatistica ORDER BY ALL",
    "Base_Produto": "SELECT * FROM marts.produto_mensal ORDER BY ALL",
    "Base_Devolucao": "SELECT * FROM marts.devolucao_mensal ORDER BY ALL",
}


class Planilha:
    def __init__(self, con: duckdb.DuckDBPyConnection):
        self.con = con
        self.wb = Workbook()
        self.wb.active.title = "Painel"
        for nome in ("Orçamento", "Margem", "Comercial", "Produtos", "Qualidade", "Premissas"):
            self.wb.create_sheet(nome)
        self.colunas = {}
        for nome, sql in BASES.items():
            self.colar_base(nome, sql)
        self.ultimo_mes = self.valor(f"SELECT max(mes) FROM marts.movimento WHERE ano = {ANO}")
        self.categorias = self.lista("SELECT DISTINCT categoria FROM gold.dim_produto ORDER BY 1")

    def valor(self, sql: str):
        return self.con.execute(sql).fetchone()[0]

    def lista(self, sql: str) -> list:
        return [linha[0] for linha in self.con.execute(sql).fetchall()]

    def colar_base(self, nome: str, sql: str):
        resultado = self.con.execute(sql)
        titulos = [d[0] for d in resultado.description]
        linhas = resultado.fetchall()
        ws = self.wb.create_sheet(nome)
        ws.append(titulos)
        for linha in linhas:
            ws.append([float(v) if isinstance(v, Decimal) else v for v in linha])
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for indice, titulo in enumerate(titulos):
            letra = chr(ord("A") + indice)
            ws.column_dimensions[letra].width = 20
            self.colunas[nome, titulo] = f"{nome}!${letra}$2:${letra}${len(linhas) + 1}"

    def soma(self, base: str, medida: str, *filtros: tuple[str, str]) -> str:
        """Devolve um SOMASES (SUMIFS no arquivo) sobre uma das bases."""
        partes = [self.colunas[base, medida]]
        for coluna, criterio in filtros:
            partes += [self.colunas[base, coluna], criterio]
        return f"SUMIFS({','.join(partes)})"

    def acumulado(self, base: str, medida: str, ano: int, *filtros: tuple[str, str]) -> str:
        return self.soma(base, medida, ("ano", str(ano)), ("mes", f'"<="&{MES}'), *filtros)

    def painel(self):
        ws = self.wb["Painel"]
        e.preparar(ws, "Painel gerencial: distribuidora de atacarejo",
                   "Dados sintéticos. Valores em R$. Troque o mês na célula amarela.",
                   [26, 15, 15, 12, 16, 16, 12, 16, 12])
        ws["A4"] = "Mês de análise (2026)"
        ws["A4"].font = Font(name="Calibri", bold=True)
        ws["B4"] = self.ultimo_mes
        ws["B4"].fill = e.ENTRADA
        ws["B4"].font = Font(name="Calibri", bold=True, size=12)
        ws["B4"].alignment = Alignment(horizontal="center")
        meses = ",".join(str(m) for m in range(1, self.ultimo_mes + 1))
        validacao = DataValidation(type="list", formula1=f'"{meses}"', showErrorMessage=True)
        ws.add_data_validation(validacao)
        validacao.add("B4")
        nomes = ",".join(f'"{m}"' for m in MESES)
        ws["C4"] = f'=CHOOSE(B4,{nomes})&"/{ANO}"'

        e.cabecalho(ws, 6, ["Indicador", "Mês", "Orçado no mês", "Desvio",
                            "Acumulado", "Orçado acumulado", "Desvio",
                            "Mesmo período de 2025", "Variação"])
        medidas = [("Receita bruta", "receita_bruta", None), ("(-) Descontos", "descontos", None),
                   ("(-) Devoluções", "devolucoes", None),
                   ("Receita líquida", "receita_liquida", "receita_orcada"),
                   ("(-) Custo (CMV)", "cmv", None),
                   ("Lucro bruto", "lucro_bruto", "lucro_orcado")]
        formatos = [None, e.REAIS, e.REAIS, e.VAR_PCT, e.REAIS, e.REAIS, e.VAR_PCT, e.REAIS, e.VAR_PCT]
        b, o = "Base_Comercial", "Base_Orcamento"
        for n, (nome, medida, orcada) in enumerate(medidas, start=7):
            no_mes = (("ano", str(ANO)), ("mes", MES))
            e.escrever(ws, n, [
                nome,
                "=" + self.soma(b, medida, *no_mes),
                "=" + self.soma(o, orcada, *no_mes) if orcada else None,
                f"=IFERROR(B{n}/C{n}-1,0)" if orcada else None,
                "=" + self.acumulado(b, medida, ANO),
                "=" + self.acumulado(o, orcada, ANO) if orcada else None,
                f"=IFERROR(E{n}/F{n}-1,0)" if orcada else None,
                "=" + self.acumulado(b, medida, ANO - 1),
                f"=IFERROR(E{n}/H{n}-1,0)",
            ], formatos, total=orcada is not None)

        formatos = [None, e.PCT, e.PCT, e.PP, e.PCT, e.PCT, e.PP, e.PCT, e.PP]
        razoes = [("Margem bruta", 12, 10, True), ("Desconto / receita bruta", 8, 7, False),
                  ("Devolução / receita bruta", 9, 7, False)]
        for n, (nome, cima, baixo, orcada) in enumerate(razoes, start=13):
            razao = {c: f"=IFERROR({c}{cima}/{c}{baixo},0)" for c in "BCEFH"}
            e.escrever(ws, n, [
                nome, razao["B"], razao["C"] if orcada else None,
                f"=(B{n}-C{n})*100" if orcada else None,
                razao["E"], razao["F"] if orcada else None,
                f"=(E{n}-F{n})*100" if orcada else None,
                razao["H"], f"=(E{n}-H{n})*100",
            ], formatos)
        for area in ("D10", "G10", "I10", "D12:D13", "G12:G13", "I12:I13"):
            ws.conditional_formatting.add(
                area, CellIsRule(operator="lessThan", formula=["0"], font=e.ALERTA))

        inicio = 54
        e.secao(ws, inicio - 1, "Dados dos gráficos")
        e.cabecalho(ws, inicio, ["Mês", "Receita 2025", "Receita 2026", "Receita orçada",
                                 "Margem 2025", "Margem 2026", "Margem orçada"])
        for m in range(1, self.ultimo_mes + 1):
            atual, anterior = (("ano", str(ANO)), ("mes", str(m))), (("ano", str(ANO - 1)), ("mes", str(m)))

            def margem(base, lucro, receita, filtros):
                return f"=IFERROR({self.soma(base, lucro, *filtros)}/{self.soma(base, receita, *filtros)},0)"

            e.escrever(ws, inicio + m, [
                MESES[m - 1],
                "=" + self.soma(b, "receita_liquida", *anterior),
                "=" + self.soma(b, "receita_liquida", *atual),
                "=" + self.soma(o, "receita_orcada", *atual),
                margem(b, "lucro_bruto", "receita_liquida", anterior),
                margem(b, "lucro_bruto", "receita_liquida", atual),
                margem(o, "lucro_orcado", "receita_orcada", atual),
            ], [None, e.REAIS, e.REAIS, e.REAIS, e.PCT, e.PCT, e.PCT])
        fim = inicio + self.ultimo_mes
        categorias = Reference(ws, min_col=1, min_row=inicio + 1, max_row=fim)

        receita = BarChart()
        receita.title = "Receita líquida por mês"
        receita.y_axis.number_format = "#,##0"
        receita.add_data(Reference(ws, min_col=2, max_col=4, min_row=inicio, max_row=fim), titles_from_data=True)
        margem_grafico = LineChart()
        margem_grafico.title = "Margem bruta por mês"
        margem_grafico.y_axis.number_format = "0%"
        margem_grafico.y_axis.scaling.min = 0.10
        margem_grafico.y_axis.scaling.max = 0.22
        margem_grafico.add_data(Reference(ws, min_col=5, max_col=7, min_row=inicio, max_row=fim), titles_from_data=True)
        for grafico, ancora in ((receita, "A17"), (margem_grafico, "A35")):
            grafico.set_categories(categorias)
            grafico.height, grafico.width = 8, 25
            grafico.legend.position = "b"
            grafico.x_axis.delete = grafico.y_axis.delete = False
            for serie, cor in zip(grafico.series, (e.CINZA, e.AZUL, e.LARANJA)):
                if grafico is receita:
                    serie.graphicalProperties.solidFill = cor
                else:
                    serie.graphicalProperties.line.solidFill = cor
                    serie.graphicalProperties.line.width = 28000
                    serie.smooth = False
            ws.add_chart(grafico, ancora)
        ws.freeze_panes = "A5"
        ws.print_area = "A1:I51"
        ws.page_setup.fitToHeight = 1
        ws.page_setup.orientation = "portrait"

    def orcamento(self):
        ws = self.wb["Orçamento"]
        e.preparar(ws, "Vamos bater o orçamento?",
                   "Projeção do ano = realizado até o mês + orçamento restante × atingimento atual da categoria.",
                   [24, 16, 16, 15, 13, 16, 16, 13])
        n_cat = len(self.categorias)
        blocos = [("Receita líquida", "receita_liquida", "receita_orcada", 4),
                  ("Lucro bruto", "lucro_bruto", "lucro_orcado", 4 + n_cat + 5)]
        formatos = [None, e.REAIS, e.REAIS, e.VAR_REAIS, e.PCT, e.REAIS, e.REAIS, e.VAR_REAIS]
        for titulo, real, orcado, inicio in blocos:
            e.secao(ws, inicio, titulo)
            e.cabecalho(ws, inicio + 1, ["Categoria", "Realizado acumulado", "Orçado acumulado",
                                         "Diferença", "Atingimento", "Orçado no ano",
                                         "Projeção do ano", "Diferença projetada"])
            primeira, total = inicio + 2, inicio + 2 + n_cat
            for n, categoria in enumerate(self.categorias, start=primeira):
                filtro = ("categoria", f"$A{n}")
                e.escrever(ws, n, [
                    categoria,
                    "=" + self.acumulado("Base_Comercial", real, ANO, filtro),
                    "=" + self.acumulado("Base_Orcamento", orcado, ANO, filtro),
                    f"=B{n}-C{n}", f"=IFERROR(B{n}/C{n},0)",
                    "=" + self.soma("Base_Orcamento", orcado, ("ano", str(ANO)), filtro),
                    f"=B{n}+(F{n}-C{n})*E{n}", f"=G{n}-F{n}",
                ], formatos)
            somas = {c: f"=SUM({c}{primeira}:{c}{total - 1})" for c in "BCDFGH"}
            e.escrever(ws, total, ["Total", somas["B"], somas["C"], somas["D"],
                                   f"=IFERROR(B{total}/C{total},0)",
                                   somas["F"], somas["G"], somas["H"]], formatos, total=True)
            for col in "DH":
                ws.conditional_formatting.add(
                    f"{col}{primeira}:{col}{total}",
                    CellIsRule(operator="lessThan", formula=["0"], font=e.ALERTA))

    def margem(self):
        ws = self.wb["Margem"]
        e.preparar(ws, "Onde a margem mudou?",
                   "Acumulado até o mês escolhido no Painel, contra o mesmo período de 2025.",
                   [24, 15, 15, 11, 14, 14, 11, 11, 11, 13])
        grupos = [("Por categoria", "categoria", self.categorias),
                  ("Por canal", "canal", self.lista("SELECT DISTINCT canal FROM gold.dim_cliente ORDER BY 1")),
                  ("Por cidade", "cidade", self.lista("SELECT DISTINCT cidade FROM gold.dim_cliente ORDER BY 1"))]
        formatos = [None, e.REAIS, e.REAIS, e.VAR_PCT, e.REAIS, e.REAIS, e.VAR_PCT, e.PCT, e.PCT, e.PP]
        linha = 4
        for titulo, coluna, itens in grupos:
            e.secao(ws, linha, titulo)
            e.cabecalho(ws, linha + 1, [coluna.capitalize(), "Receita 2025", "Receita 2026", "Variação",
                                        "Lucro 2025", "Lucro 2026", "Variação",
                                        "Margem 2025", "Margem 2026", "Mudança"])
            primeira, total = linha + 2, linha + 2 + len(itens)
            for n, item in enumerate([*itens, "Total"], start=primeira):
                if n == total:
                    valores = [f"=SUM({c}{primeira}:{c}{total - 1})" for c in "BCEF"]
                else:
                    valores = ["=" + self.acumulado("Base_Comercial", medida, ano, (coluna, f"$A{n}"))
                               for medida in ("receita_liquida", "lucro_bruto")
                               for ano in (ANO - 1, ANO)]
                e.escrever(ws, n, [
                    item, valores[0], valores[1], f"=IFERROR(C{n}/B{n}-1,0)",
                    valores[2], valores[3], f"=IFERROR(F{n}/E{n}-1,0)",
                    f"=IFERROR(E{n}/B{n},0)", f"=IFERROR(F{n}/C{n},0)", f"=(I{n}-H{n})*100",
                ], formatos, total=n == total)
            for col in "DGJ":
                ws.conditional_formatting.add(
                    f"{col}{primeira}:{col}{total}",
                    CellIsRule(operator="lessThan", formula=["0"], font=e.ALERTA))
            linha = total + 3
        ws.freeze_panes = "B4"

    def comercial(self):
        ws = self.wb["Comercial"]
        e.preparar(ws, "Como cada vendedor usa desconto?",
                   "Desconto ponderado = descontos / receita bruta. Outlier = acima de Q3 + 1,5 × IQR.",
                   [24, 16, 15, 11, 13, 13, 12, 12, 12, 14])
        e.cabecalho(ws, 4, ["Vendedor", "Receita líquida", "Lucro bruto", "Margem",
                            "Desconto 2025", "Desconto 2026", "Mudança",
                            "Desconto mediano", "Desvio padrão", "Outlier?"])
        formatos = [None, e.REAIS, e.REAIS, e.PCT, e.PCT, e.PCT, e.PP, e.PCT, e.PCT]
        vendedores = self.lista("SELECT nome FROM gold.dim_vendedor ORDER BY 1")
        fim = 4 + len(vendedores)
        limite = f"$B${fim + 5}"
        b, est = "Base_Vendedor", "Base_Estatistica"
        for n, vendedor in enumerate(vendedores, start=5):
            filtro = ("vendedor", f"$A{n}")

            def desconto(ano):
                return (f"=IFERROR({self.acumulado(b, 'descontos', ano, filtro)}/"
                        f"{self.acumulado(b, 'receita_bruta', ano, filtro)},0)")

            # Há uma única linha por vendedor e mês de corte, então SOMASES funciona como busca.
            corte = (("ano", str(ANO)), ("mes_corte", MES), filtro)
            e.escrever(ws, n, [
                vendedor,
                "=" + self.acumulado(b, "receita_liquida", ANO, filtro),
                "=" + self.acumulado(b, "lucro_bruto", ANO, filtro),
                f"=IFERROR(C{n}/B{n},0)", desconto(ANO - 1), desconto(ANO), f"=(F{n}-E{n})*100",
                "=" + self.soma(est, "desconto_mediano", *corte),
                "=" + self.soma(est, "desconto_desvio", *corte),
                f'=IF(F{n}>{limite},"Investigar","")',
            ], formatos)
        faixa = f"F5:F{fim}"
        resumo = [("Q1", f"=QUARTILE({faixa},1)", e.PCT),
                  ("Q3", f"=QUARTILE({faixa},3)", e.PCT),
                  ("IQR (Q3 - Q1)", f"=B{fim + 3}-B{fim + 2}", e.PCT),
                  ("Limite para outlier", f"=B{fim + 3}+1.5*B{fim + 4}", e.PCT),
                  ("Correlação desconto × margem", f"=IFERROR(CORREL({faixa},D5:D{fim}),0)", "0.00")]
        for n, (nome, formula, formato) in enumerate(resumo, start=fim + 2):
            e.escrever(ws, n, [nome, formula], [None, formato])
        ws.column_dimensions["A"].width = 31
        for n in range(5, fim + 1):
            ws.cell(n, 10).alignment = Alignment(horizontal="center")
        ws.cell(fim + 8, 1, "Correlação não prova causa, e são poucos vendedores: "
                            "use como pista para investigar.").font = Font(name="Calibri", italic=True)
        ws.conditional_formatting.add(
            f"A5:J{fim}", FormulaRule(formula=[f'$J5="Investigar"'], font=e.ALERTA))

    def produtos(self):
        produtos = self.con.execute("SELECT nome, categoria FROM gold.dim_produto ORDER BY 1").fetchall()
        calc = self.wb.create_sheet("Calc_ABC")
        calc.append(["produto", "categoria", "receita", "lucro", "chave_ordenacao"])
        for n, (nome, categoria) in enumerate(produtos, start=2):
            filtro = ("produto", f"$A{n}")
            calc.append([nome, categoria,
                         "=" + self.acumulado("Base_Produto", "receita_liquida", ANO, filtro),
                         "=" + self.acumulado("Base_Produto", "lucro_bruto", ANO, filtro),
                         f"=C{n}+ROW()/1000000"])  # desempate
        fim_calc = len(produtos) + 1

        ws = self.wb["Produtos"]
        e.preparar(ws, "Em quais produtos focar?",
                   "Curva ABC da receita acumulada: A até 80%, B até 95%, C o restante.",
                   [34, 19, 14, 13, 10, 13, 9, 3, 20, 14, 14, 14])
        e.cabecalho(ws, 4, ["Produto", "Categoria", "Receita líquida", "Lucro bruto",
                            "Margem", "% acumulado", "Classe"])
        fim = 4 + len(produtos)
        formatos = [None, None, e.REAIS, e.REAIS, e.PCT, e.PCT]
        for posicao, n in enumerate(range(5, fim + 1), start=1):
            linha = (f"MATCH(LARGE(Calc_ABC!$E$2:$E${fim_calc},{posicao}),"
                     f"Calc_ABC!$E$2:$E${fim_calc},0)")
            e.escrever(ws, n, [
                *[f"=INDEX(Calc_ABC!${c}$2:${c}${fim_calc},{linha})" for c in "ABCD"],
                f"=IFERROR(D{n}/C{n},0)",
                f"=IFERROR(SUM(C$5:C{n})/SUM(C$5:C${fim}),0)",
                # Olha o acumulado antes do item, para quem cruza os 80% ainda ser A.
                '="A"' if n == 5 else f'=IF(F{n - 1}<0.8,"A",IF(F{n - 1}<0.95,"B","C"))',
            ], formatos)
            ws.cell(n, 7).alignment = Alignment(horizontal="center")

        e.cabecalho(ws, 4, ["Motivo da devolução", "Valor 2025", "Valor 2026", "Custo perdido 2026"], coluna=9)
        motivos = self.lista("SELECT DISTINCT motivo FROM gold.fato_devolucoes ORDER BY 1")
        for n, motivo in enumerate(motivos, start=5):
            filtro = ("motivo", f"$I{n}")
            ws.cell(n, 9, motivo)
            for col, medida, ano in ((10, "valor_devolvido", ANO - 1), (11, "valor_devolvido", ANO),
                                     (12, "custo_perdido", ANO)):
                ws.cell(n, col, "=" + self.acumulado("Base_Devolucao", medida, ano, filtro)).number_format = e.REAIS
        resumo = 5 + len(motivos) + 2
        e.cabecalho(ws, resumo, ["Classe", "Produtos", "% da receita"], coluna=9)
        for n, classe in enumerate("ABC", start=resumo + 1):
            ws.cell(n, 9, classe)
            ws.cell(n, 10, f"=COUNTIF(G5:G{fim},I{n})")
            ws.cell(n, 11, f"=IFERROR(SUMIFS(C5:C{fim},G5:G{fim},I{n})/SUM(C5:C{fim}),0)").number_format = e.PCT
        ws.freeze_panes = "A5"
        calc.sheet_state = "hidden"

    def qualidade(self):
        ws = self.wb["Qualidade"]
        e.preparar(ws, "Posso confiar no número?",
                   "Toda linha lida é válida ou tem um motivo de exclusão.", [54, 17, 17, 17, 15])
        e.cabecalho(ws, 4, ["Fonte", "Linhas lidas", "Válidas", "Excluídas", "Sem explicação"])
        n = 5
        for linha in self.con.execute("SELECT * FROM qualidade.resumo ORDER BY fonte DESC").fetchall():
            e.escrever(ws, n, [*linha, f"=B{n}-C{n}-D{n}"], [None, "#,##0", "#,##0", "#,##0", "#,##0"])
            n += 1

        n += 1
        e.cabecalho(ws, n, ["Motivo de exclusão", "Fonte", "Linhas"])
        for fonte, motivo, linhas in self.con.execute(
                "SELECT * FROM qualidade.exclusoes ORDER BY fonte DESC, linhas DESC").fetchall():
            n += 1
            e.escrever(ws, n, [motivo, fonte, linhas], [None, None, "#,##0"])
        n += 1
        zerados = self.valor("""SELECT count(*) FROM silver.vendas
                                WHERE desconto_preenchido_com_zero""")
        e.escrever(ws, n, ["Ajuste, sem exclusão: desconto vazio virou zero", "Vendas", zerados],
                   [None, None, "#,##0"])

        n += 2
        e.cabecalho(ws, n, ["Reconciliação", "Gold (SQL)", "Bases do Excel", "Diferença"])
        comparacoes = [
            ("Receita bruta", "SELECT sum(valor_bruto) FROM gold.fato_vendas", "Base_Comercial", "receita_bruta"),
            ("Descontos", "SELECT sum(valor_desconto) FROM gold.fato_vendas", "Base_Comercial", "descontos"),
            ("Devoluções", "SELECT sum(valor_devolvido) FROM gold.fato_devolucoes", "Base_Comercial", "devolucoes"),
            ("Receita líquida por vendedor", "SELECT sum(receita_liquida) FROM marts.movimento", "Base_Vendedor", "receita_liquida"),
            ("Receita líquida por produto", "SELECT sum(receita_liquida) FROM marts.movimento", "Base_Produto", "receita_liquida"),
            ("Lucro bruto", "SELECT sum(lucro_bruto) FROM marts.movimento", "Base_Comercial", "lucro_bruto"),
            ("Orçamento de receita", "SELECT sum(receita_orcada) FROM gold.fato_orcamento", "Base_Orcamento", "receita_orcada"),
        ]
        for nome, sql, base, medida in comparacoes:
            n += 1
            e.escrever(ws, n, [nome, float(self.valor(sql)),
                               f"=SUM({self.colunas[base, medida]})", f"=ROUND(B{n}-C{n},2)"],
                       [None, "#,##0.00", "#,##0.00", "#,##0.00"])

        n += 2
        e.cabecalho(ws, n, ["Verificação automática", "Falhas"])
        for nome, falhas in self.con.execute("SELECT * FROM qualidade.verificacoes").fetchall():
            n += 1
            e.escrever(ws, n, [nome, int(falhas)])

    def premissas(self):
        ws = self.wb["Premissas"]
        e.preparar(ws, "De onde vem cada número?", "Definições usadas em todas as abas.", [30, 100])
        e.cabecalho(ws, 4, ["Item", "Definição"])
        definicoes = [
            ("Dados", "100% sintéticos. Não representam nenhuma empresa real."),
            ("Período", f"jan/2025 a {MESES[self.ultimo_mes - 1]}/{ANO}, só meses fechados. Orçamento de {ANO}."),
            ("Receita bruta", "Quantidade × preço unitário dos itens faturados."),
            ("Receita líquida", "Receita bruta - descontos - devoluções. Não considera impostos."),
            ("CMV", "Custo no momento da venda - custo recuperado em devoluções."),
            ("Avaria e validade", "Devolução não recupera o custo: o produto é perdido."),
            ("Lucro bruto", "Receita líquida - CMV. Não inclui frete, comissão nem despesas fixas."),
            ("Margem bruta", "Lucro bruto / receita líquida."),
            ("Data da devolução", "A devolução reduz o resultado do mês em que ocorre, e não o da venda."),
            ("Canceladas", "Ficam fora de todos os indicadores."),
            ("Desconto vazio", "Tratado como zero e contado na aba Qualidade."),
            ("Custo vazio", "Item excluído, porque inflaria o lucro. Contado na aba Qualidade."),
            ("Acumulado", "De janeiro até o mês escolhido no Painel."),
            ("Projeção", "Realizado + orçamento restante × atingimento acumulado, por categoria. É linear, não é previsão estatística."),
            ("p.p.", "Pontos percentuais: de 18% para 16% é uma queda de 2 p.p."),
            ("Abas Base_*", "Saída do SQL, sem fórmulas. Podem alimentar tabelas dinâmicas."),
        ]
        for n, linha in enumerate(definicoes, start=5):
            e.escrever(ws, n, list(linha))
            ws.cell(n, 2).alignment = Alignment(wrap_text=True)

    def salvar(self, destino: Path):
        for aba in (self.painel, self.orcamento, self.margem, self.comercial,
                    self.produtos, self.qualidade, self.premissas):
            aba()
        self.wb.properties.creator = "bi-atacarejo"
        self.wb.properties.created = datetime(2026, 11, 1)
        self.wb.calculation.fullCalcOnLoad = True
        destino.parent.mkdir(parents=True, exist_ok=True)
        self.wb.save(destino)


def recalcular(arquivo: Path) -> bool:
    """
    O openpyxl grava fórmulas sem resultado, e visualizadores (celular, e-mail,
    modo protegido do Excel) mostrariam zeros. Se houver LibreOffice, ele calcula.
    """
    soffice = shutil.which("soffice")
    if not soffice:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [soffice, f"-env:UserInstallation={Path(tmp, 'perfil').as_uri()}", "--headless",
             "--convert-to", "xlsx", "--outdir", tmp, str(arquivo)],
            check=True, capture_output=True, timeout=180,
        )
        convertido = Path(tmp, arquivo.name)
        if not convertido.exists():
            return False
        shutil.copyfile(convertido, arquivo)
    return True


def gerar_planilha(banco: Path, destino: Path) -> bool:
    with duckdb.connect(str(banco), read_only=True) as con:
        Planilha(con).salvar(destino)
    return recalcular(destino)
