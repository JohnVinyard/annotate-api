import json
import datetime
import pytz
from falcon.media import BaseHandler


class JsonEncoderWithDateTime(json.JSONEncoder):
    def __init__(self):
        super(JsonEncoderWithDateTime, self).__init__()

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return datetime.datetime.utcnow() \
                .replace(tzinfo=pytz.utc).isoformat()
        else:
            return super(JsonEncoderWithDateTime, self).default(o)


class JSONWithDateTimeHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.encoder = JsonEncoderWithDateTime()

    def deserialize(self, raw):
        return json.loads(raw.decode())

    def serialize(self, obj):
        return self.encoder.encode(obj).encode()

__all__ = [
    JSONWithDateTimeHandler
]