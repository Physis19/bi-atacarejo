-- Algum vendedor dá desconto fora do padrão em 2026?
-- Praticar: quartis e regra do IQR.
WITH vendedor AS (
    SELECT vendedor, sum(descontos) / sum(receita_bruta) AS desconto
    FROM marts.vendedor_mensal
    WHERE ano = 2026
    GROUP BY vendedor
),
quartis AS (
    SELECT quantile_cont(desconto, 0.25) AS q1, quantile_cont(desconto, 0.75) AS q3
    FROM vendedor
)
SELECT
    vendedor,
    round(100 * desconto, 2) AS desconto_pct,
    desconto > q3 + 1.5 * (q3 - q1) AS investigar
FROM vendedor, quartis
ORDER BY desconto DESC;
