class SlaveMock:

    def __init__(self, nickname="slave1", ip=None, password="testpass", owner=123456):
        self.nickname = nickname
        self.ip = ip
        self.password = password
        self.owner = owner

        # for DBOperator output imitation
        self.slave_nickname = nickname
        self.slave_ip = ip
        self.slave_password = password
        self.slave_owner = owner

    def to_tuple(self):
        return self.nickname, self.ip, self.owner, self.password
