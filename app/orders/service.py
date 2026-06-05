from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.orders.models import Order, OrderItem
from app.orders.schemas import OrderCreate, OrderStatusUpdate
from app.products.models import Product


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def get_order_by_id(db: AsyncSession, order_id: int) -> Order | None:
    """Busca um pedido pelo id, carregando itens e produtos."""
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items)
            .selectinload(OrderItem.product)
            .selectinload(Product.category)
        )
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


# ─── Criação ──────────────────────────────────────────────────────────────────


async def create_order(db: AsyncSession, user_id: int, data: OrderCreate) -> Order:
    """
    Cria um pedido completo:
    1. Valida estoque de todos os produtos
    2. Calcula o total
    3. Decrementa o estoque
    4. Salva o pedido e os itens
    """
    # busca todos os produtos de uma vez — evita N queries
    product_ids = [item.product_id for item in data.items]
    result = await db.execute(
        select(Product).where(
            Product.id.in_(product_ids),
            Product.is_active == True,  # noqa: E712
        )
    )
    products = {p.id: p for p in result.scalars().all()}

    # valida cada item antes de criar qualquer coisa
    for item in data.items:
        product = products.get(item.product_id)

        if not product:
            raise ValueError(f"Produto {item.product_id} não encontrado ou inativo.")

        if product.stock < item.quantity:
            raise ValueError(
                f"Estoque insuficiente para '{product.name}'. "
                f"Disponível: {product.stock}, solicitado: {item.quantity}."
            )

    # tudo válido — cria o pedido e os itens
    total = Decimal("0")
    order_items = []

    for item in data.items:
        product = products[item.product_id]
        unit_price = Decimal(str(product.price))
        subtotal = unit_price * item.quantity

        total += subtotal

        # decrementa estoque
        product.stock -= item.quantity

        order_items.append(
            OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=unit_price,
            )
        )

    order = Order(
        user_id=user_id,
        total=total,
        items=order_items,
    )

    db.add(order)
    await db.flush()
    await db.refresh(order)

    # recarrega com todos os relacionamentos para a resposta
    return await get_order_by_id(db, order.id)


# ─── Listagem ─────────────────────────────────────────────────────────────────


async def get_user_orders(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[Order], int]:
    """Retorna pedidos paginados de um usuário específico."""
    query = (
        select(Order)
        .options(
            selectinload(Order.items)
            .selectinload(OrderItem.product)
            .selectinload(Product.category)
        )
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    return list(result.scalars().all()), total


async def get_all_orders(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[Order], int]:
    """Retorna todos os pedidos paginados — exclusivo para admin."""
    query = (
        select(Order)
        .options(
            selectinload(Order.items)
            .selectinload(OrderItem.product)
            .selectinload(Product.category)
        )
        .order_by(Order.created_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    return list(result.scalars().all()), total


# ─── Atualização ──────────────────────────────────────────────────────────────


async def update_order_status(
    db: AsyncSession, order: Order, data: OrderStatusUpdate
) -> Order:
    """
    Atualiza o status do pedido.
    Se cancelado, devolve o estoque de todos os itens.
    """
    if data.status == "cancelled" and order.status != "cancelled":
        # devolve estoque dos produtos
        product_ids = [item.product_id for item in order.items]
        result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products = {p.id: p for p in result.scalars().all()}

        for item in order.items:
            product = products.get(item.product_id)
            if product:
                product.stock += item.quantity

    order.status = data.status
    await db.flush()
    return await get_order_by_id(db, order.id)
