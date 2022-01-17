class PyChainException(Exception):
    pass


class PeerException(PyChainException):
    pass


class NetworkJoinException(PeerException):
    pass
