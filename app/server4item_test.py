import pytest

from server4item import *


def test_base_manager():
    m = BaseManager()

    with pytest.raises(NotImplementedError):
        m.create(Item())

    with pytest.raises(NotImplementedError):
        m.remove(Item())
