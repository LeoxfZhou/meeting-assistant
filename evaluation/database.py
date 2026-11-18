from contextlib import contextmanager
from uuid import uuid4
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
from alembic import command
from alembic.config import Config
from app.core.config import Settings


@contextmanager
def isolated_database():
    settings=Settings()
    url=make_url(settings.database_url.get_secret_value())
    if settings.app_env not in {'development','test'} or url.host not in {'127.0.0.1','localhost'}:
        raise ValueError('Evaluation requires a local development instance')
    admin_url=url.set(drivername='postgresql',database='postgres').render_as_string(hide_password=False)
    name='meeting_assistant_eval_'+uuid4().hex
    with psycopg.connect(admin_url,autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    try:
        test_url=url.set(database=name).render_as_string(hide_password=False)
        cfg=Config('alembic.ini');cfg.attributes['database_url']=test_url
        command.upgrade(cfg,'head')
        yield test_url
    finally:
        with psycopg.connect(admin_url,autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
