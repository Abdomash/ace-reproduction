──────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────
Num Passed Tests : 6
Num Failed Tests : 1
Num Total  Tests : 7
──────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match venmo.Transaction, venmo.TransactionLike
>> Passed Requirement
obtain added, updated, removed venmo.Transaction records using models.changed_records,
and assert 0 transactions were added or removed.
>> Passed Requirement
assert updated transactions have only changed in like_count field using models.changed_field_names.
>> Passed Requirement
obtain added, updated, removed venmo.TransactionLike records using models.changed_records,
and assert 0 transaction likes were removed.
>> Passed Requirement
assert all updated transactions were created after private_data.min_transaction_datetime
──────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────
>> Failed Requirement
assert set of updated transaction ids match exactly to
private_data.to_like_transaction_ids (ignore order).
```python
with test(
    """
    assert set of updated transaction ids match exactly to
    private_data.to_like_transaction_ids (ignore order).
    """
):
    updated_transaction_ids = unique_list_of(updated_transactions, "id")
    test.case(
```
----------
AssertionError:
[371, 372, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 5902, 5903, 5904, 5918, 5920, 6241, 6242, 6243, 6244,
6246, 6247, 6261, 6262, 6263, 6264, 6265, 6266, 6267, 7345, 7346, 7347, 7348, 7349, 7350, 7351, 7352, 7353, 7354]
==
[371, 372, 861, 862, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 5902, 5903, 5904, 5918, 5920, 6241, 6242, 6243,
6244, 6246, 6247, 6260, 6261, 6262, 6263, 6264, 6265, 6266, 6267, 7345, 7346, 7347, 7348, 7349, 7350, 7351, 7352, 7353, 7354]

In right but not left:
[861, 862, 6260]

Original values:
[371, 372, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 5902, 5903, 5904, 5918, 5920, 6241, 6242, 6243, 6244,
6246, 6247, 6261, 6262, 6263, 6264, 6265, 6266, 6267, 7345, 7346, 7347, 7348, 7349, 7350, 7351, 7352, 7353, 7354]
==
[1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 5902, 5903, 5904, 6260, 6261, 6262, 6263, 6264, 6265, 6266, 6267,
7345, 7346, 7347, 7348, 7349, 7350, 7351, 7352, 7353, 7354, 371, 372, 861, 862, 5918, 5920, 6241, 6242, 6243, 6244, 6246, 6247]