import hashlib
import zlib
import string

from models import User, Token, Repo, HMap, CSet, Blob
from peewee import IntegrityError, SQL, fn
import RDF
import datetime

import logging
logger = logging.getLogger('debug')

# This factor (among others) determines whether a snapshot is stored rather
# than a delta, depending on the size of the latest snapshot and subsequent
# deltas. For the latest snapshot `base` and deltas `d1`, `d2`, ..., `dn`
# a new snapshot is definitely stored if:
#
# `SNAPF * len(base) <= len(d1) + len(d2) + ... + len(dn)`
#
# In short, larger values will result in longer delta chains and likely reduce
# storage size at the expense of higher revision reconstruction costs.
#
# TODO: Empirically determine a good value with real data/statistics.
SNAPF = 10.0

# Pagination size for indexes (number of resource URIs per page)
INDEX_PAGE_SIZE = 1000

def compress(s):
    return zlib.compress(s)

def decompress(s):
    return zlib.decompress(s)

def __shasum(s):
    return hashlib.sha1(s).digest()

def __get_shasum(key):
    sha = __shasum(key.encode("utf-8")) #hashing
    return sha

'''parse serialized RDF'''
def parse(s, fmt):
    # Parse serialized RDF:
    #
    # RDF/XML:      application/rdf+xml
    # N-Triples:    application/n-triples
    # Turtle:       text/turtle
    stmts = set()
    parser = RDF.Parser(mime_type=fmt)
    for st in parser.parse_string_as_stream(s, "urn:x-default:tailr"):
        stmts.add(str(st) + " .")
    return stmts

def join(parts, sep):
    return string.joinfields(parts, sep)


def get_repo(username, reponame):
    try:
        repo = (Repo
            .select()
            .join(User)
            .where((User.name == username) & (Repo.name == reponame))
            .naive()
            .get())
    except Repo.DoesNotExist:
        repo = None
    return repo

def get_chain_at_ts(repo, key, ts):
    sha = __get_shasum(key)
    return __get_chain_at_ts(repo, sha, ts)

def __get_chain_at_ts(repo, sha, ts):
    # Fetch all relevant changes from the last "non-delta" onwards,
    # ordered by time. The returned delta-chain consists of either:
    # a snapshot followed by 0 or more deltas, or
    # a single delete.
    chain = list(CSet
        .select(CSet.time, CSet.type, CSet.len)
        .where(
            (CSet.repo == repo) &
            (CSet.hkey == sha) &
            (CSet.time <= ts) &
            (CSet.time >= SQL(
                "COALESCE((SELECT time FROM cset "
                "WHERE repo_id = %s "
                "AND hkey_id = %s "
                "AND time <= %s "
                "AND type != %s "
                "ORDER BY time DESC "
                "LIMIT 1), 0)",
                repo.id, sha, ts, CSet.DELTA
            )))
        .order_by(CSet.time)
        .naive())
    
    return chain

def get_chain_tail(repo, key):
    sha = __get_shasum(key)
    return __get_chain_tail(repo, sha)

def __get_chain_tail(repo, sha):
    chain = list(CSet
            .select(CSet.time, CSet.type, CSet.len)
            .where(
                (CSet.repo == repo) &
                (CSet.hkey == sha) &
                (CSet.time >= SQL(
                    "COALESCE((SELECT time FROM cset "
                    "WHERE repo_id = %s "
                    "AND hkey_id = %s "
                    "AND type != %s "
                    "ORDER BY time DESC "
                    "LIMIT 1), 0)",
                    repo.id, sha, CSet.DELTA
                )))
            .order_by(CSet.time)
            .naive())

    return chain

def get_chain_last_cset(repo, key):
    sha = __get_shasum(key)
    return __get_chain_last_cset(repo, sha)

def __get_chain_last_cset(repo, sha):
    try:
        last = (CSet
                .select(CSet.time, CSet.type, CSet.len)
                .where(
                    (CSet.repo == repo) &
                    (CSet.hkey == sha))
                .order_by(CSet.time.desc())
                .limit(1)
                .naive()
                .get())
    except CSet.DoesNotExist:
        return None
    return last

def __get_blob_list(repo, sha, chain):
    return list(__get_blobs(repo, sha, chain))

def __get_blobs(repo, sha, chain):
    #logger.info(":: get_blobs")

    blobs = (Blob
        .select(Blob.data)
        .where(
            (Blob.repo == repo) &
            (Blob.hkey == sha) &
            (Blob.time << map(lambda e: e.time, chain)))
        .order_by(Blob.time)
        .naive())
    return blobs

'''get revision as set of statements'''
def get_revision(repo, key, chain):
    #logger.info(":: get_revision")

    sha = __get_shasum(key)
    return __get_revision(repo, sha, chain)

def __get_revision(repo, sha, chain):
    blobs = __get_blobs(repo, sha, chain)
    #if len(chain) == 1:
         # Special case, where we can simply return
         # the blob data of the snapshot.
    #     snap = blobs.first().data
    #     return decompress(snap)

    stmts = set()

    for i, blob in enumerate(blobs.iterator()):
        data = decompress(blob.data)

        if i == 0:
            # Base snapshot for the delta chain
            stmts.update(data.splitlines())
        else:
            for line in data.splitlines():
                mode, stmt = line[0], line[2:]
                if mode == "A":
                    stmts.add(stmt)
                else:
                    stmts.discard(stmt)
    return stmts

def get_csets(repo, key):
    sha = __get_shasum(key)

    # Generate a timemap containing historic change information
    # for the requested key. The timemap is in the default link-format
    # or as JSON (http://mementoweb.org/guide/timemap-json/).
    csets = (CSet
        .select(CSet.time)
        .where((CSet.repo == repo) & (CSet.hkey == sha))
        .order_by(CSet.time.desc())
        .naive())

    return csets

def get_cset_at_ts(repo, key, ts):
    sha = __get_shasum(key)
    return __get_cset_at_ts(repo, sha, ts)

def __get_cset_at_ts(repo, sha, ts):
    try:
        cset = (CSet
                .select(CSet.time, CSet.type)
                .where((CSet.repo == repo) & (CSet.hkey == sha) & (CSet.time == ts))
                .naive())
    except CSet.DoesNotExist:
        return None

    return cset

def get_cset_next_after_ts(repo, key, ts):
    sha = __get_shasum(key)
    return __get_cset_next_after_ts(repo, sha, ts)

def __get_cset_next_after_ts(repo, sha, ts):
    try:
        cset = (CSet
                .select(CSet.time, CSet.type)
                .where((CSet.repo == repo) & (CSet.hkey == sha) & (CSet.time > ts))
                .order_by(CSet.time)
                .limit(1)
                .naive())
    except CSet.DoesNotExist:
        return None

    return cset

def get_repo_index(repo, ts, page):
    # Subquery for selecting max. time per hkey group
    mx = (CSet
        .select(CSet.hkey, fn.Max(CSet.time).alias("maxtime"))
        .where((CSet.repo == repo) & (CSet.time <= ts))
        .group_by(CSet.hkey)
        .order_by(CSet.hkey)
        .paginate(page, INDEX_PAGE_SIZE)
        .alias("mx"))

    # Query for all the relevant csets (those with max. time values)
    cs = (CSet
        .select(CSet.hkey, CSet.time)
        .join(mx, on=(
            (CSet.hkey == mx.c.hkey_id) &
            (CSet.time == mx.c.maxtime)))
        .where((CSet.repo == repo) & (CSet.type != CSet.DELETE))
        .alias("cs"))

    # Join with the hmap table to retrieve the plain key values
    hm = (HMap
        .select(HMap.val)
        .join(cs, on=(HMap.sha == cs.c.hkey_id))
        .naive())

    return hm.iterator()    

def save_revision(repo, key, chain, stmts, ts):
    sha = __get_shasum(key)

    # TODO: Allow adding revisions with datetime prior to latest #2
    if chain and len(chain) > 0 and not ts > chain[-1].time:
        # Appended timestamps must be monotonically increasing!
        raise ValueError

    if chain == None or len(chain) == 0:
        # Mapping for `key` likely does not exist:
        # Store the SHA-to-KEY mapping in HMap,
        # looking out for possible collisions.
        try:
            HMap.create(sha=sha, val=key)
        except IntegrityError:
            val = (HMap
                   .select(HMap.val)
                   .where(HMap.sha == sha)
                   .scalar())
            if val != key:
                raise IntegrityError

    return __save_revision(repo, sha, chain, stmts, ts)

def __save_revision(repo, sha, chain, stmts, ts):
    # TODO: Allow adding revisions with datetime prior to latest #2
    if chain and len(chain) > 0 and not ts > chain[-1].time:
        # Appended timestamps must be monotonically increasing!
        raise ValueError

    if len(chain) == 0 or chain[0].type == CSet.DELETE:
        # Provide dummy value for `patch` which is never stored.
        # If we get here, we always store a snapshot later on!
        patch = ""
    else:
        # Reconstruct the previous state of the resource
        prev = __get_revision(repo, sha, chain)

        if stmts == prev:
            # No changes, nothing to be done. Bail out.
            return None

        patch = compress(join(
            map(lambda s: "D " + s, prev - stmts) +
            map(lambda s: "A " + s, stmts - prev), "\n"))

    snapc = compress(join(stmts, "\n"))

    # Calculate the accumulated size of the delta chain including
    # the (potential) patch from the previous to the pushed state.
    accumulated_len = reduce(lambda s, e: s + e.len, chain[1:], 0) + len(patch)

    base_len = len(chain) > 0 and chain[0].len or 0 # base length

    if (len(chain) == 0 or
        chain[0].type == CSet.DELETE or
        len(snapc) <= len(patch) or
        SNAPF * base_len <= accumulated_len):
        # Store the current state as a new snapshot
        Blob.create(repo=repo, hkey=sha, time=ts, data=snapc)
        CSet.create(repo=repo, hkey=sha, time=ts, type=CSet.SNAPSHOT,
            len=len(snapc))
    else:
        # Store a directed delta between the previous and current state
        Blob.create(repo=repo, hkey=sha, time=ts, data=patch)
        CSet.create(repo=repo, hkey=sha, time=ts, type=CSet.DELTA,
            len=len(patch))
    return 0

def get_delta_of_memento(repo, key, ts):
    sha = __get_shasum(key)
    return __get_delta_of_memento(repo, sha, ts)

def __get_delta_of_memento(repo, sha, ts):
    added = set()
    deleted = set()

    chain = __get_chain_at_ts(repo, sha, ts)

    if len(chain) > 0:
        cset = chain[-1]
        if cset.type == CSet.DELETE:
            # everything was deleted and is a delta here
            # get the chain before the delete, therefore decrease timestamp of current memento
            prev_chain = __get_chain_at_ts(repo, sha, cset.time - datetime.timedelta(seconds=1))
            if len(prev_chain) > 0:
                prev_data = __get_revision(repo, sha, prev_chain)
                deleted = map(lambda s: "D " + s, prev_data)
        elif cset.type == CSet.DELTA:
            # If Memento is a delta, we just need to deliver the delta itself
            data = decompress(__get_blob_list(repo, sha, chain)[-1].data)
            for line in data.splitlines():
                if line[0] == "A":
                    added.add(line)
                else:
                    deleted.add(line)
        else:
            # CSet is Snapshot => Calculate Delta from snapshot to last delta
            current_data = __get_revision(repo, sha, chain)
            # get the chain before the snashot, therefore decrease timestamp of current memento
            prev_chain = __get_chain_at_ts(repo, sha, cset.time - datetime.timedelta(seconds=1))
            if len(prev_chain) > 0:
                prev_data = __get_revision(repo, sha, prev_chain)
                added = map(lambda s: "A " + s, current_data - prev_data)
                deleted = map(lambda s: "D " + s, prev_data - current_data)
            else:
                # No Memento before this snapshot, everything was added
                added = map(lambda s: "A " + s, current_data)

    return added, deleted

def get_delta_between_mementos(repo, key, ts, delta_ts):
    sha = __get_shasum(key)
    return __get_delta_between_mementos(repo, sha, ts, delta_ts)

def __get_delta_between_mementos(repo, sha, ts, delta_ts):
    added = set()
    deleted = set()

    chain = __get_chain_at_ts(repo, sha, ts)
    prev_chain = __get_chain_at_ts(repo, sha, delta_ts)

    if len(chain) > 0 and len(prev_chain) > 0:
        data = __get_revision(repo, sha, chain)
        prev_data = __get_revision(repo, sha, prev_chain)
        added = map(lambda s: "A " + s, data - prev_data)
        deleted = map(lambda s: "D " + s, prev_data - data)
    else:
        # In any other case at least at one time there is no resource. 
        raise ValueError
    return added, deleted


def save_revision_delete(repo, key, ts):
    sha = __get_shasum(key)

    # Insert the new "delete" change.
    CSet.create(repo=repo, hkey=sha, time=ts, type=CSet.DELETE, len=0)

#### Repository management ####

def remove_repo(repo):
    # remove all csets
    __remove_csets_repo(repo)
    # remove keys from hmap
    __cleanup_hmap()
    # remove repo
    __remove_repo(repo)

def __cleanup_hmap():
    # TODO delete all entries whose sha is not referenced in CSet any more
    pass

def __remove_repo(repo):
    # remove repo
    repo.delete_instance(recursive=True)

def __remove_csets_repo(repo):
    # remove blobs
    q_blobs = Blob.delete().where(Blob.repo == repo)
    q_blobs.execute()

    # remove csets
    q_csets = CSet.delete().where(CSet.repo == repo)
    q_csets.execute()

def __remove_csets(repo, sha):
    # remove blobs
    q_blobs = Blob.delete().where(Blob.repo == repo, Blob.hkey == sha)
    q_blobs.execute()

    # remove csets
    q_csets = CSet.delete().where(CSet.repo == repo, CSet.hkey == sha)
    q_csets.execute()

def __remove_cset(repo, sha, ts):
    # remove blob
    try:
        blob = Blob.get(Blob.repo == repo, Blob.hkey == sha, Blob.time == ts)
        blob.delete_instance()
    except Blob.DoesNotExist:
        return None

    # remove cset
    try:
        cset = CSet.get(CSet.repo == repo, CSet.hkey == sha, CSet.time == ts)
        cset.delete_instance()
    except CSet.DoesNotExist:
        return None

def remove_revision(repo, key, ts):
    # (repo, hkey, time) is composite key for cset
    sha = __get_shasum(key)
    return __remove_revision(repo, sha, ts)

def __remove_revision(repo, sha, ts):
    # keep next revision statements
    stmts_ats = set()
    cset_ats = __get_cset_next_after_ts(repo, sha, ts)
    if (cset_ats != None and list(cset_ats)[-1].type == CSet.DELTA):
        # not last cset
        chain_ats = __get_chain_at_ts(repo, sha, cset_ats.time)
        stmts_ats = __get_revision(repo, sha, chain_ats)

    # remove blob and cset
    __remove_cset(repo, sha, ts)

    # if not last cset, re-compute next cset
    if (cset_ats != None and list(cset_ats)[-1].type == CSet.DELTA):
        __remove_cset(repo, sha, cset_ats.time)
        chain = __get_chain_at_ts(repo, sha, cset_ats.time)
        __save_revision(repo, sha, chain, stmts_ats, cset_ats.time)

    # if all csets removed, remove key from hmap
    if (cset_ats == None):
        __cleanup_hmap()
