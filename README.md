# Ecommerce API

REST API for e-commerce applications built with FastAPI. Supports product management, order processing, and user authentication with JWT.

## Features

- JWT authentication with access and refresh tokens
- Role-based access control (admin and customer)
- Product catalog with categories, pagination, and search
- Order management with stock validation and status tracking
- Async database access with SQLAlchemy and PostgreSQL
- Database migrations with Alembic
- Containerized with Docker and Docker Compose

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL + SQLAlchemy (async) + AsyncPG |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Authentication | JWT (python-jose) + bcrypt |
| Testing | pytest + pytest-asyncio + httpx |
| Containerization | Docker + Docker Compose |

## Getting Started

### Prerequisites

- Docker and Docker Compose installed

### Running with Docker

```bash
git clone https://github.com/IsaacTeles-cmd/Ecommerce-API-FastAPI-JWT-Docker.git
cd ecommerce-api
cp .env.example .env
docker compose up --build
```

The API will be available at `http://localhost:8000`.  
Interactive documentation at `http://localhost:8000/docs`.

### Running locally

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Requires a running PostgreSQL instance and a configured `.env` file.

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ecommerce
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## API Endpoints

### Auth

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Create account |
| POST | `/auth/login` | No | Login and receive JWT |
| POST | `/auth/refresh` | Yes | Refresh access token |
| GET | `/auth/me` | Yes | Get current user data |

### Products

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/products` | No | List products (paginated) |
| GET | `/products/{id}` | No | Get product detail |
| POST | `/products` | Admin | Create product |
| PATCH | `/products/{id}` | Admin | Update product |
| DELETE | `/products/{id}` | Admin | Soft delete product |
| GET | `/categories` | No | List categories |
| POST | `/categories` | Admin | Create category |

### Orders

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/orders` | Yes | Create order |
| GET | `/orders/me` | Yes | List my orders |
| GET | `/orders/{id}` | Yes | Get order detail |
| GET | `/orders/admin` | Admin | List all orders |
| PATCH | `/orders/{id}/status` | Admin | Update order status |

## Running Tests

```bash
pytest tests/ -v
```

Tests use an in-memory SQLite database and do not require a running PostgreSQL instance.

## Project Structure

```
ecommerce-api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── auth/
│   ├── products/
│   └── orders/
├── tests/
├── alembic/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## License

MIT