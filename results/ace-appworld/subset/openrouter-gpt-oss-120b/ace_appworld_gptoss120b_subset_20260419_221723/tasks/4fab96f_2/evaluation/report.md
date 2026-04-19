──────────────────────────────────────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────────────────────────────────────
Num Passed Tests : 3
Num Failed Tests : 5
Num Total  Tests : 8
──────────────────────────────────────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
assert model changes match venmo.Notification
>> Passed Requirement
obtain added, removed venmo.Notification records using models.changed_records,
and assert 0 notifications were removed.
──────────────────────────────────────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────────────────────────────────────
>> Failed Requirement
assert all receiver ids of added notifications match keys of
private_data.venmo_user_id_to_notification_messages ignoring order.
```python
with test(
    """
    assert all receiver ids of added notifications match keys of
    private_data.venmo_user_id_to_notification_messages ignoring order.
    """
):
    test.case(
        set_of(added_notifications, "user_id"),
```
----------
AssertionError:  {59, 36, 70} == {36, 70, 41, 86, 59}

In right but not left:
[41, 86]
>> Failed Requirement
assert set of added notfications messages match flattened values
of private_data.venmo_user_id_to_notification_messages.
```python
with test(
    """
    assert set of added notfications messages match flattened values
    of private_data.venmo_user_id_to_notification_messages.
    """
):
    test.case(
        set_of(added_notifications, "message"),
```
----------
AssertionError:
{'Kiara Bailey has sent you a reminder for their payment request of $45.00.', 'Kiara Bailey has sent you a reminder for their payment request of $35.00.', 'Kiara Bailey has sent you a reminder
for their payment request of $9.00.', 'Kiara Bailey has sent you a reminder for their payment request of $6.00.', 'Kiara Bailey has sent you a reminder for their payment request of $326.00.',
'Kiara Bailey has sent you a reminder for their payment request of $195.00.', 'Kiara Bailey has sent you a reminder for their payment request of $90.00.', 'Kiara Bailey has sent you a reminder
for their payment request of $14.00.'}
==
{'Kiara Bailey has sent you a reminder for their payment request of $40.00.', 'Kiara Bailey has sent you a reminder for their payment request of $45.00.', 'Kiara Bailey has sent you a reminder
for their payment request of $25.00.', 'Kiara Bailey has sent you a reminder for their payment request of $35.00.', 'Kiara Bailey has sent you a reminder for their payment request of $30.00.',
'Kiara Bailey has sent you a reminder for their payment request of $60.00.', 'Kiara Bailey has sent you a reminder for their payment request of $9.00.', 'Kiara Bailey has sent you a reminder
for their payment request of $6.00.', 'Kiara Bailey has sent you a reminder for their payment request of $326.00.', 'Kiara Bailey has sent you a reminder for their payment request of $23.00.',
'Kiara Bailey has sent you a reminder for their payment request of $195.00.', 'Kiara Bailey has sent you a reminder for their payment request of $90.00.', 'Kiara Bailey has sent you a reminder
for their payment request of $14.00.'}

In right but not left:
['Kiara Bailey has sent you a reminder for their payment request of $40.00.', 'Kiara Bailey has sent you a reminder for their payment request of $25.00.', 'Kiara Bailey has sent you a reminder
for their payment request of $30.00.', 'Kiara Bailey has sent you a reminder for their payment request of $60.00.', 'Kiara Bailey has sent you a reminder for their payment request of $23.00.']
>> Failed Requirement
assert user_id to message mapping from notifications match private_data.venmo_user_id_to_notification_messages
```python
with test(
    """
    assert user_id to message mapping from notifications match private_data.venmo_user_id_to_notification_messages
    """
):
    venmo_user_id_to_notification_messages = {
        id_: set(notification_messages)
        for id_, notification_messages in private_data.venmo_user_id_to_notification_messages.items()
```
----------
AssertionError:
defaultdict(<class 'set'>, {59: {'Kiara Bailey has sent you a reminder for their payment request of $6.00.', 'Kiara Bailey has sent you a reminder for their payment request of $45.00.', 'Kiara
Bailey has sent you a reminder for their payment request of $14.00.', 'Kiara Bailey has sent you a reminder for their payment request of $195.00.'}, 36: {'Kiara Bailey has sent you a reminder
for their payment request of $9.00.', 'Kiara Bailey has sent you a reminder for their payment request of $35.00.', 'Kiara Bailey has sent you a reminder for their payment request of $90.00.'},
70: {'Kiara Bailey has sent you a reminder for their payment request of $326.00.'}})
==
{59: {'Kiara Bailey has sent you a reminder for their payment request of $6.00.', 'Kiara Bailey has sent you a reminder for their payment request of $45.00.', 'Kiara Bailey has sent you a
reminder for their payment request of $14.00.', 'Kiara Bailey has sent you a reminder for their payment request of $195.00.'}, 70: {'Kiara Bailey has sent you a reminder for their payment
request of $326.00.'}, 86: {'Kiara Bailey has sent you a reminder for their payment request of $6.00.', 'Kiara Bailey has sent you a reminder for their payment request of $40.00.', 'Kiara
Bailey has sent you a reminder for their payment request of $25.00.', 'Kiara Bailey has sent you a reminder for their payment request of $23.00.'}, 41: {'Kiara Bailey has sent you a reminder
for their payment request of $25.00.', 'Kiara Bailey has sent you a reminder for their payment request of $30.00.', 'Kiara Bailey has sent you a reminder for their payment request of
$60.00.'}, 36: {'Kiara Bailey has sent you a reminder for their payment request of $9.00.', 'Kiara Bailey has sent you a reminder for their payment request of $35.00.', 'Kiara Bailey has sent
you a reminder for their payment request of $90.00.'}}
>> Failed Requirement
assert set of added notfications payment_request_ids match flattened values
of private_data.venmo_user_id_to_notification_payment_request_ids.
```python
with test(
    """
    assert set of added notfications payment_request_ids match flattened values
    of private_data.venmo_user_id_to_notification_payment_request_ids.
    """
):
    test.case(
        set_of(added_notifications, "data.payment_request_id"),
```
----------
AssertionError:
{4512, 4515, 4580, 4581, 4518, 4583, 4531, 4509, 4511}
==
{4512, 4576, 4515, 4580, 4581, 4518, 4583, 4575, 4559, 4561, 4562, 4531, 4565, 4571, 4509, 4511}

In right but not left:
[4576, 4575, 4559, 4561, 4562, 4565, 4571]
>> Failed Requirement
assert user_id to message mapping from notifications match
private_data.venmo_user_id_to_notification_messages
```python
with test(
    """
    assert user_id to message mapping from notifications match
    private_data.venmo_user_id_to_notification_messages
    """
):
    venmo_user_id_to_notification_payment_request_ids = {
        id_: set(notification_payment_request_ids)
```
----------
AssertionError:
defaultdict(<class 'set'>, {59: {4512, 4515, 4518, 4509, 4511}, 36: {4580, 4581, 4583}, 70: {4531}})
==
{59: {4512, 4515, 4518, 4509, 4511}, 70: {4531}, 86: {4561, 4562, 4565, 4559}, 41: {4576, 4571, 4575}, 36: {4580, 4581, 4583}}