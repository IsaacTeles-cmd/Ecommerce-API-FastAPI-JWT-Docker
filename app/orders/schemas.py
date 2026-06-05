from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field

from app.products.schemas import ProductOut


# ─── Order Item ───────────────────────────────────────────────────────────────


class OrderItemCreate(BaseModel):
    """Um item dentro do pedido — produto e quantidade."""

    product_id: int
    quantity: int = Field(ge=1)


class OrderItemOut(BaseModel):
    """Item do pedido retornado pela API."""

    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    product: ProductOut

    model_config = {"from_attributes": True}


# ─── Order ────────────────────────────────────────────────────────────────────


class OrderCreate(BaseModel):
    """Dados para criar um novo pedido."""

    items: list[OrderItemCreate] = Field(min_length=1)


class OrderStatusUpdate(BaseModel):
    """Atualização de status do pedido — exclusivo para admin."""

    status: str = Field(pattern="^(pending|confirmed|shipped|delivered|cancelled)$")


class OrderOut(BaseModel):
    """Pedido completo retornado pela API."""

    id: int
    user_id: int
    status: str
    total: Decimal
    created_at: datetime
    items: list[OrderItemOut]

    model_config = {"from_attributes": True}


class OrderListOut(BaseModel):
    """Resposta paginada de listagem de pedidos."""

    total: int
    page: int
    page_size: int
    items: list[OrderOut]
