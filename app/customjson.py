import json
import datetime
from falcon.media import BaseHandler
from enum import Enum


class JsonEncoder(json.JSONEncoder):

    def __init__(self, convert_to_links):
        super().__init__()
        self.convert_to_links = convert_to_links

    def default(self, o):
        try:
            return self.convert_to_links.convert_to_link(o)
        except KeyError:
            pass

        if isinstance(o, datetime.datetime):
            return o.isoformat() + 'Z'
        elif isinstance(o, Enum):
            return o.value
        else:
            return super().default(o)


class JSONHandler(BaseHandler):
    def __init__(self, convert_to_links):
        super().__init__()
        self.encoder = JsonEncoder(convert_to_links)

    def deserialize(self, raw):
        return json.loads(raw.decode())

    def serialize(self, obj):
        return self.encoder.encode(obj).encode()

__all__ = [
    JSONHandler
]