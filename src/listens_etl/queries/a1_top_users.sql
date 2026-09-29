-- Top 10 users by number of songs listened to (every listen counts, including repeats).
SELECT
    user_name,
    count(*) AS number_of_listens
FROM listens
GROUP BY user_name
ORDER BY number_of_listens DESC, user_name
LIMIT 10;
