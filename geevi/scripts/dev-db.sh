#!/usr/bin/env bash
# Dedicated loopback-only PostgreSQL cluster for Geevi development and tests (no Docker needed).
# Never touches any other PostgreSQL server or database on this machine.
set -euo pipefail
export LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PGDATA="${GEEVI_PGDATA:-$ROOT/.pgdata}"
PORT="${GEEVI_PGPORT:-5433}"
case "${1:-start}" in
  start)
    if [ ! -d "$PGDATA" ]; then
      initdb -D "$PGDATA" -U geevi --auth=trust -E UTF8 --locale=C >/dev/null
      { echo "listen_addresses = '127.0.0.1'"; echo "port = $PORT"; echo "unix_socket_directories = '$PGDATA'"; } >> "$PGDATA/postgresql.conf"
    fi
    pg_ctl -D "$PGDATA" status >/dev/null 2>&1 || pg_ctl -D "$PGDATA" -l "$PGDATA/server.log" -w start >/dev/null
    psql -h 127.0.0.1 -p "$PORT" -U geevi -d postgres -tAc "select 1 from pg_database where datname='geevi'" | grep -q 1 \
      || createdb -h 127.0.0.1 -p "$PORT" -U geevi geevi
    echo "PostgreSQL ready on 127.0.0.1:$PORT (database geevi, user geevi)";;
  stop) pg_ctl -D "$PGDATA" -m fast stop;;
  reset)
    dropdb -h 127.0.0.1 -p "$PORT" -U geevi --if-exists geevi
    createdb -h 127.0.0.1 -p "$PORT" -U geevi geevi; echo "database geevi recreated";;
  *) echo "usage: $0 start|stop|reset"; exit 2;;
esac
