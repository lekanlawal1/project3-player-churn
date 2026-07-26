-- 02: Churn label — did the player leave their club between editions?
--
-- Scope: players present in BOTH editions with a club on both sides.
--   - No FIFA 18 club → free agent, nothing to churn from.
--   - Missing from FIFA 19 → retirement or the league lost its game license;
--     indistinguishable from a transfer in this data, so excluded rather than
--     mislabeled (decision documented in the cleaning log).
--
-- churned = 1 when the FIFA 19 club differs from the player's FIFA 18 club
-- *after* translating the FIFA 18 club to its FIFA 19 canonical name (01).

CREATE OR REPLACE TABLE labeled AS
SELECT
    p.*,
    n.club_19,
    CASE
        WHEN n.club_19 IS DISTINCT FROM COALESCE(m.club_19_canonical, p.club)
        THEN 1 ELSE 0
    END AS churned
FROM clean_f18 p
JOIN clean_f19_clubs n ON p.id = n.id
LEFT JOIN club_mapping m ON p.club = m.club_18
WHERE p.club IS NOT NULL AND n.club_19 IS NOT NULL;
