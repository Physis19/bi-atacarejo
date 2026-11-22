CREATE SCHEMA qualidade;

CREATE VIEW qualidade.resumo AS
SELECT 'Vendas' AS fonte, count(*) AS lidas,
       count(*) FILTER (WHERE motivo_exclusao IS NULL) AS validas,
       count(*) FILTER (WHERE motivo_exclusao IS NOT NULL) AS excluidas
FROM silver.vendas_avaliadas
UNION ALL
SELECT 'Devoluções', count(*),
       count(*) FILTER (WHERE motivo_exclusao IS NULL),
       count(*) FILTER (WHERE motivo_exclusao IS NOT NULL)
FROM silver.devolucoes_avaliadas;

CREATE VIEW qualidade.exclusoes AS
SELECT 'Vendas' AS fonte, motivo_exclusao AS motivo, count(*) AS linhas
FROM silver.vendas_avaliadas WHERE motivo_exclusao IS NOT NULL GROUP BY ALL
UNION ALL
SELECT 'Devoluções', motivo_exclusao, count(*)
FROM silver.devolucoes_avaliadas WHERE motivo_exclusao IS NOT NULL GROUP BY ALL;

-- Cada verificação precisa dar zero. O pipeline para se alguma falhar.
CREATE VIEW qualidade.verificacoes AS
SELECT 'Linhas de vendas perdidas entre Bronze e Silver' AS verificacao,
       abs((SELECT count(*) FROM bronze.vendas)
         - (SELECT count(*) FROM silver.vendas_avaliadas))::BIGINT AS falhas
UNION ALL
SELECT 'Linhas de devoluções perdidas entre Bronze e Silver',
       abs((SELECT count(*) FROM bronze.devolucoes)
         - (SELECT count(*) FROM silver.devolucoes_avaliadas))
UNION ALL
SELECT 'Produtos sem categoria', count(*) FROM silver.produtos WHERE categoria IS NULL
UNION ALL
SELECT 'Clientes sem cidade ou data de cadastro', count(*)
FROM silver.clientes WHERE cidade IS NULL OR data_cadastro IS NULL
UNION ALL
SELECT 'Vendas anteriores ao cadastro do cliente', count(*)
FROM gold.fato_vendas f JOIN gold.dim_cliente c USING (id_cliente)
WHERE f.data < c.data_cadastro
UNION ALL
SELECT 'Itens de venda repetidos', count(*) - count(DISTINCT id_item) FROM gold.fato_vendas
UNION ALL
SELECT 'Itens com devolução acima da venda', count(*)
FROM (
    SELECT id_item
    FROM gold.fato_vendas v
    JOIN (SELECT id_item, sum(quantidade) AS devolvida
          FROM gold.fato_devolucoes GROUP BY id_item) d USING (id_item)
    WHERE d.devolvida > v.quantidade
)
UNION ALL
SELECT 'Lançamentos perdidos nos joins dos marts',
       abs((SELECT count(*) FROM gold.fato_vendas)
         + (SELECT count(*) FROM gold.fato_devolucoes)
         - (SELECT count(*) FROM marts.movimento))
UNION ALL
SELECT 'Células de orçamento faltando', abs(count(*) - 84) FROM gold.fato_orcamento
UNION ALL
SELECT 'Orçamento diferente da linha TOTAL do financeiro',
       CASE WHEN (SELECT sum(receita_orcada + lucro_orcado) FROM gold.fato_orcamento)
               = (SELECT sum(valor::DECIMAL(18, 2)) FROM bronze.orcamento WHERE categoria = 'TOTAL')
            THEN 0 ELSE 1 END;
