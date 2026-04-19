──────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────
Num Passed Tests : 5
Num Failed Tests : 0
Num Total  Tests : 5
──────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match phone.GlobalTextMessage, phone.UserTextMessage
>> Passed Requirement
assert 0 phone.UserTextMessage records were removed.
>> Passed Requirement
assert receiver_ids of added global text messages match exactly to
private_data.no_account_phone_user_ids (ignore order).
>> Passed Requirement
assert all added global text messages have message public_data.message_text (normalize_text=True).
──────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────
None