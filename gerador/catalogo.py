"""Cadastros base da distribuidora fictícia. Nenhuma marca ou empresa real."""

# categoria: (peso nas vendas, markup, [(produto, custo da embalagem de venda)])
CATEGORIAS = {
    "Mercearia": (26, 1.22, [
        ("Arroz branco fardo 30kg", 112), ("Arroz parboilizado fardo 30kg", 108),
        ("Feijão carioca fardo 10kg", 58), ("Feijão preto fardo 10kg", 54),
        ("Açúcar cristal fardo 30kg", 92), ("Café torrado cx 10x250g", 118),
        ("Óleo de soja cx 20x900ml", 126), ("Macarrão espaguete fardo 10x500g", 29),
        ("Farinha de mandioca fardo 20kg", 74), ("Flocão de milho fardo 20x500g", 31),
        ("Extrato de tomate cx 24x300g", 46), ("Biscoito cream cracker cx 20x350g", 72),
    ]),
    "Bebidas": (36, 1.27, [
        ("Refrigerante cola fardo 6x2L", 38), ("Refrigerante guaraná fardo 6x2L", 31),
        ("Refrigerante laranja fardo 6x2L", 29), ("Água mineral fardo 12x500ml", 11),
        ("Água com gás fardo 12x500ml", 15), ("Cerveja pilsen cx 12x350ml", 33),
        ("Cerveja puro malte cx 12x350ml", 41), ("Energético fardo 6x473ml", 36),
        ("Suco de uva cx 12x1L", 64), ("Suco em pó cx 15 unidades", 14),
        ("Cachaça cx 12x965ml", 98), ("Isotônico fardo 6x500ml", 22),
    ]),
    "Frios e laticínios": (14, 1.30, [
        ("Queijo muçarela peça 4kg", 112), ("Queijo prato peça 3kg", 96),
        ("Queijo coalho peça 2kg", 58), ("Presunto cozido peça 3kg", 54),
        ("Mortadela peça 4kg", 37), ("Manteiga cx 12x200g", 88),
        ("Margarina cx 12x500g", 52), ("Requeijão balde 3,6kg", 61),
        ("Iogurte cx 12x170g", 24), ("Leite UHT cx 12x1L", 54),
        ("Creme de leite cx 27x200g", 69), ("Salame peça 1kg", 43),
    ]),
    "Congelados": (12, 1.29, [
        ("Frango inteiro cx 18kg", 148), ("Coxa e sobrecoxa cx 15kg", 119),
        ("Filé de peito cx 12kg", 161), ("Linguiça toscana cx 10kg", 128),
        ("Hambúrguer bovino cx 36 un", 47), ("Batata pré-frita cx 10kg", 104),
        ("Pão de queijo pct 5kg", 59), ("Salsicha pct 5kg", 42),
        ("Polpa de fruta cx 10kg", 71), ("Empanado de frango cx 5kg", 63),
        ("Lasanha cx 12x600g", 97), ("Sorvete balde 10L", 78),
    ]),
    "Limpeza": (10, 1.35, [
        ("Detergente cx 24x500ml", 43), ("Sabão em pó cx 20x800g", 132),
        ("Sabão em barra cx 10x1kg", 76), ("Água sanitária cx 12x1L", 25),
        ("Desinfetante cx 6x2L", 28), ("Amaciante cx 6x2L", 39),
        ("Esponja pct 60 un", 34), ("Álcool 70 cx 12x1L", 72),
        ("Limpador multiuso cx 12x500ml", 36), ("Lã de aço fardo 14 pct", 27),
        ("Inseticida cx 12x300ml", 104), ("Saco de lixo fardo 10 rolos", 30),
    ]),
    "Higiene": (9, 1.33, [
        ("Papel higiênico fardo 64 rolos", 68), ("Creme dental cx 12x90g", 35),
        ("Sabonete cx 72x85g", 94), ("Shampoo cx 12x325ml", 101),
        ("Condicionador cx 12x325ml", 106), ("Desodorante cx 12x150ml", 112),
        ("Absorvente fardo 24 pct", 73), ("Fralda fardo 8 pct", 138),
        ("Escova dental cx 12 un", 32), ("Lenço umedecido cx 12 pct", 65),
        ("Aparelho de barbear cx 24 un", 57), ("Algodão fardo 20 pct", 41),
    ]),
    "Descartáveis": (7, 1.17, [
        ("Copo 200ml cx 2500 un", 89), ("Copo 50ml cx 5000 un", 78),
        ("Prato descartável cx 500 un", 64), ("Garfo descartável cx 1000 un", 45),
        ("Guardanapo fardo 40 pct", 38), ("Marmita alumínio cx 100 un", 49),
        ("Embalagem isopor fardo 100 un", 33), ("Sacola plástica fardo 1000 un", 36),
        ("Filme PVC bobina 300m", 24), ("Papel alumínio cx 25 rolos", 91),
        ("Canudo cx 2000 un", 21), ("Papel toalha fardo 12 pct", 44),
    ]),
}

# canal: (clientes, itens por nota, quantidade máxima, desconto típico, fator de preço, frequência)
CANAIS = {
    "Mercadinho": (170, (3, 6), 8, 0.025, 1.00, 1.0),
    "Supermercado": (45, (4, 8), 16, 0.040, 0.98, 1.4),
    "Bar e restaurante": (105, (2, 5), 6, 0.020, 1.02, 0.9),
    "Consumidor final": (120, (1, 3), 2, 0.005, 1.07, 0.5),
}

# cidade: (UF, peso)
CIDADES = {
    "Maceió": ("AL", 36), "Arapiraca": ("AL", 14), "Rio Largo": ("AL", 8),
    "Palmeira dos Índios": ("AL", 7), "São Miguel dos Campos": ("AL", 6),
    "Penedo": ("AL", 6), "Marechal Deodoro": ("AL", 5), "União dos Palmares": ("AL", 6),
    "Garanhuns": ("PE", 7), "Propriá": ("SE", 5),
}

SAZONALIDADE = [0.96, 0.94, 1.00, 0.98, 1.01, 1.09, 0.99, 0.98, 1.00, 1.03, 1.06, 1.22]
