import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from peewee import *
from database import MDB as Database

from config import settings, dbconf, bsconf
from models import *

import models

database = Database(**dbconf)
blobstore = None # Blobstore(bsconf.nodes, **bsconf.opts)
models.initialize(database, blobstore)


# import requests

# # os.environ["COOKIE_SECRET"] = "secret"
# # os.environ["GITHUB_CLIENT_ID"] = "x"
# # os.environ["GITHUB_SECRET"] = "y"
# os.environ["DATABASE_URL"] = "mysql://Oleg1@localhost/db1"

# from database import MDB as Database

# # from config import dbconf, bsconf
# from models import *
# import models

# from peewee import *
# from database import *
# from peewee import fn
# from playhouse.db_url import connect


# import tornado.testing
import unittest
import requests
import json

# # database = Database(**dbconf)
# # dbproxy = Proxy()
# # dbproxy.initialize(database)

# databse = connect("mysql://tailr:tailr@db/tailr")

# # blobstore = None # Blobstore(bsconf.nodes, **bsconf.opts)
# # models.initialize(database, blobstore)
# # database.create_tables([
# #     User,
# #     Token,
# #     Repo,
# #     HMap,
# #     CSet,
# #     Blob,
# # ])



user1 = User()
user2 = User()
repo1 = Repo()
repo2 = Repo()
token = Token()


def seed():
	user1 = User.create(name="user1", confirmed=True, github_id="1234", email="user1@example.com")
	user2 = User.create(name="user2", confirmed=True, github_id="5678", email="user2@example.com")
	token = Token.create(value="123456", user=user1, seen=True, desc="important description")
	repo1 = Repo.create(user=user1, name="repo1", desc="important description")
	repo2 = Repo.create(user=user2, name="repo2", desc="important description")

# TODO for local testing check if db is freshly initialized, or has already been seeded  
seed()


class Authorized(unittest.TestCase):

	#######	#######	#######	#######	#######	#######	#######	#######	#######	#######
	# unittest module does sort the tests with cmp()
	# therefore tests are orderer by naming them testXYZ
	# third digit is there to slot tests in
	#######	#######	#######	#######	#######	#######	#######	#######	#######	#######

	def setUp(self):
		pass

	tailrToken = "123456"
	userName = "user1"
	repoName = "repo1"
	repo = (Repo.select(Repo.id).where((Repo.name == "repo1")).naive().get())
	
	key = "http://rdf.data-vocabulary.org/"
	keyWithFragment = "http://rdf.data-vocabulary.org/#fragment"

	uploadDateString = "2013-07-12-00:00:00"
	uploadDateString2 = "2014-08-13-00:00:00"

	params_key = {'key':key}
	params_key_timemap = {'key':key, 'timemap': "true"}
	params_index = {'index': "true"}
	params_datetime = {'key':key,'datetime':uploadDateString}
	params_datetime2 = {'key':key,'datetime':uploadDateString2}
	empty_params = {}

	contentType = "application/n-triples"
	header = {'Authorization':"token "+tailrToken, 'Content-Type':contentType}
	apiURI = "http://localhost:5000/api/"+userName+"/"+repoName
	apiURI2 = "http://localhost:5000/api/user2/repo2"
	notExistingRepo = "http://localhost:5000/api/user1/XXX"

	# payload = set()
	# payload.add("<www.example.com> <http://www.w3.org/2002/07/owl#onProperty> <http://qudt.org/schema/qudt#default> .")
	payload = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person> ."
	payload2 = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person> ."+"\n"+"<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expressions> <http://data.bnf.fr/vocabulary/roles/s70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Persons> ."

	# def uploadValid(self):
	# 	r = request.put(apiURI, params=params, headers=header, data=payload)
	# 	# r = request.put(apiURI, params=params, headers=header)
	# 	self.assertEqual(r.status_code, 500)

	@staticmethod
	def numberOfCSets(repo):
		cs = CSet.select().where(CSet.repo == repo)
		# print ("count of changesets for "+repo.name+" = "+cs.count())
		return cs.count()


	def test010_put_on_empty(self):
		r = requests.put(self.apiURI, params=self.params_datetime, headers=self.header, data=self.payload2)
		self.assertEqual(r.status_code, 200)

	def test011_number_of_changesets_is_set(self):
		self.assertEqual(self.numberOfCSets(self.repo),1)

		
	def test020_put_on_existing(self):
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 200, msg=r.reason)


	def test021_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSets(self.repo),2)


	def test030_get_repo_index(self):
		r = requests.get(self.apiURI, params=self.params_index)
		# only one key in repo
		self.assertEqual(len(r.text.splitlines()), 1)


	def test040_get_repo_timemap(self):
		r = requests.get(self.apiURI, params=self.params_key_timemap)
		resjson = json.loads(r.text)
		# 2 revisions pushed
		# TODO proper unicode decoding. For some reason, u'' in this json is dealt with as an string
		self.assertEqual(len(resjson[u'mementos'][u'list']), 2)
		

	# TODO GET repo ?key mementos on several times (&datetime)

	# TODO GET repo ?key without datetime and timestamp
	#last memento for key should be shown




	# def test_delete_():
	# 	pass

	# 
	# 
	# 
	# TODO Also check content of db not only request
	# 
	# 
	# 


	def test_put_unowned_repo(self):
		# unauthorized because of unowned repo
		# 403 write access fordbidden
		r = requests.put(self.apiURI2, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 403)

	def test_put_without_key(self):
		# 400 Bad Request
		r = requests.put(self.apiURI, params=self.empty_params, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 400)

	def test_put_unexisting_repo(self):
		# 404
		r = requests.put(self.notExistingRepo, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 404)

	# Wird sich in Zukunft eruebrigen, wenn das als feature implementiert ist
	def test030_put_with_older_timestamp(self):
		# 400 Bad Request
		uploadDateString = "2012-07-12-00:00:00"
		params_datetime = {'key':self.key,'datetime':uploadDateString}
		r = requests.put(self.apiURI, params=params_datetime, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 400)


	# TODO raise 400 three times if (index and timemap) or (index and key) or (timemap and not key):
            # raise HTTPError(reason="Invalid arguments.", status_code=400)

	# TODO Raise specific errors, if data is compromised

	# TODO raise integrity error somehow


class Unauthorized(unittest.TestCase):
	def setUp(self):
		pass

	tailrToken = "5678"
	key = "http://rdf.data-vocabulary.org/rdf.xml"
	params = {'key':key}
	contentType = "application/n-triples"
	header = {'Authorization':"token "+tailrToken, 'Content-Type':contentType}
	apiURI = "http://localhost:5000/api/user1/repo1"
	apiURI2 = "http://localhost:5000/api/user2/repo2"

	payload = set()

	def test_put_wrong_token(self):
		# unauthorized because of wrong token
		# 401 unauthorized
		r = requests.put(self.apiURI, params=self.params, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 401)






# # Create Account with credentials
# # class Create


# # Login and check for success

# # Sign in with Github account

# # Create repo

# # Show Repo

# # Push valid data and check for success

# #

# # push invalid data and check response


if __name__ == '__main__':
	unittest.main()