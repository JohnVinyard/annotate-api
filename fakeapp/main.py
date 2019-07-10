from falcon_lambda import logger, wsgi
import logging

logger.setup_lambda_logger(logging.DEBUG)
log = logging.getLogger(__name__)


from app import Application
try:
    api = Application()
except Exception as e:
    log.error(e)


def lambda_handler(event, context):
    log.debug(event)
    resp = wsgi.adapter(api, event, context)
    log.debug(resp)
    return resp
