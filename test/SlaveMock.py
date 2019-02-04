class SlaveMock:

    def __init__(self, nickname="slave1", ip="0.0.0.0"):
        self.nickname = nickname
        self.ip = ip

    def to_tuple(self):
        return self.nickname, self.ip
