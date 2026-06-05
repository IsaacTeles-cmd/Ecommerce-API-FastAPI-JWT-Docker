from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_current_admin, get_current_user
from app.auth.models import User
from app.database import get_db
from app.products.schemas import (
    CategoryCreate,
    CategoryOut,
    ProductCreate,
    ProductListOut,
    ProductOut,
    ProductUpdate,
)
from app.products.service import (
    create_category,
    create_product,
    delete_product,
    get_all_categories,
    get_product_by_id,
    get_products,
    update_product,
)

router = APIRouter(prefix="/products", tags=["Products"])
categories_router = APIRouter(prefix="/categories", tags=["Categories"])


# ─── Categories ───────────────────────────────────────────────────────────────


@categories_router.get(
    "",
    response_model=list[CategoryOut],
    summary="Listar todas as categorias",
)
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> list[CategoryOut]:
    return await get_all_categories(db)


@categories_router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova categoria (admin)",
)
async def create_new_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> CategoryOut:
    try:
        return await create_category(db, data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma categoria com esse nome.",
        )


# ─── Products ─────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=ProductListOut,
    summary="Listar produtos com paginação e filtros",
)
async def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    category_id: int | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> ProductListOut:
    products, total = await get_products(
        db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        search=search,
    )
    return ProductListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=products,
    )


@router.get(
    "/{product_id}",
    response_model=ProductOut,
    summary="Buscar produto por ID",
)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> ProductOut:
    product = await get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )
    return product


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo produto (admin)",
)
async def create_new_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> ProductOut:
    try:
        return await create_product(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    summary="Atualizar produto parcialmente (admin)",
)
async def update_existing_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> ProductOut:
    product = await get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )
    try:
        return await update_product(db, product, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover produto (admin)",
)
async def remove_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> None:
    product = await get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )
    await delete_product(db, product)
