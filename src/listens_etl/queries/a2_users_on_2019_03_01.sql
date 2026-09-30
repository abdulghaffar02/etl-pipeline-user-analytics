-- Users who listened to at least one song on 2019-03-01 (UTC).
-- plain range on listened_at lets DuckDB skip blocks
SELECT count(DISTINCT user_name) AS number_of_users
FROM listens
WHERE listened_at >= TIMESTAMP '2019-03-01'
  AND listened_at <  TIMESTAMP '2019-03-02';
