import pytest


class TestRegister:
    """Testes do endpoint POST /auth/register"""

    async def test_register_success(self, client):
        """Deve criar um novo usuário com sucesso."""
        response = await client.post(
            "/auth/register",
            json={
                "email": "novo@test.com",
                "full_name": "Novo Usuário",
                "password": "Senha123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "novo@test.com"
        assert data["full_name"] == "Novo Usuário"
        assert data["role"] == "customer"
        assert data["is_active"] is True
        assert "hashed_password" not in data  # nunca expõe a senha

    async def test_register_duplicate_email(self, client):
        """Deve rejeitar e-mail já cadastrado com 409."""
        payload = {
            "email": "duplicado@test.com",
            "full_name": "Usuário",
            "password": "Senha123",
        }
        await client.post("/auth/register", json=payload)
        response = await client.post("/auth/register", json=payload)

        assert response.status_code == 409

    async def test_register_invalid_email(self, client):
        """Deve rejeitar e-mail inválido com 422."""
        response = await client.post(
            "/auth/register",
            json={
                "email": "nao-eh-um-email",
                "full_name": "Usuário",
                "password": "Senha123",
            },
        )

        assert response.status_code == 422

    async def test_register_weak_password(self, client):
        """Deve rejeitar senha sem maiúscula ou número com 422."""
        response = await client.post(
            "/auth/register",
            json={
                "email": "fraco@test.com",
                "full_name": "Usuário",
                "password": "senhafraca",  # sem maiúscula e sem número
            },
        )

        assert response.status_code == 422

    async def test_register_short_password(self, client):
        """Deve rejeitar senha com menos de 8 caracteres com 422."""
        response = await client.post(
            "/auth/register",
            json={
                "email": "curto@test.com",
                "full_name": "Usuário",
                "password": "Ab1",
            },
        )

        assert response.status_code == 422


class TestLogin:
    """Testes do endpoint POST /auth/login"""

    async def test_login_success(self, client):
        """Deve retornar access_token e refresh_token."""
        await client.post(
            "/auth/register",
            json={
                "email": "login@test.com",
                "full_name": "Usuário Login",
                "password": "Senha123",
            },
        )

        response = await client.post(
            "/auth/login",
            json={
                "email": "login@test.com",
                "full_name": "Usuário Login",
                "password": "Senha123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client):
        """Deve rejeitar senha incorreta com 401."""
        await client.post(
            "/auth/register",
            json={
                "email": "errado@test.com",
                "full_name": "Usuário",
                "password": "Senha123",
            },
        )

        response = await client.post(
            "/auth/login",
            json={
                "email": "errado@test.com",
                "full_name": "Usuário",
                "password": "SenhaErrada1",
            },
        )

        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client):
        """Deve rejeitar usuário inexistente com 401."""
        response = await client.post(
            "/auth/login",
            json={
                "email": "naoexiste@test.com",
                "full_name": "Usuário",
                "password": "Senha123",
            },
        )

        assert response.status_code == 401


class TestMe:
    """Testes do endpoint GET /auth/me"""

    async def test_me_success(self, client, customer_headers):
        """Deve retornar dados do usuário autenticado."""
        response = await client.get("/auth/me", headers=customer_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "customer@test.com"
        assert "hashed_password" not in data

    async def test_me_without_token(self, client):
        """Deve rejeitar requisição sem token com 401."""
        response = await client.get("/auth/me")

        assert response.status_code == 401

    async def test_me_invalid_token(self, client):
        """Deve rejeitar token inválido com 401."""
        response = await client.get(
            "/auth/me", headers={"Authorization": "Bearer token-invalido"}
        )

        assert response.status_code == 401


class TestRefresh:
    """Testes do endpoint POST /auth/refresh"""

    async def test_refresh_success(self, client):
        """Deve retornar novo par de tokens com refresh_token válido."""
        await client.post(
            "/auth/register",
            json={
                "email": "refresh@test.com",
                "full_name": "Usuário Refresh",
                "password": "Senha123",
            },
        )
        login = await client.post(
            "/auth/login",
            json={
                "email": "refresh@test.com",
                "full_name": "Usuário Refresh",
                "password": "Senha123",
            },
        )
        refresh_token = login.json()["refresh_token"]

        response = await client.post(
            "/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client):
        """Deve rejeitar refresh_token inválido com 401."""
        response = await client.post(
            "/auth/refresh", json={"refresh_token": "token-invalido"}
        )

        assert response.status_code == 401
