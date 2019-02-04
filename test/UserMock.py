class UserMock:

    def __init__(self, telegram_id=123456, full_name="Alex Korenkov", nickname="@lox"):
        self.id = telegram_id
        self.full_name = full_name
        self.name = nickname
