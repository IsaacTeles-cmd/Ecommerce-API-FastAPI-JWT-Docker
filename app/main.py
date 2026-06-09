from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.products.router import categories_router, router as products_router
from app.orders.router import router as orders_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Código antes do yield roda na inicialização.
    Código depois do yield roda no encerramento.
    """
    print(" Aplicação iniciando...")
    yield
    print(" Aplicação encerrando...")


app = FastAPI(
    title="E-commerce API",
    description="API REST para gerenciamento de produtos, pedidos e usuários.",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajuste para o domínio do seu frontend em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(products_router)
app.include_router(orders_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Verifica se a API está no ar."""
    return {"status": "ok"}
