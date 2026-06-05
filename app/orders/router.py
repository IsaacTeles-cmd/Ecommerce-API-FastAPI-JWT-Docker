from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin, get_current_user
from app.auth.models import User
from app.database import get_db
from app.orders.schemas import OrderCreate, OrderListOut, OrderOut, OrderStatusUpdate
from app.orders.service import (
    create_order,
    get_all_orders,
    get_order_by_id,
    get_user_orders,
    update_order_status,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo pedido",
)
async def create_new_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderOut:
    """
    Cria um pedido para o usuário autenticado.
    - Valida estoque de todos os produtos antes de confirmar
    - Decrementa estoque automaticamente
    - Calcula o total com os preços do momento da compra
    """
    try:
        return await create_order(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/me",
    response_model=OrderListOut,
    summary="Listar meus pedidos",
)
async def list_my_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderListOut:
    """Retorna os pedidos do usuário autenticado com paginação."""
    orders, total = await get_user_orders(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return OrderListOut(total=total, page=page, page_size=page_size, items=orders)


@router.get(
    "/admin",
    response_model=OrderListOut,
    summary="Listar todos os pedidos (admin)",
)
async def list_all_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> OrderListOut:
    """Retorna todos os pedidos do sistema — exclusivo para admin."""
    orders, total = await get_all_orders(db, page=page, page_size=page_size)
    return OrderListOut(total=total, page=page, page_size=page_size, items=orders)


@router.get(
    "/{order_id}",
    response_model=OrderOut,
    summary="Buscar pedido por ID",
)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderOut:
    """
    Retorna um pedido pelo ID.
    - Usuário comum só acessa seus próprios pedidos
    - Admin acessa qualquer pedido
    """
    order = await get_order_by_id(db, order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado.",
        )

    # usuário comum só pode ver seus próprios pedidos
    if current_user.role != "admin" and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado.",
        )

    return order


@router.patch(
    "/{order_id}/status",
    response_model=OrderOut,
    summary="Atualizar status do pedido (admin)",
)
async def update_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> OrderOut:
    """
    Atualiza o status de um pedido.
    - Se cancelado, devolve o estoque automaticamente
    """
    order = await get_order_by_id(db, order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado.",
        )

    return await update_order_status(db, order, data)
