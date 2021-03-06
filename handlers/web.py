import functools
import random

import datetime
import logging

import tornado.auth
import tornado.escape
import tornado.gen
import tornado.httpclient
import tornado.web

from tornado.web import HTTPError
from tornado.web import authenticated

import peewee

from peewee import fn

from models import User, Repo, HMap, CSet, Token
from handlers import RequestHandler
import revision_logic
import statistic

logger = logging.getLogger('debug')

QSDATEFMT = "%Y-%m-%d-%H:%M:%S"
def now():
    # replace microseconds, because otherwise this fraction will cause 
    # inconsitencies when comparing to datetimes that are exact to the second only
    return datetime.datetime.utcnow().replace(microsecond=0)

def date(s, fmt):
    return datetime.datetime.strptime(s, fmt)

class BaseHandler(RequestHandler):
    """Base class for all web front end handlers."""

    def get_current_user(self):
        uid = self.get_secure_cookie("uid")
        user = User.get(User.id == uid) if uid else None
        return user

    def set_current_user(self, user):
        self.set_secure_cookie("uid", str(user.id))

    def clear_current_user(self):
        self.clear_cookie("uid")

    def write_error(self, status_code, **kwargs):
        if status_code == 404:
            self.render("error/404.html")
        else:
            self.render("error/gen.html")

class HomeHandler(BaseHandler):
    """Renders the website index page - nothing more."""

    def get(self):
        self.render("home/index.html")

class AboutHandler(BaseHandler):
    def get(self):
        self.render("home/about.html")

class DocumentationHandler(BaseHandler):
    def get(self):
        self.render("home/documentation.html")

class SearchHandler(BaseHandler):
    def get(self):
        query = tornado.escape.url_unescape(self.get_argument("q", ""))

        if query:
            pattern = "%" + query + "%"
            repos = (Repo.select().join(User).alias("user")
                .where(Repo.name ** pattern, Repo.private == False))
            users = User.select().where(User.name ** pattern)
        else:
            repos = []
            users = []

        self.render("search/show.html", query=query, repos=repos, users=users)

class UserHandler(BaseHandler):
    def get(self, username):
        try:
            user = User.select().where(User.name == username).get()
            self.render("user/show.html", title=user.name, user=user)
        except User.DoesNotExist:
            raise HTTPError(reason="User not found.", status_code=404)

class EditUserHandler(BaseHandler):
    @authenticated
    def get(self):
        user = self.current_user
        title = "Edit account information"
        self.render("user/edit.html", title=title, user=user)

    @authenticated
    def post(self):
        user = self.current_user
        user.name = self.get_argument("username", None)
        user.homepage_url = self.get_argument("homepage", None)
        user.avatar_url = self.get_argument("avatar", None)
        user.email = self.get_argument("email", None)
        user.save()
        self.redirect(self.reverse_url("web:settings"))

class StatisticHandler(BaseHandler):
    def get(self):
        usercount = statistic.get_user_count()
        if "users" in self.request.path:
            page = int(self.get_query_argument("page", "1"))
            users = statistic.get_all_users(page)
            self.render("statistic/users.html", title="All Users", users=users, usercount=usercount, page_size=statistic.INDEX_PAGE_SIZE, current_page=page)
        else:
            repocount = statistic.get_repo_count()
            resourcecount = statistic.get_resource_count()
            revisioncount = statistic.get_revision_count()
            self.render("statistic/show.html", title="TailR - Statistics", usercount=usercount, repocount=repocount, resourcecount=resourcecount, revisioncount=revisioncount)

class RepoHandler(BaseHandler):
    def get(self, username, reponame):
        try:
            repo = (Repo.select().join(User).alias("user")
                    .where((User.name == username) & (Repo.name == reponame))
                    .get())
            if not repo.private:
                self._get(repo)
            else:
                self._getAuth(repo)
        except Repo.DoesNotExist:
            raise HTTPError(reason="Repo not found.", status_code=404)

    def _getAuth(self, repo):
        if self.current_user == None or repo.user.name != self.current_user.name:
            #raise HTTPError(reason="Unauthorized access: third party private repo.", status_code=403)
            raise HTTPError(reason="Repo not found.", status_code=404)
        else:
            self._get(repo)

    def _get(self, repo):
        title = repo.user.name + "/" + repo.name

        timemap = self.get_query_argument("timemap", "false") == "true"
        datetime = self.get_query_argument("datetime", None)
        key = self.get_query_argument("key", None)
        index = self.get_query_argument("index", "false") == "true"

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
        if key and not timemap:
            chain = revision_logic.get_chain_at_ts(repo, key, ts)
            # use ts of cset instead of now(), to make prev work
            if len(chain) != 0:
                ts = chain[-1].time

            cs_prev = revision_logic.get_cset_prev_before_ts(repo, key, ts)
            cs_next = revision_logic.get_cset_next_after_ts(repo, key, ts)
            if cs_prev:
                cs_prev_str = self.request.protocol + "://" + self.request.host + self.request.path + "?key=" + key + "&datetime=" + cs_prev.time.strftime(QSDATEFMT)
            else:
                cs_prev_str = ""
            if cs_next:
                cs_next_str = self.request.protocol + "://" + self.request.host + self.request.path + "?key=" + key + "&datetime=" + cs_next.time.strftime(QSDATEFMT)
            else:
                cs_next_str = ""
            commit_message = revision_logic.get_commit_message(repo, key, ts)

            self.render("repo/memento.html", repo=repo, key=key, datetime=datetime, cs_next_str=cs_next_str, cs_prev_str=cs_prev_str, commit_message=commit_message)
        elif key and timemap:
            self.render("repo/history.html", repo=repo, key=key)
        elif index:
            cs = (CSet.select(fn.distinct(CSet.hkey)).where((CSet.repo == repo) & (CSet.time <= ts)).alias("cs"))
            key_count = (HMap.select(HMap.val).join(cs, on=(HMap.sha == cs.c.hkey_id))).count()

            page = int(self.get_query_argument("page", "1"))

            hm = revision_logic.get_repo_index(repo, ts, page)

            self.render("repo/index.html", repo=repo, title=title, key_count=key_count, page_size=revision_logic.INDEX_PAGE_SIZE, hm=hm, current_page=page)
        else:
            hm = list(revision_logic.get_repo_index(repo, ts, 1, 5))
            # cs = (CSet.select(fn.distinct(CSet.hkey)).where(CSet.repo == repo).limit(5).alias("cs"))
            # samples = (HMap.select(HMap.val).join(cs, on=(HMap.sha == cs.c.hkey_id)))
            self.render("repo/show.html", title=title, repo=repo, hm=hm)


    @authenticated
    def delete(self, username, reponame):
        if username != self.current_user.name:
            raise HTTPError(reason="Unauthorized: Not your Repo", status_code=403)
            
        key = self.get_query_argument("key")
        update = self.get_query_argument("update", "false") == "true"
        repo = revision_logic.get_repo(username, reponame)

        if not key:
            raise HTTPError(reason="Missing argument 'key'.", status_code=400)
        if repo == None:
            raise HTTPError(reason="Repo not found.", status_code=404)

        datestr = self.get_query_argument("datetime", None)
        ts = date(datestr, QSDATEFMT) or now()
        
        if update:
            # When update-param is set and the ts is the exact one of an existing cset (ts does not need to be increasing)
            if revision_logic.get_cset_at_ts(repo, key, ts):
                revision_logic.remove_revision(repo, key, ts)
                self.finish()
                return
            else:
                raise HTTPError(reason="No memento exists for given timestamp. When 'update' is set this must apply", status_code=400)


class CreateRepoHandler(BaseHandler):
    @authenticated
    def get(self):
        user = self.current_user
        title = "Create a new repository"
        self.render("repo/new.html", title=title, user=user)

    @authenticated
    def post(self):
        reponame = self.get_argument("reponame", None)
        desc = self.get_argument("description", None)
        private = self.get_argument("private", "false") == "true"
        user = self.current_user
        if not reponame:
            self.redirect(self.reverse_url("web:create-repo"))
            return
        repo = Repo.create(user=user, name=reponame, desc=desc, private=private)
        self.redirect(self.reverse_url("web:repo", user.name, repo.name))

class DelRepoHandler(BaseHandler):
    @authenticated
    def post(self, username, reponame):
        verify = self.get_argument("verify", None)
        try:
            repo = revision_logic.get_repo(username, reponame)
            if repo == None:
                raise HTTPError(reason="Repo not found.", status_code=404)
            if username != self.current_user.name:
                raise HTTPError(reason="Unauthorized delete: third party repo.", status_code=403)
            if (repo.name == verify):
                revision_logic.remove_repo(repo)
                self.redirect(self.reverse_url("web:user", self.current_user.name))
            else:
                raise HTTPError(501)
        except:
          raise HTTPError(reason="Some exception occured.", status_code=404)

class EditRepoHandler(BaseHandler):
    @authenticated
    def post(self, username, reponame):
        try:
            repo = revision_logic.get_repo(username, reponame)
            if repo == None:
                raise HTTPError(reason="Repo not found.", status_code=404)
            if username != self.current_user.name:
                raise HTTPError(reason="Unauthorized edit: third party repo.", status_code=403)
            else:
                if self.get_argument("description", None):
                    repo.desc = self.get_argument("description", None)
                repo.private = self.get_argument("private", "false") == "true"
                repo.save()
                self.redirect(self.reverse_url("web:repo", username, reponame))
        except:
            raise HTTPError(reason="Some exception occured.", status_code=404)

class SettingsHandler(BaseHandler):
    @authenticated
    def get(self):
        user = self.current_user
        title = "Account settings"
        self.render("settings/index.html", title=title, user=user,
            tokens=user.tokens)

    def on_finish(self):
        q = Token.update(seen=True).where(Token.user == self.current_user)
        q.execute()
        super(SettingsHandler, self).on_finish()

class NewTokenHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("tokens/new.html")

    @authenticated
    def post(self):
        user = self.current_user
        desc = self.get_argument("description")
        value = "%040x" % random.randrange(16**40)
        # TODO: Retry on duplicate token value (peewee.IntegrityError)?
        Token.create(user=user, value=value, desc=desc)
        self.redirect(self.reverse_url("web:settings"))

class DelTokenHandler(BaseHandler):
    @authenticated
    def post(self, id):
        try:
            token = Token.get((Token.user == self.current_user) & (Token.id == id))
            token.delete_instance()
            self.redirect(self.reverse_url("web:settings"))
        except:
            raise HTTPError(404)

class JoinHandler(BaseHandler):
    """Allows users to join through email and password or GitHub OAuth."""

    def get(self):
        if not self.current_user:
            self.render("join/new.html")
        else:
            self.redirect("/")

    # def post(self):
    #     email = self.get_argument("email")
    #     name = self.get_argument("username")
    #     pass, salt = ...
    #     try:
    #         User.create(name=username, email=email, pass=pass, salt=salt)
    #     except peewee.IntegrityError:
    #         self.redirect(self.reverse_url("web:join"))
    #     self.redirect("/")

class AuthHandler(BaseHandler):
    """Authenticates users via username and password."""

    def get(self):
        if not self.current_user:
            self.render("auth/new.html", title="TailR - Sign in")
        else:
            self.redirect("/")

    # def post(self):
    #     username = self.get_argument("username")
    #     user = User.get(User.name == username)
    #     # confirm password, else deny access
    #     if user... == ...:
    #         self.set_current_user(user)
    #         self.redirect(self.get_argument("next", "/"))
    #     else:
    #         self.redirect(self.reverse_url("web:auth"))

class GitHubOAuth2Mixin(tornado.auth.OAuth2Mixin):
    """GitHub authentication using OAuth2."""

    _OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    _OAUTH_SETTINGS_KEY = "github_oauth"

    _GITHUB_API_BASE_URL = "https://api.github.com"

    @tornado.auth._auth_return_future
    def get_authenticated_user(self, redirect_uri, code, callback):
        http = self.get_auth_http_client()

        body = tornado.auth.urllib_parse.urlencode({
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": self.settings[self._OAUTH_SETTINGS_KEY]["key"],
            "client_secret": self.settings[self._OAUTH_SETTINGS_KEY]["secret"],
        })

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        http.fetch(self._OAUTH_ACCESS_TOKEN_URL,
            functools.partial(self._on_access_token, callback),
            method="POST", headers=headers, body=body)

    def _on_access_token(self, future, response):
        if response.error:
            msg = "GitHub auth error: %s: %s" % (response.error, response.body)
            future.set_exception(tornado.auth.AuthError(msg))
            return

        args = tornado.escape.json_decode(response.body)

        self.github_request("/user",
            functools.partial(self._on_user_info, future),
            access_token=args["access_token"])

    @tornado.auth._auth_return_future
    def github_request(self, path, callback, access_token=None, **args):
        url = self._GITHUB_API_BASE_URL + path

        headers = {
            "User-Agent": "tailr",
            "Accept": "application/json",
        }

        if access_token is not None:
            headers["Authorization"] = "token %s" % access_token

        callback = functools.partial(self._on_github_request, callback)

        http = self.get_auth_http_client()

        http.fetch(url, callback, headers=headers)

    def _on_github_request(self, future, response):
        if response.error:
            msg = "GitHub API error: %s: %s" % (response.error, response.body)
            future.set_exception(tornado.auth.AuthError(msg))
            return

        result = tornado.escape.json_decode(response.body)
        future.set_result(result)

    def _on_user_info(self, future, info):
        future.set_result(info)

    def get_auth_http_client(self):
        return tornado.httpclient.AsyncHTTPClient()

class GitHubAuthHandler(BaseHandler, GitHubOAuth2Mixin):
    """Authenticates users via GitHub OAuth."""

    @tornado.gen.coroutine
    def get(self):
        if self.get_argument("code", False):
            info = yield self.get_authenticated_user(
                redirect_uri=self.redirect_uri,
                code=self.get_argument("code"))

            github_id = info.get("id", None)

            if github_id is None:
                self.redirect(self.reverse_url("web:auth"))
                return

            try:
                user = User.get(User.github_id == github_id)
            except User.DoesNotExist:
                user = None

            if user is None:
                data = dict(
                    name=info.get("login"),
                    github_id=github_id,
                    homepage_url=info.get("html_url", None),
                    avatar_url=info.get("avatar_url", None),
                    email=info.get("email", None),
                    confirmed=True)

                try:
                    # try to use the users GitHub login name
                    user = User.create(**data)
                except peewee.IntegrityError:
                    # assign a temporary, random name
                    data["name"] = "%040x" % random.randrange(16**40)
                    user = User.create(**data)

            self.set_current_user(user)

            self.redirect(self.get_argument("next", "/"))
        else:
            # TODO: pass additional random `state` parameter and
            #       check the value in the conditional branch above
            yield self.authorize_redirect(
                redirect_uri=self.redirect_uri,
                client_id=self.settings["github_oauth"]["key"],
                response_type="code",
                scope=["user:email"])

    @property
    def redirect_uri(self):
        return "%s://%s%s" % (self.request.protocol,
            self.request.host, "/auth/github")

class DeauthHandler(BaseHandler):
    @authenticated
    def post(self):
        self.clear_current_user()
        self.redirect("/")

class ErrorHandler(BaseHandler):
    """Generates an error response with ``status_code`` for all requests."""

    def initialize(self, status_code):
        self.set_status(status_code)

    def prepare(self):
        super(ErrorHandler, self).prepare()
        raise tornado.web.HTTPError(self.get_status())

    def check_xsrf_cookie(self):
        pass
