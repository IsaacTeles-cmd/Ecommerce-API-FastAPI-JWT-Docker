import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# banco SQLite em memória — isolado, rápido e descartável
DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def engine():
    """Cria o engine do banco de testes uma vez por sessão."""
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine):
    """Fábrica de sessões conectada ao banco de testes."""
    return sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def clean_db(session_factory):
    """
    Limpa todas as tabelas antes de cada teste.
    Garante que cada teste começa com banco vazio.
    """
    yield
    async with session_factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest.fixture(scope="session")
async def client(engine, session_factory):
    """
    Cliente HTTP para fazer requisições à API nos testes.
    Substitui o banco real pelo banco de testes via dependency override.
    """

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(client, session_factory):
    """Cria um usuário admin e retorna seus dados + token."""
    # registra o usuário
    await client.post(
        "/auth/register",
        json={
            "email": "admin@test.com",
            "full_name": "Admin Teste",
            "password": "Admin123",
        },
    )
    # promove para admin diretamente via banco
    from sqlalchemy import update
    from app.auth.models import User

    async with session_factory() as db:
        await db.execute(
            update(User).where(User.email == "admin@test.com").values(role="admin")
        )
        await db.commit()

    # faz login e retorna token
    response = await client.post(
        "/auth/login",
        json={
            "email": "admin@test.com",
            "full_name": "Admin Teste",
            "password": "Admin123",
        },
    )
    token = response.json()["access_token"]

    return {"email": "admin@test.com", "token": token}


@pytest.fixture
async def customer_user(client):
    """Cria um usuário customer e retorna seus dados + token."""
    await client.post(
        "/auth/register",
        json={
            "email": "customer@test.com",
            "full_name": "Customer Teste",
            "password": "Customer123",
        },
    )

    response = await client.post(
        "/auth/login",
        json={
            "email": "customer@test.com",
            "full_name": "Customer Teste",
            "password": "Customer123",
        },
    )
    token = response.json()["access_token"]

    return {"email": "customer@test.com", "token": token}


@pytest.fixture
async def auth_headers(admin_user):
    """Headers de autenticação para admin."""
    return {"Authorization": f"Bearer {admin_user['token']}"}


@pytest.fixture
async def customer_headers(customer_user):
    """Headers de autenticação para customer."""
    return {"Authorization": f"Bearer {customer_user['token']}"}
