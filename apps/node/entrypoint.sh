#!/usr/bin/env bash

set -e

mkdir -p /var/log/pychain

exec supervisord -c /etc/supervisor/supervisord.conf
