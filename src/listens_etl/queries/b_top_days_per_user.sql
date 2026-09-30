-- Each user's 3 days with the most listens.
-- Ties go to the earlier date. Users with fewer than 3 active days get fewer rows.
WITH daily AS (
    SELECT
        user_name,
        listened_date,
        count(*) AS number_of_listens
    FROM listens
    GROUP BY user_name, listened_date
)
SELECT
    user_name     AS "user",
    number_of_listens,
    listened_date AS "date"
FROM daily
QUALIFY row_number() OVER (
    PARTITION BY user_name ORDER BY number_of_listens DESC, listened_date
) <= 3
ORDER BY "user", number_of_listens DESC, "date";
