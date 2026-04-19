──────────────────────────────────────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────────────────────────────────────
Num Passed Tests : 6
Num Failed Tests : 0
Num Total  Tests : 6
──────────────────────────────────────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match spotify.UserDownloadedSong.
>> Passed Requirement
obtain added, updated, removed spotify.UserDownloadedSong records using models.changed_records,
and assert 0 have been removed.
>> Passed Requirement
assert added downloaded song_ids match private_data.to_download_song_ids (ignore_order=True)
>> Passed Requirement
assert all added downloaded song_ids are in private_data.library_song_ids
>> Passed Requirement
assert all added downloaded song_ids are in private_data.liked_song_ids
──────────────────────────────────────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────────────────────────────────────
None