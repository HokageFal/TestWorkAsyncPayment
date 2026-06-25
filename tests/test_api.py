import uuid

import pytest
from httpx import AsyncClient


async def test_post_payment_success(client: AsyncClient, payment_payload: dict, idempotency_key: str, api_key: str):
    resp = await client.post(
        "/api/v1/payments",
        json=payment_payload,
        headers={"X-API-Key": api_key, "Idempotency-Key": idempotency_key},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "id" in body
    assert body["status"] == "pending"
    assert body["currency"] == "RUB"


async def test_post_payment_idempotency(client: AsyncClient, payment_payload: dict, api_key: str):
    idem = str(uuid.uuid4())
    headers = {"X-API-Key": api_key, "Idempotency-Key": idem}
    r1 = await client.post("/api/v1/payments", json=payment_payload, headers=headers)
    r2 = await client.post("/api/v1/payments", json=payment_payload, headers=headers)
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["id"] == r2.json()["id"]


async def test_post_payment_missing_api_key(client: AsyncClient, payment_payload: dict, idempotency_key: str):
    resp = await client.post(
        "/api/v1/payments",
        json=payment_payload,
        headers={"Idempotency-Key": idempotency_key},
    )
    assert resp.status_code == 401


async def test_post_payment_wrong_api_key(client: AsyncClient, payment_payload: dict, idempotency_key: str):
    resp = await client.post(
        "/api/v1/payments",
        json=payment_payload,
        headers={"X-API-Key": "wrong", "Idempotency-Key": idempotency_key},
    )
    assert resp.status_code == 401


async def test_post_payment_missing_idempotency_key(client: AsyncClient, payment_payload: dict, api_key: str):
    resp = await client.post(
        "/api/v1/payments",
        json=payment_payload,
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 422


async def test_post_payment_invalid_amount(client: AsyncClient, api_key: str, idempotency_key: str):
    resp = await client.post(
        "/api/v1/payments",
        json={"amount": "0", "currency": "RUB", "webhook_url": "https://example.com/"},
        headers={"X-API-Key": api_key, "Idempotency-Key": idempotency_key},
    )
    assert resp.status_code == 422


async def test_get_payment_success(client: AsyncClient, payment_payload: dict, api_key: str):
    idem = str(uuid.uuid4())
    create_resp = await client.post(
        "/api/v1/payments",
        json=payment_payload,
        headers={"X-API-Key": api_key, "Idempotency-Key": idem},
    )
    assert create_resp.status_code == 202
    payment_id = create_resp.json()["id"]

    get_resp = await client.get(
        f"/api/v1/payments/{payment_id}",
        headers={"X-API-Key": api_key},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == payment_id


async def test_get_payment_not_found(client: AsyncClient, api_key: str):
    resp = await client.get(
        f"/api/v1/payments/{uuid.uuid4()}",
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 404


async def test_get_payment_missing_api_key(client: AsyncClient):
    resp = await client.get(f"/api/v1/payments/{uuid.uuid4()}")
    assert resp.status_code == 401
