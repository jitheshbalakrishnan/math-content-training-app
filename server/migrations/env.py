from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.config import DATABASE_URL
from app.models import Base

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)


def run() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run()
