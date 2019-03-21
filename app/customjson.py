import json
import datetime
import pytz
from falcon.media import BaseHandler
from enum import Enum


class JsonEncoder(json.JSONEncoder):
    def __init__(self):
        super().__init__()

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return datetime.datetime.utcnow() \
                .replace(tzinfo=pytz.utc).isoformat()
        elif isinstance(o, Enum):
            return o.value
        else:
            return super().default(o)


class JSONHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.encoder = JsonEncoder()

    def deserialize(self, raw):
        return json.loads(raw.decode())

    def serialize(self, obj):
        return self.encoder.encode(obj).encode()

__all__ = [
    JSONHandler
]