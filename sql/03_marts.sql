-- Marts: a camada de negócio, dentro da Gold. É aqui que cada KPI é definido.
CREATE SCHEMA marts;

-- Vendas e devoluções são unidas com UNION ALL. Um JOIN entre os fatos
-- repetiria a venda quando houvesse mais de uma devolução do mesmo item.
CREATE VIEW marts.movimento AS
WITH lancamentos AS (
    SELECT data, id_cliente, id_vendedor, id_produto,
           valor_bruto, valor_desconto, 0 AS valor_devolvido, custo AS cmv
    FROM gold.fato_vendas
    UNION ALL
    SELECT data, id_cliente, id_vendedor, id_produto,
           0, 0, valor_devolvido, -custo_recuperado
    FROM gold.fato_devolucoes
)
SELECT
    l.*,
    d.ano, d.mes,
    p.categoria, c.canal, c.cidade,
    l.valor_bruto - l.valor_desconto - l.valor_devolvido         AS receita_liquida,
    l.valor_bruto - l.valor_desconto - l.valor_devolvido - l.cmv AS lucro_bruto
FROM lancamentos l
JOIN gold.dim_data d USING (data)
JOIN gold.dim_produto p USING (id_produto)
JOIN gold.dim_cliente c USING (id_cliente);

CREATE VIEW marts.comercial_mensal AS
SELECT
    ano, mes, categoria, canal, cidade,
    sum(valor_bruto)     AS receita_bruta,
    sum(valor_desconto)  AS descontos,
    sum(valor_devolvido) AS devolucoes,
    sum(receita_liquida) AS receita_liquida,
    sum(cmv)             AS cmv,
    sum(lucro_bruto)     AS lucro_bruto
FROM marts.movimento
GROUP BY ALL;

CREATE VIEW marts.vendedor_mensal AS
SELECT
    m.ano, m.mes, v.nome AS vendedor,
    sum(m.valor_bruto)     AS receita_bruta,
    sum(m.valor_desconto)  AS descontos,
    sum(m.receita_liquida) AS receita_liquida,
    sum(m.lucro_bruto)     AS lucro_bruto
FROM marts.movimento m
JOIN gold.dim_vendedor v USING (id_vendedor)
GROUP BY ALL;

-- Mediana não pode ser somada, então é calculada para cada mês de corte.
CREATE VIEW marts.vendedor_estatistica AS
WITH cortes AS (
    SELECT DISTINCT d.ano, d.mes
    FROM gold.dim_data d
    JOIN gold.fato_vendas f USING (data)
)
SELECT
    k.ano, k.mes AS mes_corte, v.nome AS vendedor,
    median(f.desconto_pct)::DOUBLE AS desconto_mediano,
    stddev_samp(f.desconto_pct)    AS desconto_desvio
FROM cortes k
JOIN gold.fato_vendas f ON year(f.data) = k.ano AND month(f.data) <= k.mes
JOIN gold.dim_vendedor v USING (id_vendedor)
GROUP BY ALL;

CREATE VIEW marts.produto_mensal AS
SELECT
    m.ano, m.mes, p.nome AS produto, m.categoria,
    sum(m.receita_liquida) AS receita_liquida,
    sum(m.lucro_bruto)     AS lucro_bruto
FROM marts.movimento m
JOIN gold.dim_produto p USING (id_produto)
GROUP BY ALL;

CREATE VIEW marts.devolucao_mensal AS
SELECT
    year(f.data) AS ano, month(f.data) AS mes,
    p.categoria, c.cidade, f.motivo,
    sum(f.valor_devolvido) AS valor_devolvido,
    sum(f.custo_perdido)   AS custo_perdido
FROM gold.fato_devolucoes f
JOIN gold.dim_produto p USING (id_produto)
JOIN gold.dim_cliente c USING (id_cliente)
GROUP BY ALL;

CREATE VIEW marts.orcado_realizado AS
WITH realizado AS (
    SELECT ano, mes, categoria,
           sum(receita_liquida) AS receita, sum(lucro_bruto) AS lucro
    FROM marts.movimento
    GROUP BY ALL
)
SELECT
    o.ano, o.mes, o.categoria,
    o.receita_orcada, r.receita AS receita_realizada,
    o.lucro_orcado,   r.lucro   AS lucro_realizado
FROM gold.fato_orcamento o
LEFT JOIN realizado r USING (ano, mes, categoria);
