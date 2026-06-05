from decimal import Decimal

from pydantic import BaseModel, Field


# ─── Category ─────────────────────────────────────────────────────────────────


class CategoryCreate(BaseModel):
    """Dados para criar uma nova categoria."""

    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class CategoryOut(BaseModel):
    """Dados de categoria retornados pela API."""

    id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}


# ─── Product ──────────────────────────────────────────────────────────────────


class ProductCreate(BaseModel):
    """Dados para criar um novo produto."""

    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(gt=0, decimal_places=2)
    stock: int = Field(ge=0, default=0)
    category_id: int | None = None


class ProductUpdate(BaseModel):
    """
    Dados para atualizar um produto.
    Todos os campos são opcionais — só atualiza o que for enviado.
    """

    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    category_id: int | None = None


class ProductOut(BaseModel):
    """Dados de produto retornados pela API."""

    id: int
    name: str
    description: str | None
    price: Decimal
    stock: int
    is_active: bool
    category: CategoryOut | None

    model_config = {"from_attributes": True}


class ProductListOut(BaseModel):
    """Resposta paginada de listagem de produtos."""

    total: int
    page: int
    page_size: int
    items: list[ProductOut]
