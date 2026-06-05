from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.schemas import TokenData, UserCreate
from app.config import settings

import bcrypt


# ─── Senha ────────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Gera o hash bcrypt de uma senha em texto puro."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara senha em texto puro com o hash salvo no banco."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


# ─── Usuário ──────────────────────────────────────────────────────────────────


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Busca um usuário pelo e-mail. Retorna None se não encontrar."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    """
    Cria um novo usuário no banco.
    A senha é hasheada antes de salvar — nunca armazenamos texto puro.
    """
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()  # envia ao banco mas não comita — o commit fica no get_db()
    await db.refresh(user)  # atualiza o objeto com id e timestamps gerados pelo banco
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """
    Valida e-mail e senha.
    Retorna o usuário se válido, None caso contrário.
    Nunca informa se foi o e-mail ou a senha que errou — isso é intencional.
    """
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ─── JWT ──────────────────────────────────────────────────────────────────────


def create_access_token(user_id: int, role: str) -> str:
    """Gera um JWT de curta duração para autenticar requisições."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: int, role: str) -> str:
    """Gera um JWT de longa duração usado apenas para renovar o access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str) -> TokenData:
    """
    Decodifica e valida um JWT.
    Lança JWTError se o token for inválido, expirado ou do tipo errado.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    user_id: str | None = payload.get("sub")
    role: str | None = payload.get("role")
    token_type: str | None = payload.get("type")

    if not user_id or not role or token_type != expected_type:
        raise JWTError("Token inválido.")

    return TokenData(user_id=int(user_id), role=role)
