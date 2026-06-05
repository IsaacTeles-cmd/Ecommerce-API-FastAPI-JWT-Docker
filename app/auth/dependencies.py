from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import decode_token, get_user_by_email
from app.database import get_db

# Extrai o token do header "Authorization: Bearer <token>"
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency principal de autenticação.
    Valida o JWT e retorna o usuário autenticado.
    Usada em qualquer endpoint que exija login.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_data = decode_token(credentials.credentials, expected_type="access")
    except JWTError:
        raise credentials_exception

    user = await get_user_by_email(db, email=None)  # busca por id abaixo
    # busca direta por id para não depender do email no token
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency para rotas exclusivas de administrador.
    Reutiliza get_current_user e adiciona verificação de role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )
    return current_user
