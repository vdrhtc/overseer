from datetime import datetime


class SlaveState:

    RAW_MESSAGE_PARTS = 3

    def __init__(self, slave_nickname, raw_message):

        self._slave_nickname = slave_nickname
        self._raw_message = raw_message
        self._received_at = datetime.now()
        self._parse_raw_message(raw_message)

    def _parse_raw_message(self, raw_message):

        parts = raw_message.split("\r\n")

        if len(parts) != SlaveState.RAW_MESSAGE_PARTS:
            raise ValueError("Raw message contains %d parts. "
                             "Expected %d" % (len(parts), SlaveState.RAW_MESSAGE_PARTS))

        self._sent_at = parts[0]  # datetime
        self._state = parts[1]  # state message
        self._alert = parts[2]

    def get_state_message(self):
        return self._received_at.strftime("%Y-%m-%d %H:%M:%S") + \
               " - " + self._slave_nickname + "\n" +\
               self._state

    def get_alert(self):
        return self._alert


