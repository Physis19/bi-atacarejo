"""Aparência da planilha, separada das regras de cálculo."""

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

AZUL = "1F3A5F"
CINZA = "A6A6A6"
LARANJA = "D9822B"

REAIS = '#,##0;-#,##0;"-"'
PCT = "0.0%"
PP = '+0.0" p.p.";-0.0" p.p.";0.0" p.p."'
VAR_PCT = "+0.0%;-0.0%;0.0%"
VAR_REAIS = '+#,##0;-#,##0;"-"'

ENTRADA = PatternFill("solid", fgColor="FFF2CC")
ALERTA = Font(name="Calibri", color="C00000", bold=True)


def preparar(ws, titulo: str, subtitulo: str, larguras: list[int]):
    ws.sheet_view.showGridLines = False
    ws["A1"] = titulo
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=AZUL)
    ws["A2"] = subtitulo
    ws["A2"].font = Font(name="Calibri", italic=True, color="595959")
    for indice, largura in enumerate(larguras):
        ws.column_dimensions[chr(ord("A") + indice)].width = largura
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToHeight = 0


def secao(ws, linha: int, texto: str):
    ws.cell(linha, 1, texto).font = Font(name="Calibri", size=12, bold=True, color=AZUL)


def cabecalho(ws, linha: int, titulos: list[str], coluna: int = 1):
    for indice, titulo in enumerate(titulos):
        celula = ws.cell(linha, coluna + indice, titulo)
        celula.font = Font(name="Calibri", bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor=AZUL)
        celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[linha].height = 32


def escrever(ws, linha: int, valores: list, formatos: list | None = None, total=False):
    formatos = formatos or []
    for indice, valor in enumerate(valores):
        celula = ws.cell(linha, indice + 1, valor)
        celula.border = Border(bottom=Side(style="hair", color=CINZA))
        if indice < len(formatos) and formatos[indice]:
            celula.number_format = formatos[indice]
        if total:
            celula.font = Font(name="Calibri", bold=True)
            celula.fill = PatternFill("solid", fgColor="E8EEF4")
