import pytest

from pychain.node.exceptions import GUIDNotInNetwork
from pychain.node.models import GUID


def test_guid_init():
    assert GUID(1).id == 1


def test_guid_eq():
    assert GUID(1) == GUID(1)
    assert GUID(1) != GUID(2)


def test_guid_hash():
    assert hash(GUID(1)) == 1


def test_guid_int():
    assert int(GUID(1)) == 1


def test_guid_lt():
    assert GUID(1) < GUID(2)


def test_guid_repr():
    assert repr(GUID(1)) == "GUID(id=1)"


def test_guid_str():
    assert str(GUID(1)) == "1"


@pytest.mark.parametrize(
    "guid,start_guid,stop_guid,guid_max,expected",
    [
        (GUID(6), GUID(2), GUID(8), GUID(9), [GUID(1), GUID(9)]),
        (GUID(9), GUID(7), GUID(5), GUID(9), [GUID(6)]),
        (GUID(9), GUID(1), GUID(9), GUID(9), []),
        (GUID(1), GUID(3), GUID(1), GUID(4), [GUID(2)]),
    ],
)
def test_guid_get_backup_peers(guid, start_guid, stop_guid, guid_max, expected):
    assert guid.get_backup_peers(start_guid, stop_guid, guid_max) == expected


@pytest.mark.parametrize(
    "guid,start_guid,stop_guid,guid_max",
    [
        (GUID(1), GUID(3), GUID(5), GUID(4)),
        (GUID(1), GUID(5), GUID(3), GUID(4)),
    ],
)
def test_guid_get_backup_peers_not_in_network(guid, start_guid, stop_guid, guid_max):
    with pytest.raises(GUIDNotInNetwork):
        guid.get_backup_peers(start_guid, stop_guid, guid_max)


@pytest.mark.parametrize(
    "guid,guid_max,expected",
    [
        (GUID(5), GUID(9), [GUID(i) for i in [5, 4, 3, 2, 1, 9, 8, 7, 6]]),
        (GUID(1), GUID(9), [GUID(i) for i in [1, 9, 8, 7, 6, 5, 4, 3, 2]]),
        (GUID(9), GUID(9), [GUID(i) for i in [9, 8, 7, 6, 5, 4, 3, 2, 1]]),
        (GUID(1), GUID(1), [GUID(1)]),
    ],
)
def test_guid_get_network(guid, guid_max, expected):
    assert guid._get_network(guid_max) == expected


@pytest.mark.parametrize(
    "guid,guid_max,expected",
    [
        (GUID(9), GUID(9), [GUID(i) for i in [8, 7, 5, 1]]),
        (GUID(5), GUID(9), [GUID(i) for i in [4, 3, 1, 6]]),
        (GUID(1), GUID(4), [GUID(i) for i in [4, 3]]),
    ],
)
def test_guid_get_primary_peers(guid, guid_max, expected):
    assert guid.get_primary_peers(guid_max) == expected
