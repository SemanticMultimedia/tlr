from models import User, Token, Repo, HMap, CSet, Blob, CommitMessage
from peewee import IntegrityError, SQL, fn

import logging
logger = logging.getLogger('debug')

INDEX_PAGE_SIZE = 50

def get_user_count():
	return User.select().count()

def get_repo_count():
	return Repo.select().count()

def get_resource_count():
	return HMap.select().count()

def get_revision_count():
	return CSet.select().count()

def get_all_users(page):
	return User.select(User.name).paginate(page, INDEX_PAGE_SIZE)