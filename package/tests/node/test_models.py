import pytest

from pychain.node.exceptions import GUIDNotInNetwork
from pychain.node.models import GUID


def test_guid_init():
    assert GUID(0).id == 0


def test_guid_eq():
    assert GUID(0) == GUID(0)
    assert GUID(0) != GUID(1)


def test_guid_hash():
    assert hash(GUID(0)) == 0


def test_guid_int():
    assert int(GUID(0)) == 0


def test_guid_lt():
    assert GUID(0) < GUID(1)


def test_guid_repr():
    assert repr(GUID(0)) == "GUID(id=0)"


def test_guid_str():
    assert str(GUID(0)) == "0"


@pytest.mark.parametrize(
    "guid,start_guid,stop_guid,guid_max,expected",
    [
        (GUID(6), GUID(2), GUID(8), GUID(9), [GUID(i) for i in [1, 0, 9]]),
        (GUID(9), GUID(7), GUID(5), GUID(9), [GUID(6)]),
        (GUID(9), GUID(1), GUID(9), GUID(9), [GUID(0)]),
        (GUID(0), GUID(2), GUID(0), GUID(3), [GUID(1)]),
    ],
)
def test_guid_get_backup_peers(guid, start_guid, stop_guid, guid_max, expected):
    assert guid.get_backup_peers(start_guid, stop_guid, guid_max) == expected


@pytest.mark.parametrize(
    "guid,start_guid,stop_guid,guid_max",
    [
        (GUID(0), GUID(2), GUID(4), GUID(3)),
        (GUID(0), GUID(4), GUID(2), GUID(3)),
    ],
)
def test_guid_get_backup_peers_not_in_network(guid, start_guid, stop_guid, guid_max):
    with pytest.raises(GUIDNotInNetwork):
        guid.get_backup_peers(start_guid, stop_guid, guid_max)


@pytest.mark.parametrize(
    "guid,guid_max,expected",
    [
        (GUID(5), GUID(9), [GUID(i) for i in [5, 4, 3, 2, 1, 0, 9, 8, 7, 6]]),
        (GUID(0), GUID(9), [GUID(i) for i in [0, 9, 8, 7, 6, 5, 4, 3, 2, 1]]),
        (GUID(9), GUID(9), [GUID(i) for i in [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]),
        (GUID(0), GUID(0), [GUID(0)]),
    ],
)
def test_guid_get_network(guid, guid_max, expected):
    assert guid._get_network(guid_max) == expected


@pytest.mark.parametrize(
    "guid,guid_max,expected",
    [
        (GUID(9), GUID(9), [GUID(i) for i in [8, 7, 5, 1]]),
        (GUID(5), GUID(9), [GUID(i) for i in [4, 3, 1, 7]]),
        (GUID(0), GUID(3), [GUID(i) for i in [3, 2]]),
    ],
)
def test_guid_get_primary_peers(guid, guid_max, expected):
    assert guid.get_primary_peers(guid_max) == expected
