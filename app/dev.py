from app import Application
from data import build_repositories
import os

connection_string = os.environ['connection_string']
users_repo, sounds_repo, annotations_repo = \
    build_repositories(connection_string)

api = application = Application(users_repo, sounds_repo, annotations_repo)