──────────────────────────────────────────────────────── Overall Stats ─────────────────────────────────────────────────────────
Num Passed Tests : 2
Num Failed Tests : 6
Num Total  Tests : 8
──────────────────────────────────────────────────────────── Passes ────────────────────────────────────────────────────────────
>> Passed Requirement
assert answers match.
>> Passed Requirement
obtain added, removed venmo.Notification records using models.changed_records,
and assert 0 notifications were removed.
──────────────────────────────────────────────────────────── Fails ─────────────────────────────────────────────────────────────
>> Failed Requirement
assert model changes match venmo.Notification
```python
with test(
    """
    assert model changes match venmo.Notification
    """
):
    test.case(models.changed_model_names(), "==", {"venmo.Notification"})
```
----------
AssertionError:  set() == {'venmo.Notification'}

In right but not left:
['venmo.Notification']
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
AssertionError:  set() == {25, 14}

In right but not left:
[25, 14]
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
set()
==
{'Lindsey Simpson has sent you a reminder for their payment request of $62.00.', 'Lindsey Simpson has sent you a reminder for
their payment request of $17.00.', 'Lindsey Simpson has sent you a reminder for their payment request of $29.00.', 'Lindsey
Simpson has sent you a reminder for their payment request of $60.00.', 'Lindsey Simpson has sent you a reminder for their
payment request of $21.00.', 'Lindsey Simpson has sent you a reminder for their payment request of $36.00.', 'Lindsey Simpson
has sent you a reminder for their payment request of $19.00.'}

In right but not left:
['Lindsey Simpson has sent you a reminder for their payment request of $62.00.', 'Lindsey Simpson has sent you a reminder for
their payment request of $17.00.', 'Lindsey Simpson has sent you a reminder for their payment request of $29.00.', 'Lindsey
Simpson has sent you a reminder for their payment request of $60.00.', 'Lindsey Simpson has sent you a reminder for their
payment request of $21.00.', 'Lindsey Simpson has sent you a reminder for their payment request of $36.00.', 'Lindsey Simpson
has sent you a reminder for their payment request of $19.00.']
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
defaultdict(<class 'set'>, {})
==
{14: {'Lindsey Simpson has sent you a reminder for their payment request of $62.00.', 'Lindsey Simpson has sent you a reminder
for their payment request of $17.00.', 'Lindsey Simpson has sent you a reminder for their payment request of $29.00.'}, 25:
{'Lindsey Simpson has sent you a reminder for their payment request of $60.00.', 'Lindsey Simpson has sent you a reminder for
their payment request of $36.00.', 'Lindsey Simpson has sent you a reminder for their payment request of $19.00.', 'Lindsey
Simpson has sent you a reminder for their payment request of $21.00.'}}
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
AssertionError:  set() == {3456, 3457, 3461, 3463, 3464, 3470, 3455}

In right but not left:
[3456, 3457, 3461, 3463, 3464, 3470, 3455]
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
defaultdict(<class 'set'>, {})
==
{14: {3456, 3457, 3455}, 25: {3464, 3461, 3470, 3463}}