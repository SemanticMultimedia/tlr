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
import time



database = Database(**dbconf)
blobstore = None # Blobstore(bsconf.nodes, **bsconf.opts)
models.initialize(database, blobstore)

# for local testing
# os.system(parentdir+"/unprepare.py")
# os.system(parentdir+"/prepare.py")


def seed():
	user1 = User.create(name="user1", confirmed=True, github_id="1234", email="user1@example.com")
	user2 = User.create(name="user2", confirmed=True, github_id="5678", email="user2@example.com")
	token = Token.create(value="123456", user=user1, seen=True, desc="important description")
	repo1 = Repo.create(user=user1, name="repo1", desc="important description")
	repo2 = Repo.create(user=user2, name="repo2", desc="important description")

# def seed_repo3():


user1 = User()
user2 = User()
repo1 = Repo()
repo2 = Repo()
token = Token()
# TODO for local testing check if db is freshly initialized, or has already been seeded  
seed()



#######	#######	#######	#######	#######	#######	#######	#######	#######	#######
# unittest module does sort the tests with cmp()
# therefore tests are orderer by naming them test000
# third digit is there to slot tests in
#######	#######	#######	#######	#######	#######	#######	#######	#######	#######
#######	#######	#######	#######	#######	#######	#######	#######	#######	#######
# at sometimes calling time.sleep() is unavoidable
# precision of the timestamps in the db are seconds
# if you try to create two or more CSets within one second, primary keys will be the same
#######	#######	#######	#######	#######	#######	#######	#######	#######	#######




# Fixture for Athorized pushing 
class Authorized(unittest.TestCase):


	def setUp(self):
		pass

	tailrToken = "123456"
	userName = "user1"
	repoName = "repo1"
	repo = (Repo.select(Repo.id).where((Repo.name == "repo1")).naive().get())
	
	key = "http://rdf.data-vocabulary.org/"
	key_ttl = "http://www.w3.org/TR/rdf-syntax-grammar"
	key_xml = "http://www.w3.org/TR/rdf-syntax-grammarXML"

	ttlFile = "test/example.ttl"
	ttlFile2 = "test/example2.ttl"
	xmlFile = "test/example.xml"
	xmlFile2 = "test/example2.xml"
	xmlFile3 = "test/example3.xml"

	keyWithFragment = "http://rdf.data-vocabulary.org/#fragment"

	uploadDateString = "2013-07-12-00:00:00"
	uploadDateString2 = "2013-07-13-00:00:00"
	uploadDateString3 = "2013-07-11-00:00:00"

	params_key = {'key':key}
	params_key_timemap = {'key':key, 'timemap': "true"}
	params_index = {'index': "true"}
	params_ttl = {'key': key_ttl}
	params_ttl_datetime = {'key': key_ttl,'datetime':uploadDateString}
	params_xml = {'key': key_xml}
	params_xml_datetime = {'key': key_xml,'datetime':uploadDateString}
	params_xml_datetime2 = {'key': key_xml,'datetime':uploadDateString2}
	params_xml_datetime2_update = {'key': key_xml,'datetime': uploadDateString2,'update': "true"}
	params_datetime = {'key':key,'datetime':uploadDateString}
	params_datetime2 = {'key':key,'datetime':uploadDateString2}
	params_datetime3 = {'key':key,'datetime':uploadDateString3}
	empty_params = {}

	contentType_ntriples = "application/n-triples"
	header = {'Authorization':"token "+tailrToken, 'Content-Type':contentType_ntriples}
	header_ttl = {'Authorization':"token "+tailrToken, 'Content-Type':"text/turtle"}
	header_xml = {'Authorization':"token "+tailrToken, 'Content-Type':"application/rdf+xml"}
	apiURI = "http://localhost:5000/api/"+userName+"/"+repoName
	apiURI2 = "http://localhost:5000/api/user2/repo2"
	userURI = "http://localhost:5000/api/"+userName
	user2URI = "http://localhost:5000/api/user2"
	user3URI = "http://localhost:5000/api/user3"
	notExistingRepo = "http://localhost:5000/api/user1/XXX"

	payload = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person> ."
	payload2 = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expressions> <http://data.bnf.fr/vocabulary/roles/s70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Persons> ."+"\n"+"<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person> ."
	payload_compromised_angle_bracket = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person ."
	payload_compromised_wrong_blankNode = ":ab123 <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Persons> ."
	payload_compromised_missing_object = "_:ab123 <http://data.bnf.fr/vocabulary/roles/r70> . "
	payload_compromised_wrong_uri = "<data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person> ."



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
		self.assertEqual(r.status_code, 200, "putting on an empty repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test011_number_of_changesets_is_set(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),1, "pushing on empty repo did not create a changeset")

	def test012_hmap_entry_exists(self):
		self.assertEqual(self.numberOfHMaps(),1, "pushing on empty repo did not create a hmap entry")

	def test013_blob_entry_exists(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),1, "pushing on empty repo did not create a blob")

	def test014_put_with_same_timestamp(self):
		r = requests.put(self.apiURI, params=self.params_datetime, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 400, "putting with exact same timestamp does not return httpcode 400\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test015_number_of_csets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),1, "pushing on same timestamp did create a changeset")

	def test016_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),1, "pushing on same timestamp did create a blob")



	def test020_put_on_existing(self):
		# put without timestamp (to current time)
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 200, "putting on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test021_timestamp_equals_current_time(self):
		cset= self.getLastCSetForRepo(self.repo)
		# python creates pythonic datetime.timedelta object
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


	# Will be a feature in the future, this will be obsolete then
	def test030_put_with_older_timestamp(self):
		# 400 Bad Request
		uploadDateString = "2012-07-12-00:00:00"
		params_datetime = {'key':self.key,'datetime':uploadDateString}
		r = requests.put(self.apiURI, params=params_datetime, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 400, "PUT with older timestamp than newest CSet does not return 400\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)



	def test040_get_repo_index(self):
		r = requests.get(self.apiURI, params=self.params_index)
		# only one key in repo
		self.assertEqual(len(r.text.splitlines()), 1, "wrong number of keys in repo (returned via GET index page of repo)")

	def test041_get_user_index(self):
		r = requests.get(self.userURI)
		resjson = json.loads(r.text)
		# 1 repo for user1
		# TODO proper unicode decoding. For some reason, u'' in this json is dealt with as a string
		self.assertEqual(len(resjson[u'repositories'][u'list']), 1, "wrong number of repos for user1 (returned via GET user)\n "+ str(len(r.text.splitlines())) +" instead of 1")

	def test042_get_user2_index(self):
		r = requests.get(self.user2URI)
		resjson = json.loads(r.text)
		# 1 repo for user2
		# TODO proper unicode decoding. For some reason, u'' in this json is dealt with as a string
		self.assertEqual(len(resjson[u'repositories'][u'list']), 1, "wrong number of repos for user2 (returned via GET user)\n "+ str(len(r.text.splitlines())) +" instead of 1")


	def test050_get_repo_key_timemap(self):
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
		# if nothing else is given, the last memento should be returned
		r = requests.get(self.apiURI, params=self.params_key)
		self.assertEqual(r.text, self.payload, "GET memento without datetime param returns the wrong memento")

	def test061_get_repo_key_memento_with_datetime_before(self):
		# if get query timestamp is before first revision there is no resource
		r = requests.get(self.apiURI, params=self.params_datetime3)
		self.assertEqual(r.status_code, 404, "GET memento with invalid (too early) datetime does not respond with 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)


	def test070_put_exact_same_data(self):
		# this is a perfect legitimate request, should return 200
		# sleep to avoid pushing within the same second
		time.sleep(1)
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 200, "putting same payload on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test071_number_of_csets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),2, "pushing same data to repo did create a changeset")

	def test072_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),2, "pushing same data to repo did create a blob")
	


	def test080_put_compromised_data(self):
		# time.sleep(1)
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload_compromised_angle_bracket)
		self.assertEqual(r.status_code, 500, "PUT compromised data (missing '>') does not respond with 500\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test081_number_of_csets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),2, "pushing compromised data '>' to repo did create a changeset")

	def test082_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),2, "pushing compromised data '>' to repo did create a blob")


	def test083_put_compromised_data2(self):
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload_compromised_wrong_blankNode)
		self.assertEqual(r.status_code, 500, "PUT compromised data (wrong blank node) does not respond with 500\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test084_put_compromised_data3(self):
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload_compromised_missing_object)
		self.assertEqual(r.status_code, 500, "PUT compromised data (missing object in n-triple) does not respond with 500\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test085_put_compromised_data4(self):
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload_compromised_wrong_uri)
		self.assertEqual(r.status_code, 500, "PUT compromised data (compromised uri) does not respond with 500\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test086_number_of_csets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),2, "pushing compromised data (missing object, compromised uri, compromised blank node) to repo did create a changeset")

	def test087_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),2, "pushing compromised data (missing object, compromised uri, compromised blank node) to repo did create a blob")




	def test100_put_ttl(self):
		r = requests.put(self.apiURI, params=self.params_ttl_datetime, headers=self.header_ttl, data=open(self.ttlFile2, 'rb'))
		self.assertEqual(r.status_code, 200, "putting turtle on an existing repo with new key does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test101_hmap_entry_added(self):
		self.assertEqual(self.numberOfHMaps(),2, "pushing ttl with new key on repo did not create a hmap entry")

	def test102_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),3, "pushing ttl with new key on existing repo did not create a blob")

	def test103_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),3, "pushing ttl with new key on existing repo did not create a changeset")

	def test104_get_repo_index(self):
		r = requests.get(self.apiURI, params=self.params_index)
		# two keys in repo
		self.assertEqual(len(r.text.splitlines()), 2, "wrong number of keys in repo (returned via GET index page of repo) after pushing new key")



	def test110_put_ttl_on_existing(self):
		r = requests.put(self.apiURI, params=self.params_ttl, headers=self.header_ttl, data=open(self.ttlFile, 'rb'))
		self.assertEqual(r.status_code, 200, "putting turtle on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test111_no_hmap_entry_added(self):
		self.assertEqual(self.numberOfHMaps(),2, "pushing ttl on existing key on repo did create a hmap entry")

	def test112_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),4, "pushing ttl with existing key did not create a blob")

	def test113_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),4, "pushing ttl with existing key on existing repo did not create a changeset")

	def test114_get_repo_index(self):
		r = requests.get(self.apiURI, params=self.params_index)
		# two keys in repo
		self.assertEqual(len(r.text.splitlines()), 2, "wrong number of keys in repo (returned via GET index page of repo) after pushing on existing key")





	def test120_put_xml(self):
		r = requests.put(self.apiURI, params=self.params_xml_datetime, headers=self.header_xml, data=open(self.xmlFile2, 'rb'))
		self.assertEqual(r.status_code, 200, "putting turtle on an existing repo with new does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test121_hmap_entry_added(self):
		self.assertEqual(self.numberOfHMaps(),3, "pushing xml with new key on repo did not create a hmap entry")

	def test122_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),5, "pushing xml with new key on existing repo did not create a blob")

	def test123_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),5, "pushing xml with new key on existing repo did not create a changeset")

	def test124_get_repo_index(self):
		r = requests.get(self.apiURI, params=self.params_index)
		# three keys in repo
		self.assertEqual(len(r.text.splitlines()), 3, "wrong number of keys in repo (returned via GET index page of repo) after pushing new key")


	def test130_put_xml_on_existing(self):
		r = requests.put(self.apiURI, params=self.params_xml_datetime2, headers=self.header_xml, data=open(self.xmlFile, 'rb'))
		self.assertEqual(r.status_code, 200, "putting turtle on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test131_no_hmap_entry_added(self):
		self.assertEqual(self.numberOfHMaps(),3, "pushing xml on existing key on repo did create a hmap entry")

	def test132_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),6, "pushing xml with existing key did not create a blob")

	def test133_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),6, "pushing xml with existing key on existing repo did not create a changeset")

	def test134_get_repo_index(self):
		r = requests.get(self.apiURI, params=self.params_index)
		# three keys in repo
		self.assertEqual(len(r.text.splitlines()), 3, "wrong number of keys in repo (returned via GET index page of repo) after pushing on existing key")





	def test140_delete_existing(self):
		# delete without timestamp (to current time)
		time.sleep(1)
		r = requests.delete(self.apiURI, params=self.params_key, headers=self.header)
		self.assertEqual(r.status_code, 200, "deleting a key does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test141_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),7, "deleting key on existing repo did not create a changeset")

	def test142_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),6, "deleting key on existing repo did create a blob")

	def test143_get_repo_timemap(self):
		r = requests.get(self.apiURI, params=self.params_key_timemap)
		resjson = json.loads(r.text)
		# 3 revisions pushed
		# TODO proper unicode decoding. For some reason, u'' in this json is dealt with as a string
		self.assertEqual(len(resjson[u'mementos'][u'list']), 3, "wrong number of mementos in repo,key (returned via GET timemap page of key) after delete")

	def test144_get_repo_key_memento_after_delete(self):
		r = requests.get(self.apiURI, params=self.params_key)
		self.assertEqual(r.status_code, 404, "GET memento after delete does not respond with 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)



	def test150_delete_existing_after_delete(self):
		# delete without timestamp (to current time)
		time.sleep(1)
		r = requests.delete(self.apiURI, params=self.params_key, headers=self.header)
		self.assertEqual(r.status_code, 200, "deleting a key after a delete does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

# THIS ONE IS ACTUALLY FALSE, Deleting after delete should not create a changeset
	def test151_number_of_csets_not_changed(self):
		time.sleep(1)
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),8, "deleting a key after a delete did create a changeset")

	def test152_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),6, "deleting a key after a delete did create a blob")

	def test153_get_deleted_repo(self):
		r = requests.get(self.apiURI, params=self.params_key)
		self.assertEqual(r.status_code, 404, "GET a deleted key does not return httpcode 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test154_put_after_delete(self):
		time.sleep(1)
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 200, "putting on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test155_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),7, "pushing after delete did not create a blob")

	def test156_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),9, "pushing after delete did not create a changeset")


	# Will get obsolete in the future, when this is implemented
	def test160_delete_with_older_timestamp(self):
		# 400 Bad Request
		uploadDateString = "2012-07-12-00:00:00"
		params_datetime = {'key':self.key,'datetime':uploadDateString}
		r = requests.delete(self.apiURI, params=params_datetime, headers=self.header)
		self.assertEqual(r.status_code, 400, "DELETE with older timestamp than newest CSet does not return 400\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)


	# def test170_add_repo(self):
	# 	global user1
	# 	repo3 = Repo.create(user=user1, name="repo3", desc="important description")
	# 	self.assertEqual(len(resjson[u'repositories'][u'list']), 2, "wrong number of repos for user1 (returned via GET user)\n "+ str(len(r.text.splitlines())) +" instead of 1")

	def test180_get_index_for_non_existing_user(self):
		r = requests.get(self.user3URI)
		self.assertEqual(r.status_code, 404, "GET index of non existing user does not respond with 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test181_get_user3_index(self):
		user3 = User.create(name="user3", confirmed=True, github_id="5678", email="user3@example.com")
		r = requests.get(self.user3URI)
		resjson = json.loads(r.text)
		# 0 repos for user1
		# TODO proper unicode decoding. For some reason, u'' in this json is dealt with as a string
		self.assertEqual(len(resjson[u'repositories'][u'list']), 0, "wrong number of repos for user3 (returned via GET user)\n "+ str(len(r.text.splitlines())) +" instead of 0")

	def test190_put_xml_on_existing(self):
		r = requests.put(self.apiURI, params=self.params_xml, headers=self.header_xml, data=open(self.xmlFile3, 'rb'))
		self.assertEqual(r.status_code, 200, "putting turtle on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test191_delete_revision(self):
		time.sleep(1)
		r = requests.delete(self.apiURI, params=self.params_xml_datetime2_update, headers=self.header_xml)
		self.assertEqual(r.status_code, 200, "deleting a revision does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	# TODO test other return formats 

	# TODO check if snapshots and deltas are created as wanted, somehow force a second snapshot after initial one




	def test_put_unowned_repo(self):
		# unauthorized because of unowned repo
		# 403 write access fordbidden
		r = requests.put(self.apiURI2, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 403, "PUT to unownded repo does not return 403 (write access forbidden)\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test_delete_unowned_repo(self):
		# unauthorized because of unowned repo
		# 403 write access fordbidden
		r = requests.delete(self.apiURI2, params=self.params_key, headers=self.header)
		self.assertEqual(r.status_code, 403, "DELETE on unownded repo does not return 403 (write access forbidden)\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test_put_without_key(self):
		# 400 Bad Request
		r = requests.put(self.apiURI, params=self.empty_params, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 400, "PUT without key does not return 400\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test_delete_without_key(self):
		# 400 Bad Request
		r = requests.delete(self.apiURI, params=self.empty_params, headers=self.header)
		self.assertEqual(r.status_code, 400, "DELETE without key does not return 400\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test_put_unexisting_repo(self):
		# 404
		r = requests.put(self.notExistingRepo, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 404, "PUT to unexisting repo does not return 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test_delete_unexisting_repo(self):
		# 404
		r = requests.delete(self.notExistingRepo, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 404, "PUT to unexisting repo does not return 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)


	def test_get_bad_request_index_and_timestamp(self):
		r = requests.get(self.apiURI+"?timemap=true&index=true")
		self.assertEqual(r.status_code, 400, "Bad GET request with index and timestamp =true does not return 400\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)


	def test_get_bad_request_index_and_key(self):
		r = requests.get(self.apiURI+"?key="+self.key+"&index=true")
		self.assertEqual(r.status_code, 400, "Bad GET request with index=true and key set does not return 400\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test_get_bad_request_timemap_and_not_key(self):
		r = requests.get(self.apiURI+"?timemap=true")
		self.assertEqual(r.status_code, 400, "Bad GET request with timemap=true and no key set does not return 400\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)




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



if __name__ == '__main__':
	unittest.main()