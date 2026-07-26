-- 03: Feature engineering — the model-ready table.
--
-- Squad-context features are the point of doing this in SQL: a player's churn
-- risk isn't just who they are, it's where they stand in their squad's pecking
-- order. Window functions over PARTITION BY club express that directly.
-- All features are computed from the FIFA 18 snapshot only (no leakage).

CREATE OR REPLACE TABLE features AS
SELECT
    id,
    name,
    club,
    churned,

    -- who the player is
    age,
    CASE
        WHEN age <= 20 THEN 'U21'
        WHEN age <= 24 THEN '21-24'
        WHEN age <= 28 THEN '25-28'
        WHEN age <= 32 THEN '29-32'
        ELSE '33+'
    END AS age_band,
    overall,
    potential,
    potential - overall AS growth_headroom,          -- young talent outgrowing the club
    wage_eur,
    value_eur,
    primary_position,
    CASE
        WHEN primary_position = 'GK' THEN 'GK'
        WHEN primary_position IN ('CB', 'LB', 'RB', 'LWB', 'RWB') THEN 'DEF'
        WHEN primary_position IN ('CDM', 'CM', 'CAM', 'LM', 'RM') THEN 'MID'
        ELSE 'FWD'
    END AS position_group,

    -- where the player stands in the squad (window functions)
    COUNT(*)      OVER club_w                                    AS squad_size,
    ROUND(AVG(overall) OVER club_w, 2)                           AS club_avg_overall,
    ROUND(overall - AVG(overall) OVER club_w, 2)                 AS overall_vs_club_avg,
    RANK() OVER (PARTITION BY club ORDER BY overall DESC)        AS overall_rank_in_club,
    RANK() OVER (PARTITION BY club ORDER BY wage_eur DESC NULLS LAST) AS wage_rank_in_club,
    ROUND(wage_eur / NULLIF(MEDIAN(wage_eur) OVER club_w, 0), 3) AS wage_to_club_median,
    CASE
        WHEN RANK() OVER (PARTITION BY club ORDER BY overall DESC) <= 3 THEN 1 ELSE 0
    END AS is_top3_in_club

FROM labeled
WINDOW club_w AS (PARTITION BY club);
