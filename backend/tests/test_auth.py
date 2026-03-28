import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantConfig
from app.models.user import User
from app.utils.security import hash_password, verify_password, create_access_token, decode_token


@pytest.mark.asyncio
async def test_hash_and_verify_password():
    hashed = hash_password("MySecret123!")
    assert verify_password("MySecret123!", hashed)
    assert not verify_password("WrongPassword", hashed)


@pytest.mark.asyncio
async def test_create_and_decode_access_token():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = create_access_token(user_id, tenant_id, "agent")
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["role"] == "agent"
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, slug="test-co", name="Test Co", subdomain="test.tickets.com")
    db_session.add(tenant)
    db_session.add(TenantConfig(tenant_id=tenant_id))

    user = User(
        tenant_id=tenant_id,
        email="test@test.com",
        full_name="Test User",
        password_hash=hash_password("Pass123!"),
        role="agent",
    )
    db_session.add(user)
    await db_session.flush()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@test.com", "password": "Pass123!", "tenant_slug": "test-co"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, slug="test-co-2", name="Test Co 2", subdomain="test2.tickets.com")
    db_session.add(tenant)
    db_session.add(TenantConfig(tenant_id=tenant_id))

    user = User(
        tenant_id=tenant_id,
        email="user2@test.com",
        full_name="User 2",
        password_hash=hash_password("RightPass!"),
        role="requester",
    )
    db_session.add(user)
    await db_session.flush()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user2@test.com", "password": "WrongPass", "tenant_slug": "test-co-2"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, db_session: AsyncSession):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, slug="test-co-3", name="Test Co 3", subdomain="test3.tickets.com")
    db_session.add(tenant)
    db_session.add(TenantConfig(tenant_id=tenant_id))

    user = User(
        tenant_id=tenant_id,
        email="me@test.com",
        full_name="Me User",
        password_hash=hash_password("Pass123!"),
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(user.id, tenant_id, "admin")
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["role"] == "admin"
