-- First song each user listened to.
-- Two users' first listen shares its second with another one. ListenBrainz tags the
-- later plays in such a group with dedup_tag = 1, 2, ..., so untagged sorts first.
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
