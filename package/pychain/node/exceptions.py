class PyChainException(Exception):
    pass


class GUIDException(PyChainException):
    pass


class GUIDNotInNetwork(GUIDException):
    pass


class PeerException(PyChainException):
    pass


class NetworkJoinException(PeerException):
    pass
