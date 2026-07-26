-- 01: Entity resolution — map each FIFA 18 club to its FIFA 19 name.
--
-- Problem: club labels drift between editions ("Real Madrid CF" → "Real Madrid",
-- "FC Bayern Munich" → "FC Bayern München"). A naive string comparison counts a
-- whole renamed squad as "transferred", inflating churn from ~29% to 45%.
--
-- Fix: majority vote. For each FIFA 18 club, the FIFA 19 club most of its
-- retained players ended up at IS the same club under its new name — real
-- transfers scatter across many destinations and lose the vote. Requires at
-- least 3 voters so a tiny club with one retained player can't self-certify.

CREATE OR REPLACE TABLE club_mapping AS
WITH retained AS (
    SELECT p.club AS club_18, n.club_19
    FROM clean_f18 p
    JOIN clean_f19_clubs n ON p.id = n.id
    WHERE p.club IS NOT NULL AND n.club_19 IS NOT NULL
),
votes AS (
    SELECT
        club_18,
        club_19,
        COUNT(*) AS voters,
        ROW_NUMBER() OVER (PARTITION BY club_18 ORDER BY COUNT(*) DESC, club_19) AS rk
    FROM retained
    GROUP BY club_18, club_19
)
SELECT club_18, club_19 AS club_19_canonical, voters
FROM votes
WHERE rk = 1 AND voters >= 3;
