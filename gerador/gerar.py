"""
Simula as extrações de um ERP e o orçamento enviado pelo financeiro.

Usa só random.Random(SEED) e datas fixas: rodar de novo gera os mesmos dados.
Os arquivos saem com problemas propositais de qualidade, como numa extração real.
"""

import calendar
import csv
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook

from gerador import cenario
from gerador.catalogo import CANAIS, CATEGORIAS, CIDADES, SAZONALIDADE

SEED = 42
INICIO = date(2025, 1, 1)
FIM = date(2026, 10, 31)
NOTAS_POR_MES = 620
CRESCIMENTO_2026 = 1.09
META_CRESCIMENTO = 1.12


def numero(valor, casas=2) -> str:
    """Formata como o ERP exporta: vírgula decimal."""
    return f"{valor:.{casas}f}".replace(".", ",")


def gravar_csv(caminho: Path, linhas: list[dict]):
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]), delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)


def criar_cadastros(rng: random.Random):
    vendedores = [
        {"id_vendedor": f"V{i:02}", "nome": f"Vendedor {i:02}"} for i in range(1, 13)
    ]

    produtos = []
    for categoria, (_, markup, itens) in CATEGORIAS.items():
        for nome, custo in itens:
            produtos.append({
                "id_produto": f"P{len(produtos) + 1:03}", "nome": nome,
                "categoria": categoria, "custo": custo,
                "markup": markup * rng.uniform(0.97, 1.03),
                "peso": rng.lognormvariate(0, 0.8),
            })

    clientes = []
    for canal, (quantidade, *_) in CANAIS.items():
        for i in range(quantidade):
            cidade = rng.choices(list(CIDADES), [p for _, p in CIDADES.values()])[0]
            cadastro = INICIO - timedelta(days=rng.randint(30, 1800))
            if rng.random() < 0.05:
                cadastro = INICIO + timedelta(days=rng.randint(0, 540))
            clientes.append({
                "id_cliente": f"C{len(clientes) + 1:04}",
                "nome": f"{canal} {i + 1:03}", "canal": canal,
                "cidade": cidade, "uf": CIDADES[cidade][0],
                "data_cadastro": cadastro,
                "id_vendedor": vendedores[i % len(vendedores)]["id_vendedor"],
            })
    return vendedores, produtos, clientes


def simular(rng: random.Random, produtos, clientes):
    por_categoria = defaultdict(list)
    for produto in produtos:
        por_categoria[produto["categoria"]].append(produto)
    categorias = list(CATEGORIAS)
    pesos_categoria = [CATEGORIAS[c][0] for c in categorias]
    peso_cliente = {
        c["id_cliente"]: CANAIS[c["canal"]][5] * rng.lognormvariate(0, 0.35) for c in clientes
    }

    vendas, devolucoes = [], []
    nota = 0
    for ano in (2025, 2026):
        for mes in range(1, 13):
            if date(ano, mes, 1) > FIM:
                break
            ultimo = calendar.monthrange(ano, mes)[1]
            crescimento = CRESCIMENTO_2026 if ano == 2026 else 1
            quantidade_notas = round(
                NOTAS_POR_MES * SAZONALIDADE[mes - 1] * crescimento * rng.uniform(0.98, 1.02)
            )
            ativos = [c for c in clientes if c["data_cadastro"] <= date(ano, mes, 1)]
            pesos = [peso_cliente[c["id_cliente"]] for c in ativos]

            for dia in sorted(rng.randint(1, ultimo) for _ in range(quantidade_notas)):
                nota += 1
                data = date(ano, mes, dia)
                cliente = rng.choices(ativos, pesos)[0]
                _, itens, qtd_max, desconto_base, fator_canal, _ = CANAIS[cliente["canal"]]
                status = "CANCELADA" if rng.random() < 0.018 else "FATURADA"
                inflacao = 1 + 0.003 * ((ano - 2025) * 12 + mes - 1)

                for _ in range(rng.randint(*itens)):
                    categoria = rng.choices(categorias, pesos_categoria)[0]
                    lista = por_categoria[categoria]
                    produto = rng.choices(lista, [p["peso"] for p in lista])[0]
                    base = produto["custo"] * inflacao
                    custo = round(base * cenario.fator_custo(data, categoria), 2)
                    preco = round(
                        base * produto["markup"] * fator_canal
                        * cenario.fator_preco(data, categoria), 2
                    )
                    desconto = max(0, rng.gauss(desconto_base, 0.012))
                    desconto += cenario.desconto_extra(data, cliente["id_vendedor"])
                    venda = {
                        "id_item": f"I{len(vendas) + 1:06}", "nota": f"NF{nota:06}",
                        "data": data, "id_cliente": cliente["id_cliente"],
                        "id_vendedor": cliente["id_vendedor"],
                        "id_produto": produto["id_produto"], "categoria": categoria,
                        "quantidade": rng.randint(1, qtd_max), "preco_unitario": preco,
                        "custo_unitario": custo, "desconto_pct": round(desconto, 3),
                        "status": status,
                    }
                    vendas.append(venda)
                    if status == "CANCELADA":
                        continue

                    extra, motivo_extra = cenario.devolucao_extra(data, categoria, cliente["cidade"])
                    sorteio = rng.random()
                    if sorteio >= 0.016 + extra:
                        continue
                    if sorteio < extra:
                        motivo = motivo_extra
                    else:
                        motivo = rng.choices(
                            ["erro de pedido", "atraso", "desistência", "avaria", "validade"],
                            [30, 20, 20, 22, 8],
                        )[0]
                    data_devolucao = data + timedelta(days=rng.randint(1, 12))
                    if data_devolucao <= FIM:
                        devolucoes.append({
                            "id_devolucao": f"D{len(devolucoes) + 1:05}",
                            "id_item": venda["id_item"], "data": data_devolucao,
                            "quantidade": rng.randint(max(1, venda["quantidade"] // 2), venda["quantidade"]),
                            "motivo": motivo,
                        })
    return vendas, devolucoes


def criar_orcamento(rng: random.Random, vendas, devolucoes, destino: Path):
    """O financeiro parte de 2025 e aplica a meta de crescimento."""
    receita, lucro = defaultdict(float), defaultdict(float)
    por_item = {v["id_item"]: v for v in vendas}

    def somar(venda, quantidade, recupera_custo=True):
        valor = quantidade * venda["preco_unitario"] * (1 - venda["desconto_pct"])
        custo = quantidade * venda["custo_unitario"] if recupera_custo else 0
        receita[venda["categoria"]] += valor
        lucro[venda["categoria"]] += valor - custo

    for venda in vendas:
        if venda["data"].year == 2025 and venda["status"] == "FATURADA":
            somar(venda, venda["quantidade"])
    for dev in devolucoes:
        if dev["data"].year == 2025:
            somar(por_item[dev["id_item"]], -dev["quantidade"],
                  dev["motivo"] not in ("avaria", "validade"))

    pasta = Workbook()
    abas = {"Receita": pasta.active, "Lucro Bruto": pasta.create_sheet("Lucro Bruto")}
    abas["Receita"].title = "Receita"
    totais = {nome: [0] * 12 for nome in abas}
    for aba in abas.values():
        aba.append(["Categoria", *range(1, 13)])
    for categoria in CATEGORIAS:
        ajuste = rng.uniform(0.99, 1.01)
        for nome, base in (("Receita", receita), ("Lucro Bruto", lucro)):
            anual = base[categoria] * META_CRESCIMENTO * ajuste
            valores = [round(anual * s / sum(SAZONALIDADE), -2) for s in SAZONALIDADE]
            abas[nome].append([categoria, *valores])
            totais[nome] = [t + v for t, v in zip(totais[nome], valores)]
    for nome, aba in abas.items():
        aba.append(["TOTAL", *totais[nome]])
    pasta.save(destino)


def exportar_com_sujeira(rng, destino: Path, vendedores, produtos, clientes, vendas, devolucoes):
    def data_erp(valor: date) -> str:
        return valor.strftime("%d/%m/%Y") if rng.random() < 0.3 else valor.isoformat()

    linhas_vendas = []
    for v in vendas:
        linha = {k: val for k, val in v.items() if k != "categoria"}
        linha.update(
            data=data_erp(v["data"]), preco_unitario=numero(v["preco_unitario"]),
            custo_unitario=numero(v["custo_unitario"]),
            desconto_pct=numero(v["desconto_pct"], 3),
        )
        sorteio = rng.random()
        if sorteio < 0.002:
            linha["quantidade"] = rng.choice([0, -1])
        elif sorteio < 0.003:
            linha["id_produto"] = "P999"
        elif sorteio < 0.004:
            linha["data"] = "31/02/2026"
        elif sorteio < 0.005:
            linha["custo_unitario"] = ""
        elif sorteio < 0.013:
            linha["desconto_pct"] = ""
        elif sorteio < 0.04:
            linha["status"] = f" {linha['status'].lower()} "
        linhas_vendas.append(linha)
        if rng.random() < 0.006:
            linhas_vendas.append(dict(linha))  # exportação repetida

    linhas_devolucoes = []
    for d in devolucoes:
        linha = dict(d, data=data_erp(d["data"]))
        sorteio = rng.random()
        if sorteio < 0.008:
            linha["id_item"] = "I999999"
        elif sorteio < 0.016:
            linha["quantidade"] = 999
        linhas_devolucoes.append(linha)
        if rng.random() < 0.01:
            linhas_devolucoes.append(dict(linha))

    linhas_clientes = []
    for c in clientes:
        linha = {k: val for k, val in c.items() if k != "id_vendedor"}
        linha["data_cadastro"] = data_erp(c["data_cadastro"])
        if rng.random() < 0.08:
            linha.update(cidade=f" {c['cidade'].upper()} ", uf=c["uf"].lower())
        linhas_clientes.append(linha)
        if rng.random() < 0.02:
            linhas_clientes.append(dict(linha))

    linhas_produtos = [
        {
            "id_produto": p["id_produto"], "nome": p["nome"],
            "categoria": p["categoria"].upper() if rng.random() < 0.1 else p["categoria"],
        }
        for p in produtos
    ]

    gravar_csv(destino / "vendas.csv", linhas_vendas)
    gravar_csv(destino / "devolucoes.csv", linhas_devolucoes)
    gravar_csv(destino / "clientes.csv", linhas_clientes)
    gravar_csv(destino / "produtos.csv", linhas_produtos)
    gravar_csv(destino / "vendedores.csv", vendedores)


def gerar(destino: Path):
    erp, financeiro = destino / "erp", destino / "financeiro"
    erp.mkdir(parents=True, exist_ok=True)
    financeiro.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    vendedores, produtos, clientes = criar_cadastros(rng)
    vendas, devolucoes = simular(rng, produtos, clientes)
    criar_orcamento(rng, vendas, devolucoes, financeiro / "orcamento_2026.xlsx")
    exportar_com_sujeira(rng, erp, vendedores, produtos, clientes, vendas, devolucoes)
