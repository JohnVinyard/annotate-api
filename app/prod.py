from falcon_lambda import logger, wsgi
import logging
from app import Application
from data import build_repositories
import os

connection_string = os.environ['connection_string']
email_whitelist = os.environ['email_whitelist']

users_repo, sounds_repo, annotations_repo = \
    build_repositories(connection_string)

api = Application(
    users_repo,
    sounds_repo,
    annotations_repo,
    is_dev_environment=False,
    email_whitelist=email_whitelist)


logger.setup_lambda_logger(logging.DEBUG)
log = logging.getLogger(__name__)


def lambda_handler(event, context):
    log.debug(event)
    resp = wsgi.adapter(api, event, context)
    log.debug(resp)
    return resp
