-- First song each user listened to.
-- Same-second ties: ListenBrainz sets dedup_tag on the later plays.
SELECT
    user_name,
    listened_at,
    track_name,
    artist_name,
    release_name
FROM listens_enriched
QUALIFY row_number() OVER (
    PARTITION BY user_name
    ORDER BY listened_at,
             coalesce(TRY_CAST(additional_info->>'dedup_tag' AS INTEGER), 0),
             recording_msid
) = 1
ORDER BY user_name;
