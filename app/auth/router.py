from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import RefreshTokenRequest, Token, UserCreate, UserOut
from app.auth.service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_user_by_email,
)
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova conta",
)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """
    Registra um novo usuário.
    - E-mail deve ser único
    - Senha deve ter ao menos 8 caracteres, uma maiúscula e um número
    """
    existing_user = await get_user_by_email(db, data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado.",
        )

    user = await create_user(db, data)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Autenticar e obter tokens JWT",
)
async def login(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Autentica o usuário e retorna access_token e refresh_token.
    - access_token expira em 30 minutos
    - refresh_token expira em 7 dias
    """
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, user.role)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Renovar access token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Recebe um refresh_token válido e retorna um novo par de tokens.
    Útil para manter o usuário logado sem pedir senha novamente.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_data = decode_token(data.refresh_token, expected_type="refresh")
    except JWTError:
        raise credentials_exception

    from sqlalchemy import select
    from app.auth.models import User

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    new_access_token = create_access_token(user.id, user.role)
    new_refresh_token = create_refresh_token(user.id, user.role)

    return Token(access_token=new_access_token, refresh_token=new_refresh_token)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Retornar dados do usuário autenticado",
)
async def me(
    current_user=Depends(get_current_user),
) -> UserOut:
    """
    Retorna os dados do usuário autenticado.
    Requer token válido no header Authorization.
    """
    return current_user
