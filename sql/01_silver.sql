-- Silver: tipa, padroniza e separa o que não pode entrar na análise.
-- Toda linha da Bronze é válida ou tem exatamente um motivo de exclusão.
CREATE SCHEMA silver;

CREATE MACRO texto_para_data(v) AS coalesce(
    try_strptime(trim(v), '%Y-%m-%d'),
    try_strptime(trim(v), '%d/%m/%Y')
)::DATE;

CREATE MACRO texto_para_numero(v) AS replace(nullif(trim(v), ''), ',', '.');

CREATE TABLE silver.produtos AS
WITH categorias(categoria) AS (
    VALUES ('Mercearia'), ('Bebidas'), ('Frios e laticínios'), ('Congelados'),
           ('Limpeza'), ('Higiene'), ('Descartáveis')
)
SELECT p.id_produto, trim(p.nome) AS nome, c.categoria
FROM bronze.produtos p
LEFT JOIN categorias c ON lower(trim(p.categoria)) = lower(c.categoria)
QUALIFY row_number() OVER (PARTITION BY p.id_produto ORDER BY p._linha) = 1;

CREATE TABLE silver.clientes AS
WITH cidades(cidade) AS (
    VALUES ('Maceió'), ('Arapiraca'), ('Rio Largo'), ('Palmeira dos Índios'),
           ('São Miguel dos Campos'), ('Penedo'), ('Marechal Deodoro'),
           ('União dos Palmares'), ('Garanhuns'), ('Propriá')
)
SELECT
    b.id_cliente,
    trim(b.nome)                     AS nome,
    trim(b.canal)                    AS canal,
    c.cidade,
    upper(trim(b.uf))                AS uf,
    texto_para_data(b.data_cadastro) AS data_cadastro
FROM bronze.clientes b
LEFT JOIN cidades c ON lower(trim(b.cidade)) = lower(c.cidade)
QUALIFY row_number() OVER (PARTITION BY b.id_cliente ORDER BY b._linha) = 1;

CREATE TABLE silver.vendedores AS
SELECT id_vendedor, trim(nome) AS nome
FROM bronze.vendedores
QUALIFY row_number() OVER (PARTITION BY id_vendedor ORDER BY _linha) = 1;

-- Vendas
CREATE TABLE silver.vendas_avaliadas AS
WITH tipadas AS (
    SELECT
        _linha, id_item, nota, id_cliente, id_vendedor, id_produto,
        texto_para_data(data)                                         AS data,
        try_cast(quantidade AS INTEGER)                               AS quantidade,
        try_cast(texto_para_numero(preco_unitario) AS DECIMAL(10, 2)) AS preco_unitario,
        try_cast(texto_para_numero(custo_unitario) AS DECIMAL(10, 2)) AS custo_unitario,
        coalesce(try_cast(texto_para_numero(desconto_pct) AS DECIMAL(6, 3)), 0) AS desconto_pct,
        texto_para_numero(desconto_pct) IS NULL                       AS desconto_preenchido_com_zero,
        upper(trim(status))                                           AS status,
        row_number() OVER (PARTITION BY id_item ORDER BY _linha)      AS ocorrencia
    FROM bronze.vendas
)
SELECT
    t.*,
    CASE
        WHEN t.ocorrencia > 1 THEN 'Duplicada'
        WHEN t.status = 'CANCELADA' THEN 'Cancelada (regra de negócio)'
        WHEN t.status IS DISTINCT FROM 'FATURADA' THEN 'Status desconhecido'
        WHEN t.data IS NULL THEN 'Data inválida'
        WHEN t.quantidade IS NULL OR t.quantidade <= 0 THEN 'Quantidade inválida'
        WHEN t.preco_unitario IS NULL OR t.preco_unitario <= 0 THEN 'Preço inválido'
        WHEN t.custo_unitario IS NULL OR t.custo_unitario <= 0 THEN 'Custo ausente'
        WHEN t.desconto_pct NOT BETWEEN 0 AND 1 THEN 'Desconto inválido'
        WHEN p.id_produto IS NULL THEN 'Produto sem cadastro'
        WHEN c.id_cliente IS NULL THEN 'Cliente sem cadastro'
        WHEN v.id_vendedor IS NULL THEN 'Vendedor sem cadastro'
    END AS motivo_exclusao
FROM tipadas t
LEFT JOIN silver.produtos p USING (id_produto)
LEFT JOIN silver.clientes c USING (id_cliente)
LEFT JOIN silver.vendedores v USING (id_vendedor);

CREATE VIEW silver.vendas AS
SELECT * FROM silver.vendas_avaliadas WHERE motivo_exclusao IS NULL;

-- Devoluções: precisam de uma venda válida e não podem superar o que foi vendido.
CREATE TABLE silver.devolucoes_avaliadas AS
WITH tipadas AS (
    SELECT
        _linha, id_devolucao, id_item,
        texto_para_data(data)           AS data,
        try_cast(quantidade AS INTEGER) AS quantidade,
        lower(trim(motivo))             AS motivo,
        row_number() OVER (PARTITION BY id_devolucao ORDER BY _linha) AS ocorrencia
    FROM bronze.devolucoes
)
SELECT
    d.*,
    CASE
        WHEN d.ocorrencia > 1 THEN 'Duplicada'
        WHEN v.id_item IS NULL THEN 'Sem venda válida'
        WHEN d.data IS NULL OR d.data < v.data THEN 'Data inválida'
        WHEN d.quantidade IS NULL OR d.quantidade <= 0 THEN 'Quantidade inválida'
        WHEN d.quantidade > v.quantidade THEN 'Maior que a venda'
    END AS motivo_exclusao
FROM tipadas d
LEFT JOIN silver.vendas v USING (id_item);

CREATE VIEW silver.devolucoes AS
SELECT * FROM silver.devolucoes_avaliadas WHERE motivo_exclusao IS NULL;

-- Orçamento: descarta a linha de total para não somar duas vezes.
CREATE TABLE silver.orcamento AS
SELECT
    2026               AS ano,
    mes::INTEGER       AS mes,
    trim(categoria)    AS categoria,
    sum(CASE WHEN aba = 'Receita' THEN valor::DECIMAL(18, 2) ELSE 0 END)     AS receita_orcada,
    sum(CASE WHEN aba = 'Lucro Bruto' THEN valor::DECIMAL(18, 2) ELSE 0 END) AS lucro_orcado
FROM bronze.orcamento
WHERE upper(trim(categoria)) <> 'TOTAL'
GROUP BY ALL;
