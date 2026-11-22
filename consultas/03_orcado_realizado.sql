-- Quanto cada categoria atingiu do orçamento até agora?
-- Praticar: comparar fatos de grãos diferentes depois de agregar.
SELECT
    categoria,
    round(100.0 * sum(receita_realizada) / sum(receita_orcada), 1) AS receita_atingida_pct,
    round(100.0 * sum(lucro_realizado) / sum(lucro_orcado), 1)     AS lucro_atingido_pct
FROM marts.orcado_realizado
WHERE receita_realizada IS NOT NULL
GROUP BY categoria
ORDER BY lucro_atingido_pct;
