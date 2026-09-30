-- Top 10 users by number of songs listened to (every listen counts, including repeats).
-- distinct_songs is there for the other way to read the question.
SELECT
    user_name,
    count(*)                       AS number_of_listens,
    count(DISTINCT recording_msid) AS distinct_songs
FROM listens
GROUP BY user_name
ORDER BY number_of_listens DESC, user_name
LIMIT 10;
