-- Quando a margem de cada categoria mudou?
-- Praticar: CASE dentro de agregação e filtro por dimensão.
SELECT
    m.categoria, d.trimestre,
    round(100.0 * sum(CASE WHEN m.ano = 2025 THEN m.lucro_bruto END)
          / sum(CASE WHEN m.ano = 2025 THEN m.receita_liquida END), 1) AS margem_2025,
    round(100.0 * sum(CASE WHEN m.ano = 2026 THEN m.lucro_bruto END)
          / sum(CASE WHEN m.ano = 2026 THEN m.receita_liquida END), 1) AS margem_2026
FROM marts.movimento m
JOIN gold.dim_data d USING (data)
WHERE m.mes <= 10
GROUP BY m.categoria, d.trimestre
ORDER BY m.categoria, d.trimestre;
