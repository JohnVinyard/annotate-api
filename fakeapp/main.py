from falcon_lambda import logger, wsgi
import logging
from app import Application
import pymongo
import os

logger.setup_lambda_logger(logging.DEBUG)
log = logging.getLogger(__name__)

mongo_connection_string = os.environ['connection_string']
mongo_client = pymongo.MongoClient(mongo_connection_string)
api = Application(mongo_client)


def lambda_handler(event, context):
    log.debug(event)
    resp = wsgi.adapter(api, event, context)
    log.debug(resp)
    return resp
