from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Dados necessários para criar um novo usuário."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(c.isupper() for c in value):
            raise ValueError("A senha deve conter ao menos uma letra maiuscúla.")
        if not any(c.isdigit() for c in value):
            raise ValueError("A senha deve conter ao menos um número.")
        return value


class UserOut(BaseModel):
    """Dados do usuário retornados pela API — nunca expôe a senha."""

    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """Tokens retornados após login bem-sucedido."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Dados extraídos do payload do JWT."""

    user_id: int
    role: str


class RefreshTokenRequest(BaseModel):
    """Corpo da requisição para renovar o access token."""

    refresh_token: str
