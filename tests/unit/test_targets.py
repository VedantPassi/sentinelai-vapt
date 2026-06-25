import pytest
from httpx import ASGITransport, AsyncClient

from conftest import unique_email
from main import app

AUTH = "/api/v1/auth"
TARGETS = "/api/v1/targets"


@pytest.fixture
async def auth_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(
            f"{AUTH}/register",
            json={"email": unique_email("tgt"), "password": "UnitPass1!", "org_name": "TargetOrg"},
        )
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


@pytest.mark.anyio
async def test_create_target(auth_client):
    resp = await auth_client.post(
        TARGETS,
        json={"name": "Example", "type": "web", "url": "https://example.com", "asset_criticality": 0.8},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Example"
    assert data["verified"] is False


@pytest.mark.anyio
async def test_list_targets(auth_client):
    await auth_client.post(
        TARGETS,
        json={"name": "T1", "type": "api", "url": "https://api.example.com"},
    )
    resp = await auth_client.get(TARGETS)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.anyio
async def test_get_target(auth_client):
    create = await auth_client.post(
        TARGETS,
        json={"name": "GetMe", "type": "network", "url": "192.168.1.0/24"},
    )
    target_id = create.json()["id"]
    resp = await auth_client.get(f"{TARGETS}/{target_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == target_id


@pytest.mark.anyio
async def test_update_target(auth_client):
    create = await auth_client.post(
        TARGETS,
        json={"name": "Old Name", "type": "web", "url": "https://example.com"},
    )
    target_id = create.json()["id"]
    resp = await auth_client.put(f"{TARGETS}/{target_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.anyio
async def test_delete_target(auth_client):
    create = await auth_client.post(
        TARGETS,
        json={"name": "DeleteMe", "type": "web", "url": "https://example.com"},
    )
    target_id = create.json()["id"]
    resp = await auth_client.delete(f"{TARGETS}/{target_id}")
    assert resp.status_code == 204
    get_resp = await auth_client.get(f"{TARGETS}/{target_id}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_target_org_isolation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c1:
        r1 = await c1.post(
            f"{AUTH}/register",
            json={"email": unique_email("org1"), "password": "Pass1234!", "org_name": "Org1"},
        )
        c1.headers["Authorization"] = f"Bearer {r1.json()['access_token']}"
        create = await c1.post(
            TARGETS,
            json={"name": "Org1 Target", "type": "web", "url": "https://org1.com"},
        )
        target_id = create.json()["id"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c2:
        r2 = await c2.post(
            f"{AUTH}/register",
            json={"email": unique_email("org2"), "password": "Pass1234!", "org_name": "Org2"},
        )
        c2.headers["Authorization"] = f"Bearer {r2.json()['access_token']}"
        resp = await c2.get(f"{TARGETS}/{target_id}")
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_unauthenticated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(TARGETS)
        assert resp.status_code == 401
