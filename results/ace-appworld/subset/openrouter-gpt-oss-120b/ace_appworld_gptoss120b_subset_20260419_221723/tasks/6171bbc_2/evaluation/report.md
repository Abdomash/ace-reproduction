──────────────────────────────────────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────────────────────────────────────
Num Passed Tests : 3
Num Failed Tests : 4
Num Total  Tests : 7
──────────────────────────────────────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match spotify.Playlist, spotify.PlaylistSong.
>> Passed Requirement
obtain added, removed spotify.PlaylistSong records using models.changed_records,
and assert 0 have been removed.
──────────────────────────────────────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────────────────────────────────────
>> Failed Requirement
obtain added, updated, removed spotify.Playlist records using models.changed_records,
and assert 1 has been added, and 0 have been updated or removed.
```python
with test(
    """
    obtain added, updated, removed spotify.Playlist records using models.changed_records,
    and assert 1 has been added, and 0 have been updated or removed.
    """
):
    added_playlists, updated_playlists, removed_playlists = models.changed_records(
        "spotify.Playlist"
```
----------
AssertionError:  3 == 1
>> Failed Requirement
assert the added playlist is named public_data.playlist_title.
```python
with test(
    """
    assert the added playlist is named public_data.playlist_title.
    """
):
    added_playlist = added_playlists[0]
    test.case(added_playlist.title, "==", public_data.playlist_title)
```
----------
AssertionError:
'My Highest Rated Playlist Songs (164336)'
==
'My Highest Rated Playlist Songs'
>> Failed Requirement
assert all song_ids of added playlist_songs match private_data.playlist_song_ids (ignore_order)
```python
with test(
    """
    assert all song_ids of added playlist_songs match private_data.playlist_song_ids (ignore_order)
    """
):
    test.case(
        list_of(added_playlist_songs, "song_id"),
        "==",
```
----------
AssertionError:
[39, 39, 39, 51, 51, 51, 52, 52, 52, 99, 99, 99, 304, 304, 304]
==
[36, 58, 146, 164, 209]

In left but not right:
[39, 39, 39, 51, 51, 51, 52, 52, 52, 99, 99, 99, 304, 304, 304]

In right but not left:
[36, 58, 146, 164, 209]

Original values:
[52, 39, 304, 51, 99, 52, 304, 99, 304, 51, 99, 39, 52, 51, 39]
==
[164, 58, 209, 146, 36]
>> Failed Requirement
assert the playlist_id of all added playlist_songs match added_playlist.id.
```python
with test(
    """
    assert the playlist_id of all added playlist_songs match added_playlist.id.
    """
):
```
----------
AssertionError:  654 == 655