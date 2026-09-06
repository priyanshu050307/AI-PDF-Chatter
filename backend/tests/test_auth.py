import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_user_signup_and_login_flow(client: AsyncClient):
    signup_payload = {
        "email": "testuser@example.com",
        "password": "Password123!",
        "full_name": "Test User"
    }

    # 1. Test Signup
    response = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "testuser@example.com"
    token = data["access_token"]

    # 2. Test Duplicate Signup Error
    duplicate_res = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert duplicate_res.status_code == 409
    assert duplicate_res.json()["error"]["code"] == "CONFLICT"

    # 3. Test Login
    login_payload = {
        "email": "testuser@example.com",
        "password": "Password123!"
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # 4. Test Invalid Login
    invalid_login = await client.post("/api/v1/auth/login", json={"email": "testuser@example.com", "password": "WrongPassword"})
    assert invalid_login.status_code == 401

    # 5. Test Protected Route (/api/v1/auth/me)
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "testuser@example.com"

    # 6. Test Unauthenticated Access
    unauth_res = await client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401
