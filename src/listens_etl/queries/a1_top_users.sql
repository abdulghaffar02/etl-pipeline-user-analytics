-- Top 10 users by number of songs listened to (every listen counts, including repeats).
-- distinct_songs covers the other reading of the question. Ranking by it gives a very
-- different top 10: hds is first here with 46,885 listens of only 102 recordings.
-- It counts recording_msids, so one song submitted with different metadata counts twice.
SELECT
    user_name,
    count(*)                       AS number_of_listens,
    count(DISTINCT recording_msid) AS distinct_songs
FROM listens
GROUP BY user_name
ORDER BY number_of_listens DESC, user_name
LIMIT 10;
