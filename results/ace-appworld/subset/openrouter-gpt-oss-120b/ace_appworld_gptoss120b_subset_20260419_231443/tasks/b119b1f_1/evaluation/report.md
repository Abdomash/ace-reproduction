──────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────
Num Passed Tests : 6
Num Failed Tests : 0
Num Total  Tests : 6
──────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match spotify.MusicPlayer.
>> Passed Requirement
assert spotify.MusicPlayer has 1 updated using models.changed_records
>> Passed Requirement
assert this music player record has updated only in the cursor_position
using models.changed_field_names
>> Passed Requirement
assert the currently playing song has ID private_data.song_id in the end state.
>> Passed Requirement
assert music player's cursor is on the song by private_data.artist_id in the end state.
──────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────
None