-- Quais produtos formam 80% da receita de 2026?
-- Praticar: soma acumulada com window function.
WITH produto AS (
    SELECT produto, sum(receita_liquida) AS receita
    FROM marts.produto_mensal
    WHERE ano = 2026
    GROUP BY produto
),
acumulado AS (
    SELECT
        produto, receita,
        sum(receita) OVER (ORDER BY receita DESC, produto) / sum(receita) OVER () AS pct_acumulado,
        receita / sum(receita) OVER () AS pct
    FROM produto
)
SELECT
    produto, receita,
    round(100 * pct_acumulado, 1) AS acumulado_pct,
    CASE WHEN pct_acumulado - pct < 0.80 THEN 'A'
         WHEN pct_acumulado - pct < 0.95 THEN 'B'
         ELSE 'C' END AS classe
FROM acumulado
ORDER BY receita DESC;
