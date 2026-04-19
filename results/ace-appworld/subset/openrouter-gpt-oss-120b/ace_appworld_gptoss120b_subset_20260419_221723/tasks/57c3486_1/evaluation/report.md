──────────────────────────────────────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────────────────────────────────────
Num Passed Tests : 5
Num Failed Tests : 0
Num Total  Tests : 5
──────────────────────────────────────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match spotify.Song, spotify.SongLike.
>> Passed Requirement
assert all newly song likes are from artists that main_user follows via models.changed_records
>> Passed Requirement
assert all songs from artists main_user follows are liked now by using
private_data.followed_artist_song_ids.
>> Passed Requirement
assert none of the updated or removed song likes are from artists that main_user follows,
using private_data.followed_artist_song_ids.
──────────────────────────────────────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────────────────────────────────────
None