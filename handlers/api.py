import datetime
import functools
import string

import json
import traceback

from tornado.web import HTTPError
from tornado.escape import url_escape, json_encode
#from peewee import IntegrityError, SQL, fn
from peewee import IntegrityError
from RDF import RedlandError

from models import User, Token, Repo, HMap, CSet, Blob
from handlers import RequestHandler
import revision_logic

import logging
logger = logging.getLogger('debug')

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
    # replace microseconds, because otherwise this fraction will cause 
    # inconsitencies when comparing to datetimes that are exact to the second only
    return datetime.datetime.utcnow().replace(microsecond=0)

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

class UserHandler(BaseHandler):
    """Processes user-regarding requests, such as the index page for a user"""
    def get(self, username):
        try:
            user = User.select().where(User.name == username).get()
        except User.DoesNotExist:
            raise HTTPError(reason="User not found.", status_code=404)
        
        repos = Repo.select().where(Repo.user == user)
        reposit = repos.iterator()

        # TODO: Paginate?

        first = None
        try:
            first = reposit.next()
        except StopIteration:
            # No repos for user
            # No need to raise an error, just return empty list in json
            pass
            

        accept = self.request.headers.get("Accept", "")
        user_url = (self.request.protocol + "://" + self.request.host)

        if "application/json" in accept or "*/*" in accept:
            self.set_header("Content-Type", "application/json")

            self.write('{"username": ' + json_encode(username))
            self.write(', "repositories": {"list":[')

            m = ('{{"name": "{0}", "uri": "' + user_url +
                 '/'+username+'/{0}"}}')

            if first:
                self.write(m.format(first.name))

            for repo in reposit:
                self.write(', ' + m.format(repo.name))

            self.write(']}')
            self.write('}')

        # TODO other return formats

class RepoHandler(BaseHandler):

# Memento/Timegate Notes:
# Header:
# Vary: accept-datetime --> timegate used content-negotiation
# timegate-responses contain: original, timemap, from, until, 


    """Processes repository calls: Push, timegate, memento, timemap etc."""
    def get(self, username, reponame):
        timemap = self.get_query_argument("timemap", "false") == "true"
        index = self.get_query_argument("index", "false") == "true"
        key = self.get_query_argument("key", None)
        delta = self.get_query_argument("delta", "false") == "true"
        # if delta is not True but there is a delta param, check if it is a valid ts. 
        if self.get_query_argument("delta", False) and not delta:
            datestr = self.get_query_argument("delta")
            try:
                delta_ts = date(datestr, QSDATEFMT)
            except ValueError:
                raise HTTPError(reason="Invalid format of delta timestamp", status_code=400)
        else:
            delta_ts = None

        if (index and timemap) or (index and key) or (timemap and not key):
            raise HTTPError(reason="Invalid arguments.", status_code=400)

        if self.get_query_argument("datetime", None):
            datestr = self.get_query_argument("datetime")
            try:
                ts = date(datestr, QSDATEFMT)
            except ValueError:
                raise HTTPError(reason="Invalid format of datetime param", status_code=400)
        elif "Accept-Datetime" in self.request.headers:
            datestr = self.request.headers.get("Accept-Datetime")
            ts = date(datestr, RFC1123DATEFMT)
        else:
            ts = now()

        #load repo
        repo = revision_logic.get_repo(username, reponame)
        if repo == None:
            raise HTTPError(reason="Repo not found.", status_code=404)

        if key and not timemap and not delta and not delta_ts:
            self.__get_revision(repo, key, ts)
            # # currently no need to query next and prev through api. Link-Field in Header should contain them
            # if self.get_query_argument("next", None) == "true":
            #     self.__get_next_memento(repo,key,ts)
            # elif self.get_query_argument("prev", None) == "true":
            #     self.__get_prev_memento(repo,key,ts)
            # else:
            #     self.__get_revision(repo, key, ts)
        elif key and timemap:
            self.__get_timemap(repo, key)
        elif key and delta:
            self.__get_delta_of_memento(repo, key, ts)
        elif key and delta_ts:
            self.__get_delta_between_mementos(repo, key, ts, delta_ts)
        elif index:
            self.__get_index(repo, ts)
        else:
            raise HTTPError(reason="Missing arguments.", status_code=400)

    def __get_revision(self, repo, key, ts, header_only=False):
        # Recreate the resource for the given key
        # - in its latest state (if no `datetime` was provided) or
        # - in the state it was in at the time indicated by the passed `datetime` argument.

        if not header_only:
            self.set_header("Content-Type", "application/n-quads")
        self.set_header("Vary", "accept-datetime")

        chain = revision_logic.get_chain_at_ts(repo, key, ts)
        if len(chain) == 0:
            raise HTTPError(reason="Resource not found in repo.", status_code=404)

        # if no datetime given, ts will be now(), therefor cs_prev and cs_next won't work
        # therefore get time of last cset in chain
        ts = chain[-1].time

        timegate_url = (self.request.protocol + "://" +
                        self.request.host + self.request.path) + "?key=" + key
        timemap_url = (self.request.protocol + "://" +
                       self.request.host + self.request.path + "?key=" + key + "&timemap=true")

        link_header = ( '<%s>; rel="original"'
                        ', <%s>; rel="timegate"'
                        ', <%s>; rel="timemap"'
                        % (key, timegate_url, timemap_url))

        cs_first = revision_logic.get_first_cset_of_repo(repo, key)
        cs_last = revision_logic.get_last_cset_of_repo(repo, key)
        cs_prev = revision_logic.get_cset_prev_before_ts(repo, key, ts)
        cs_next = revision_logic.get_cset_next_after_ts(repo, key, ts)

        cs_first_url = self.request.protocol + "://" + self.request.host + self.request.path + "?key=" + key + "&datetime=" + cs_first.time.strftime(QSDATEFMT)

        if cs_first.time == cs_last.time:
            # only one CSet
            link_header += (', <%s>; rel="first last memento"; datetime="%s"' % (cs_first_url, cs_first.time.strftime(RFC1123DATEFMT)))
        else:
            # more than one CSet --> first != last
            cs_last_url = self.request.protocol + "://" + self.request.host + self.request.path + "?key=" + key + "&datetime=" + cs_last.time.strftime(QSDATEFMT)

            if cs_prev:
                cs_prev_url = self.request.protocol + "://" + self.request.host + self.request.path + "?key=" + key + "&datetime=" + cs_prev.time.strftime(QSDATEFMT)
                if cs_prev.time == cs_first.time:
                    link_header += (', <%s>; rel="prev first memento"; datetime="%s"' % (cs_prev_url, cs_prev.time.strftime(RFC1123DATEFMT)))
                else:
                    link_header += (', <%s>; rel="first memento"; datetime="%s"' % (cs_first_url, cs_first.time.strftime(RFC1123DATEFMT)))
                    link_header += (', <%s>; rel="prev memento"; datetime="%s"' % (cs_prev_url, cs_prev.time.strftime(RFC1123DATEFMT)))
            else: 
                link_header += (', <%s>; rel="first memento"; datetime="%s"' % (cs_first_url, cs_first.time.strftime(RFC1123DATEFMT)))

            if cs_next:
                cs_next_url = self.request.protocol + "://" + self.request.host + self.request.path + "?key=" + key + "&datetime=" + cs_next.time.strftime(QSDATEFMT)
                if cs_next.time == cs_last.time:
                    link_header += (', <%s>; rel="next last memento"; datetime="%s"' % (cs_next_url, cs_next.time.strftime(RFC1123DATEFMT)))
                else:
                    link_header += (', <%s>; rel="next memento"; datetime="%s"' % (cs_next_url, cs_next.time.strftime(RFC1123DATEFMT)))
                    link_header += (', <%s>; rel="last memento"; datetime="%s"' % (cs_last_url, cs_last.time.strftime(RFC1123DATEFMT)))
            else:
                link_header += (', <%s>; rel="last memento"; datetime="%s"' % (cs_last_url, cs_last.time.strftime(RFC1123DATEFMT)))


        self.set_header("Memento-Datetime",
                        chain[-1].time.strftime(RFC1123DATEFMT))

        self.set_header("Link", link_header)

        if not header_only:
            if chain[0].type == CSet.DELETE:
                # The last change was a delete. Return a 404 response with
                # appropriate "Link" and "Memento-Datetime" headers.
                raise HTTPError(reason="Resource does not exist at that time (has been deleted).", status_code=404)

            stmts = revision_logic.get_revision(repo, key, chain)

            self.write(join(stmts, "\n"))


    def __get_delta_of_memento(self, repo, key, ts):
        added, deleted = revision_logic.get_delta_of_memento(repo, key, ts)

        accept = self.request.headers.get("Accept", "")
        self.set_header("Vary", "accept-datetime")
        if "application/json" in accept:
            encoder = json.JSONEncoder()

            self.set_header("Content-Type", "application/json")
            self.write('{"resource_uri": "'+self.request.protocol+"://"+self.request.host+self.request.uri+'"')

            self.write(', "added":')
            self.write(encoder.encode(added))
            self.write(', "deleted":')
            self.write(encoder.encode(deleted))

            self.write('}')
        else:
            added = map(lambda s: "A " + s, added)
            deleted = map(lambda s: "D " + s, deleted)
            
            self.set_header("Content-Type", "text/plain")
            self.write(join(added, "\n"))
            self.write("\n")
            self.write(join(deleted, "\n"))


    def __get_delta_between_mementos(self, repo, key, ts, delta_ts):
        try:
            if ts > delta_ts:
                added, deleted = revision_logic.get_delta_between_mementos(repo, key, ts, delta_ts)
            else:
                added, deleted = revision_logic.get_delta_between_mementos(repo, key, delta_ts, ts)
        except ValueError:
            raise HTTPError(reason="No delta possible for given timestamps", status_code=400)

        self.set_header("Vary", "accept-datetime")
        self.set_header("Content-Type", "text/plain")
        self.write(join(added, "\n"))
        self.write("\n")
        self.write(join(deleted, "\n"))

    def __get_timemap(self, repo, key, header_only=False):
        if not header_only:
            # Generate a timemap containing historic change information
            # for the requested key. The timemap is in the default link-format
            # or as JSON (http://mementoweb.org/guide/timemap-json/).

            csets = revision_logic.get_csets(repo, key)
            csit = csets.iterator()
            number_of_csets = revision_logic.get_csets_count(repo, key)

            # TODO: Paginate?
            # TODO Header only request

            try:
                last_cset = csit.next()
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
                self.write(', "timegate_uri": "' + timegate_url + '"')
                self.write(', "timemap_uri": "' + timemap_url + '"')

                self.write(', "mementos": {"list":[')

                m = ('{{"datetime": "{0}", "uri": "' + timegate_url +
                     '&datetime={1}"}}')

                self.write(m.format(last_cset.time.isoformat(),
                                    last_cset.time.strftime(QSDATEFMT)))

                for cs in csit:
                    self.write(', ' + m.format(cs.time.isoformat(),
                                               cs.time.strftime(QSDATEFMT)))

                self.write(']}')
                self.write('}')
            elif "application/link-format" in accept:
                self.set_header("Content-Type", "application/link-format")

                m = (',\n' +
                     '<' + timegate_url + '&datetime={0}>\n' +
                     '  ; rel="memento{1}"' +
                     '; datetime="{2}"' +
                     '; type="application/n-quads"')

                self.write('<' + key + '>\n  ; rel="original"')
                self.write(',\n<' + timemap_url + '>\n  ; rel="self"')
                self.write(',\n<' + timegate_url + '>\n  ; rel="timegate"')
                self.write(m.format(last_cset.time.strftime(QSDATEFMT)," last", 
                                    last_cset.time.strftime(RFC1123DATEFMT)))

                count = 0
                for cs in csit:
                    # index starts at 0, first element already skipped -> -2
                    if count == number_of_csets - 2:
                        self.write(m.format(cs.time.strftime(QSDATEFMT)," first",
                                        cs.time.strftime(RFC1123DATEFMT)))
                    else:
                        self.write(m.format(cs.time.strftime(QSDATEFMT),"",
                                        cs.time.strftime(RFC1123DATEFMT)))
                    count += 1
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


    def __get_next_memento(self, repo, key, ts):
        return revision_logic.get_cset_next_after_ts(repo, key, ts)

    def __get_next_memento_uri(self, repo, key, ts):
        cs_next = __get_next_memento(repo, key, ts)
        if cs_next:
            return self.request.protocol + "://" + self.request.host + self.request.path + "?key=" + key + "&datetime=" + cs_next.time.strftime(QSDATEFMT)
        else:
            return None


    def __get_prev_memento(self, repo, key, ts):
        return revision_logic.get_cset_prev_before_ts(repo, key, ts)

    def __get_prev_memento_uri(self, repo, key, ts):
        cs_prev = __get_prev_memento(repo, key, ts)
        if cs_prev:
            return self.request.protocol + "://" + self.request.host + self.request.path + "?key=" + key + "&datetime=" + cs_prev.time.strftime(QSDATEFMT)
        else:
            return None


    @authenticated
    def put(self, username, reponame):
        # Create a new revision of the resource specified by `key`.
        fmt = self.request.headers.get("Content-Type", "application/n-triples")
        key = self.get_query_argument("key", None)
        commit_message = self.get_query_argument("m", None)
        # force = self.get_query_argument("force", None)
        # replace = self.get_query_argument("replace", None)

        if username != self.current_user.name:
            raise HTTPError(403)
        if not key:
            raise HTTPError(reason="Missing argument 'key'.", status_code=400)

        repo = revision_logic.get_repo(username, reponame)
        if repo == None:
            raise HTTPError(reason="Repo not found.", status_code=404)

        datestr = self.get_query_argument("datetime", None)
        ts = datestr and date(datestr, QSDATEFMT) or now()


        # Parse and normalize into a set of N-Quad lines
        try:
            stmts = revision_logic.parse(self.request.body, fmt)
        except RedlandError, e:
            # TODO decide about error code. This is actual a client side error (4XX), but also not a bad request as such
            raise HTTPError(reason="Error while parsing payload: " + e.value, status_code=500)

        try:
            prev_state = revision_logic.insert_revision(repo, key, stmts, ts)
        except ValueError:
            # raise HTTPError(reason="Timestamps must be monotonically increasing.", status_code=400)
            raise HTTPError(reason="Error while saving revision.", status_code=500)
        except IntegrityError:
            raise HTTPError(500)
        else:
            if commit_message:
                revision_logic.add_commit_message(repo, key, ts, commit_message)
        if prev_state == None:
            self.finish()

            
        # def setHeader(self, key, timemap):

    def head(self, username, reponame):
    
        timemap = self.get_query_argument("timemap", "false") == "true"
        index = self.get_query_argument("index", "false") == "true"
        key = self.get_query_argument("key", None)
    
        if (index and timemap) or (index and key) or (timemap and not key):
            raise HTTPError(reason="Invalid arguments.", status_code=400)

        if self.get_query_argument("datetime", None):
            datestr = self.get_query_argument("datetime")
            try:
                ts = date(datestr, QSDATEFMT)
            except ValueError:
                raise HTTPError(reason="Invalid format of datetime param", status_code=400)
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
            self.__get_revision(repo, key, ts, True)
        elif key and timemap:
            self.__get_timemap(repo, key, True)
        else:
            raise HTTPError(reason="Malformed HEAD request.", status_code=400)

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


    @authenticated
    def delete(self, username, reponame):
        # Check whether the key exists and if maybe the last change already is
        # a delete, else insert a `CSet.DELETE` entry without any blob data.

        key = self.get_query_argument("key")
        update = self.get_query_argument("update", "false") == "true"
        repo = revision_logic.get_repo(username, reponame)

        if username != self.current_user.name:
            raise HTTPError(reason="Unauthorized: Unowned Repo", status_code=403)
        if not key:
            raise HTTPError(reason="Missing argument 'key'.", status_code=400)
        if repo == None:
            raise HTTPError(reason="Repo not found.", status_code=404)

        datestr = self.get_query_argument("datetime", None)
        ts = datestr and date(datestr, QSDATEFMT) or now()

        if update:
            # When update-param is set and the ts is the exact one of an existing cset (ts does not need to be increasing)
            if revision_logic.get_cset_at_ts(repo, key, ts):
                revision_logic.remove_revision(repo, key, ts)
                self.finish()
                return
            else:
                raise HTTPError(reason="No memento exists for given timestamp. When 'update' is set this must apply", status_code=400)
        else:
            try:
                revision_logic.save_revision_delete(repo, key, ts)
            except LookupError:
                raise HTTPError(reason="Resource does not exist at given time.", status_code=404)
