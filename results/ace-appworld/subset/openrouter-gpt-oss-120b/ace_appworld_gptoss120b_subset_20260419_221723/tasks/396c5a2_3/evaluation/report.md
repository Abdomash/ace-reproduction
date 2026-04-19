──────────────────────────────────────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────────────────────────────────────
Num Passed Tests : 6
Num Failed Tests : 0
Num Total  Tests : 6
──────────────────────────────────────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match spotify.MusicPlayer.
>> Passed Requirement
assert 1 spotify.MusicPlayer has been updated using models.changed_records.
>> Passed Requirement
get the end-state queue_song_ids and
assert all private_data.existing_queue_song_ids are in end-state queue_song_ids.
>> Passed Requirement
assert all private_data.to_be_added_queue_song_ids are in the end state queue_song_ids
>> Passed Requirement
assert union of private_data.to_be_added_queue_song_ids and private_data.existing_queue_song_ids
match the end-state queue_song_ids.
──────────────────────────────────────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────────────────────────────────────
None