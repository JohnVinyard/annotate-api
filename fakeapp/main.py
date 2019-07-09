from falcon_lambda import logger, wsgi
from .app import Application


api = Application()


def lambda_handler(event, context):
    resp = wsgi.adapter(api, event, context)
    return resp
