import unittest.mock
import uuid

import pytest

from pantos.validatornode.database.access import update_transfer_task_id


@pytest.mark.parametrize('task_id', [
    '618ce6a4-34c6-45cf-be75-ae8c46377b29',
    '4c76907e-7660-4195-8858-92e6426f55ea'
])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_task_id_correct(mock_get_session,
                                         database_session_maker, task_id,
                                         initialized_database_session,
                                         transfer):
    mock_get_session.return_value = database_session_maker
    initialized_database_session.add(transfer)
    initialized_database_session.commit()
    assert transfer.task_id != task_id
    update_transfer_task_id(transfer.id, uuid.UUID(task_id))
    initialized_database_session.refresh(transfer)
    assert transfer.task_id == task_id
