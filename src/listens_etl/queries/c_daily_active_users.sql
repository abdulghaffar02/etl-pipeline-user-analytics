-- Daily active users: a user is active on day X if they listened in [X-6 days, X].
--
-- Distinct counts don't add up across days (a user active on 5 of the 7 days would be
-- counted 5 times), so instead each (user, day) pair is expanded to the 7 days it makes
-- the user active on, then counted once per day. That's 7x the user-days, not a join
-- against all listens.
--
-- Percentage is out of all users in the database. The first 6 days have incomplete
-- windows and the last day only covers a few minutes; they're kept, not hidden.
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
