──────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────
Num Passed Tests : 3
Num Failed Tests : 3
Num Total  Tests : 6
──────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
obtain added, updated, removed spotify.UserDownloadedSong records using models.changed_records,
and assert 0 have been removed.
>> Passed Requirement
assert all added downloaded song_ids are in private_data.liked_song_ids
──────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────
>> Failed Requirement
assert model changes match spotify.UserDownloadedSong.
```python
with test(
    """
    assert model changes match spotify.UserDownloadedSong.
    """
):
    test.case(models.changed_model_names(), "==", {"spotify.UserDownloadedSong"})
```
----------
AssertionError:
{'spotify.UserDownloadedSong', 'spotify.UserLibrarySong'}
==
{'spotify.UserDownloadedSong'}

In left but not right:
['spotify.UserLibrarySong']
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
[8, 9, 17, 18, 19, 24, 28, 29, 30, 32, 33, 35, 36, 44, 45, 48, 55, 58, 59, 80, 87, 97, 110, 112, 132, 143, 151, 163, 199, 221,
223, 248, 259, 323]
==
[9, 28, 87, 110, 151, 199]

In left but not right:
[8, 17, 18, 19, 24, 29, 30, 32, 33, 35, 36, 44, 45, 48, 55, 58, 59, 80, 97, 112, 132, 143, 163, 221, 223, 248, 259, 323]

Original values:
[58, 9, 32, 97, 248, 28, 36, 199, 33, 45, 151, 55, 323, 48, 143, 30, 8, 259, 29, 19, 59, 35, 221, 44, 80, 18, 112, 223, 163, 87,
132, 110, 24, 17]
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
AssertionError:  58 in [4, 294, 103, 199, 9, 265, 301, 110, 15, 207, 208, 87, 151, 28]