import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from test_helper import parse_link_header

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

import hashlib

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
	repo3 = Repo.create(user=user1, name="lov_test", desc="important description")
	# i = 0 
	# tailrToken = "123456"
	# header = {'Authorization':"token "+tailrToken, 'Content-Type':"application/n-triples"}
	# payload = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person> ."
	# apiURI = "http://localhost:5000/api/user1/lov_test"
	# while i <= 1000:
	# 	key = "http://www.key.de/"+str(i)
	# 	params = {'key':key}
	# 	r = requests.put(apiURI, params=params, headers=header, data=payload)
	# 	i += 1

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

	uploadDateString0 = "2011-07-12-00:00:00"
	uploadDateString = "2013-07-12-00:00:00"
	uploadDateString2 = "2013-07-13-00:00:00"
	uploadDateString3 = "2013-07-11-00:00:00"
	uploadDateString4 = "2014-07-11-00:00:00"
	uploadDateString5 = "2013-07-14-10:00:00"
	uploadDateString5a = "2013-07-14-20:00:00"

	params_key = {'key':key}
	params_key_delta = {'key':key, 'delta': "true"}
	params_datetime_delta = {'key':key, 'delta': "true", 'datetime':uploadDateString}
	params_key_timemap = {'key':key, 'timemap': "true"}
	params_index = {'index': "true"}
	params_ttl = {'key': key_ttl}
	params_ttl_datetime = {'key': key_ttl,'datetime':uploadDateString}
	params_xml = {'key': key_xml}
	params_xml_datetime = {'key': key_xml,'datetime':uploadDateString}
	params_xml_datetime2 = {'key': key_xml,'datetime':uploadDateString2}
	params_xml_datetime2_update = {'key': key_xml, 'datetime':uploadDateString2,'update': "true"}
	params_xml_datetime4_update = {'key': key_xml, 'datetime':uploadDateString4,'update': "true"}
	params_datetime0 = {'key':key,'datetime':uploadDateString0}
	params_datetime = {'key':key,'datetime':uploadDateString}
	params_datetime2 = {'key':key,'datetime':uploadDateString2}
	params_datetime3 = {'key':key,'datetime':uploadDateString3}
	params_datetime4 = {'key':key,'datetime':uploadDateString4}
	params_datetime5 = {'key':key,'datetime':uploadDateString5}
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
	payload3 = "<http://PROPLAYERXYZ.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://PROPLAYERXYZ.bnf.fr/vocabulary/roles/r70> <http://PROPLAYERXYZ.bnf.fr/ark:/12148/cb12204024r#foaf:Person> ."
	empty_payload = ""
	payload_compromised_angle_bracket = "<http://data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person ."
	payload_compromised_wrong_blankNode = ":ab123 <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Persons> ."
	payload_compromised_missing_object = "_:ab123 <http://data.bnf.fr/vocabulary/roles/r70> . "
	payload_compromised_wrong_uri = "<data.bnf.fr/ark:/12148/cb308749370#frbr:Expression> <http://data.bnf.fr/vocabulary/roles/r70> <http://data.bnf.fr/ark:/12148/cb12204024r#foaf:Person> ."


	datetime_clipboard = datetime.datetime.now()

	@classmethod
	def shasum(self, s):
		return hashlib.sha1(s).digest()

	@classmethod
	def get_shasum(self, key):
		sha = Authorized.shasum(key.encode("utf-8")) #hashing
		return sha


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


	@staticmethod
	def getCSetForRepoAtTime(repo, ts, key):
		sha = Authorized.get_shasum(key)
		return CSet.get(CSet.repo == repo, CSet.hkey == sha, CSet.time == ts)


	@staticmethod
	def look_for_string_in_link_header(link_header, s):
		for k,v in link_header.items():
			for m,n in v.items():
				if s in n:
					return True
		return False

	@staticmethod
	def get_datetime_for_memento_rel(link_header, s):
		for k,v in link_header.items():
			for m,n in v.items():
				if s in n:
					return v['datetime']

	@staticmethod
	def get_key_for_value_from_link_header(link_header, s):
		for k,v in link_header.items():
			for m,n in v.items():
				for no in n:
					if s == no:
						return k

	# initial state
	def test000_no_hmap_entry_on_start(self):
		self.assertEqual(self.numberOfHMaps(),0,"hmap table has entries initially")

	def test001_no_cset_entry_on_start(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),0, "cset table has entries initially")

	def test002_no_blob_entry_on_start(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),0,"blob table has entries initially")


	# put empty with timestamp 
	def test010_put_on_empty(self):
		r = requests.put(self.apiURI, params=self.params_datetime, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 200, "putting on an empty repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test011_number_of_changesets_is_set(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),1, "pushing on empty repo did not create a changeset")

	def test012_hmap_entry_exists(self):
		self.assertEqual(self.numberOfHMaps(),1, "pushing on empty repo did not create a hmap entry")

	def test013_blob_entry_exists(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),1, "pushing on empty repo did not create a blob")


	def test014_next_does_not_exist_if_only_one_cset(self):
		r = requests.get(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertFalse(self.look_for_string_in_link_header(link_header, "next"), "Link-header did contain a next entry, although there is only one cset and therefore no next one")

	def test015_prev_does_not_exist_if_only_one_cset(self):
		r = requests.get(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertFalse(self.look_for_string_in_link_header(link_header, "prev"), "Link-header did contain a prev entry, although there is only one cset and therefore no previous one")

	def test016_prev_equals_first_if_only_one_cset(self):
		r = requests.get(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertEqual(self.get_datetime_for_memento_rel(link_header, 'first')[0], self.get_datetime_for_memento_rel(link_header, 'last')[0], "first and last entry were not the same, when there is only one cset")

	def test017_prev_and_first_equals_only_cset_if_only_one_cset(self):
		r = requests.get(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		datetime_str = datetime.datetime.strptime(self.get_datetime_for_memento_rel(link_header, 'first')[0], '%a, %d %b %Y %H:%M:%S GMT').strftime("%Y-%m-%d-%H:%M:%S")
		self.assertEqual(datetime_str, self.uploadDateString , "first and last did not equal the only cset, when there is only one cset")



	# put on same timestamp 
	def test014_put_with_same_timestamp(self):
		r = requests.put(self.apiURI, params=self.params_datetime, headers=self.header, data=self.payload2)
		self.assertEqual(r.status_code, 200, "putting with exact same timestamp does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test015_number_of_csets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),1, "pushing on same timestamp did create a changeset")

	def test016_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),1, "pushing on same timestamp did create a blob")

	def test017_get_content_of_key(self):
		r = requests.get(self.apiURI, params=self.params_datetime)
		self.assertEqual(r.text, self.payload2, "pushing on same time did not replace the memento ")


	# put on existing with current time
	def test020_put_without_timestamp(self):
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 200, "putting on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test021_timestamp_equals_current_time(self):
		cset= self.getLastCSetForRepo(self.repo)
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

	def test025_next_does_not_exist_for_latest_memento(self):
		r = requests.get(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertFalse(self.look_for_string_in_link_header(link_header, "next"), "Link-header did contain a next entry for latest memento")


	def test025_prev_exists_for_latest_memento(self):
		r = requests.get(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertTrue(self.look_for_string_in_link_header(link_header, "prev"), "Link-header did not contain a prev entry for latest memento")

	def test025_prev_is_first_memento_for_latest_memento_when_two_exist(self):
		r = requests.get(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		datetime_str = datetime.datetime.strptime(self.get_datetime_for_memento_rel(link_header, 'prev')[0], '%a, %d %b %Y %H:%M:%S GMT').strftime("%Y-%m-%d-%H:%M:%S")
		self.assertEqual(datetime_str, self.uploadDateString , "first and prev entry were not the same, when there is only one memento")

	def test025_first_is_first_memento_for_latest_memento_when_two_exist(self):
		r = requests.get(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		datetime_str = datetime.datetime.strptime(self.get_datetime_for_memento_rel(link_header, 'first')[0], '%a, %d %b %Y %H:%M:%S GMT').strftime("%Y-%m-%d-%H:%M:%S")
		self.assertEqual(datetime_str, self.uploadDateString)



	def test026_prev_does_not_exist_for_first_cset(self):
		r = requests.get(self.apiURI, params=self.params_datetime, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertFalse(self.look_for_string_in_link_header(link_header, "prev"), "Link-header did contain a prev entry for first memento")

	def test026_next_exists_for_first_cset(self):
		r = requests.get(self.apiURI, params=self.params_datetime, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertTrue(self.look_for_string_in_link_header(link_header, "next"), "Link-header did not contain a next entryfor first memento")

	def test026_next_equals_last_for_first_cset_when_two_exist(self):
		r = requests.get(self.apiURI, params=self.params_datetime, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		datetime_str = datetime.datetime.strptime(self.get_datetime_for_memento_rel(link_header, 'next')[0], '%a, %d %b %Y %H:%M:%S GMT').strftime("%Y-%m-%d-%H:%M:%S")
		datetime_str2 = datetime.datetime.strptime(self.get_datetime_for_memento_rel(link_header, 'last')[0], '%a, %d %b %Y %H:%M:%S GMT').strftime("%Y-%m-%d-%H:%M:%S")
		self.assertEqual(datetime_str, datetime_str2 , "next and last entry were not the same for first memento, when there are two mementos")



	# GET-requests after first pushes
	def test040_get_repo_index(self):
		r = requests.get(self.apiURI, params=self.params_index)
		# only one key in repo
		self.assertEqual(len(r.text.splitlines()), 1, "wrong number of keys in repo (returned via GET index page of repo)")

	def test041_get_user_index(self):
		r = requests.get(self.userURI)
		resjson = json.loads(r.text)
		# 1 repo for user1
		# TODO proper unicode decoding. For some reason, u'' in this json is dealt with as a string
		self.assertEqual(len(resjson[u'repositories'][u'list']), 2, "wrong number of repos for user1 (returned via GET user)\n "+ str(len(resjson[u'repositories'][u'list'])) +" instead of 2")

	def test042_get_user2_index(self):
		r = requests.get(self.user2URI)
		resjson = json.loads(r.text)
		# 1 repo for user2
		# TODO proper unicode decoding. For some reason, u'' in this json is dealt with as a string
		self.assertEqual(len(resjson[u'repositories'][u'list']), 1, "wrong number of repos for user2 (returned via GET user)\n "+ str(len(r.text.splitlines())) +" instead of 1")

	def test043_get_repo_key_timemap(self):
		r = requests.get(self.apiURI, params=self.params_key_timemap)
		resjson = json.loads(r.text)
		# 2 revisions pushed
		# TODO proper unicode decoding. For some reason, u'' in this json is dealt with as a string
		self.assertEqual(len(resjson[u'mementos']['list']), 2, "wrong number of mementos in repo,key (returned via GET timemap page of key)\n"+ str(len(resjson[u'mementos']['list']))+" instead of 2")
		


	# GET-requests for mementos with several timestamps
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



	# PUT same data
	def test070_put_exact_same_data(self):
		time.sleep(1)
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 200, "putting same payload on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test071_number_of_csets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),2, "pushing same data to repo did create a changeset")

	def test072_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),2, "pushing same data to repo did create a blob")
	

	# PUT compromised payload
	def test080_put_compromised_data(self):
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



	# PUT turtle
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

	def test105_initial_cset_is_snapshot(self):
		c = self.getCSetForRepoAtTime(self.repo, self.uploadDateString, self.key_ttl)
		self.assertEqual(c.type, 0, "Pushing initially does not create snapshot but delta instead ("+str(c.type)+")")


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

	def test115_last_cset_is_delta(self):
		c = self.getLastCSetForRepo(self.repo)
		self.assertEqual(c.type, 1, "Pushing with just a small change in payload does not create delta but snapshot instead ("+str(c.type)+")")


	# PUT xml
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



	# # # # # # # # # # 
	# DELETE
	# # # # # # # # # #
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
		self.assertEqual(len(resjson[u'mementos']['list']), 3, "wrong number of mementos in repo,key (returned via GET timemap page of key) after delete")

	def test144_get_repo_key_memento_after_delete(self):
		r = requests.get(self.apiURI, params=self.params_key)
		self.assertEqual(r.status_code, 404, "GET memento after delete does not respond with 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)


	# DELETE after delete
	def test150_delete_existing_after_delete(self):
		# delete without timestamp (to current time)
		time.sleep(1)
		r = requests.delete(self.apiURI, params=self.params_key, headers=self.header)
		self.assertEqual(r.status_code, 200, "deleting a key after a delete does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test151_number_of_csets_not_changed(self):
		time.sleep(1)
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),7, "deleting a key after a delete did create a changeset")

	def test152_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),6, "deleting a key after a delete did create a blob")

	def test153_get_deleted_repo(self):
		r = requests.get(self.apiURI, params=self.params_key)
		self.assertEqual(r.status_code, 404, "GET a deleted key does not return httpcode 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)


	# PUT after delete
	def test160_put_after_delete(self):
		time.sleep(1)
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload)
		self.assertEqual(r.status_code, 200, "putting on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test161_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),8, "pushing after delete did not create a changeset")

	def test162_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),7, "pushing after delete did not create a blob")



	# DELETE before everything
	def test170_delete_with_older_timestamp_than_oldest(self):
		uploadDateString = "2012-07-12-00:00:00"
		params_datetime = {'key':self.key,'datetime':uploadDateString}
		r = requests.delete(self.apiURI, params=params_datetime, headers=self.header)
		self.assertEqual(r.status_code, 404, "DELETE with older timestamp than oldest CSet does not return 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test171_number_of_csets_not_changed(self):
		time.sleep(1)
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),8, "deleting a key before everything did create a changeset")

	def test172_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),7, "deleting a key before everything did create a blob")


	# DELETE inbetween
	def test173_delete_with_timestamp_inbetween(self):
		uploadDateString = "2013-07-14-20:00:00"
		params_datetime = {'key':self.key,'datetime':uploadDateString}
		r = requests.delete(self.apiURI, params=params_datetime, headers=self.header)
		self.assertEqual(r.status_code, 200, "DELETE with timestamp inbetween does not return 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test174_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),7, "pushing after delete did not create a blob")

	def test175_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),9, "pushing after delete did not create a changeset")


	

	# DELETE before a delete prepones the time of the deletion
	def test180_get_content_of_key_before_delete(self):
		params_datetime = {'key':self.key,'datetime':self.uploadDateString5}
		r = requests.get(self.apiURI, params=params_datetime)
		self.assertEqual(r.text, self.payload2, "content of resource right before delete is not the right one")

	def test181_delete_right_before_delete(self):
		# deletes the delete after it and sets the new delete
		params_datetime = {'key':self.key,'datetime':self.uploadDateString5}
		r = requests.delete(self.apiURI, params=params_datetime, headers=self.header)
		self.assertEqual(r.status_code, 200, "DELETE with timestamp right before delete does not return 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test182_get_delete_right_before_delete(self):
		# deletes the delete after it and sets the new delete
		params_datetime = {'key':self.key,'datetime':self.uploadDateString5}
		r = requests.get(self.apiURI, params=params_datetime)
		self.assertEqual(r.status_code, 404, "GET with timestamp at new delete does not respond with 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test183_number_of_changesets_not_changed(self):
		# deletes the delete after it and sets the new delete
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),9, "pushing after delete did not create a changeset")

	def test184_number_of_blobs_not_changed(self):
		# deletes the delete after it and sets the new delete
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),7, "pushing after delete did not create a blob")

	# DELETE after a delete does not do anything because resource is already deleted
	def test185_delete_right_after_delete(self):
		# the new delte should be discarded
		params_datetime = {'key':self.key,'datetime':self.uploadDateString5a}
		r = requests.delete(self.apiURI, params=params_datetime, headers=self.header)
		self.assertEqual(r.status_code, 200, "DELETE with timestamp inbetween does not return 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test186_get_delete_after_delete_right_after_delete(self):
		# resource already deleted before, so still should be 404
		params_datetime = {'key':self.key,'datetime':self.uploadDateString5}
		r = requests.get(self.apiURI, params=params_datetime)
		self.assertEqual(r.status_code, 404, "GET with timestamp at new delete after deleting after it does not respond with 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test187_number_of_changesets_not_changed(self):
		# nothing done
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),9, "pushing after delete did not create a changeset")

	def test188_number_of_blobs_not_changed(self):
		# nothing done
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),7, "pushing after delete did not create a blob")



	def test190_put_xml_on_existing2(self):
		r = requests.put(self.apiURI, params=self.params_xml, headers=self.header_xml, data=open(self.xmlFile3, 'rb'))
		self.assertEqual(r.status_code, 200, "putting turtle on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test191_no_hmap_entry_added(self):
		self.assertEqual(self.numberOfHMaps(),3, "pushing xml on existing key on repo did create a hmap entry")

	def test192_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),8, "pushing xml with existing key did not create a blob")

	def test193_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),10, "pushing xml with existing key on existing repo did not create a changeset")




	# DELETE with &update=true (tries to delete one specific revision)
	def test200_delete_revision_with_update_at_non_existing_ts(self):
		r = requests.delete(self.apiURI, params=self.params_xml_datetime4_update, headers=self.header_xml)
		self.assertEqual(r.status_code, 400, "deleting a revision at non-exitsing timestamp does not return 400\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test201_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),8, "deleting a revision at non-exitsing timestamp did create a blob")

	def test202_number_of_changesets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),10, "deleting a revision at non-exitsing timestamp did create a changeset")		


	def test210_delete_revision(self):
		time.sleep(1)
		r = requests.delete(self.apiURI, params=self.params_xml_datetime2_update, headers=self.header_xml)
		self.assertEqual(r.status_code, 200, "deleting a revision does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test211_number_of_blobs_decreased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),7, "deleting a revision did not delete a blob")

	def test212_number_of_changesets_decreased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),9, "deleting a revision did not delete a changeset")





	def test220_put_insert_revision(self):
		r = requests.put(self.apiURI, params=self.params_datetime4, headers=self.header, data=self.payload2)
		self.assertEqual(r.status_code, 200, "inserting on an existing repo does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test221_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),8, "inserting on an existing repo did not create a blob")

	def test222_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),10, "inserting on an existing repo did not create a changeset")

	def test223_get_repo_key_memento_after_insert(self):
		r = requests.get(self.apiURI, params=self.params_datetime4)
		self.assertEqual(r.text, self.payload2, "GET memento with datetime after insert returns the wrong memento. Was:\n"+r.text+"\nshould be:\n"+self.payload2)


	# PUT before everything
	def test230_put_insert_revision_before(self):
		r = requests.put(self.apiURI, params=self.params_datetime0, headers=self.header, data=self.payload3)
		self.assertEqual(r.status_code, 200, "inserting on an existing repo before initial revision does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test231_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),9, "inserting on an existing repo before initial revision did not create a blob")

	def test232_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),11, "inserting on an existing repo before initial revision did not create a changeset")



	# PUT after everything
	def test240_put_insert_revision_after(self):
		time.sleep(1)
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload3)
		self.assertEqual(r.status_code, 200, "inserting on an existing repo after last revision does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test241_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),10, "inserting on an existing repo after last revision did not create a blob")

	def test242_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),12, "inserting on an existing repo after last revision did not create a changeset")


	def test250_put_replace_revision(self):
		r = requests.put(self.apiURI, params=self.params_datetime4, headers=self.header, data=self.payload3)
		self.assertEqual(r.status_code, 200, "replacing an existing revision does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)
	
	def test251_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),10, "inserting on an existing repo after last revision did not create a blob")

	def test252_number_of_changesets_not_changed(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),12, "inserting on an existing repo after last revision did not create a changeset")



	def test260_get_delta_of_revision_without_timestamp(self):
		# shall return the delta of the last reveision
		r = requests.get(self.apiURI, params=self.params_key_delta, headers=self.header)
		delta_string = "A "+ self.payload3 +"\nD "+ self.payload
		self.assertEqual(r.text, delta_string)


	def test261_get_delta_of_revision_with_timestamp(self):
		r = requests.get(self.apiURI, params=self.params_datetime_delta, headers=self.header)
		lines = self.payload2.splitlines()
		delta_string = ""
		for line in lines:
			delta_string += "A " + line + "\n"
		delta_string += "D "+ self.payload3
		self.assertEqual(r.text, delta_string)


	def test262_get_delta_between_two_non_delete_revisions_with_timestamp(self):
		# if delta param is timestamp a delte is calculated between to timestamps
		r = requests.get(self.apiURI, params={'key': self.key, 'datetime': self.uploadDateString4, 'delta': self.uploadDateString}, headers=self.header)
		lines = self.payload2.splitlines()
		delta_string = "A "+ self.payload3
		for line in lines:
			delta_string += "\nD " + line
		self.assertEqual(r.text, delta_string)

	def test263_get_delta_between_two_delete_revisions_with_timestamps_unordered(self):
		r = requests.get(self.apiURI, params={'key': self.key, 'datetime': self.uploadDateString, 'delta': self.uploadDateString4}, headers=self.header)
		lines = self.payload2.splitlines()
		delta_string = "A "+ self.payload3
		for line in lines:
			delta_string += "\nD " + line
		self.assertEqual(r.text, delta_string)
	
	def test264_get_delta_between_revisions_with_same_data(self):
		r = requests.get(self.apiURI, params={'key': self.key, 'datetime': self.uploadDateString4, 'delta': self.uploadDateString0}, headers=self.header)
		self.assertEqual(r.text, "")

	def test265_get_delta_between_two_non_delete_revisions_without_timestamp(self):
		r = requests.get(self.apiURI, params={'key': self.key, 'delta': self.uploadDateString}, headers=self.header)
		lines = self.payload2.splitlines()
		delta_string = "A "+ self.payload3
		for line in lines:
			delta_string += "\nD " + line
		self.assertEqual(r.text, delta_string)

	def test266_get_delta_after_delete(self):
		r = requests.get(self.apiURI, params={'key': self.key, "datetime": self.uploadDateString4, 'delta': "true"}, headers=self.header)
		delta_string = "A "+ self.payload3
		self.assertEqual(r.text, delta_string)
	
	def test267_get_delta_of_delete(self):
		r = requests.get(self.apiURI, params={'key': self.key, 'datetime': self.uploadDateString5, 'delta': "true"}, headers=self.header)
		lines = self.payload2.splitlines()
		delta_string = "D " + lines[0]+ "\n" + "D " + lines[1]
		self.assertEqual(r.text, delta_string)

	def test268_get_delta_between_non_delete_revision_with_timestamp_and_delete(self):
		r = requests.get(self.apiURI, params={'key': self.key, 'datetime': self.uploadDateString0, 'delta': self.uploadDateString5}, headers=self.header)
		delta_string = "D "+ self.payload3
		self.assertEqual(r.text, delta_string)
		
	def test269_get_delta_of_first_revision(self):
		r = requests.get(self.apiURI, params={'key': self.key, "datetime": self.uploadDateString0, 'delta': "true"}, headers=self.header)
		delta_string = "A "+ self.payload3
		self.assertEqual(r.text, delta_string)



	def test280_get_delta_between_two_delete_revisions_with_timestamp(self):
		time.sleep(1)
		rd = requests.delete(self.apiURI, params=self.params_key, headers=self.header)
		r = requests.get(self.apiURI, params={'key': self.key, 'delta': self.uploadDateString5}, headers=self.header)
		self.assertEqual(r.text, "")

	def test281_number_of_blobs_not_changed(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),10, "deleting after everything did create a blob")

	def test282_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),13, "deleting after everything did not create a changeset")



	def test_290_put_same_data_than_before_delete(self):
		time.sleep(1)
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.payload3)
		self.assertEqual(r.status_code, 200, "inserting on an existing repo after last revision does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test_291_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),11, "pushing after everything did not create a blob")

	def test_292_number_of_changesets_increased(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),14, "pushing after everything did not create a changeset")



	def test_300_head_request_without_timestamp_for_latest_resource_does_not_contain_next(self):
		r = requests.head(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertFalse(self.look_for_string_in_link_header(link_header, "next"))
		

	def test_301_first_equals_first_cset_for_last_memento(self):
		r = requests.head(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		datetime_str = datetime.datetime.strptime(self.get_datetime_for_memento_rel(link_header, 'first')[0], '%a, %d %b %Y %H:%M:%S GMT').strftime("%Y-%m-%d-%H:%M:%S")
		self.assertEqual(datetime_str, self.uploadDateString0 , "first entry in link-header was not the first one")


	def test_302_next_in_link_header_is_next_for_memento_inbetween(self):
		r = requests.head(self.apiURI, params=self.params_datetime5, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		datetime_str = datetime.datetime.strptime(self.get_datetime_for_memento_rel(link_header, 'next')[0], '%a, %d %b %Y %H:%M:%S GMT').strftime("%Y-%m-%d-%H:%M:%S")
		self.assertEqual(datetime_str, self.uploadDateString4 , "next entry in link-header of head-request was not the next one")

	def test_302_prev_in_link_header_is_prev_for_memento_inbetween(self):
		r = requests.head(self.apiURI, params=self.params_datetime5, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		datetime_str = datetime.datetime.strptime(self.get_datetime_for_memento_rel(link_header, 'prev')[0], '%a, %d %b %Y %H:%M:%S GMT').strftime("%Y-%m-%d-%H:%M:%S")
		self.assertEqual(datetime_str, self.uploadDateString , "prev entry in link-header of head-request was not the prev one")

	def test_302_first_in_link_header_is_first_for_memento_inbetween(self):
		r = requests.head(self.apiURI, params=self.params_datetime5, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		datetime_str = datetime.datetime.strptime(self.get_datetime_for_memento_rel(link_header, 'first')[0], '%a, %d %b %Y %H:%M:%S GMT').strftime("%Y-%m-%d-%H:%M:%S")
		self.assertEqual(datetime_str, self.uploadDateString0 , "first entry in link-header of head-request was not the first one")


	# timemap is contained


	def test_310_delete_revision_between_same_data(self):
		# deletes revision between two revisions that have the same data. 
		# after that there are two revisions with same data behind each other. 
		# tailr shall delete the second one, because resource has been existing since first one

		rg = requests.get(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(rg.headers['Link'])
		datetime_str = datetime.datetime.strptime(self.get_datetime_for_memento_rel(link_header, 'prev')[0], '%a, %d %b %Y %H:%M:%S GMT').strftime("%Y-%m-%d-%H:%M:%S")
		r = requests.delete(self.apiURI, params={'key': self.key, 'datetime':datetime_str, 'update': "true"}, headers=self.header)
		self.assertEqual(r.status_code, 200, "deleting a delete-revision does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)
	
	def test_311_number_of_blobs_decreased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),10, "deleting revision, so that two with same data follow each other did not delete blob of following revision")

	def test_312_number_of_changesets_decreased_by_two(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),12, "deleting revision, so that two with same data follow each other did not delete changesets of deleted revision and of following revision")


	# timegate is given and right
	def test_320_timegate_set_in_link_header(self):
		r = requests.head(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertEqual(self.get_key_for_value_from_link_header(link_header, "timegate"), self.apiURI+"?key="+self.key, "timegate was not set or not right in link-header")

	def test_321_timemap_set_in_link_header(self):
		r = requests.head(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertEqual(self.get_key_for_value_from_link_header(link_header, "timemap"), self.apiURI+"?key="+self.key+"&timemap=true", "timemap was not set or not right in link-header")

	def test_321_original_set_in_link_header(self):
		r = requests.head(self.apiURI, params=self.params_key, headers=self.header)
		link_header = parse_link_header(r.headers['Link'])
		self.assertEqual(self.get_key_for_value_from_link_header(link_header, "original"), self.key, "original was not set or not right in link-header")
	



	def test_330_put_empty_payload(self):
		r = requests.put(self.apiURI, params=self.params_key, headers=self.header, data=self.empty_payload)
		self.assertEqual(r.status_code, 200, "putting empty payload does not return httpcode 200\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test_331_number_of_blobs_increased(self):
		self.assertEqual(self.numberOfBlobsForRepo(self.repo),11, "dputting empty payload did not create a blob")

	def test_332_number_of_changesets_increased_by_two(self):
		self.assertEqual(self.numberOfCSetsForRepo(self.repo),13, "dputting empty payload did not create a changeset")

	def test_333_get_content_after_empty_put(self):
		r = requests.get(self.apiURI, params=self.params_key)
		self.assertEqual(r.text, self.empty_payload, "GET memento after empty push returns the wrong memento. Was:\n"+r.text+"\nshould be:\n"+self.empty_payload)
	
	# TODO Tests
	# test commit messages

	# TODO test for more facts about deleting a revision
	# update-delete without ts shall not create a del-cset
	# TODO delete mit update=true zu einem zeitpunkt, an dem keine revision existiert, soll kein delete erzeugen

	# TODO test other return formats 

	# TODO check if snapshots and deltas are created as wanted, somehow force a second snapshot after initial one


	def test780_get_index_for_non_existing_user(self):
		r = requests.get(self.user3URI)
		self.assertEqual(r.status_code, 404, "GET index of non existing user does not respond with 404\n"+"Statuscode was instead: "+str(r.status_code)+"\nHTTP-reason was: "+r.reason)

	def test781_get_user3_index(self):
		user3 = User.create(name="user3", confirmed=True, github_id="5678", email="user3@example.com")
		r = requests.get(self.user3URI)
		resjson = json.loads(r.text)
		# 0 repos for user1
		# TODO proper unicode decoding. For some reason, u'' in this json is dealt with as a string
		self.assertEqual(len(resjson[u'repositories'][u'list']), 0, "wrong number of repos for user3 (returned via GET user)\n "+ str(len(r.text.splitlines())) +" instead of 0")



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