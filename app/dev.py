from app import Application
from data import build_repositories
import os

connection_string = os.environ['connection_string']
email_whitelist = os.environ['email_whitelist']

users_repo, sounds_repo, annotations_repo = \
    build_repositories(connection_string)

api = application = Application(
    users_repo,
    sounds_repo,
    annotations_repo,
    is_dev_environment=True,
    email_whitelist=email_whitelist)
