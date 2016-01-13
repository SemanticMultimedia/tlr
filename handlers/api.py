import datetime
import functools
import string

import json
import traceback

from tornado.web import HTTPError
from tornado.escape import url_escape, json_encode
#from peewee import IntegrityError, SQL, fn
from peewee import IntegrityError

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

    def write_error(self, status_code, **kwargs):
        self.set_header('Content-Type', 'text/json')
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            lines = []
            for line in traceback.format_exception(*kwargs["exc_info"]):
                lines.append(line)
            self.finish(json.dumps({
                'error': {
                    'code': status_code,
                    'message': self._reason,
                    'traceback': lines,
                }
            }))
        else:
            self.finish(json.dumps({
                'error': {
                    'code': status_code,
                    'message': self._reason,
                }
            }))


class RepoHandler(BaseHandler):

    # def setHeader(self, key, timemap):
    #
    #     if key and not timemap:
    #         self.set_header("Content-Type", "application/n-quads")
    #         self.set_header("Vary", "accept-datetime")
    #
    #         sha = revision_logic.get_shasum(key)
    #         chain = revision_logic.get_chain(repo, sha, ts)
    #
    #         if chain == None:
    #             raise HTTPError(404)
    #
    #         timegate_url = (self.request.protocol + "://" +
    #                         self.request.host + self.request.path)
    #         timemap_url = (self.request.protocol + "://" +
    #                         self.request.host + self.request.uri + "&timemap=true")
    #
    #         #TODO: set link for "first memento", "last memento"
    #         self.set_header("Link",
    #                         '<%s>; rel="original"'
    #                         ', <%s>; rel="timegate"'
    #                         ', <%s>; rel="timemap"'
    #                         % (key, timegate_url, timemap_url))
    #
    #         self.set_header("Memento-Datetime",
    #                         chain[-1].time.strftime(RFC1123DATEFMT))
    #     elif key and timemap:
    #         self.set_header("Content-Type", "application/json")


    # """Processes repository calls: Push, timegate, memento, timemap etc."""
    # def head(self, username, reponame):
    #     self.check_args()
    #
    #     timemap = self.get_query_argument("timemap", "false") == "true"
    #     index = self.get_query_argument("index", "false") == "true"
    #     key = self.get_query_argument("key", None)
    #
    #     if (index and timemap) or (index and key) or (timemap and not key):
    #         raise HTTPError(400)
    #
    #     if self.get_query_argument("datetime", None):
    #         datestr = self.get_query_argument("datetime")
    #         ts = date(datestr, QSDATEFMT)
    #     elif "Accept-Datetime" in self.request.headers:
    #         datestr = self.request.headers.get("Accept-Datetime")
    #         ts = date(datestr, RFC1123DATEFMT)
    #     else:
    #         ts = now()
    #
    #     #load repo
    #     repo = revision_logic.load_repo(username, reponame)
    #     if repo == None:
    #         raise HTTPError(404)
    #
    #     self.setHeader()
    #
    #     self.finish()


    """Processes repository calls: Push, timegate, memento, timemap etc."""
    def get(self, username, reponame):
        timemap = self.get_query_argument("timemap", "false") == "true"
        index = self.get_query_argument("index", "false") == "true"
        key = self.get_query_argument("key", None)

        if (index and timemap) or (index and key) or (timemap and not key):
            raise HTTPError(reason="Invalid arguments.", status_code=400)

        if self.get_query_argument("datetime", None):
            datestr = self.get_query_argument("datetime")
            ts = date(datestr, QSDATEFMT)
        elif "Accept-Datetime" in self.request.headers:
            datestr = self.request.headers.get("Accept-Datetime")
            ts = date(datestr, RFC1123DATEFMT)
        else:
            ts = now()

        #load repo
        repo = revision_logic.get_repo(username, reponame)
        if repo == None:
            raise HTTPError(reason="Repo not found.", status_code=404)

        if key and not timemap:
            self.__get_revision(repo, key, ts)
        elif key and timemap:
            self.__get_timemap(repo, key)
        elif index:
            self.__get_index(repo, ts)
        else:
            raise HTTPError(reason="Missing arguments.", status_code=400)

    def __get_revision(self, repo, key, ts):
        # Recreate the resource for the given key
        # - in its latest state (if no `datetime` was provided) or
        # - in the state it was in at the time indicated by the passed `datetime` argument.

        self.set_header("Content-Type", "application/n-quads")
        self.set_header("Vary", "accept-datetime")

        chain = revision_logic.get_chain_at_ts(repo, key, ts)

        if len(chain) == 0:
            raise HTTPError(reason="Resource not found in repo.", status_code=404)

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
            raise HTTPError(reason="Resource not exists at time (has been deleted).", status_code=404)

        stmts = revision_logic.get_revision(repo, key, chain)

        self.write(join(stmts, "\n"))

    def __get_timemap(self, repo, key):
        # Generate a timemap containing historic change information
        # for the requested key. The timemap is in the default link-format
        # or as JSON (http://mementoweb.org/guide/timemap-json/).

        csets = revision_logic.get_csets(repo, key)
        csit = csets.iterator()

        # TODO: Paginate?

        try:
            first = csit.next()
        except StopIteration:
            # Resource for given key does not exist.
            raise HTTPError(reason="Resource not found in repo.", status_code=404)

        timemap_url = (self.request.protocol + "://" +
                       self.request.host + self.request.uri)
        timegate_url = (self.request.protocol + "://" +
                        self.request.host + self.request.path + "?key=" + key)
        accept = self.request.headers.get("Accept", "")

        if "application/json" in accept or "*/*" in accept:
            self.set_header("Content-Type", "application/json")

            self.write('{"original_uri": ' + json_encode(key))
            self.write(', "mementos": {"list":[')

            m = ('{{"datetime": "{0}", "uri": "' + timegate_url +
                 '&datetime={1}"}}')

            self.write(m.format(first.time.isoformat(),
                                first.time.strftime(QSDATEFMT)))

            for cs in csit:
                self.write(', ' + m.format(cs.time.isoformat(),
                                           cs.time.strftime(QSDATEFMT)))

            self.write(']}')
            self.write('}')
        elif "application/link-format" in accept:
            self.set_header("Content-Type", "application/link-format")

            m = (',\n' +
                 '<' + timegate_url + '&datetime={0}>\n' +
                 '  ; rel="memento"' +
                 '; datetime="{1}"' +
                 '; type="application/n-quads"')

            self.write('<' + key + '>\n  ; rel="original"')
            self.write(',\n<' + timemap_url + '>\n  ; rel="self"')
            self.write(m.format(first.time.strftime(QSDATEFMT),
                                first.time.strftime(RFC1123DATEFMT)))

            for cs in csit:
                self.write(m.format(cs.time.strftime(QSDATEFMT),
                                    cs.time.strftime(RFC1123DATEFMT)))
        else:
            raise HTTPError(reason="Requested timemap format not supported.", status_code=400)

    def __get_index(self, repo, ts):
        # Generate an index of all URIs contained in the dataset at the
        # provided point in time or in its current state.

        self.set_header("Vary", "accept-datetime")
        self.set_header("Content-Type", "text/plain")

        page = int(self.get_query_argument("page", "1"))

        hm = revision_logic.get_repo_index(repo, ts, page)

        for h in hm:
            self.write(h.val + "\n")

    @authenticated
    def put(self, username, reponame):
        # Create a new revision of the resource specified by `key`.
        fmt = self.request.headers.get("Content-Type", "application/n-triples")
        key = self.get_query_argument("key", None)

        if username != self.current_user.name:
            raise HTTPError(403)
        if not key:
            raise HTTPError(reason="Missing argument 'key'.", status_code=400)

        repo = revision_logic.get_repo(username, reponame)
        if repo == None:
            raise HTTPError(reason="Repo not found.", status_code=404)

        datestr = self.get_query_argument("datetime", None)
        ts = datestr and date(datestr, QSDATEFMT) or now()

        chain = revision_logic.get_chain_tail(repo, key)

        # Parse and normalize into a set of N-Quad lines
        stmts = revision_logic.parse(self.request.body, fmt)

        try:
            prev_state = revision_logic.save_revision(repo, key, chain, stmts, ts)
        except ValueError:
            raise HTTPError(reason="Timestamps must be monotonically increasing.", status_code=400)
        except IntegrityError:
            raise HTTPError(500)

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
            raise HTTPError(reason="Missing argument 'key'.", status_code=400)

        repo = revision_logic.get_repo(username, reponame)
        if repo == None:
            raise HTTPError(reason="Repo not found.", status_code=404)

        datestr = self.get_query_argument("datetime", None)
        ts = datestr and date(datestr, QSDATEFMT) or now()

        #chain = revision_logic.get_chain_tail(repo, key)

        last = revision_logic.get_chain_last_cset(repo, key)

        if last == None:
            raise HTTPError(reason="Resource not found in repo.", status_code=404)

        if not ts > last.time:
            # Appended timestamps must be monotonically increasing!
            raise HTTPError(reason="Timestamps must be monotonically increasing.", status_code=400)

        if last.type == CSet.DELETE:
            # The resource was deleted already, return instantly.
            self.finish()

        revision_logic.save_revision_delete(repo, key, ts)
