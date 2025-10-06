#!/bin/bash
set -e

# Используем переменные из .env
# DB_BOT_USER, DB_BOT_PASSWORD, DB_APP_USER, DB_APP_PASSWORD, POSTGRES_DB, POSTGRES_USER

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "psybot" <<-EOSQL

-- Создаём пользователя bot, если не существует
DO
\$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_BOT_USER}') THEN
      EXECUTE format('CREATE USER %I WITH PASSWORD %L;', '${DB_BOT_USER}', '${DB_BOT_PASSWORD}');
      EXECUTE format('GRANT ALL PRIVILEGES ON DATABASE %I TO %I;', 'psybot', '${DB_BOT_USER}');
      EXECUTE format('GRANT ALL ON SCHEMA public TO %I;', '${DB_BOT_USER}');
   END IF;
END
\$\$;

-- Создаём пользователя app, если не существует
DO
\$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_APP_USER}') THEN
      EXECUTE format('CREATE USER %I WITH PASSWORD %L;', '${DB_APP_USER}', '${DB_APP_PASSWORD}');
      EXECUTE format('GRANT USAGE ON SCHEMA public TO %I;', '${DB_APP_USER}');
      EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I;', '${POSTGRES_DB}', '${DB_APP_USER}');
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I;', '${DB_APP_USER}');
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO %I;', '${DB_APP_USER}');
   END IF;
END
\$\$;

-- Настраиваем: всё, что создаёт BOT в public — доступно APP для чтения
ALTER DEFAULT PRIVILEGES FOR ROLE ${DB_BOT_USER} IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${DB_APP_USER};

EOSQL