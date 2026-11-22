-- Gold: modelo estrela. O grão de cada fato está acima da tabela.
CREATE SCHEMA gold;

CREATE TABLE gold.dim_produto  AS SELECT * FROM silver.produtos;
CREATE TABLE gold.dim_cliente  AS SELECT * FROM silver.clientes;
CREATE TABLE gold.dim_vendedor AS SELECT * FROM silver.vendedores;

-- Um dia por linha, incluindo novembro e dezembro por causa do orçamento.
CREATE TABLE gold.dim_data AS
SELECT
    d::DATE AS data,
    year(d) AS ano,
    month(d) AS mes,
    quarter(d) AS trimestre,
    ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'][month(d)] AS mes_nome
FROM generate_series(DATE '2025-01-01', DATE '2026-12-31', INTERVAL 1 DAY) AS s(d);

-- Grão: um item de nota faturada. O custo é o do momento da venda.
CREATE TABLE gold.fato_vendas AS
SELECT
    id_item, nota, data, id_cliente, id_vendedor, id_produto,
    quantidade, desconto_pct,
    (quantidade * preco_unitario)::DECIMAL(18, 2)                      AS valor_bruto,
    round(quantidade * preco_unitario * desconto_pct, 2)::DECIMAL(18, 2) AS valor_desconto,
    (quantidade * custo_unitario)::DECIMAL(18, 2)                      AS custo
FROM silver.vendas;

-- Grão: uma devolução, lançada no mês em que aconteceu (e não no mês da venda).
-- Avaria e validade não recuperam custo: o produto é perdido.
CREATE TABLE gold.fato_devolucoes AS
SELECT
    d.id_devolucao, d.id_item, d.data,
    v.id_cliente, v.id_vendedor, v.id_produto,
    d.quantidade, d.motivo,
    round(d.quantidade * v.preco_unitario * (1 - v.desconto_pct), 2)::DECIMAL(18, 2) AS valor_devolvido,
    (CASE WHEN d.motivo IN ('avaria', 'validade') THEN 0
          ELSE d.quantidade * v.custo_unitario END)::DECIMAL(18, 2) AS custo_recuperado,
    (CASE WHEN d.motivo IN ('avaria', 'validade') THEN d.quantidade * v.custo_unitario
          ELSE 0 END)::DECIMAL(18, 2) AS custo_perdido
FROM silver.devolucoes d
JOIN silver.vendas v USING (id_item);

-- Grão: categoria por mês. Não se liga direto aos itens, só depois de agregar.
CREATE TABLE gold.fato_orcamento AS SELECT * FROM silver.orcamento;
