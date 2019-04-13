import json
import datetime
import pytz
from falcon.media import BaseHandler
from enum import Enum
from string import Formatter


class JsonEncoder(json.JSONEncoder):

    def __init__(self, convert_to_links):
        super().__init__()
        self.convert_to_links = convert_to_links

    def _extract_keys_from_template_string(self, template):
        # KLUDGE: What happens if there are multiple keys in the template?
        return (x[1] for x in Formatter().parse(template))

    def default(self, o):
        try:
            link_template = self.convert_to_links[o.__class__]
            key = next(self._extract_keys_from_template_string(link_template))
            format_dict = {key: o.identifier}
            return link_template.format(**format_dict)
        except KeyError:
            pass

        if isinstance(o, datetime.datetime):
            return datetime.datetime.utcnow().isoformat() + 'Z'
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