──────────────────────────────────────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────────────────────────────────────
Num Passed Tests : 4
Num Failed Tests : 2
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
assert all added downloaded song_ids are in private_data.liked_song_ids
──────────────────────────────────────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────────────────────────────────────
>> Failed Requirement
assert added downloaded song_ids match private_data.to_download_song_ids (ignore_order=True)
```python
with test(
    """
    assert added downloaded song_ids match private_data.to_download_song_ids (ignore_order=True)
    """
):
    downloaded_song_ids = list_of(added_downloaded_songs, "song_id")
    test.case(downloaded_song_ids, "==", private_data.to_download_song_ids, ignore_order=True)
```
----------
AssertionError:
[8, 9, 17, 18, 19, 24, 28, 29, 30, 32, 33, 35, 36, 44, 45, 48, 55, 58, 59, 80, 87, 97, 110, 112, 132, 143, 151, 163, 199, 221, 223, 248, 259, 323]
==
[9, 28, 87, 110, 151, 199]

In left but not right:
[8, 17, 18, 19, 24, 29, 30, 32, 33, 35, 36, 44, 45, 48, 55, 58, 59, 80, 97, 112, 132, 143, 163, 221, 223, 248, 259, 323]

Original values:
[9, 19, 223, 8, 259, 112, 221, 32, 45, 59, 35, 151, 323, 29, 44, 87, 58, 199, 18, 97, 248, 80, 163, 110, 24, 17, 30, 132, 55, 48, 143, 33, 28, 36]
==
[199, 9, 110, 87, 151, 28]
>> Failed Requirement
assert all added downloaded song_ids are in private_data.library_song_ids
```python
with test(
    """
    assert all added downloaded song_ids are in private_data.library_song_ids
    """
):
    test.case(downloaded_song_ids, "all in", private_data.library_song_ids)
```
----------
AssertionError:  19 in [4, 294, 103, 199, 9, 265, 301, 110, 15, 207, 208, 87, 151, 28]