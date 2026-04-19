──────────────────────────────────────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────────────────────────────────────
Num Passed Tests : 8
Num Failed Tests : 0
Num Total  Tests : 8
──────────────────────────────────────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match file_system.File, file_system.Directory.
>> Passed Requirement
obtain added, updated, removed file_system.File records using models.changed_records,
and assert 0 were updated or removed.
>> Passed Requirement
assert all added files have tilde_path starting with public_data.backup_directory_path.
>> Passed Requirement
assert all added files have path ending with ".md".
>> Passed Requirement
assert all added file_system.File records' paths match keys of
private_data.file_path_to_content. (ignore_case)
>> Passed Requirement
assert all added file_system.File records' contents
match values of private_data.file_path_to_content (strip).
>> Passed Requirement
assert all added file_system.File records' path to content
mapping match that of private_data.file_path_to_content
(strip and ignore case).
──────────────────────────────────────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────────────────────────────────────
None