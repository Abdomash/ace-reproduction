──────────────────────────────────────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────────────────────────────────────
Num Passed Tests : 6
Num Failed Tests : 0
Num Total  Tests : 6
──────────────────────────────────────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match spotify.UserArtistFollowing.
>> Passed Requirement
obtain added, updated, removed spotify.UserArtistFollowing records using models.changed_records,
and assert 0 have been removed.
>> Passed Requirement
assert private_data.to_be_followed_artist_ids_by_songs artists have been newly followed.
>> Passed Requirement
assert private_data.to_be_followed_artist_ids_by_albums artists have been newly followed.
>> Passed Requirement
assert artist_ids from added artists match union of
private_data.to_be_followed_artist_ids_by_songs and private_data.to_be_followed_artist_ids_by_albums.
──────────────────────────────────────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────────────────────────────────────
None