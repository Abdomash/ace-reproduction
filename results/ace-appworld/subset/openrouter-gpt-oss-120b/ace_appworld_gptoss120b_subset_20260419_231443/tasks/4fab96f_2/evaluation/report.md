──────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────
Num Passed Tests : 8
Num Failed Tests : 0
Num Total  Tests : 8
──────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match venmo.Notification
>> Passed Requirement
obtain added, removed venmo.Notification records using models.changed_records,
and assert 0 notifications were removed.
>> Passed Requirement
assert all receiver ids of added notifications match keys of
private_data.venmo_user_id_to_notification_messages ignoring order.
>> Passed Requirement
assert set of added notfications messages match flattened values
of private_data.venmo_user_id_to_notification_messages.
>> Passed Requirement
assert user_id to message mapping from notifications match private_data.venmo_user_id_to_notification_messages
>> Passed Requirement
assert set of added notfications payment_request_ids match flattened values
of private_data.venmo_user_id_to_notification_payment_request_ids.
>> Passed Requirement
assert user_id to message mapping from notifications match
private_data.venmo_user_id_to_notification_messages
──────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────
None