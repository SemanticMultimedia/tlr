# tailr

*A platform for preserving history on the web of data.*


## Introduction

A public Tailr instance can be found at [tailr.s16a.org](http://tailr.s16a.org/) providing repositories for e.g. [LOV](http://tailr.s16a.org/mgns/LOV) and [DBpedia Live](http://tailr.s16a.org/mgns/dbpediaLive).

## Configuration

The application is configured using environment variables which you can specify directly in your shell, using [Foreman](https://github.com/ddollar/foreman)/[Honcho](https://github.com/nickstenning/honcho) env files or through [Docker](https://docs.docker.com/reference/run/#env-environment-variables) when running inside a container.

**`DATABASE_URL`**

To allow the application to connect to the database and persist information, you need to set the [database URL](http://peewee.readthedocs.org/en/stable/peewee/database.html#connecting-using-a-database-url) in the environment. The typical format for most database management systems is `protocol://user:pass@host:port/database`.

**`COOKIE_SECRET`**

In order to sign cookies and prevent forgery, Tornado requires you to set a cookie secret. You can read more about secure cookies in the [Tornado docs](http://tornado.readthedocs.org/en/stable/guide/security.html#cookies-and-secure-cookies). You can easily generate a random hex string to use as a secret by running:

```shell
python -c "import random; print '%0256x' % random.randrange(16**256)"
```

**`GITHUB_CLIENT_ID` and `GITHUB_SECRET`**

Sign up and sign in for users via [GitHub OAuth](https://developer.github.com/v3/oauth/) is supported. You will need to create an application from your [GitHub settings page](https://github.com/settings/developers) and set these two environment variables to the values belonging to the created application.

**`DEBUG`**

To enable Tornado [debug mode](http://tornado.readthedocs.org/en/stable/guide/running.html#debug-mode-and-automatic-reloading), set this variable to `1`. This should mostly be used during development. The default value is `0`.


## Getting started

For local development, a virtual machine can be set up using [Vagrant](https://github.com/mitchellh/vagrant). The default `Vagrantfile` will install [Docker](https://www.docker.com/) on the machine and pull images for [MariaDB](https://registry.hub.docker.com/_/mariadb/) and [Python](https://registry.hub.docker.com/_/python/).

To create and start the VM, run:

```shell
vagrant up
```

*Note: There currently is an [issue with the "docker" provisioner](https://github.com/mitchellh/vagrant/issues/5697) for Vagrant. If you see an error message during machine provisioning, run `vagrant ssh`, then `apt-get update`, `exit` and then again `vagrant provision`.*

You now have a virtual machine running Ubuntu 14.04 with Docker installed. You can ssh into the machine using `vagrant ssh`. The project directory is mounted to `/vagrant` by default. From there you can launch all application services together using [Docker Compose](https://docs.docker.com/compose/):

```shell
# build the app image, start linked db and app containers
docker-compose up
# launch another temporary app container to run the database migration
docker-compose run --rm app python prepare.py
```

Then open [localhost:5000](http://localhost:5000/) on your machine.

To launch a container for an interactive console with a database connection and play around with your models and code, run:

```shell
# launch a temporary app container with a console
docker-compose run --rm app python console.py
```


## Deploying

Since Docker Compose is not yet recommended for production use, we will use a pure Docker approach for deployments.

First, we will build the application image:

```shell
# build the application image and tag it
docker build -t semanticmultimedia/tailr .
```

It is probably a good idea to publish tagged releases to [Docker Hub](https://hub.docker.com/). This way, we avoid re-building them for deployments:

```shell
# best append a version identifier in the build step above and push the resulting image to docker hub
docker push semanticmultimedia/tailr:0.0.2
```

We can then launch a database container and one or more application containers linked to it:

```shell
# start the database container
docker run -d -e MYSQL_ROOT_PASSWORD=root -e MYSQL_USER=tailr -e MYSQL_PASSWORD=tailr -e MYSQL_DATABASE=tailr --name mariadb mariadb

# run the database migration in a temporary application container (only important env variable is for the database here)
docker run --rm -it --link mariadb:db -e COOKIE_SECRET=x -e GITHUB_CLIENT_ID=y -e GITHUB_SECRET=z -e DATABASE_URL=mysql://tailr:tailr@db/tailr semanticmultimedia/tailr python prepare.py

# run the application container, linking it to the db container and binding container port 5000 to port 8000 on 127.0.0.1 of the host machine
# replace the dummy "xxx" values for the GitHub access with the actual client-id and secret
docker run -d --link mariadb:db -e COOKIE_SECRET=secret -e GITHUB_CLIENT_ID=xxx -e GITHUB_SECRET=xxx -e DATABASE_URL=mysql://tailr:tailr@db/tailr -p 127.0.0.1:8000:5000 --name tailr semanticmultimedia/tailr

# for a mysql shell, run the following command replacing "xxx" with the name of the database container (see `docker ps -a`)
docker run --rm -it --link xxx:mysql mariadb sh -c 'exec mysql -h"$MYSQL_PORT_3306_TCP_ADDR" -P"$MYSQL_PORT_3306_TCP_PORT" -uroot -p"$MYSQL_ENV_MYSQL_ROOT_PASSWORD"'
```

You can launch a number of application containers mapped to different ports on the host, e.g. 4 instances with ports `8000`-`8003`, and then configure an Apache or Nginx vhost as a reverse-proxy to these. This way, you can scale the web application layer simply by adding more containers and load-balancing between them.

An Nginx configuration could look like this:

```nginx
# /etc/nginx/sites-available/tailr.s16a.org

upstream tailr {
  server 127.0.0.1:8000
  server 127.0.0.1:8001
  server 127.0.0.1:8002
  server 127.0.0.1:8003
}

server {
  listen 80;
  listen [::]:80;

  root /var/www/tailr;
  index index.html index.htm;

  server_name tailr.s16a.org;

  # Allow client uploads
  client_max_body_size 10m;

  # Only retry if there was a communication error, not a timeout on the Tornado
  # server (to avoid propagating "queries of death" to all frontends)
  proxy_next_upstream error;

  location = /favicon.ico {
    rewrite (.*) /static/favicon.ico;
    access_log off;
  }

  location = /robots.txt {
    rewrite (/*) /static/robots.txt;
    access_log off;
  }

  # Serve static files directly through nginx
  # (not applicable when running out of a container)
  # location /static/ {
  #   try_files $uri $uri/ =404;
  #   if ($query_string) {
  #     expires max;
  #   }
  # }

  # Reverse proxy to application
  location / {
    proxy_pass_header Server;
    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Scheme $scheme;
    proxy_redirect off;
    proxy_pass http://tailr;
  }
}
```

Additional information on "running and deploying" Tornado apps in general can be found in the [official docs](http://tornado.readthedocs.org/en/stable/guide/running.html).


## Push API

The Push API allows to insert new data revisions into the system. A customized documentation of the Push API can be found in your repository.

```shell
# export the token for later use
export TOKEN="0bc283..."

# create a new revision of a resource with an RDF description
curl -X PUT \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/n-triples" \
  --data-binary @path/to/resource.nt \
  "http://tailr.s16a.org/api/USER_NAME/REPO_NAME?key=http://...&datetime=yyyy-MM-dd-HH:mm:ss"

# mark a resource as deleted
curl -X DELETE \
-H "Authorization: token $TOKEN" \
"http://tailr.s16a.org/api/USER_NAME/REPO_NAME?key=http://...&datetime=..."
```

## Storage model

Tailr uses a hybrid storage model of independent copies (snapshots) and inter-revision changes (deltas).

## Memento API

Prior states of linked data resources tracked in your repositories are accessible through a [Memento](https://datatracker.ietf.org/doc/rfc7089/) API.

You can request a certain resource from this repository by specifying its URI in the key query parameter. Specify the date and time for the resource state you are interested in by passing an Accept-Datetime HTTP header, for instance:

```shell
curl -H "Accept-Datetime: Thu, 11 June 2015 09:45:00 GMT" "http://tailr.s16a.org/api/USER_NAME/REPO_NAME?key=http://..."
```

In order to link to a certain resource state, you may also provide the datetime argument as a query parameter:

```shell
curl "http://tailr.s16a.org/api/USER_NAME/REPO_NAME?key=http://...&datetime=2015-06-11-09:45:00"
```

To find out when a resource was changed, query for the timemap:

```shell
curl "http://tailr.s16a.org/api/USER_NAME/REPO_NAME?key=http://...&timemap=true"
```

You can find links to a small sample of resources from this repository below:

