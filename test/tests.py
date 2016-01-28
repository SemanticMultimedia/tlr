import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from peewee import *
from database import MDB as Database

from config import settings, dbconf, bsconf
from models import *
import models

import unittest
import requests
import json
import datetime



database = Database(**dbconf)
blobstore = None # Blobstore(bsconf.nodes, **bsconf.opts)
models.initialize(database, blobstore)

# for local testing
os.system(parentdir+"/unprepare.py")
os.system(parentdir+"/prepare.py")


def seed():
	user1 = User.create(name="user1", confirmed=True, github_id="1234", email="user1@example.com")
	user2 = User.create(name="user2", confirmed=True, github_id="5678", email="user2@example.com")
	token = Token.create(value="123456", user=user1, seen=True, desc="important description")
	repo1 = Repo.create(user=user1, name="repo1", desc="important description")
	repo2 = Repo.create(user=user2, name="repo2", desc="important description")


user1 = User()
user2 = User()
repo1 = Repo()
repo2 = Repo()
token = Token()
# TODO for local testing check if db is freshly initialized, or has already been seeded  
seed()


# Fixture for Athorized pushing 
class Authorized(unittest.TestCase):

	#######	#######	#######	#######	#######	#######	#######	#######	#######	#######
	# unittest module does sort the tests with cmp()
	# therefore tests are orderer by naming them test000
	# third digit is there to slot tests in
	#######	#######	#######	#######	#######	#######	#######	#######	#######	#######

	def setUp(self):
		pass

	tailrToken = "123456"
	userName = "user1"
	repoName = "repo1"
	repo = (Repo.select(Repo.id).where((Repo.name == "repo1")).naive().get())
	
	key = "http://rdf.data-vocabulary.org/"
	key_ttl = "http://www.w3.org/TR/rdf-syntax-grammar"

	ttlFile = "example.ttl"

	keyWithFragment = "http://rdf.data-vocabulary.org/#fragment"

	uploadDateString = "2013-07-12-00:00:00"
	uploadDateString2 = "2013-07-13-00:00:00"
	uploadDateString3 = "2013-07-11-00:00:00"

	params_key = {'key':key}
	params_key_timemap = {'key':key, 'timemap': "true"}
	params_index = {'index': "true"}
	params_ttl = {'key': key_ttl}
	params_datetime = {'key':key,'datetime':uploadDateString}
	params_datetime2 = {'key':key,'datetime':uploadDateString2}
	params_datetime3 = {'key':key,'datetime':uploadDateString3}
	empty_params = {}

	contentType_ntriples = "application/n-triples"
	header = {'Authorization':"token "+tailrToken, 'Content-Type':contentType_ntriples}
	header_ttl = {'Authorization':"token "+tailrToken, 'Content-Type':"text/turtle"}
	apiURI = "http://localhost:5000/api/"+userName+"/"+repoName
	apiURI2 = "http://localhost:5000/api/user2/repo2"
	notExistingRepo = "http://localhost:5000/api/user1/XXX"

	payload = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person> ."
	payload2 = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expressions> <http://data.bnf.fr/vocabulary/roles/s70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Persons> ."+"\n"+"<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person> ."
	payload_compromised_angle_bracket = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person ."
	payload_compromised_missing_dot = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Persons> "

	@staticmethod
	def numberOfCSetsForRepo(repo):
		cs = CSet.select().where(CSet.repo == repo)
		return cs.count()

	@staticmethod
	def numberOfHMaps():
		hmaps = HMap.select().where(HMap.val != "")
		return hmaps.count()

	@staticmethod
	def numberOfBlobsForRepo(repo):
		blobs = Blob.select().where(Blob.repo == repo)
		return blobs.count()

	@staticmethod
	def getLastCSetForRepo(repo):
		return CSet.select().where(CSet.repo == repo).order_by(CSet.time.desc()).get()





	def test000_no_hmap_entry_on_start(self):
		self.assertEqual(self.numberOfHMaps(),0,"hmap table has entries initially")

	def test001_no_cset_entry_on_start(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),0, "cset table has entries initially")

	def test002_no_blob_entry_on_start(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),0,"blob table has entries initially")

	def test010_put_on_empty(self):
		# put with timestamp
		r = requests.put(self.apiURI, params=self.params_datetime, headers=self.header, data=self.payload2)
		self.assertEqual(r.status_code, 200, "putting on an empty repo does not return httpcode 200")

	def test011_number_of_changesets_is_set(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),1, "pushing on empty repo did not create a changeset")

	def test012_hmap_entry_exists(self):
		self.assertEqual(self.numberOfHMaps(),1, "pushing on empty repo did not create a hmap entry")

	def test013_blob_entry_exists(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),1, "pushing on empty repo did not create a blob")



	def test020_put_on_existing(self):
		# put without timestamp (to current time)
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 200, "putting on an existing repo does not return httpcode 200\n"+r.reason)

	def test021_timestamp_equals_current_time(self):
		cset= self.getLastCSetForRepo(self.repo)
		# python creates pythonic timedelta object
		# test for 2 seconds, although most times only miliseconds pass until here
		timeDiff = (datetime.datetime.now() - cset.time)
		lessThan2SecondsPassed = timeDiff.total_seconds() < 2
		self.assertTrue(lessThan2SecondsPassed, "Cset was not created on current time")

	def test022_no_hmap_entry_for_existing_push(self):
		self.assertEqual(self.numberOfHMaps(),1, "pushing on existing repo did not create a hmap entry")

	def test023_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),2, "pushing on existing repo did not create a changeset")

	def test024_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),2, "pushing on existing repo did not create a blob")



	def test040_get_repo_index(self):
		r = requests.get(self.apiURI, params=self.params_index)
		# only one key in repo
		self.assertEqual(len(r.text.splitlines()), 1, "wrong number of keys in repo (returned via GET index page of repo)")


	def test050_get_repo_timemap(self):
		r = requests.get(self.apiURI, params=self.params_key_timemap)
		resjson = json.loads(r.text)
		# 2 revisions pushed
		# TODO proper unicode decoding. For some reason, u'' in this json is dealt with as a string
		self.assertEqual(len(resjson[u'mementos'][u'list']), 2, "wrong number of mementos in repo,key (returned via GET timemap page of key)")
		

	def test060_get_repo_key_memento_with_datetime(self):
		# datetimeparam is the exact one 
		r = requests.get(self.apiURI, params=self.params_datetime)
		self.assertEqual(r.text, self.payload2, "GET memento with datetime param returns the wrong memento")

	def test061_get_repo_key_memento_with_datetime_inbetween(self):
		# datetimeparam not exactly that of memento but a day after. tailr should chose the last one
		r = requests.get(self.apiURI, params=self.params_datetime2)
		self.assertEqual(r.text, self.payload2, "GET memento with datetime param between two mementos returns the wrong memento")

	def test062_get_repo_key_memento_without_datetime(self):
		# if nothing else is given, the last memento shouldbe returned
		r = requests.get(self.apiURI, params=self.params_key)
		self.assertEqual(r.text, self.payload, "GET memento without datetime param returns the wrong memento")

	def test061_get_repo_key_memento_with_datetime_before(self):
		# if get query timestamp is before first revision there is no resource
		r = requests.get(self.apiURI, params=self.params_datetime3)
		self.assertEqual(r.status_code, 404, "GET memento with invalid (too early) datetime does not respond with 404")


	def test070_put_exact_same_data(self):
		# this is a perfect legitimate request, should return 200
		# crucial point is, what happens in the database --> see next tests
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 200, "putting same payload on an existing repo does not return httpcode 200\n"+r.reason)

	def test071_number_of_csets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),2, "pushing same data to repo did create a changeset")

	def test072_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),2, "pushing same data to repo did create a blob")
	

	def test_080_put_compromised_data(self):
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload_compromised_angle_bracket)
		self.assertEqual(r.status_code, 500, "PUT compromised data (missing '>') does not respond with 500")

	def test081_number_of_csets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),2, "pushing compromised data '>' to repo did create a changeset")

	def test082_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),2, "pushing compromised data '>' to repo did create a blob")

	def test_090_put_compromised_data2(self):
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload_compromised_missing_dot)
		self.assertEqual(r.status_code, 500, "PUT compromised data (missing '.') does not respond with 500")

	def test091_number_of_csets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),2, "pushing compromised data (missing '.') to repo did create a changeset")

	def test092_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),2, "pushing compromised data (missing '.') to repo did create a blob")



	def test100_put_ttl(self):
		r = requests.put(self.apiURI, params=self.params_ttl, headers=self.header_ttl, data=open(self.ttlFile, 'rb'))
		self.assertEqual(r.status_code, 200, "putting turtle on an existing repo does not return httpcode 200\n"+r.reason)

	def test101_hmap_entry_added(self):
		self.assertEqual(self.numberOfHMaps(),2, "pushing ttl with new key on repo did not create a hmap entry")

	def test102_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),3, "pushing ttl with new key on existing repo did not create a blob")

	def test103_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),3, "pushing ttl with new key on existing repo did not create a changeset")


	# TODO check for specific csets and hmaps not only for count of whole repo 

	# TODO def test_delete_():
	# TODO get after delete and expect deleted resource

	# TODO check if snapshots and deltas are created as wanted, somehow dorce a second snapshot after initial one



	# TODO Test all sorts of datatypes that tailr accepts


	def test_put_unowned_repo(self):
		# unauthorized because of unowned repo
		# 403 write access fordbidden
		r = requests.put(self.apiURI2, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 403, "PUT to unownded repo does not return 403 (write access forbidden)")

	def test_put_without_key(self):
		# 400 Bad Request
		r = requests.put(self.apiURI, params=self.empty_params, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 400, "PUT without key does not return 400")

	def test_put_unexisting_repo(self):
		# 404
		r = requests.put(self.notExistingRepo, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 404, "PUT to unexisting repo does not return 404")

	# Wird sich in Zukunft eruebrigen, wenn das als feature implementiert ist
	def test030_put_with_older_timestamp(self):
		# 400 Bad Request
		uploadDateString = "2012-07-12-00:00:00"
		params_datetime = {'key':self.key,'datetime':uploadDateString}
		r = requests.put(self.apiURI, params=params_datetime, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 400, "PUT with older timestamp than newest CSet does not return 400")


	def test_get_bad_request_index_and_timestamp(self):
		r = requests.get(self.apiURI+"?timemap=true&index=true")
		self.assertEqual(r.status_code, 400, "Bad GET request with index and timestamp =true does not return 400")


	def test_get_bad_request_index_and_key(self):
		r = requests.get(self.apiURI+"?key="+self.key+"&index=true")
		self.assertEqual(r.status_code, 400, "Bad GET request with index=true and key set does not return 400")

	def test_get_bad_request_timemap_and_not_key(self):
		r = requests.get(self.apiURI+"?timemap=true")
		self.assertEqual(r.status_code, 400, "Bad GET request with timemap=true and no key set does not return 400")

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
		self.assertEqual(r.status_code, 401, "PUT with wrong token does not return 401")






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