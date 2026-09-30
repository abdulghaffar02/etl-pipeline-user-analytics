-- Daily active users: a user is active on day X if they listened in [X-6 days, X].
-- Each active (user, day) is spread over the 7 days it counts for, then users are
-- counted once per day. Summing daily counts would count some users several times.
WITH user_days AS (
    SELECT DISTINCT user_name, listened_date FROM listens
),
active AS (
    SELECT DISTINCT user_name, listened_date + CAST(n AS INTEGER) AS day
    FROM user_days, range(7) AS t(n)
),
days AS (
    SELECT CAST(d AS DATE) AS day
    FROM (SELECT min(listened_date) AS first_day, max(listened_date) AS last_day FROM listens),
         generate_series(first_day, last_day, INTERVAL 1 DAY) AS t(d)
),
total AS (
    SELECT count(DISTINCT user_name) AS users FROM listens
)
SELECT
    days.day AS "date",
    count(active.user_name) AS number_active_users,
    round(100.0 * count(active.user_name) / NULLIF(total.users, 0), 2) AS percentage_active_users
FROM days
CROSS JOIN total
LEFT JOIN active ON active.day = days.day
GROUP BY days.day, total.users
ORDER BY "date";
