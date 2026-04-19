──────────────────────────────────────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────────────────────────────────────
Num Passed Tests : 10
Num Failed Tests : 0
Num Total  Tests : 10
──────────────────────────────────────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match venmo.Transaction, phone.GlobalTextMessage, phone.UserTextMessage,
ignoring venmo.User and venmo.Notification
>> Passed Requirement
obtain added, updated, deleted venmo.Transactions using models.changed_records
assert 1 is added, 0 is updated, and 0 is deleted.
>> Passed Requirement
assert the added transaction receiver_id is private_data.friend_venmo_user_id.
>> Passed Requirement
assert the added transaction has description public_data.note.
>> Passed Requirement
assert the added transaction has amount private_data.grocery_cost.
>> Passed Requirement
obtain added, updated, deleted phone.GlobalTextMessage using models.changed_records
assert 1 is added, 0 is updated, and 0 is deleted.
>> Passed Requirement
assert the added global_text_message's receiver_id is to private_data.friend_phone_user_id.
>> Passed Requirement
assert the added global_text_message has message, public_data.message_text (ignore case).
>> Passed Requirement
assert none of the records from phone.UserTextMessage have been deleted
──────────────────────────────────────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────────────────────────────────────
None