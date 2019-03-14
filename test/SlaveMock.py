class SlaveMock:

    def __init__(self, nickname="slave1", ip=None, password="testpass", owner=123456):
        self.nickname = nickname
        self.ip = ip
        self.password = password
        self.owner = owner

    def to_tuple(self):
        return self.nickname, self.ip, self.owner, self.password
