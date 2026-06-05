from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.products.models import Category, Product
from app.products.schemas import CategoryCreate, ProductCreate, ProductUpdate


# ─── Category ─────────────────────────────────────────────────────────────────


async def get_all_categories(db: AsyncSession) -> list[Category]:
    """Retorna todas as categorias cadastradas."""
    result = await db.execute(select(Category).order_by(Category.name))
    return list(result.scalars().all())


async def get_category_by_id(db: AsyncSession, category_id: int) -> Category | None:
    """Busca uma categoria pelo id."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    """Cria uma nova categoria."""
    category = Category(name=data.name, description=data.description)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


# ─── Product ──────────────────────────────────────────────────────────────────


async def get_products(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    category_id: int | None = None,
    search: str | None = None,
) -> tuple[list[Product], int]:
    """
    Retorna produtos paginados com filtros opcionais.
    Retorna uma tupla: (lista de produtos, total de registros).
    """
    query = (
        select(Product)
        .options(selectinload(Product.category))  # carrega categoria em uma só query
        .where(Product.is_active == True)  # noqa: E712 — só produtos ativos
    )

    # filtro por categoria
    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    # filtro por busca no nome ou descrição
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))

    # query de contagem para paginação
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # aplica paginação
    offset = (page - 1) * page_size
    query = query.order_by(Product.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_product_by_id(db: AsyncSession, product_id: int) -> Product | None:
    """Busca um produto pelo id, carregando sua categoria junto."""
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product_id)
    )
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, data: ProductCreate) -> Product:
    """
    Cria um novo produto.
    Valida se a categoria existe antes de salvar.
    """
    if data.category_id is not None:
        category = await get_category_by_id(db, data.category_id)
        if not category:
            raise ValueError(f"Categoria {data.category_id} não encontrada.")

    product = Product(
        name=data.name,
        description=data.description,
        price=data.price,
        stock=data.stock,
        category_id=data.category_id,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product, ["category"])
    return product


async def update_product(
    db: AsyncSession, product: Product, data: ProductUpdate
) -> Product:
    """
    Atualiza apenas os campos enviados — campos não enviados permanecem iguais.
    """
    update_data = data.model_dump(
        exclude_unset=True
    )  # só campos que vieram na requisição

    for field, value in update_data.items():
        setattr(product, field, value)

    await db.flush()
    await db.refresh(product, ["category"])
    return product


async def delete_product(db: AsyncSession, product: Product) -> None:
    """
    Soft delete — marca o produto como inativo em vez de deletar do banco.
    Preserva histórico e dados de pedidos relacionados.
    """
    product.is_active = False
    await db.flush()
