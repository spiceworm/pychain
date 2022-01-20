FROM python:3.10.2-bullseye

EXPOSE 80

HEALTHCHECK CMD curl --fail http://localhost:80/api/v1/status || exit 1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gettext-base \
        nginx \
        redis-server \
        supervisor \
    && apt-get clean \
    && rm -Rf /var/lib/apt/lists/*

# TODO: remove IPython once it is no longer needed for development purposes
RUN pip install --upgrade pip \
    && pip install  \
        IPython \
        tox \
        uvicorn[standard]

COPY ./apps/node/requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY ./package /pychain
RUN pip install /pychain

COPY ./apps/node /app

# Remove the default nginx config so ours can use the `default_server` setting in the `listen`
# directive and also set `server_name _;` so nginx will respond if we query by domain name or
# IP address.
RUN rm /etc/nginx/sites-enabled/default \
    && ln -s /app/nginx.conf /etc/nginx/conf.d/pychain.conf \
    && ln -s /app/supervisor.conf /etc/supervisor/conf.d/

ENTRYPOINT ["/app/entrypoint.sh"]
