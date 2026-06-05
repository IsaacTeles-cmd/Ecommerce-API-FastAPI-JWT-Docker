from logging.config import fileConfig
import sys
import os

sys.path.append(os.getcwd())

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.database import Base
from app.auth.models import User  # noqa: F401
from app.products.models import Category, Product  # noqa: F401
from app.orders.models import Order, OrderItem  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# Lê DATABASE_URL do ambiente e converte asyncpg → psycopg2
# O Alembic usa conexão síncrona, então não pode usar asyncpg
def get_url() -> str:
    url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_url()  # sobrescreve com a URL correta

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
