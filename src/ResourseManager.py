import json


class ResourceManager:

    def __init__(self, strings_file="resources/strings.json", numbers_file="resources/numbers.json"):
        self._strings_file = strings_file
        self._numbers_file = numbers_file

    def get_string(self, string_id):
        with open(self._strings_file, "r") as f:
            return json.load(f)[string_id]

    def get_number(self, number_id):
        with open(self._numbers_file, "r") as f:
            return json.load(f)[number_id]
