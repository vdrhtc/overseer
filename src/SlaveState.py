import datetime
import json
from json import JSONDecodeError


class SlaveState:

    RAW_MESSAGE_PARTS = 3

    def __init__(self, slave_nickname, raw_message):

        self._slave_nickname = slave_nickname
        self._raw_message = raw_message
        self._received_at = datetime.datetime.now()
        self._parse_raw_message(raw_message)

    def _parse_raw_message(self, raw_message):

        try:
            data = json.loads(raw_message)
            self._sent_at = data["sent_at"]  # datetime
            self._state = data["state"]  # state message
            self._alerts = data["alerts"]
        except (JSONDecodeError, KeyError):
            self._sent_at = ""  # datetime
            self._state = raw_message  # state message
            self._alerts = ("")

    def get_state_message(self):
        return self._received_at.strftime("%Y-%m-%d %H:%M:%S") + \
               " - " + self._slave_nickname + "\n" +\
               self._state

    def get_alert_message(self, alert):
        if alert is not "":
            return self._received_at.strftime("%Y-%m-%d %H:%M:%S") + \
                   " - " + self._slave_nickname + "\nAlert! " +\
                   alert

    def get_alerts(self):
        return self._alerts

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        else:
            return False


