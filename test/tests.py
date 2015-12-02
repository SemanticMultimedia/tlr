import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

# os.environ["COOKIE_SECRET"] = "secret"
# os.environ["GITHUB_CLIENT_ID"] = "x"
# os.environ["GITHUB_SECRET"] = "y"
# os.environ["DATABASE_URL"] = "mysql://tailr:tailr@db/tailr"

from database import MDB as Database

# from config import dbconf, bsconf
from models import *
import models

from peewee import *
from database import *
from peewee import fn


import tornado.testing
import unittest


# database = Database(**dbconf)
# blobstore = None # Blobstore(bsconf.nodes, **bsconf.opts)
# models.initialize(database, blobstore)
# database.create_tables([
#     User,
#     Token,
#     Repo,
#     HMap,
#     CSet,
#     Blob,
# ])



user1 = User()
user2 = User()
repo = Repo()

def addOne(x):
	return x + 1

def multiply(x,y):
	return x * y

def seed():
	user1 = User.create(name="user1", email="user1@example.com")
	user2 = User.create(name="user2", email="user2@example.com")
	repo = Repo.create(user=user1, name="testrepo1", desc="")

seed()

class MyTest(unittest.TestCase):
	def setUp(self):
		pass

	def test_number_five(self):
		self.assertEqual(addOne(5),6)

	def test_multiply(self):
		self.assertEqual(multiply(5,6),30)


# Create Account with credentials
# class Create


# Login and check for success

# Sign in with Github account

# Create repo

# Show Repo

# Push valid data and check for success

#

# push invalid data and check response


if __name__ == '__main__':
	unittest.main()