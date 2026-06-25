import pytest
from httpx import ASGITransport, AsyncClient

from conftest import unique_email
from main import app

BASE = "/api/v1/auth"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_register_success(client):
    resp = await client.post(
        f"{BASE}/register",
        json={"email": unique_email("reg"), "password": "UnitPass1!", "org_name": "UnitOrg"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_register_duplicate_email(client):
    email = unique_email("dup")
    payload = {"email": email, "password": "UnitPass1!", "org_name": "Org"}
    await client.post(f"{BASE}/register", json=payload)
    resp = await client.post(f"{BASE}/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


@pytest.mark.anyio
async def test_login_success(client):
    email = unique_email("login")
    await client.post(
        f"{BASE}/register",
        json={"email": email, "password": "UnitPass1!", "org_name": "Org"},
    )
    resp = await client.post(
        f"{BASE}/login",
        json={"email": email, "password": "UnitPass1!"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.anyio
async def test_login_wrong_password(client):
    email = unique_email("badpw")
    await client.post(
        f"{BASE}/register",
        json={"email": email, "password": "UnitPass1!", "org_name": "Org"},
    )
    resp = await client.post(
        f"{BASE}/login",
        json={"email": email, "password": "WrongPass!"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_unknown_email(client):
    resp = await client.post(
        f"{BASE}/login",
        json={"email": unique_email("ghost"), "password": "Whatever1!"},
    )
    assert resp.status_code == 401
