from alembic import context

from app.core.config import Settings
from app.db.session import Base, build_engine
from app.models.knowledge import CompanyDocument, KnowledgeChunk  # noqa: F401
from app.models.action_item import ActionItem, Task  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.meeting import Meeting  # noqa: F401 - 注册 metadata

config = context.config
target_metadata = Base.metadata
url = config.attributes.get("database_url") or Settings().database_url.get_secret_value()

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
