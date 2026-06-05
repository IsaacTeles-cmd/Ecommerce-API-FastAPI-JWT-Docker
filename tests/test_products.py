import pytest


@pytest.fixture
async def category(client, auth_headers):
    """Cria uma categoria de teste e retorna seus dados."""
    response = await client.post(
        "/categories",
        json={"name": "Eletrônicos", "description": "Smartphones e notebooks"},
        headers=auth_headers,
    )
    return response.json()


@pytest.fixture
async def product(client, auth_headers, category):
    """Cria um produto de teste e retorna seus dados."""
    response = await client.post(
        "/products",
        json={
            "name": "iPhone 15",
            "description": "Smartphone Apple 128GB",
            "price": "999.99",
            "stock": 10,
            "category_id": category["id"],
        },
        headers=auth_headers,
    )
    return response.json()


class TestCategories:
    """Testes dos endpoints de categorias."""

    async def test_create_category_success(self, client, auth_headers):
        """Admin deve criar categoria com sucesso."""
        response = await client.post(
            "/categories",
            json={"name": "Roupas", "description": "Camisetas e calças"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Roupas"
        assert data["id"] is not None

    async def test_create_category_duplicate(self, client, auth_headers):
        """Deve rejeitar categoria com nome duplicado com 409."""
        payload = {"name": "Duplicada"}
        await client.post("/categories", json=payload, headers=auth_headers)
        response = await client.post("/categories", json=payload, headers=auth_headers)

        assert response.status_code == 409

    async def test_create_category_forbidden_for_customer(
        self, client, customer_headers
    ):
        """Customer não deve conseguir criar categoria."""
        response = await client.post(
            "/categories",
            json={"name": "Proibida"},
            headers=customer_headers,
        )

        assert response.status_code == 403

    async def test_list_categories(self, client, category):
        """Deve listar categorias sem autenticação."""
        response = await client.get("/categories")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(c["name"] == "Eletrônicos" for c in data)


class TestProducts:
    """Testes dos endpoints de produtos."""

    async def test_create_product_success(self, client, auth_headers, category):
        """Admin deve criar produto com sucesso."""
        response = await client.post(
            "/products",
            json={
                "name": "Notebook Dell",
                "description": "Intel i7 16GB",
                "price": "3499.90",
                "stock": 5,
                "category_id": category["id"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Notebook Dell"
        assert data["price"] == "3499.90"
        assert data["stock"] == 5
        assert data["is_active"] is True
        assert data["category"]["name"] == "Eletrônicos"

    async def test_create_product_forbidden_for_customer(
        self, client, customer_headers, category
    ):
        """Customer não deve conseguir criar produto."""
        response = await client.post(
            "/products",
            json={
                "name": "Produto Proibido",
                "price": "99.99",
                "stock": 1,
            },
            headers=customer_headers,
        )

        assert response.status_code == 403

    async def test_create_product_invalid_category(self, client, auth_headers):
        """Deve rejeitar produto com categoria inexistente com 404."""
        response = await client.post(
            "/products",
            json={
                "name": "Produto Sem Categoria",
                "price": "99.99",
                "stock": 1,
                "category_id": 99999,
            },
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_list_products(self, client, product):
        """Deve listar produtos sem autenticação."""
        response = await client.get("/products")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["page"] == 1
        assert len(data["items"]) >= 1

    async def test_list_products_with_search(self, client, product):
        """Deve filtrar produtos pelo nome."""
        response = await client.get("/products?search=iPhone")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "iPhone 15"

    async def test_list_products_search_no_results(self, client, product):
        """Deve retornar lista vazia para busca sem resultados."""
        response = await client.get("/products?search=ProdutoInexistente")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_get_product_by_id(self, client, product):
        """Deve retornar produto pelo ID."""
        response = await client.get(f"/products/{product['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product["id"]
        assert data["name"] == "iPhone 15"

    async def test_get_product_not_found(self, client):
        """Deve retornar 404 para produto inexistente."""
        response = await client.get("/products/99999")

        assert response.status_code == 404

    async def test_update_product(self, client, auth_headers, product):
        """Admin deve atualizar produto parcialmente."""
        response = await client.patch(
            f"/products/{product['id']}",
            json={"price": "899.99", "stock": 8},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["price"] == "899.99"
        assert data["stock"] == 8
        assert data["name"] == "iPhone 15"  # nome não mudou

    async def test_delete_product_soft(self, client, auth_headers, product):
        """Soft delete deve remover produto da listagem."""
        delete_response = await client.delete(
            f"/products/{product['id']}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        # produto não aparece mais na listagem
        list_response = await client.get("/products")
        ids = [p["id"] for p in list_response.json()["items"]]
        assert product["id"] not in ids

    async def test_delete_product_not_found(self, client, auth_headers):
        """Deve retornar 404 ao deletar produto inexistente."""
        response = await client.delete(
            "/products/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404
