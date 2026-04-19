──────────────────────────────────────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────────────────────────────────────
Num Passed Tests : 7
Num Failed Tests : 0
Num Total  Tests : 7
──────────────────────────────────────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────────────────────────────────────
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
assert set of updated transaction ids match exactly to
private_data.to_like_transaction_ids (ignore order).
>> Passed Requirement
assert all updated transactions were created after private_data.min_transaction_datetime
──────────────────────────────────────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────────────────────────────────────
None