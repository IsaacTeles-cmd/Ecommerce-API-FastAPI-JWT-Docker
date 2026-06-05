import pytest


@pytest.fixture
async def category(client, auth_headers):
    response = await client.post(
        "/categories",
        json={"name": "Eletrônicos", "description": "Smartphones e notebooks"},
        headers=auth_headers,
    )
    return response.json()


@pytest.fixture
async def product_a(client, auth_headers, category):
    response = await client.post(
        "/products",
        json={
            "name": "iPhone 15",
            "price": "999.99",
            "stock": 10,
            "category_id": category["id"],
        },
        headers=auth_headers,
    )
    return response.json()


@pytest.fixture
async def product_b(client, auth_headers, category):
    response = await client.post(
        "/products",
        json={
            "name": "Notebook Dell",
            "price": "3499.90",
            "stock": 5,
            "category_id": category["id"],
        },
        headers=auth_headers,
    )
    return response.json()


class TestCreateOrder:
    """Testes do endpoint POST /orders"""

    async def test_create_order_success(
        self, client, customer_headers, product_a, product_b
    ):
        """Deve criar pedido com múltiplos itens e calcular total correto."""
        response = await client.post(
            "/orders",
            json={
                "items": [
                    {"product_id": product_a["id"], "quantity": 2},
                    {"product_id": product_b["id"], "quantity": 1},
                ]
            },
            headers=customer_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert len(data["items"]) == 2

        # total = (999.99 * 2) + (3499.90 * 1) = 5499.88
        assert float(data["total"]) == pytest.approx(5499.88, rel=1e-2)

    async def test_create_order_decrements_stock(
        self, client, customer_headers, auth_headers, product_a
    ):
        """Criar pedido deve decrementar o estoque do produto."""
        stock_before = product_a["stock"]

        await client.post(
            "/orders",
            json={"items": [{"product_id": product_a["id"], "quantity": 3}]},
            headers=customer_headers,
        )

        product_response = await client.get(f"/products/{product_a['id']}")
        stock_after = product_response.json()["stock"]

        assert stock_after == stock_before - 3

    async def test_create_order_insufficient_stock(
        self, client, customer_headers, product_a
    ):
        """Deve rejeitar pedido com estoque insuficiente com 400."""
        response = await client.post(
            "/orders",
            json={"items": [{"product_id": product_a["id"], "quantity": 999}]},
            headers=customer_headers,
        )

        assert response.status_code == 400
        assert "Estoque insuficiente" in response.json()["detail"]

    async def test_create_order_nonexistent_product(self, client, customer_headers):
        """Deve rejeitar pedido com produto inexistente com 400."""
        response = await client.post(
            "/orders",
            json={"items": [{"product_id": 99999, "quantity": 1}]},
            headers=customer_headers,
        )

        assert response.status_code == 400

    async def test_create_order_empty_items(self, client, customer_headers):
        """Deve rejeitar pedido sem itens com 422."""
        response = await client.post(
            "/orders",
            json={"items": []},
            headers=customer_headers,
        )

        assert response.status_code == 422

    async def test_create_order_requires_auth(self, client, product_a):
        """Deve rejeitar pedido sem autenticação com 401."""
        response = await client.post(
            "/orders",
            json={"items": [{"product_id": product_a["id"], "quantity": 1}]},
        )

        assert response.status_code == 401


class TestListOrders:
    """Testes dos endpoints de listagem de pedidos."""

    async def test_list_my_orders(self, client, customer_headers, product_a):
        """Deve retornar apenas os pedidos do usuário autenticado."""
        await client.post(
            "/orders",
            json={"items": [{"product_id": product_a["id"], "quantity": 1}]},
            headers=customer_headers,
        )

        response = await client.get("/orders/me", headers=customer_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_list_admin_orders(
        self, client, auth_headers, customer_headers, product_a
    ):
        """Admin deve ver todos os pedidos do sistema."""
        await client.post(
            "/orders",
            json={"items": [{"product_id": product_a["id"], "quantity": 1}]},
            headers=customer_headers,
        )

        response = await client.get("/orders/admin", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["total"] >= 1

    async def test_list_admin_orders_forbidden_for_customer(
        self, client, customer_headers
    ):
        """Customer não deve acessar listagem admin."""
        response = await client.get("/orders/admin", headers=customer_headers)

        assert response.status_code == 403


class TestGetOrder:
    """Testes do endpoint GET /orders/{id}"""

    async def test_get_own_order(self, client, customer_headers, product_a):
        """Usuário deve conseguir ver seu próprio pedido."""
        order = (
            await client.post(
                "/orders",
                json={"items": [{"product_id": product_a["id"], "quantity": 1}]},
                headers=customer_headers,
            )
        ).json()

        response = await client.get(f"/orders/{order['id']}", headers=customer_headers)

        assert response.status_code == 200
        assert response.json()["id"] == order["id"]

    async def test_get_other_user_order_forbidden(
        self, client, customer_headers, auth_headers, product_a
    ):
        """Usuário não deve ver pedido de outro usuário."""
        # admin cria um pedido
        order = (
            await client.post(
                "/orders",
                json={"items": [{"product_id": product_a["id"], "quantity": 1}]},
                headers=auth_headers,
            )
        ).json()

        # customer tenta acessar o pedido do admin
        response = await client.get(f"/orders/{order['id']}", headers=customer_headers)

        assert response.status_code == 403

    async def test_get_order_not_found(self, client, customer_headers):
        """Deve retornar 404 para pedido inexistente."""
        response = await client.get("/orders/99999", headers=customer_headers)

        assert response.status_code == 404


class TestUpdateOrderStatus:
    """Testes do endpoint PATCH /orders/{id}/status"""

    async def test_update_status_success(
        self, client, auth_headers, customer_headers, product_a
    ):
        """Admin deve atualizar status do pedido."""
        order = (
            await client.post(
                "/orders",
                json={"items": [{"product_id": product_a["id"], "quantity": 1}]},
                headers=customer_headers,
            )
        ).json()

        response = await client.patch(
            f"/orders/{order['id']}/status",
            json={"status": "confirmed"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    async def test_cancel_order_restores_stock(
        self, client, auth_headers, customer_headers, product_a
    ):
        """Cancelar pedido deve restaurar o estoque."""
        stock_before = product_a["stock"]

        order = (
            await client.post(
                "/orders",
                json={"items": [{"product_id": product_a["id"], "quantity": 2}]},
                headers=customer_headers,
            )
        ).json()

        # confirma que o estoque diminuiu
        stock_after_order = (await client.get(f"/products/{product_a['id']}")).json()[
            "stock"
        ]
        assert stock_after_order == stock_before - 2

        # cancela o pedido
        await client.patch(
            f"/orders/{order['id']}/status",
            json={"status": "cancelled"},
            headers=auth_headers,
        )

        # confirma que o estoque voltou
        stock_after_cancel = (await client.get(f"/products/{product_a['id']}")).json()[
            "stock"
        ]
        assert stock_after_cancel == stock_before

    async def test_update_status_invalid(
        self, client, auth_headers, customer_headers, product_a
    ):
        """Deve rejeitar status inválido com 422."""
        order = (
            await client.post(
                "/orders",
                json={"items": [{"product_id": product_a["id"], "quantity": 1}]},
                headers=customer_headers,
            )
        ).json()

        response = await client.patch(
            f"/orders/{order['id']}/status",
            json={"status": "invalido"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    async def test_update_status_forbidden_for_customer(
        self, client, customer_headers, product_a
    ):
        """Customer não deve atualizar status de pedido."""
        order = (
            await client.post(
                "/orders",
                json={"items": [{"product_id": product_a["id"], "quantity": 1}]},
                headers=customer_headers,
            )
        ).json()

        response = await client.patch(
            f"/orders/{order['id']}/status",
            json={"status": "confirmed"},
            headers=customer_headers,
        )

        assert response.status_code == 403
