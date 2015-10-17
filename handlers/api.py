import datetime
import functools
import hashlib
import string
import time
import zlib

from tornado.web import HTTPError
from tornado.escape import url_escape, json_encode
from peewee import IntegrityError, SQL, fn
import RDF

from models import User, Token, Repo, HMap, CSet, Blob
from handlers import RequestHandler
import revision_logic

def authenticated(method):
    """Decorate API methods to require user authentication via token."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            raise HTTPError(401)
        return method(self, *args, **kwargs)
    return wrapper

# Query string date format, e.g. `...?datetime=2015-05-11-16:56:21`
QSDATEFMT = "%Y-%m-%d-%H:%M:%S"

# RFC 1123 date format, e.g. `Mon, 11 May 2015 16:56:21 GMT`
RFC1123DATEFMT = "%a, %d %b %Y %H:%M:%S GMT"

def date(s, fmt):
    return datetime.datetime.strptime(s, fmt)

def now():
    return datetime.datetime.utcnow()

# Pagination size for indexes (number of resource URIs per page)
INDEX_PAGE_SIZE = 1000

# TODO: Tune zlib compression parameters `level`, `wbits`, `bufsize`?

def join(parts, sep):
    return string.joinfields(parts, sep)

class BaseHandler(RequestHandler):
    """Base class for all web API handlers."""

    def get_current_user(self):
        try:
            header = self.request.headers["Authorization"]
            method, value = header.split(" ")
            if method == "token":
                user = User.select().join(Token).where(Token.value == value)
                return user.get()
            else:
                return None
        except (KeyError, ValueError, User.DoesNotExist):
            return None

    def check_xsrf_cookie(self):
        pass

class RepoHandler(BaseHandler):
    """Processes repository calls: Push, timegate, memento, timemap etc."""
    # def head(self, username, reponame):
    #     pass

    def get(self, username, reponame):
        
        timemap = self.get_query_argument("timemap", "false") == "true"
        index = self.get_query_argument("index", "false") == "true"
        key = self.get_query_argument("key", None)
        
        if (index and timemap) or (index and key) or (timemap and not key):
        
            raise HTTPError(400)

        if self.get_query_argument("datetime", None):
            datestr = self.get_query_argument("datetime")
            ts = date(datestr, QSDATEFMT)
        elif "Accept-Datetime" in self.request.headers:
            datestr = self.request.headers.get("Accept-Datetime")
            ts = date(datestr, RFC1123DATEFMT)
        else:
            ts = now()

        #load repo
        repo = revision_logic.load_repo(username, reponame)
        if repo == None:
            raise HTTPError(404)

        if key and not timemap:
            # Recreate the resource for the given key in its latest state -
            # if no `datetime` was provided - or in the state it was in at
            # the time indicated by the passed `datetime` argument.

            self.set_header("Content-Type", "application/n-quads")
            self.set_header("Vary", "accept-datetime")

            sha = revision_logic.get_shasum(key)
            chain = revision_logic.get_chain(repo, sha, ts)

            if chain == None:
                raise HTTPError(404)

            timegate_url = (self.request.protocol + "://" +
                self.request.host + self.request.path)
            timemap_url = (self.request.protocol + "://" +
                self.request.host + self.request.uri + "&timemap=true")

            self.set_header("Link",
                '<%s>; rel="original"'
                ', <%s>; rel="timegate"'
                ', <%s>; rel="timemap"'
                % (key, timegate_url, timemap_url))

            self.set_header("Memento-Datetime",
                chain[-1].time.strftime(RFC1123DATEFMT))

            if chain[0].type == CSet.DELETE:
                # The last change was a delete. Return a 404 response with
                # appropriate "Link" and "Memento-Datetime" headers.
                raise HTTPError(404)

            # Load the data required in order to restore the resource state.
            blobs = revision_logic.create_blobs(repo, sha, chain)
            if len(chain) == 1:
                # Special case, where we can simply return
                # the blob data of the snapshot.
                snap = blobs.first().data
                return self.finish(revision_logic.decompress(snap))

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

            self.write(join(stmts, "\n"))
        elif key and timemap:
            # Generate a timemap containing historic change information
            # for the requested key. The timemap is in the default link-format
            # or as JSON (http://mementoweb.org/guide/timemap-json/).

            sha = revision_logic.get_shasum(key)
            csit = revision_logic.create_cset(repo, sha)            
                
            # TODO: Paginate?

            try:
                first = csit.next()
            except StopIteration:
                # Resource for given key does not exist.
                raise HTTPError(404)

            req = self.request
            base = req.protocol + "://" + req.host + req.path

            accept = self.request.headers.get("Accept", "")

            if "application/json" in accept or "*/*" in accept:
                self.set_header("Content-Type", "application/json")

                self.write('{"original_uri": ' + json_encode(key))
                self.write(', "mementos": {"list":[')

                m = ('{{"datetime": "{0}", "uri": "' + base + '?key=' +
                    url_escape(key) +
                    '&datetime={1}"}}')

                self.write(m.format(first.time.isoformat(),
                    first.time.strftime(QSDATEFMT)))

                for cs in csit:
                    self.write(', ' + m.format(cs.time.isoformat(),
                        cs.time.strftime(QSDATEFMT)))

                self.write(']}')
                self.write('}')
            else:
                m = (',\n'
                    '<' + base + '?key=' + url_escape(key) + '&datetime={0}>'
                    '; rel="memento"'
                    '; datetime="{1}"'
                    '; type="application/n-quads"')

                self.set_header("Content-Type", "application/link-format")

                self.write('<' + key + '>; rel="original"')
                self.write(m.format(first.time.strftime(QSDATEFMT),
                    first.time.strftime(RFC1123DATEFMT)))

                for cs in csit:
                    self.write(m.format(cs.time.strftime(QSDATEFMT),
                        cs.time.strftime(RFC1123DATEFMT)))
        elif index:
            # Generate an index of all URIs contained in the dataset at the
            # provided point in time or in its current state.

            self.set_header("Vary", "accept-datetime")
            self.set_header("Content-Type", "text/plain")

            page = int(self.get_query_argument("page", "1"))

            hm = generate_index(repo, ts, page)

            for h in hm:
                self.write(h.val + "\n")
        else:
            raise HTTPError(400)
            
    @authenticated
    def put(self, username, reponame):
        # Create a new revision of the resource specified by `key`.
        fmt = self.request.headers.get("Content-Type", "application/n-triples")
        key = self.get_query_argument("key", None)

        if username != self.current_user.name:
            raise HTTPError(403)

        if not key:
            raise HTTPError(400)

        datestr = self.get_query_argument("datetime", None)
        ts = datestr and date(datestr, QSDATEFMT) or now()

        repo = revision_logic.loadRepo(username, reponame)
        if repo == None:
            raise HTTPError(404)

        sha = revision_logic.get_shasum(key)
        chain = revision_logic.get_chain_without_time(repo, sha)

        try:
            revision_logic.detect_collisions(chain, sha, ts, key)
        except ValueError:
            raise HTTPError(400)
        except IntegrityError:
            raise HTTPError(500)
        

        # Parse and normalize into a set of N-Quad lines
        stmts = parse(self.request.body, fmt)
        snapc = compress(join(stmts, "\n"))

        prev_state = revision_logic.reconstruct_prev_state(chain, repo, sha, stmts, patch, snapc, ts)
        if prev_state == None:
            self.finish()

    @authenticated
    def delete(self, username, reponame):
        # Check whether the key exists and if maybe the last change already is
        # a delete, else insert a `CSet.DELETE` entry without any blob data.

        key = self.get_query_argument("key")

        if username != self.current_user.name:
            raise HTTPError(403)

        if not key:
            raise HTTPError(400)

        datestr = self.get_query_argument("datetime", None)
        ts = datestr and date(datestr, QSDATEFMT) or now()

        repo = revision_logic.load_repo(username, reponame)
        if repo == None:
            raise HTTPError(404)
        
        sha = revision_logic.get_shasum(key)
        last = revision_logic.create_last_set(sha, repo)
        if last[0] == False:
            raise HTTPError(400)

        if not ts > last[1]:
            # Appended timestamps must be monotonically increasing!
            raise HTTPError(400)

        if last[2] == CSet.DELETE:
            # The resource was deleted already, return instantly.
            return self.finish()

        insert_delete_changes(repo, last, ts)
