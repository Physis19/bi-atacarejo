-- Como a receita líquida evolui contra o mês anterior e o mesmo mês de 2025?
-- Praticar: CTE e LAG.
WITH mensal AS (
    SELECT ano, mes, sum(receita_liquida) AS receita
    FROM marts.movimento
    GROUP BY ano, mes
)
SELECT
    ano, mes, receita,
    round(100.0 * (receita / lag(receita) OVER (ORDER BY ano, mes) - 1), 1) AS var_mes_pct,
    round(100.0 * (receita / lag(receita) OVER (PARTITION BY mes ORDER BY ano) - 1), 1) AS var_ano_pct
FROM mensal
ORDER BY ano, mes;
